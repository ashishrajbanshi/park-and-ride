"""
Step 2: Calculate accessibility and reliability scores for each scenario
"""

import sys
sys.path.append('case_study/vw_chattanooga/scripts')

from config import *
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np

print("="*80)
print("Step 2: Accessibility & Reliability Score Calculation")
print("="*80)

engine = create_engine(DB_CONNECTION)

# ============================================
# Calculate composite accessibility scores
# ============================================

for scenario_name, distance in WALKING_SCENARIOS.items():
    
    print(f"\n📊 Processing {scenario_name.upper()} scenario ({distance}m)...")
    
    sql_accessibility = f"""
    -- Create accessibility scores table
    DROP TABLE IF EXISTS vw_accessibility_scores_{scenario_name} CASCADE;
    
    CREATE TABLE vw_accessibility_scores_{scenario_name} AS
    WITH normalized_metrics AS (
        SELECT 
            parking_id,
            name,
            distance_to_vw_m,
            num_stops_{distance}m,
            total_daily_trips,
            num_routes,
            avg_walk_distance_m,
            nearest_stop_distance_m,
            has_adequate_transit,
            
            -- Normalize each component to 0-100 scale
            
            -- 1. Number of stops score (more stops = better redundancy)
            (num_stops_{distance}m::FLOAT / 
                NULLIF(MAX(num_stops_{distance}m) OVER (), 0)) * 100 
                as stops_score,
            
            -- 2. Trip frequency score (more trips = better service)
            (total_daily_trips::FLOAT / 
                NULLIF(MAX(total_daily_trips) OVER (), 0)) * 100 
                as frequency_score,
            
            -- 3. Service reliability score 
            -- Based on: if you miss one bus, how soon is the next?
            -- High frequency = high reliability
            CASE 
                WHEN total_daily_trips >= 100 THEN 100  -- Every ~10 min
                WHEN total_daily_trips >= 50 THEN 80    -- Every ~20 min
                WHEN total_daily_trips >= 30 THEN 60    -- Every ~30 min
                WHEN total_daily_trips >= 15 THEN 40    -- Every hour
                WHEN total_daily_trips >= 10 THEN 20    -- Every 1.5 hours
                ELSE 10
            END as reliability_score,
            
            -- 4. Walking distance score (closer = better)
            (100 - (nearest_stop_distance_m::FLOAT / 
                NULLIF(MAX(nearest_stop_distance_m) OVER (), 0)) * 100) 
                as proximity_score,
            
            -- 5. Route diversity score (more routes = more options)
            (num_routes::FLOAT / 
                NULLIF(MAX(num_routes) OVER (), 0)) * 100 
                as diversity_score,
            
            -- 6. Distance from VW score (optimal range: 8-15km)
            CASE 
                WHEN distance_to_vw_m >= {OPTIMAL_DISTANCE_MIN} 
                    AND distance_to_vw_m <= {OPTIMAL_DISTANCE_MAX} THEN 100
                WHEN distance_to_vw_m < {OPTIMAL_DISTANCE_MIN} THEN
                    (distance_to_vw_m / {OPTIMAL_DISTANCE_MIN}::FLOAT) * 100
                ELSE
                    GREATEST(0, 100 - ((distance_to_vw_m - {OPTIMAL_DISTANCE_MAX}) / 10000.0 * 100))
            END as distance_optimality_score
            
        FROM vw_transit_access_{scenario_name}
        WHERE has_adequate_transit = TRUE  -- Only score lots with minimum transit
    )
    SELECT 
        parking_id,
        name,
        distance_to_vw_m,
        num_stops_{distance}m as num_stops,
        total_daily_trips,
        num_routes,
        nearest_stop_distance_m,
        
        -- Individual component scores
        stops_score::NUMERIC(5,2) as stops_score,
        frequency_score::NUMERIC(5,2) as frequency_score,
        reliability_score::NUMERIC(5,2) as reliability_score,
        proximity_score::NUMERIC(5,2) as proximity_score,
        diversity_score::NUMERIC(5,2) as diversity_score,
        distance_optimality_score::NUMERIC(5,2) as distance_score,
        
        -- COMPOSITE ACCESSIBILITY SCORE (weighted average)
        (
            stops_score * {ACCESSIBILITY_WEIGHTS['num_stops']} +
            frequency_score * {ACCESSIBILITY_WEIGHTS['trip_frequency']} +
            reliability_score * {ACCESSIBILITY_WEIGHTS['service_reliability']} +
            proximity_score * {ACCESSIBILITY_WEIGHTS['walking_distance']} +
            diversity_score * {ACCESSIBILITY_WEIGHTS['route_diversity']}
        )::NUMERIC(5,2) as accessibility_score,
        
        -- Service quality classification
        CASE 
            WHEN total_daily_trips >= 100 THEN 'Excellent - High Frequency'
            WHEN total_daily_trips >= 50 THEN 'Good - Moderate Frequency'
            WHEN total_daily_trips >= 30 THEN 'Fair - Basic Service'
            WHEN total_daily_trips >= 10 THEN 'Limited - Minimal Service'
            ELSE 'Poor - Inadequate Service'
        END as service_quality,
        
        -- Reliability classification
        CASE 
            WHEN total_daily_trips >= 50 AND num_stops_{distance}m >= 3 THEN 'High Reliability'
            WHEN total_daily_trips >= 30 AND num_stops_{distance}m >= 2 THEN 'Moderate Reliability'
            WHEN total_daily_trips >= 10 THEN 'Low Reliability'
            ELSE 'Unreliable'
        END as reliability_class
        
    FROM normalized_metrics;
    
    -- Add ranking within this scenario
    ALTER TABLE vw_accessibility_scores_{scenario_name} 
    ADD COLUMN rank_{scenario_name} INTEGER;
    
    UPDATE vw_accessibility_scores_{scenario_name}
    SET rank_{scenario_name} = sub.rank
    FROM (
        SELECT parking_id,
               ROW_NUMBER() OVER (ORDER BY accessibility_score DESC) as rank
        FROM vw_accessibility_scores_{scenario_name}
    ) sub
    WHERE vw_accessibility_scores_{scenario_name}.parking_id = sub.parking_id;
    
    -- Statistics
    SELECT 
        COUNT(*) as total_scored,
        AVG(accessibility_score)::NUMERIC(5,2) as avg_score,
        MAX(accessibility_score)::NUMERIC(5,2) as max_score,
        MIN(accessibility_score)::NUMERIC(5,2) as min_score,
        service_quality,
        COUNT(*) as count
    FROM vw_accessibility_scores_{scenario_name}
    GROUP BY service_quality
    ORDER BY MAX(accessibility_score) DESC;
    """
    
    with engine.connect() as conn:
        result = conn.execute(text(sql_accessibility))
        conn.commit()
        
        print(f"\n   ✓ Accessibility scores calculated")
        print(f"\n   Service Quality Distribution:")
        
        df_quality = pd.DataFrame(result.fetchall(),
                                  columns=['Total', 'Avg Score', 'Max Score', 'Min Score',
                                          'Service Quality', 'Count'])
        print(df_quality[['Service Quality', 'Count', 'Avg Score']].to_string(index=False))

# ============================================
# Compare scenarios
# ============================================
print("\n📈 Comparing across all scenarios...")

sql_comparison = """
-- Create comprehensive comparison table
DROP TABLE IF EXISTS vw_scenario_comparison CASCADE;

CREATE TABLE vw_scenario_comparison AS
SELECT 
    pc.parking_id,
    pc.name,
    pc.capacity,
    pc.distance_to_vw_m,
    pc.vw_distance_category,
    
    -- Conservative (500m)
    s500.accessibility_score as score_500m,
    s500.rank_conservative as rank_500m,
    s500.service_quality as quality_500m,
    s500.num_stops as stops_500m,
    
    -- Moderate (800m)
    s800.accessibility_score as score_800m,
    s800.rank_moderate as rank_800m,
    s800.service_quality as quality_800m,
    s800.num_stops as stops_800m,
    
    -- Extended (1000m)
    s1000.accessibility_score as score_1000m,
    s1000.rank_extended as rank_1000m,
    s1000.service_quality as quality_1000m,
    s1000.num_stops as stops_1000m,
    
    -- Best scenario for this lot
    CASE 
        WHEN s1000.accessibility_score >= s800.accessibility_score 
            AND s1000.accessibility_score >= s500.accessibility_score THEN 'Extended (1000m)'
        WHEN s800.accessibility_score >= s500.accessibility_score THEN 'Moderate (800m)'
        ELSE 'Conservative (500m)'
    END as best_scenario,
    
    -- Maximum accessibility score across scenarios
    GREATEST(
        COALESCE(s500.accessibility_score, 0),
        COALESCE(s800.accessibility_score, 0),
        COALESCE(s1000.accessibility_score, 0)
    ) as max_accessibility_score

FROM vw_parking_candidates pc
LEFT JOIN vw_accessibility_scores_conservative s500 USING (parking_id)
LEFT JOIN vw_accessibility_scores_moderate s800 USING (parking_id)
LEFT JOIN vw_accessibility_scores_extended s1000 USING (parking_id)
WHERE pc.is_candidate = TRUE
    AND (s500.accessibility_score IS NOT NULL 
        OR s800.accessibility_score IS NOT NULL 
        OR s1000.accessibility_score IS NOT NULL);

SELECT 
    best_scenario,
    COUNT(*) as num_lots,
    AVG(max_accessibility_score)::NUMERIC(5,2) as avg_best_score
FROM vw_scenario_comparison
GROUP BY best_scenario
ORDER BY COUNT(*) DESC;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_comparison))
    conn.commit()
    
    print("\n   Best Scenario Distribution:")
    df_best = pd.DataFrame(result.fetchall(),
                          columns=['Best Scenario', 'Count', 'Avg Score'])
    print(df_best.to_string(index=False))

# ============================================
# Export results
# ============================================
print("\n💾 Exporting accessibility analysis...")

# Export each scenario
for scenario_name in WALKING_SCENARIOS.keys():
    df = pd.read_sql(f"""
        SELECT * FROM vw_accessibility_scores_{scenario_name}
        ORDER BY rank_{scenario_name}
    """, engine)
    
    output_path = f"{RESULTS_DIR}/rankings/accessibility_scores_{scenario_name}.csv"
    df.to_csv(output_path, index=False)
    print(f"✓ {scenario_name}: {output_path}")

# Export comparison
df_comparison = pd.read_sql("SELECT * FROM vw_scenario_comparison ORDER BY max_accessibility_score DESC", engine)
output_path = f"{RESULTS_DIR}/rankings/scenario_comparison.csv"
df_comparison.to_csv(output_path, index=False)
print(f"✓ Comparison: {output_path}")

print("\n" + "="*80)
print("✅ STEP 2 COMPLETE: Accessibility Scoring")
print("="*80)
print(f"\nNext: Run 03_rank_and_optimize.py")