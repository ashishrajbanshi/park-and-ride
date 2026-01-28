import geopandas as gpd
from sqlalchemy import create_engine, text

DB_CONNECTION = "postgresql://postgres:qrakken@localhost:5432/chattanooga_parkride"
engine = create_engine(DB_CONNECTION)

print("Creating separate catchment layers...\n")

# Define catchment types
catchments = {
    'parking_walk_400m': 'walk_400m',
    'parking_walk_800m': 'walk_800m',
    'parking_drive_3km': 'drive_3km',
    'parking_drive_5km': 'drive_5km'
}

for view_name, geom_col in catchments.items():
    print(f"Creating {view_name}...")
    
    sql = f"""
    DROP VIEW IF EXISTS {view_name} CASCADE;
    
    CREATE VIEW {view_name} AS
    SELECT 
        parking_id,
        name,
        capacity,
        type,
        {geom_col} as geometry
    FROM parking_catchments;
    """
    
    with engine.connect() as conn:
        conn.execute(text(sql))
        conn.commit()
    
    print(f"✓ {view_name} created")

print("\n✅ All catchment views created!")
print("Refresh your database in ArcGIS Pro to see them")