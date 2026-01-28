from sqlalchemy import create_engine, text
import pandas as pd

DB_CONNECTION = "postgresql://postgres:qrakken@localhost:5432/chattanooga_parkride"
engine = create_engine(DB_CONNECTION)

print("🎯 CALCULATING ACCESSIBILITY SCORES\n")

sql_accessibility = """
DROP TABLE IF EXISTS parking_accessibility_scores CASCADE;

CREATE TABLE parking_accessibility_scores AS
WITH transit_scores AS (
    SELECT 
        parking_id,
        COUNT(DISTINCT stop_id) as num_stops,
        AVG(daily_trips) as avg_daily_trips,
        AVG(num_routes) as avg_routes,
        AVG(distance_meters) as avg_distance_to_stop
    FROM parking_transit_access
    GROUP BY parking_id
),
normalized_metrics AS (
    SELECT 
        pde.*,
        cd.pop_walk_800m,
        cd.avg_income_5km,
        cd.blocks_served_5km,
        ts.num_stops,
        ts.avg_daily_trips,
        ts.avg_routes,
        ts.avg_distance_to_stop,
        
        -- Normalize each metric to 0-100 scale
        (pde.population_5km::FLOAT / MAX(pde.population_5km) OVER ()) * 100 as norm_population,
        (pde.potential_demand_high::FLOAT / MAX(pde.potential_demand_high) OVER ()) * 100 as norm_demand,
        (pde.capacity::FLOAT / MAX(pde.capacity) OVER ()) * 100 as norm_capacity,
        (ts.num_stops::FLOAT / NULLIF(MAX(ts.num_stops) OVER (), 0)) * 100 as norm_transit_stops,
        (ts.avg_daily_trips::FLOAT / NULLIF(MAX(ts.avg_daily_trips) OVER (), 0)) * 100 as norm_transit_freq,
        (100 - (ts.avg_distance_to_stop::FLOAT / NULLIF(MAX(ts.avg_distance_to_stop) OVER (), 0)) * 100) as norm_proximity
        
    FROM parking_demand_estimate pde
    JOIN catchment_demographics cd USING (parking_id)
    LEFT JOIN transit_scores ts USING (parking_id)
)
SELECT 
    parking_id,
    name,
    capacity,
    population_5km,
    potential_demand_high as estimated_demand,
    num_stops as transit_stops_nearby,
    avg_daily_trips::INT as avg_transit_frequency,
    avg_distance_to_stop::INT as avg_walk_distance_m,
    
    -- Individual dimension scores
    norm_population::DECIMAL(5,2) as population_score,
    norm_demand::DECIMAL(5,2) as demand_score,
    norm_capacity::DECIMAL(5,2) as capacity_score,
    norm_transit_stops::DECIMAL(5,2) as transit_access_score,
    norm_transit_freq::DECIMAL(5,2) as transit_frequency_score,
    norm_proximity::DECIMAL(5,2) as proximity_score,
    
    -- COMPOSITE ACCESSIBILITY SCORE (weighted average)
    (
        norm_demand * 0.30 +           -- 30% weight on demand
        norm_transit_stops * 0.25 +     -- 25% weight on transit access
        norm_transit_freq * 0.20 +      -- 20% weight on service frequency
        norm_capacity * 0.15 +          -- 15% weight on capacity
        norm_proximity * 0.10           -- 10% weight on proximity
    )::DECIMAL(5,2) as composite_score,
    
    -- Supply-demand balance indicator
    CASE 
        WHEN potential_demand_high > capacity * 1.5 THEN 'High Demand - Undersupplied'
        WHEN potential_demand_high > capacity THEN 'Adequate Demand - Consider Expansion'
        WHEN potential_demand_high > capacity * 0.5 THEN 'Balanced'
        ELSE 'Low Demand - Oversupplied'
    END as supply_demand_status

FROM normalized_metrics;

-- Add ranking
ALTER TABLE parking_accessibility_scores ADD COLUMN rank INTEGER;

UPDATE parking_accessibility_scores
SET rank = sub.rank
FROM (
    SELECT parking_id, 
           ROW_NUMBER() OVER (ORDER BY composite_score DESC) as rank
    FROM parking_accessibility_scores
) sub
WHERE parking_accessibility_scores.parking_id = sub.parking_id;

-- Show top 10
SELECT 
    rank,
    name,
    composite_score,
    estimated_demand,
    capacity,
    supply_demand_status
FROM parking_accessibility_scores
ORDER BY rank
LIMIT 10;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_accessibility))
    conn.commit()
    
    # Fetch and display top 10
    top10 = pd.DataFrame(result.fetchall(), 
                         columns=['Rank', 'Name', 'Score', 'Demand', 
                                 'Capacity', 'Status'])
    
    print("🏆 TOP 10 PARK & RIDE SITES:\n")
    print(top10.to_string(index=False))
    print("\n✅ ACCESSIBILITY SCORING COMPLETE!")

# Export results to CSV
print("\n📄 Exporting results...")
results_df = pd.read_sql(
    "SELECT * FROM parking_accessibility_scores ORDER BY rank",
    engine
)
results_df.to_csv('results/parking_rankings.csv', index=False)
print("✓ Saved to: results/parking_rankings.csv")

print("\nNext step: Visualize in ArcGIS Pro")