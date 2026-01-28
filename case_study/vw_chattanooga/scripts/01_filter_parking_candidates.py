"""
Step 1: Filter parking lot candidates for VW Chattanooga P&R analysis
Excludes lots too close to the plant and those without transit access
"""

import sys
sys.path.append('case_study/vw_chattanooga/scripts')

from config import *
from sqlalchemy import create_engine, text
import pandas as pd
import geopandas as gpd

print("="*80)
print("VW CHATTANOOGA P&R CASE STUDY")
print("Step 1: Parking Lot Candidate Filtering")
print("="*80)

engine = create_engine(DB_CONNECTION)

# ============================================
# Create VW Plant location point
# ============================================
print(f"\n📍 VW Plant Location: {VW_PLANT['name']}")
print(f"   Coordinates: ({VW_PLANT['latitude']}, {VW_PLANT['longitude']})")

sql_create_vw_point = f"""
-- Drop if exists
DROP TABLE IF EXISTS vw_plant_location CASCADE;

-- Create VW plant point
CREATE TABLE vw_plant_location AS
SELECT 
    '{VW_PLANT['name']}'::TEXT as name,
    {VW_PLANT['latitude']}::FLOAT as latitude,
    {VW_PLANT['longitude']}::FLOAT as longitude,
    ST_Transform(
        ST_SetSRID(
            ST_MakePoint({VW_PLANT['longitude']}, {VW_PLANT['latitude']}),
            {CRS_WGS84}
        ),
        {CRS_UTM}
    ) as geometry;

-- Create exclusion zone (buffer around VW plant)
DROP TABLE IF EXISTS vw_exclusion_zone CASCADE;

CREATE TABLE vw_exclusion_zone AS
SELECT 
    'VW Plant Exclusion Zone'::TEXT as name,
    {EXCLUSION_RADIUS_METERS}::INT as radius_meters,
    ST_Buffer(geometry, {EXCLUSION_RADIUS_METERS}) as geometry
FROM vw_plant_location;

SELECT 'VW plant location and exclusion zone created' as status;
"""

with engine.connect() as conn:
    conn.execute(text(sql_create_vw_point))
    conn.commit()
    print(f"✓ Created VW plant point")
    print(f"✓ Created {EXCLUSION_RADIUS_METERS}m exclusion zone")

# ============================================
# Calculate distances to VW plant
# ============================================
print("\n📏 Calculating distances from parking lots to VW plant...")

sql_distances = """
-- Add distance column to parking lots
ALTER TABLE parking_lots 
DROP COLUMN IF EXISTS distance_to_vw_m;

ALTER TABLE parking_lots 
ADD COLUMN distance_to_vw_m FLOAT;

-- Calculate distances
UPDATE parking_lots pl
SET distance_to_vw_m = ST_Distance(
    pl.geometry,
    (SELECT geometry FROM vw_plant_location)
);

-- Add categorization
ALTER TABLE parking_lots 
DROP COLUMN IF EXISTS vw_distance_category;

ALTER TABLE parking_lots 
ADD COLUMN vw_distance_category TEXT;

UPDATE parking_lots
SET vw_distance_category = 
    CASE 
        WHEN distance_to_vw_m < 5000 THEN 'Too Close - Excluded'
        WHEN distance_to_vw_m >= 5000 AND distance_to_vw_m < 8000 THEN 'Near - Marginal'
        WHEN distance_to_vw_m >= 8000 AND distance_to_vw_m <= 15000 THEN 'Optimal Distance'
        WHEN distance_to_vw_m > 15000 AND distance_to_vw_m <= 25000 THEN 'Far - Acceptable'
        ELSE 'Very Far - Questionable'
    END;

-- Summary statistics
SELECT 
    vw_distance_category,
    COUNT(*) as num_lots,
    MIN(distance_to_vw_m)::INT as min_dist_m,
    AVG(distance_to_vw_m)::INT as avg_dist_m,
    MAX(distance_to_vw_m)::INT as max_dist_m
FROM parking_lots
GROUP BY vw_distance_category
ORDER BY MIN(distance_to_vw_m);
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_distances))
    conn.commit()
    
    print("\n📊 Distance Distribution:")
    df_dist = pd.DataFrame(result.fetchall(), 
                           columns=['Category', 'Count', 'Min (m)', 'Avg (m)', 'Max (m)'])
    print(df_dist.to_string(index=False))

# ============================================
# Filter parking candidates
# ============================================
print("\n🔍 Filtering parking lot candidates...")

sql_filter = """
-- Create table of eligible parking candidates
DROP TABLE IF EXISTS vw_parking_candidates CASCADE;

CREATE TABLE vw_parking_candidates AS
SELECT 
    pl.parking_id,
    pl.name,
    pl.capacity,
    pl.type,
    pl.geometry,
    pl.distance_to_vw_m,
    pl.vw_distance_category,
    
    -- Check if excluded
    CASE 
        WHEN pl.distance_to_vw_m < 5000 THEN FALSE
        ELSE TRUE
    END as is_candidate,
    
    -- Reason for inclusion/exclusion
    CASE 
        WHEN pl.distance_to_vw_m < 5000 THEN 'Excluded: Within ' || 5000 || 'm of VW plant'
        ELSE 'Eligible: Beyond exclusion zone'
    END as candidate_status

FROM parking_lots pl;

-- Summary
SELECT 
    is_candidate,
    COUNT(*) as num_lots,
    SUM(capacity) as total_capacity
FROM vw_parking_candidates
GROUP BY is_candidate;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_filter))
    conn.commit()
    
    print("\n📋 Candidate Summary:")
    df_candidates = pd.DataFrame(result.fetchall(),
                                 columns=['Is Candidate', 'Count', 'Total Capacity'])
    print(df_candidates.to_string(index=False))

# ============================================
# Multi-scenario transit accessibility
# ============================================
print("\n🚏 Analyzing transit accessibility under multiple walking scenarios...")

for scenario_name, distance in WALKING_SCENARIOS.items():
    print(f"\n   Scenario: {scenario_name.upper()} ({distance}m walking distance)")
    
    sql_transit = f"""
    -- Create transit accessibility table for {scenario_name} scenario
    DROP TABLE IF EXISTS vw_transit_access_{scenario_name} CASCADE;
    
    CREATE TABLE vw_transit_access_{scenario_name} AS
    SELECT 
        pc.parking_id,
        pc.name,
        pc.distance_to_vw_m,
        
        -- Transit stops within walking distance
        COUNT(DISTINCT ts.stop_id) as num_stops_{distance}m,
        
        -- Total daily trips
        SUM(COALESCE(sf.daily_trips, 0))::INT as total_daily_trips,
        
        -- Number of unique routes
        COUNT(DISTINCT sf.num_routes) as num_routes,
        
        -- Average distance to stops
        AVG(ST_Distance(pc.geometry, ts.geometry))::INT as avg_walk_distance_m,
        
        -- Nearest stop distance
        MIN(ST_Distance(pc.geometry, ts.geometry))::INT as nearest_stop_distance_m,
        
        -- Has transit access flag
        CASE 
            WHEN COUNT(DISTINCT ts.stop_id) >= {MIN_TRANSIT_STOPS} 
            AND SUM(COALESCE(sf.daily_trips, 0)) >= {MIN_DAILY_TRIPS}
            THEN TRUE
            ELSE FALSE
        END as has_adequate_transit
        
    FROM vw_parking_candidates pc
    LEFT JOIN transit_stops ts 
        ON ST_DWithin(pc.geometry, ts.geometry, {distance})
    LEFT JOIN stop_frequency sf 
        ON ts.stop_id = sf.stop_id
    WHERE pc.is_candidate = TRUE
    GROUP BY pc.parking_id, pc.name, pc.distance_to_vw_m;
    
    -- Summary for this scenario
    SELECT 
        has_adequate_transit,
        COUNT(*) as num_lots,
        AVG(num_stops_{distance}m)::NUMERIC(5,1) as avg_stops,
        AVG(total_daily_trips)::INT as avg_trips,
        AVG(nearest_stop_distance_m)::INT as avg_nearest_stop_m
    FROM vw_transit_access_{scenario_name}
    GROUP BY has_adequate_transit;
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql_transit))
        conn.commit()
        
        df_scenario = pd.DataFrame(result.fetchall(),
                                   columns=['Has Transit', 'Count', 'Avg Stops', 
                                           'Avg Trips/Day', 'Avg Nearest Stop (m)'])
        print(f"\n   Results:")
        print(df_scenario.to_string(index=False))

# ============================================
# Export summary
# ============================================
print("\n💾 Exporting filtered candidates...")

# Export eligible candidates with all scenarios
sql_export = """
SELECT 
    pc.parking_id,
    pc.name,
    pc.capacity,
    pc.type,
    pc.distance_to_vw_m,
    pc.vw_distance_category,
    
    -- Conservative scenario (500m)
    t500.num_stops_500m,
    t500.total_daily_trips as trips_500m,
    t500.nearest_stop_distance_m as nearest_stop_500m,
    t500.has_adequate_transit as transit_ok_500m,
    
    -- Moderate scenario (800m)
    t800.num_stops_800m,
    t800.total_daily_trips as trips_800m,
    t800.nearest_stop_distance_m as nearest_stop_800m,
    t800.has_adequate_transit as transit_ok_800m,
    
    -- Extended scenario (1000m)
    t1000.num_stops_1000m,
    t1000.total_daily_trips as trips_1000m,
    t1000.nearest_stop_distance_m as nearest_stop_1000m,
    t1000.has_adequate_transit as transit_ok_1000m

FROM vw_parking_candidates pc
LEFT JOIN vw_transit_access_conservative t500 USING (parking_id)
LEFT JOIN vw_transit_access_moderate t800 USING (parking_id)
LEFT JOIN vw_transit_access_extended t1000 USING (parking_id)
WHERE pc.is_candidate = TRUE
ORDER BY pc.distance_to_vw_m
"""

df_export = pd.read_sql(sql_export, engine)
output_path = f"{RESULTS_DIR}/parking_candidates_filtered.csv"
df_export.to_csv(output_path, index=False)

print(f"✓ Exported {len(df_export)} candidates to:")
print(f"  {output_path}")

print("\n" + "="*80)
print("✅ STEP 1 COMPLETE: Parking Lot Filtering")
print("="*80)
print(f"\nNext: Run 02_calculate_accessibility_scores.py")