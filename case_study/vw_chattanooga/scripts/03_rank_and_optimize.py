"""
Step 3: Final ranking and optimization of P&R locations
Combines all criteria to produce definitive rankings
"""

import sys
sys.path.append('case_study/vw_chattanooga/scripts')

from config import *
from sqlalchemy import create_engine, text
import pandas as pd
import numpy as np

print("="*80)
print("Step 3: Parking Lot Ranking & Optimization")
print("="*80)

engine = create_engine(DB_CONNECTION)

# ============================================
# Create comprehensive ranking
# ============================================
print("\n🏆 Calculating final rankings...")

sql_final_ranking = f"""
-- Drop if exists
DROP TABLE IF EXISTS vw_parkride_rankings CASCADE;

CREATE TABLE vw_parkride_rankings AS
WITH base_metrics AS (
    SELECT 
        sc.parking_id,
        sc.name,
        sc.capacity,
        sc.distance_to_vw_m,
        sc.vw_distance_category,
        
        -- Use best accessibility score across scenarios
        sc.max_accessibility_score as accessibility_score,
        sc.best_scenario,
        
        -- Best scenario metrics
        CASE 
            WHEN sc.best_scenario = 'Extended (1000m)' THEN sc.score_1000m
            WHEN sc.best_scenario = 'Moderate (800m)' THEN sc.score_800m
            ELSE sc.score_500m
        END as scenario_accessibility,
        
        CASE 
            WHEN sc.best_scenario = 'Extended (1000m)' THEN sc.stops_1000m
            WHEN sc.best_scenario = 'Moderate (800m)' THEN sc.stops_800m
            ELSE sc.stops_500m
        END as num_stops,
        
        -- Get service frequency from moderate scenario (most common)
        s800.total_daily_trips as service_frequency,
        s800.service_quality,
        s800.reliability_class,
        
        -- Normalized component scores
        
        -- 1. Transit accessibility (primary criterion)
        (sc.max_accessibility_score / 
            NULLIF(MAX(sc.max_accessibility_score) OVER (), 0)) * 100 
            as norm_transit_access,
        
        -- 2. Service frequency
        (s800.total_daily_trips::FLOAT / 
            NULLIF(MAX(s800.total_daily_trips) OVER (), 0)) * 100 
            as norm_service_freq,
        
        -- 3. Distance optimality from VW
        CASE 
            WHEN sc.distance_to_vw_m >= {OPTIMAL_DISTANCE_MIN} 
                AND sc.distance_to_vw_m <= {OPTIMAL_DISTANCE_MAX} THEN 100
            WHEN sc.distance_to_vw_m < {OPTIMAL_DISTANCE_MIN} THEN
                (sc.distance_to_vw_m / {OPTIMAL_DISTANCE_MIN}::FLOAT) * 100
            ELSE
                GREATEST(0, 100 - ((sc.distance_to_vw_m - {OPTIMAL_DISTANCE_MAX}) / 10000.0 * 100))
        END as norm_distance,
        
        -- 4. Parking capacity
        (sc.capacity::FLOAT / 
            NULLIF(MAX(sc.capacity) OVER (), 0)) * 100 
            as norm_capacity,
        
        -- 5. Optimal distance bonus (sweet spot preference)
        CASE 
            WHEN sc.distance_to_vw_m >= {OPTIMAL_DISTANCE_MIN} 
                AND sc.distance_to_vw_m <= {OPTIMAL_DISTANCE_MAX} THEN 100
            ELSE 50
        END as optimal_location_bonus
        
    FROM vw_scenario_comparison sc
    LEFT JOIN vw_accessibility_scores_moderate s800 USING (parking_id)
    WHERE sc.max_accessibility_score > 0
)
SELECT 
    parking_id,
    name,
    capacity,
    distance_to_vw_m,
    (distance_to_vw_m * 0.000621371)::NUMERIC(5,2) as distance_to_vw_miles,
    vw_distance_category,
    best_scenario as optimal_walking_scenario,
    num_stops as transit_stops_available,
    service_frequency as daily_transit_trips,
    service_quality,
    reliability_class,
    
    -- Component scores
    norm_transit_access::NUMERIC(5,2) as transit_access_score,
    norm_service_freq::NUMERIC(5,2) as frequency_score,
    norm_distance::NUMERIC(5,2) as distance_score,
    norm_capacity::NUMERIC(5,2) as capacity_score,
    optimal_location_bonus::NUMERIC(5,2) as location_bonus,
    
    -- FINAL COMPOSITE SCORE (weighted)
    (
        norm_transit_access * {RANKING_WEIGHTS['transit_accessibility']} +
        norm_service_freq * {RANKING_WEIGHTS['service_frequency']} +
        norm_distance * {RANKING_WEIGHTS['distance_from_vw']} +
        norm_capacity * {RANKING_WEIGHTS['parking_capacity']} +
        optimal_location_bonus * {RANKING_WEIGHTS['optimal_distance']}
    )::NUMERIC(5,2) as final_composite_score,
    
    -- Suitability classification
    CASE 
        WHEN (
            norm_transit_access * {RANKING_WEIGHTS['transit_accessibility']} +
            norm_service_freq * {RANKING_WEIGHTS['service_frequency']} +
            norm_distance * {RANKING_WEIGHTS['distance_from_vw']} +
            norm_capacity * {RANKING_WEIGHTS['parking_capacity']} +
            optimal_location_bonus * {RANKING_WEIGHTS['optimal_distance']}
        ) >= 80 THEN 'Excellent - Highly Recommended'
        WHEN (
            norm_transit_access * {RANKING_WEIGHTS['transit_accessibility']} +
            norm_service_freq * {RANKING_WEIGHTS['service_frequency']} +
            norm_distance * {RANKING_WEIGHTS['distance_from_vw']} +
            norm_capacity * {RANKING_WEIGHTS['parking_capacity']} +
            optimal_location_bonus * {RANKING_WEIGHTS['optimal_distance']}
        ) >= 65 THEN 'Good - Recommended'
        WHEN (
            norm_transit_access * {RANKING_WEIGHTS['transit_accessibility']} +
            norm_service_freq * {RANKING_WEIGHTS['service_frequency']} +
            norm_distance * {RANKING_WEIGHTS['distance_from_vw']} +
            norm_capacity * {RANKING_WEIGHTS['parking_capacity']} +
            optimal_location_bonus * {RANKING_WEIGHTS['optimal_distance']}
        ) >= 50 THEN 'Fair - Acceptable with Limitations'
        ELSE 'Poor - Not Recommended'
    END as suitability_rating,
    
    -- Key strengths
    ARRAY_TO_STRING(ARRAY[
        CASE WHEN norm_transit_access >= 80 THEN 'Excellent Transit Access' END,
        CASE WHEN norm_service_freq >= 80 THEN 'High Service Frequency' END,
        CASE WHEN norm_distance >= 80 THEN 'Optimal Distance from VW' END,
        CASE WHEN norm_capacity >= 80 THEN 'Large Capacity' END
    ]::TEXT[], ' | ') as key_strengths,
    
    -- Potential concerns
    ARRAY_TO_STRING(ARRAY[
        CASE WHEN norm_transit_access < 50 THEN 'Limited Transit Access' END,
        CASE WHEN norm_service_freq < 50 THEN 'Low Service Frequency' END,
        CASE WHEN distance_to_vw_m < {OPTIMAL_DISTANCE_MIN} THEN 'Too Close to VW' END,
        CASE WHEN distance_to_vw_m > {OPTIMAL_DISTANCE_MAX} THEN 'Far from VW' END,
        CASE WHEN capacity < 100 THEN 'Limited Capacity' END
    ]::TEXT[], ' | ') as potential_concerns

FROM base_metrics;

-- Add final ranking
ALTER TABLE vw_parkride_rankings ADD COLUMN final_rank INTEGER;

UPDATE vw_parkride_rankings
SET final_rank = sub.rank
FROM (
    SELECT parking_id,
           ROW_NUMBER() OVER (ORDER BY final_composite_score DESC) as rank
    FROM vw_parkride_rankings
) sub
WHERE vw_parkride_rankings.parking_id = sub.parking_id;

-- Summary statistics
SELECT 
    suitability_rating,
    COUNT(*) as num_sites,
    AVG(final_composite_score)::NUMERIC(5,2) as avg_score,
    AVG(distance_to_vw_miles)::NUMERIC(5,2) as avg_distance_miles
FROM vw_parkride_rankings
GROUP BY suitability_rating
ORDER BY AVG(final_composite_score) DESC;
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_final_ranking))
    conn.commit()
    
    print("\n📊 Ranking Summary:")
    df_summary = pd.DataFrame(result.fetchall(),
                             columns=['Suitability Rating', 'Count', 'Avg Score', 'Avg Distance (mi)'])
    print(df_summary.to_string(index=False))

# ============================================
# Display top 10 recommendations
# ============================================
print("\n🥇 TOP 10 RECOMMENDED P&R LOCATIONS:\n")

df_top10 = pd.read_sql("""
    SELECT 
        final_rank as rank,
        name,
        final_composite_score as score,
        distance_to_vw_miles as dist_mi,
        daily_transit_trips as trips,
        capacity,
        suitability_rating as rating
    FROM vw_parkride_rankings
    ORDER BY final_rank
    LIMIT 10
""", engine)

print(df_top10.to_string(index=False))

# ============================================
# Create tier classifications
# ============================================
print("\n📋 Creating tiered recommendations...")

sql_tiers = """
DROP TABLE IF EXISTS vw_parkride_tiers CASCADE;

CREATE TABLE vw_parkride_tiers AS
SELECT 
    *,
    CASE 
        WHEN final_rank <= 5 THEN 'Tier 1: Primary Recommendations'
        WHEN final_rank <= 15 THEN 'Tier 2: Strong Alternatives'
        WHEN final_rank <= 30 THEN 'Tier 3: Viable Options'
        ELSE 'Tier 4: Marginal Sites'
    END as recommendation_tier
FROM vw_parkride_rankings;

-- Tier distribution
SELECT 
    recommendation_tier,
    COUNT(*) as num_sites,
    MIN(final_composite_score)::NUMERIC(5,2) as min_score,
    MAX(final_composite_score)::NUMERIC(5,2) as max_score
FROM vw_parkride_tiers
GROUP BY recommendation_tier
ORDER BY MIN(final_rank);
"""

with engine.connect() as conn:
    result = conn.execute(text(sql_tiers))
    conn.commit()
    
    print("\n   Tier Distribution:")
    df_tiers = pd.DataFrame(result.fetchall(),
                           columns=['Tier', 'Count', 'Min Score', 'Max Score'])
    print(df_tiers.to_string(index=False))

# ============================================
# Export rankings
# ============================================
print("\n💾 Exporting final rankings...")

# Full rankings
df_rankings = pd.read_sql("""
    SELECT * FROM vw_parkride_tiers 
    ORDER BY final_rank
""", engine)

output_path = f"{RESULTS_DIR}/rankings/final_parkride_rankings.csv"
df_rankings.to_csv(output_path, index=False)
print(f"✓ Full rankings: {output_path}")

# Top 20 detailed report
df_top20 = pd.read_sql("""
    SELECT 
        final_rank,
        name,
        capacity,
        distance_to_vw_miles,
        optimal_walking_scenario,
        transit_stops_available,
        daily_transit_trips,
        service_quality,
        reliability_class,
        final_composite_score,
        suitability_rating,
        recommendation_tier,
        key_strengths,
        potential_concerns
    FROM vw_parkride_tiers
    ORDER BY final_rank
    LIMIT 20
""", engine)

output_path = f"{RESULTS_DIR}/rankings/top20_detailed_report.csv"
df_top20.to_csv(output_path, index=False)
print(f"✓ Top 20 report: {output_path}")

# Create view for ArcGIS
print("\n🗺️  Creating ArcGIS-ready view...")

sql_arcgis_view = """
DROP VIEW IF EXISTS vw_parkride_final_map CASCADE;

CREATE VIEW vw_parkride_final_map AS
SELECT 
    pl.geometry,
    r.*
FROM vw_parkride_tiers r
JOIN parking_lots pl USING (parking_id);
"""

with engine.connect() as conn:
    conn.execute(text(sql_arcgis_view))
    conn.commit()
    print("✓ View created: vw_parkride_final_map")

print("\n" + "="*80)
print("✅ STEP 3 COMPLETE: Ranking & Optimization")
print("="*80)
print(f"\nNext: Run 04_user_routing_system.py")