import geopandas as gpd
import pandas as pd
from sqlalchemy import create_engine, text
import json

# Database connection
DB_CONNECTION = "postgresql://postgres:qrakken@localhost:5432/chattanooga_parkride"
engine = create_engine(DB_CONNECTION)

print("✓ Database connection established")

# Test connection
with engine.connect() as conn:
    result = conn.execute(text("SELECT PostGIS_Version();"))
    print(f"✓ PostGIS version: {result.fetchone()[0]}")


# Load census block groups
print("\n📊 Loading census data...")
census_file = "/mnt/c/Work/park_and_ride/data/raw/mpo_census.geojson"  # Update path if needed
census = gpd.read_file(census_file)

# Check coordinate system
print(f"Original CRS: {census.crs}")

# Reproject to UTM Zone 16N (meters) for Chattanooga
census = census.to_crs(epsg=32616)
print(f"Reprojected to: {census.crs}")

# Clean column names (remove spaces and special characters)
census.columns = [col.strip().replace(' ', '_').replace('(', '').replace(')', '') 
                  for col in census.columns]

# Rename key columns for easier use
column_mapping = {
    'B01003_001E': 'total_pop',
    'Employment': 'employment',
    'B19301_001E': 'per_capita_income',
    'B19001_001E': 'median_hh_income',
    'B08134_001E': 'transport_mode',
    'B08303_001E': 'travel_time',
    'B25044_001E': 'vehicles_available',
    'B25001_001E': 'housing_units',
    'workFromHome': 'work_from_home',
    'GEOID': 'geoid',
    'NAME': 'name',
    'ALAND': 'land_area',
    'geometry': 'geometry'
}

# Select and rename only columns we need
columns_to_keep = [col for col in column_mapping.keys() if col in census.columns]
census_clean = census[columns_to_keep].rename(columns=column_mapping)

# Handle missing/invalid values
census_clean['total_pop'] = pd.to_numeric(census_clean['total_pop'], errors='coerce').fillna(0)
census_clean['employment'] = pd.to_numeric(census_clean['employment'], errors='coerce').fillna(0)
census_clean['per_capita_income'] = pd.to_numeric(census_clean['per_capita_income'], errors='coerce').fillna(0)

# Calculate derived metrics
census_clean['employment_density'] = (census_clean['employment'] / 
                                      (census_clean['land_area'] / 1000000))  # per km²
census_clean['pop_density'] = (census_clean['total_pop'] / 
                               (census_clean['land_area'] / 1000000))  # per km²

# Upload to database
print("📤 Uploading to database...")
census_clean.to_postgis('census_blocks', engine, if_exists='replace', index=False)

print(f"✓ Loaded {len(census_clean)} census block groups")
print(f"✓ Total population: {census_clean['total_pop'].sum():,.0f}")
print(f"✓ Total employment: {census_clean['employment'].sum():,.0f}")


# Load parking lots
print("\n🅿️  Loading parking lots...")
parking_file = "/mnt/c/Work/park_and_ride/data/raw/all_public_parking_lots.geojson"
with open(parking_file, 'r') as f:
    parking_data = json.load(f)

# Convert to GeoDataFrame
parking_features = []
for feature in parking_data['features']:
    props = feature['properties'].copy()
    props['geometry'] = feature['geometry']
    parking_features.append(props)

parking = gpd.GeoDataFrame.from_features(parking_data['features'])

# Set and transform CRS
parking = parking.set_crs(epsg=4326)  # Assuming WGS84 from your coordinates
parking = parking.to_crs(epsg=32616)  # Transform to UTM

# Clean column names
parking.columns = [col.lower().replace(' ', '_') for col in parking.columns]

# Add unique ID if not present
if 'parking_id' not in parking.columns:
    parking['parking_id'] = range(1, len(parking) + 1)

# Handle missing capacity (use median or default)
if parking['capacity'].isna().any():
    median_capacity = parking['capacity'].median()
    parking['capacity'].fillna(median_capacity, inplace=True)

print(f"✓ Found {len(parking)} parking lots")
print(f"✓ Total capacity: {parking['capacity'].sum():,.0f} spaces")
print(f"✓ Capacity range: {parking['capacity'].min():.0f} - {parking['capacity'].max():.0f}")

# Upload to database
parking.to_postgis('parking_lots', engine, if_exists='replace', index=False)
print("✓ Parking data uploaded")


# Load GTFS stops
print("\n🚌 Loading GTFS transit stops...")
gtfs_path = "data/raw/gtfs/"

# Read stops
stops = pd.read_csv(f"{gtfs_path}stops.txt")

# Create GeoDataFrame
stops_gdf = gpd.GeoDataFrame(
    stops,
    geometry=gpd.points_from_xy(stops.stop_lon, stops.stop_lat),
    crs='EPSG:4326'
)

# Transform to UTM
stops_gdf = stops_gdf.to_crs(epsg=32616)

# Upload to database
stops_gdf.to_postgis('transit_stops', engine, if_exists='replace', index=False)
print(f"✓ Loaded {len(stops_gdf)} transit stops")

# Calculate transit service frequency
print("📈 Calculating service frequency...")
stop_times = pd.read_csv(f"{gtfs_path}stop_times.txt")
trips = pd.read_csv(f"{gtfs_path}trips.txt")

# Count trips per stop
service_freq = (stop_times
                .merge(trips[['trip_id', 'route_id']], on='trip_id')
                .groupby('stop_id')
                .agg(
                    daily_trips=('trip_id', 'count'),
                    num_routes=('route_id', 'nunique')
                )
                .reset_index())

# Upload frequency data
service_freq.to_sql('stop_frequency', engine, if_exists='replace', index=False)
print(f"✓ Service frequency calculated for {len(service_freq)} stops")

print("\n✅ DATABASE SETUP COMPLETE!")
print("\nNext step: Run 02_spatial_analysis.py")