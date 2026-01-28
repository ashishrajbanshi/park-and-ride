"""
Step 4: User-driven routing system with alternatives
Calculates optimal routes from user origin to VW via P&R facilities
"""

import sys
sys.path.append('case_study/vw_chattanooga/scripts')

from config import *
from sqlalchemy import create_engine, text
import pandas as pd
import geopandas as gpd
from shapely.geometry import Point, LineString
import json

print("="*80)
print("Step 4: User-Based Routing & Decision Support")
print("="*80)

engine = create_engine(DB_CONNECTION)

# ============================================
# User routing function
# ============================================

def calculate_routes_from_origin(origin_lat, origin_lon, origin_name="User Home"):
    """
    Calculate optimal P&R routes from a given origin to VW Chattanooga
    
    Parameters:
    -----------
    origin_lat : float
        Latitude of origin point
    origin_lon : float
        Longitude of origin point
    origin_name : str
        Name/label for origin point
    
    Returns:
    --------
    dict : Contains top 3 P&R options with routing details
    """
    
    print(f"\n📍 Origin: {origin_name}")
    print(f"   Coordinates: ({origin_lat}, {origin_lon})")
    
    # Create origin point in database
    sql_create_origin = f"""
    DROP TABLE IF EXISTS temp_user_origin CASCADE;
    
    CREATE TEMP TABLE temp_user_origin AS
    SELECT 
        '{origin_name}'::TEXT as origin_name,
        {origin_lat}::FLOAT as latitude,
        {origin_lon}::FLOAT as longitude,
        ST_Transform(
            ST_SetSRID(
                ST_MakePoint({origin_lon}, {origin_lat}),
                {CRS_WGS84}
            ),
            {CRS_UTM}
        ) as geometry;
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql_create_origin))
        conn.commit()
    
    # Calculate distances and routes - create temp table
    sql_create_temp = """
    DROP TABLE IF EXISTS temp_parkride_routes CASCADE;
    
    CREATE TEMP TABLE temp_parkride_routes AS
    SELECT 
        r.parking_id,
        r.name as parkride_name,
        r.final_rank,
        r.final_composite_score,
        r.capacity,
        r.distance_to_vw_m,
        r.daily_transit_trips,
        r.service_quality,
        r.suitability_rating,
        r.recommendation_tier,
        
        -- Distance from origin to parking lot (driving)
        ST_Distance(
            (SELECT geometry FROM temp_user_origin),
            pl.geometry
        ) as origin_to_parking_m,
        
        -- Estimated driving time (assuming 40 km/h average in city)
        (ST_Distance(
            (SELECT geometry FROM temp_user_origin),
            pl.geometry
        ) / 1000.0 / 40.0 * 60.0)::INT as drive_time_minutes,
        
        -- Total trip distance
        (ST_Distance(
            (SELECT geometry FROM temp_user_origin),
            pl.geometry
        ) + r.distance_to_vw_m) as total_trip_distance_m,
        
        -- Estimated transit time from P&R to VW (assuming 25 km/h)
        (r.distance_to_vw_m / 1000.0 / 25.0 * 60.0)::INT as transit_time_minutes,
        
        -- Total estimated travel time (drive + wait + transit)
        (
            -- Driving time
            (ST_Distance(
                (SELECT geometry FROM temp_user_origin),
                pl.geometry
            ) / 1000.0 / 40.0 * 60.0) +
            -- Average wait time based on frequency
            CASE 
                WHEN r.daily_transit_trips >= 100 THEN 5
                WHEN r.daily_transit_trips >= 50 THEN 10
                WHEN r.daily_transit_trips >= 30 THEN 15
                ELSE 20
            END +
            -- Transit travel time
            (r.distance_to_vw_m / 1000.0 / 25.0 * 60.0)
        )::INT as total_travel_time_minutes,
        
        -- Create route geometry (simplified line)
        ST_MakeLine(
            ARRAY[
                (SELECT geometry FROM temp_user_origin),
                pl.geometry,
                (SELECT geometry FROM vw_plant_location)
            ]
        ) as route_geometry,
        
        -- Score this route for this user
        -- Combines: P&R quality + distance from origin
        (
            -- Base P&R score (70% weight)
            r.final_composite_score * 0.70 +
            -- Proximity score (30% weight) - closer is better
            (100 - LEAST(100, ST_Distance(
                (SELECT geometry FROM temp_user_origin),
                pl.geometry
            ) / 200.0)) * 0.30
        )::NUMERIC(5,2) as user_specific_score
        
    FROM vw_parkride_tiers r
    JOIN parking_lots pl USING (parking_id)
    WHERE r.final_rank <= 30  -- Only consider top 30 sites
    ORDER BY user_specific_score DESC;
    """
    
    # Execute the table creation
    with engine.connect() as conn:
        conn.execute(text(sql_create_temp))
        conn.commit()
    
    # Now read the results with ranking and recommendation labels
    sql_read = """
    SELECT 
        ROW_NUMBER() OVER (ORDER BY user_specific_score DESC) as recommendation_rank,
        parkride_name,
        final_rank as overall_rank,
        user_specific_score,
        origin_to_parking_m,
        (origin_to_parking_m * 0.000621371)::NUMERIC(5,2) as origin_to_parking_miles,
        drive_time_minutes,
        distance_to_vw_m,
        (distance_to_vw_m * 0.000621371)::NUMERIC(5,2) as distance_to_vw_miles,
        transit_time_minutes,
        total_travel_time_minutes,
        (total_trip_distance_m * 0.000621371)::NUMERIC(5,2) as total_distance_miles,
        daily_transit_trips,
        service_quality,
        suitability_rating,
        capacity
    FROM temp_parkride_routes
    ORDER BY user_specific_score DESC
    LIMIT 3;
    """
    df_routes = pd.read_sql(sql_read, engine)
    
    # Add recommendation labels in Python instead of SQL
    def get_recommendation_label(rank):
        if rank == 1:
            return '🥇 PRIMARY RECOMMENDATION'
        elif rank == 2:
            return '🥈 ALTERNATIVE 1'
        elif rank == 3:
            return '🥉 ALTERNATIVE 2'
        return ''
    
    df_routes['recommendation_label'] = df_routes['recommendation_rank'].apply(get_recommendation_label)
    
    if len(df_routes) == 0:
        print("⚠️  No suitable P&R locations found for this origin")
        return None
    
    # Display results
    print(f"\n✅ Found {len(df_routes)} optimal P&R options:\n")
    
    for idx, row in df_routes.iterrows():
        print(f"{row['recommendation_label']}")
        print(f"   Location: {row['parkride_name']}")
        score = row['user_specific_score'] if row['user_specific_score'] is not None else 0
        print(f"   User-Specific Score: {score:.1f}/100")
        print(f"   Overall System Rank: #{row['overall_rank']}")
        print(f"   ")
        print(f"   📏 Route Breakdown:")
        origin_miles = row['origin_to_parking_miles'] if row['origin_to_parking_miles'] is not None else 0
        drive_time = row['drive_time_minutes'] if row['drive_time_minutes'] is not None else 0
        distance_vw = row['distance_to_vw_miles'] if row['distance_to_vw_miles'] is not None else 0
        transit_time = row['transit_time_minutes'] if row['transit_time_minutes'] is not None else 0
        total_distance = row['total_distance_miles'] if row['total_distance_miles'] is not None else 0
        total_time = row['total_travel_time_minutes'] if row['total_travel_time_minutes'] is not None else 0
        
        print(f"      Origin → P&R: {origin_miles:.1f} mi ({drive_time} min drive)")
        print(f"      P&R → VW Plant: {distance_vw:.1f} mi ({transit_time} min transit)")
        print(f"      Total Distance: {total_distance:.1f} miles")
        print(f"      Estimated Total Time: {total_time} minutes")
        print(f"   ")
        print(f"   🚌 Transit Service:")
        print(f"      Daily Trips: {row['daily_transit_trips']}")
        print(f"      Quality: {row['service_quality']}")
        print(f"      Capacity: {row['capacity']} spaces")
        print(f"   ")
        print(f"   ⭐ Suitability: {row['suitability_rating']}")
        print()
    
    return df_routes

# ============================================
# Example usage scenarios
# ============================================

print("\n" + "="*70)
print("EXAMPLE ROUTING SCENARIOS")
print("="*70)

# Scenario 1: Downtown Chattanooga resident
print("\n📋 SCENARIO 1: Downtown Chattanooga Resident")
print("-" * 70)
scenario1 = calculate_routes_from_origin(
    origin_lat=35.0456,
    origin_lon=-85.3097,
    origin_name="Downtown Chattanooga"
)

# Scenario 2: North Chattanooga resident
print("\n📋 SCENARIO 2: North Chattanooga Resident")
print("-" * 70)
scenario2 = calculate_routes_from_origin(
    origin_lat=35.0865,
    origin_lon=-85.2818,
    origin_name="North Chattanooga"
)

# Scenario 3: East Ridge resident
print("\n📋 SCENARIO 3: East Ridge Resident")
print("-" * 70)
scenario3 = calculate_routes_from_origin(
    origin_lat=35.0141,
    origin_lon=-85.2519,
    origin_name="East Ridge"
)

# ============================================
# Export routing results
# ============================================
print("\n💾 Exporting routing examples...")

scenarios = [
    ('downtown', scenario1),
    ('north', scenario2),
    ('east_ridge', scenario3)
]

for name, df in scenarios:
    if df is not None:
        output_path = f"{RESULTS_DIR}/routes/routing_example_{name}.csv"
        df.to_csv(output_path, index=False)
        print(f"✓ {name}: {output_path}")

# ============================================
# Create interactive routing function
# ============================================
print("\n🎯 Creating user routing function...")

with open(f"{RESULTS_DIR}/routes/calculate_my_route.py", 'w') as f:
    f.write('''"""
Interactive P&R Route Calculator for VW Chattanooga Employees

Usage:
    python calculate_my_route.py <latitude> <longitude> <origin_name>

Example:
    python calculate_my_route.py 35.0456 -85.3097 "My Home"
"""

import sys
sys.path.append('../../scripts')

from config import *
from sqlalchemy import create_engine
import pandas as pd

if len(sys.argv) < 3:
    print("Usage: python calculate_my_route.py <latitude> <longitude> [origin_name]")
    print("Example: python calculate_my_route.py 35.0456 -85.3097 'My Home'")
    sys.exit(1)

lat = float(sys.argv[1])
lon = float(sys.argv[2])
name = sys.argv[3] if len(sys.argv) > 3 else "My Location"

# Import routing function
import importlib
routing = importlib.import_module('04_user_routing_system')

# Calculate routes
result = routing.calculate_routes_from_origin(lat, lon, name)

if result is not None:
    print("\\n✅ Route calculation complete!")
    print("Check the output above for your personalized P&R recommendations.")
else:
    print("\\n❌ No suitable routes found. Try a different origin location.")
''')

print(f"✓ Created: {RESULTS_DIR}/routes/calculate_my_route.py")
print("\n   Usage: python calculate_my_route.py 35.0456 -85.3097 'Home'")

print("\n" + "="*80)
print("✅ STEP 4 COMPLETE: User Routing System")
print("="*80)
print(f"\nNext: Run 05_generate_methodology_report.py")