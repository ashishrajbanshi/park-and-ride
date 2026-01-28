from sqlalchemy import create_engine, text
import pandas as pd

DB_CONNECTION = "postgresql://postgres:qrakken@localhost:5432/chattanooga_parkride"
engine = create_engine(DB_CONNECTION)

print("🔍 STARTING SPATIAL ANALYSIS\n")

# ============================================
# STEP 1: Create Catchment Buffers
# ============================================
print("📍 Creating catchment buffers around parking lots...")

sql_catchments = """
DROP TABLE IF EXISTS parking_catchments CASCADE;

CREATE TABLE parking_catchments AS
SELECT 
    parking_id,
    name,
    capacity,
    type,
    geometry as point_geom,
    ST_Buffer(geometry, 400) as walk_400m,
    ST_Buffer(geometry, 800) as walk_800m,
    ST_Buffer(geometry, 1600) as walk_1600m,
    ST_Buffer(geometry, 3000) as drive_3km,
    ST_Buffer(geometry, 5000) as drive_5km,
    ST_Buffer(geometry, 8000) as drive_8km
FROM parking_lots;

CREATE INDEX idx_parking_catch_400 ON parking_catchments USING GIST(walk_400m);
CREATE INDEX idx_parking_catch_800 ON parking_catchments USING GIST(walk_800m);
CREATE INDEX idx_parking_catch_3km ON parking_catchments USING GIST(drive_3km);
CREATE INDEX idx_parking_catch_5km ON parking_catchments USING GIST(drive_5km);

SELECT COUNT(*) as catchments_created FROM parking_catchments;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_catchments))
    conn.commit()
    count = result.fetchone()[0]
    print(f"✓ Created {count} catchment zones\n")

# ============================================
# STEP 2: Find Transit Stops Near Parking
# ============================================
print("🚏 Identifying transit stops near parking lots...")

sql_transit_proximity = """
DROP TABLE IF EXISTS parking_transit_access CASCADE;

CREATE TABLE parking_transit_access AS
SELECT 
    pc.parking_id,
    pc.name as parking_name,
    ts.stop_id,
    ts.stop_name,
    sf.daily_trips,
    sf.num_routes,
    ST_Distance(pc.point_geom, ts.geometry) as distance_meters,
    CASE 
        WHEN ST_Distance(pc.point_geom, ts.geometry) <= 200 THEN 'Excellent'
        WHEN ST_Distance(pc.point_geom, ts.geometry) <= 400 THEN 'Good'
        WHEN ST_Distance(pc.point_geom, ts.geometry) <= 800 THEN 'Fair'
        ELSE 'Poor'
    END as access_quality
FROM parking_catchments pc
CROSS JOIN transit_stops ts
LEFT JOIN stop_frequency sf ON ts.stop_id = sf.stop_id
WHERE ST_DWithin(pc.point_geom, ts.geometry, 800)  -- Within 800m (half mile)
ORDER BY pc.parking_id, distance_meters;

SELECT 
    COUNT(DISTINCT parking_id) as parking_with_transit,
    COUNT(DISTINCT stop_id) as unique_stops,
    AVG(distance_meters)::INT as avg_distance_m
FROM parking_transit_access;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_transit_proximity))
    conn.commit()
    stats = result.fetchone()
    print(f"✓ {stats[0]} parking lots have nearby transit")
    print(f"✓ {stats[1]} unique transit stops identified")
    print(f"✓ Average distance: {stats[2]}m\n")

# ============================================
# STEP 3: Calculate Population Coverage
# ============================================
print("👥 Calculating population within catchments...")

sql_population_coverage = """
DROP TABLE IF EXISTS catchment_demographics CASCADE;

CREATE TABLE catchment_demographics AS
SELECT 
    pc.parking_id,
    pc.name,
    pc.capacity,
    
    -- Population coverage at different radii
    SUM(CASE WHEN ST_Intersects(cb.geometry, pc.walk_800m) 
        THEN cb.total_pop ELSE 0 END) as pop_walk_800m,
    SUM(CASE WHEN ST_Intersects(cb.geometry, pc.drive_3km) 
        THEN cb.total_pop ELSE 0 END) as pop_drive_3km,
    SUM(CASE WHEN ST_Intersects(cb.geometry, pc.drive_5km) 
        THEN cb.total_pop ELSE 0 END) as pop_drive_5km,
    
    -- Employment coverage
    SUM(CASE WHEN ST_Intersects(cb.geometry, pc.drive_5km) 
        THEN cb.employment ELSE 0 END) as employment_5km,
    
    -- Income indicators
    AVG(CASE WHEN ST_Intersects(cb.geometry, pc.drive_5km) 
        THEN NULLIF(cb.per_capita_income, 0) END) as avg_income_5km,
    
    -- Housing units
    SUM(CASE WHEN ST_Intersects(cb.geometry, pc.drive_5km) 
        THEN cb.housing_units ELSE 0 END) as housing_units_5km,
    
    -- Number of blocks served
    COUNT(DISTINCT CASE WHEN ST_Intersects(cb.geometry, pc.drive_5km) 
        THEN cb.geoid END) as blocks_served_5km
    
FROM parking_catchments pc
CROSS JOIN census_blocks cb
WHERE ST_Intersects(cb.geometry, pc.drive_8km)  -- Pre-filter for performance
GROUP BY pc.parking_id, pc.name, pc.capacity;

SELECT 
    AVG(pop_drive_5km)::INT as avg_pop_covered,
    MAX(pop_drive_5km)::INT as max_pop_covered,
    SUM(pop_drive_5km)::INT as total_pop_in_all_catchments
FROM catchment_demographics;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_population_coverage))
    conn.commit()
    stats = result.fetchone()
    print(f"✓ Average population per catchment (5km): {stats[0]:,}")
    print(f"✓ Maximum population in any catchment: {stats[1]:,}\n")

# ============================================
# STEP 4: Estimate Demand
# ============================================
print("📊 Estimating Park & Ride demand...")

sql_demand = """
DROP TABLE IF EXISTS parking_demand_estimate CASCADE;

CREATE TABLE parking_demand_estimate AS
SELECT 
    cd.parking_id,
    cd.name,
    cd.capacity,
    cd.pop_drive_5km as population_5km,
    cd.employment_5km,
    cd.housing_units_5km,
    
    -- Estimate commuters (assume 60% of pop are workers, 80% drive)
    (cd.pop_drive_5km * 0.60 * 0.80)::INT as estimated_commuters,
    
    -- Potential P&R users (conservative: 5-10% of commuters might use P&R)
    (cd.pop_drive_5km * 0.60 * 0.80 * 0.075)::INT as potential_demand_low,
    (cd.pop_drive_5km * 0.60 * 0.80 * 0.10)::INT as potential_demand_high,
    
    -- Capacity utilization estimates
    CASE 
        WHEN cd.capacity > 0 THEN 
            ((cd.pop_drive_5km * 0.60 * 0.80 * 0.075) / cd.capacity * 100)::INT
        ELSE 0 
    END as utilization_pct_low,
    
    CASE 
        WHEN cd.capacity > 0 THEN 
            ((cd.pop_drive_5km * 0.60 * 0.80 * 0.10) / cd.capacity * 100)::INT
        ELSE 0 
    END as utilization_pct_high

FROM catchment_demographics cd;

SELECT 
    AVG(potential_demand_low)::INT as avg_demand_low,
    AVG(potential_demand_high)::INT as avg_demand_high,
    AVG(utilization_pct_low)::INT as avg_utilization_low,
    AVG(utilization_pct_high)::INT as avg_utilization_high
FROM parking_demand_estimate;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_demand))
    conn.commit()
    stats = result.fetchone()
    print(f"✓ Estimated demand per site (low): {stats[0]:,} users")
    print(f"✓ Estimated demand per site (high): {stats[1]:,} users")
    print(f"✓ Average utilization (low): {stats[2]}%")
    print(f"✓ Average utilization (high): {stats[3]}%\n")

print("✅ SPATIAL ANALYSIS COMPLETE!")
print("Next step: Run 03_accessibility_scoring.py")