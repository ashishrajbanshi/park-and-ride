from sqlalchemy import create_engine, text
import sys

# UPDATE THIS WITH YOUR ACTUAL PASSWORD
DB_CONNECTION = "postgresql://postgres:qrakken@localhost:5432/chattanooga_parkride"

try:
    engine = create_engine(DB_CONNECTION)
    print("🔗 Connecting to database...")
    
    # Test connection
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    print("✓ Connected successfully\n")
    
except Exception as e:
    print(f"❌ Connection failed: {e}")
    print("\nPlease update DB_CONNECTION with your actual password")
    sys.exit(1)

print("📊 Creating parking_with_scores view...\n")

# First, let's check what tables exist
print("Step 1: Checking existing tables...")
with engine.connect() as conn:
    result = conn.execute(text("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public' 
        AND table_type = 'BASE TABLE'
        ORDER BY table_name
    """))
    tables = [row[0] for row in result]
    
    print("Found tables:")
    for table in tables:
        print(f"  • {table}")
    
    # Check if required tables exist
    required = ['parking_lots', 'parking_accessibility_scores']
    missing = [t for t in required if t not in tables]
    
    if missing:
        print(f"\n❌ ERROR: Missing required tables: {missing}")
        print("\nYou need to run these scripts first:")
        print("  1. python scripts/01_setup_database.py")
        print("  2. python scripts/02_spatial_analysis.py")
        print("  3. python scripts/03_accessibility_scoring.py")
        sys.exit(1)
    
    print("\n✓ All required tables exist")

# Now create the view
print("\nStep 2: Creating view...")

sql_create_view = """
-- Drop if exists
DROP VIEW IF EXISTS parking_with_scores CASCADE;

-- Create view joining parking lots with their scores
CREATE VIEW parking_with_scores AS
SELECT 
    p.parking_id,
    p.name,
    p.capacity,
    p.type,
    p.geometry,
    
    -- Scores from accessibility table
    COALESCE(s.composite_score, 0) as composite_score,
    COALESCE(s.rank, 999) as rank,
    COALESCE(s.estimated_demand, 0) as estimated_demand,
    COALESCE(s.population_score, 0) as population_score,
    COALESCE(s.demand_score, 0) as demand_score,
    COALESCE(s.capacity_score, 0) as capacity_score,
    COALESCE(s.transit_access_score, 0) as transit_access_score,
    COALESCE(s.transit_frequency_score, 0) as transit_frequency_score,
    COALESCE(s.proximity_score, 0) as proximity_score,
    COALESCE(s.supply_demand_status, 'Unknown') as supply_demand_status,
    COALESCE(s.transit_stops_nearby, 0) as transit_stops_nearby,
    COALESCE(s.avg_transit_frequency, 0) as avg_transit_frequency,
    COALESCE(s.avg_walk_distance_m, 0) as avg_walk_distance_m,
    COALESCE(s.population_5km, 0) as population_5km
    
FROM parking_lots p
LEFT JOIN parking_accessibility_scores s 
    ON p.parking_id = s.parking_id;
"""

try:
    with engine.connect() as conn:
        conn.execute(text(sql_create_view))
        conn.commit()
        print("✓ View created successfully\n")
        
        # Verify the view
        print("Step 3: Verifying view...")
        result = conn.execute(text("""
            SELECT 
                COUNT(*) as total_sites,
                COUNT(CASE WHEN composite_score > 0 THEN 1 END) as sites_with_scores,
                MAX(composite_score)::NUMERIC(10,2) as max_score,
                MIN(composite_score)::NUMERIC(10,2) as min_score,
                ST_SRID(ST_Union(geometry)) as srid
            FROM parking_with_scores
        """))
        
        stats = result.fetchone()
        
        print(f"\n📈 View Statistics:")
        print(f"  Total parking sites: {stats[0]}")
        print(f"  Sites with scores: {stats[1]}")
        print(f"  Score range: {stats[3]:.2f} to {stats[2]:.2f}")
        print(f"  Coordinate system (SRID): {stats[4]}")
        
        if stats[1] == 0:
            print("\n⚠️  WARNING: No scores found!")
            print("This means parking_accessibility_scores table is empty.")
            print("You need to run: python scripts/03_accessibility_scoring.py")
        else:
            print("\n✅ View is ready to use in ArcGIS Pro!")
            
            # Show top 5
            print("\nTop 5 sites preview:")
            result = conn.execute(text("""
                SELECT rank, name, composite_score::NUMERIC(10,2), estimated_demand
                FROM parking_with_scores 
                WHERE composite_score > 0
                ORDER BY rank 
                LIMIT 5
            """))
            
            print(f"{'Rank':<6} {'Name':<40} {'Score':<10} {'Demand':<10}")
            print("-" * 70)
            for row in result:
                print(f"{row[0]:<6} {row[1]:<40} {row[2]:<10} {row[3]:<10}")

except Exception as e:
    print(f"\n❌ Error creating view: {e}")
    sys.exit(1)

print("\n" + "="*70)
print("NEXT STEPS:")
print("="*70)
print("1. Open ArcGIS Pro")
print("2. In Catalog Pane, right-click your database connection → Refresh")
print("3. Expand the database → You should now see 'parking_with_scores'")
print("4. Drag 'parking_with_scores' onto your map")
print("5. Right-click layer → Symbology → Graduated Colors")
print("6. Field: composite_score")
print("="*70)