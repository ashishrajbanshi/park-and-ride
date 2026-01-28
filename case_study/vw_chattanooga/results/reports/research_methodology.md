
# RESEARCH METHODOLOGY
## Optimizing Park-and-Ride Location Selection for Volkswagen Chattanooga Employees: A GIS-Based Multi-Criteria Decision Analysis

---

## 1. INTRODUCTION

### 1.1 Study Context and Rationale

This research presents a comprehensive spatial analysis framework for identifying and evaluating optimal Park-and-Ride (P&R) facility locations to serve employees of the Volkswagen Chattanooga Assembly Plant. The study addresses the critical need for sustainable commuting alternatives in suburban-industrial contexts where employees travel from dispersed residential areas to a centralized workplace.

The Volkswagen Chattanooga plant (35.0769°N, 85.1306°W) employs thousands of workers from throughout the Chattanooga Metropolitan Planning Organization (MPO) region. Current commuting patterns are heavily automobile-dependent, resulting in:
- High individual transportation costs
- Traffic congestion during shift changes
- Environmental impacts from single-occupancy vehicle travel
- Limited modal choice for employees without reliable personal vehicles

Park-and-Ride facilities offer a strategic intervention by enabling a hybrid commuting model where employees drive a short distance from home to a P&R location, then transfer to public transit for the remainder of their journey. The effectiveness of P&R systems depends critically on site selection—locations must be:
1. Spatially positioned to intercept commuter flows before they enter congested areas
2. Well-connected to reliable public transit services
3. Accessible to a substantial catchment of potential users
4. Neither too close nor too far from the final destination

This study employs Geographic Information Systems (GIS) and spatial analysis to systematically evaluate existing parking facilities in Chattanooga as potential P&R sites, applying rigorous multi-criteria decision analysis to rank locations based on transit accessibility, service reliability, and spatial optimization principles.

### 1.2 Research Objectives

The primary objectives of this research are to:

1. **Develop a replicable spatial methodology** for P&R site evaluation in employment-center contexts
2. **Identify and rank optimal P&R locations** serving VW Chattanooga employees
3. **Quantify transit accessibility and service reliability** at candidate locations
4. **Provide user-specific routing recommendations** based on employee residential locations
5. **Generate evidence-based policy recommendations** for transportation planning agencies

---

## 2. STUDY AREA AND CASE STUDY SELECTION

### 2.1 Geographic Scope

The study area encompasses the Chattanooga Metropolitan Planning Organization (MPO) region in southeastern Tennessee. The region is characterized by:
- Topographically constrained urban development along the Tennessee River valley
- Dispersed suburban residential patterns
- Limited public transit coverage compared to central urban core
- Industrial employment centers on the urban periphery

### 2.2 Case Study Justification: VW Chattanooga Assembly Plant

The Volkswagen Chattanooga Assembly Plant was selected as the focal destination for this analysis based on several criteria:

**Employment Scale**: The facility represents a major employment concentration with over 4,000 direct employees plus contractors, creating substantial commuting demand.

**Shift-Based Operations**: Manufacturing operations run on defined shifts, creating predictable temporal demand patterns conducive to scheduled transit service.

**Peripheral Location**: The plant's location outside the central business district means many employees commute past potential P&R sites, making interception feasible.

**Transit Connectivity**: Multiple public transit routes serve the vicinity, providing a foundation for P&R integration.

**Policy Relevance**: As a major employer and corporate citizen, VW has expressed interest in sustainable transportation alternatives for its workforce.

The case study approach allows for detailed analysis of a specific commuting context while developing generalizable methodologies applicable to other employment-center-focused P&R planning efforts.

---

## 3. DATA SOURCES AND PREPROCESSING

### 3.1 Spatial Data Acquisition

This analysis integrated multiple geospatial and tabular datasets:

#### 3.1.1 Parking Facilities Data
- **Source**: OpenStreetMap (OSM) parking amenities layer
- **Temporal Coverage**: Extracted January 2025
- **Spatial Coverage**: Chattanooga MPO region
- **Attributes**: Location (point geometry), capacity, facility type (surface lot, garage, etc.)
- **Processing**: 
  - Converted from WGS84 (EPSG:4326) to UTM Zone 16N (EPSG:32616) for metric distance calculations
  - Validated geometry integrity
  - Removed duplicate entries
  - **Total facilities extracted**: 458

#### 3.1.2 Public Transit Data
- **Source**: General Transit Feed Specification (GTFS) data from Chattanooga Area Regional Transportation Authority (CARTA)
- **Temporal Coverage**: 2024-2025 service schedules
- **Components**:
  - `stops.txt`: Transit stop locations (latitude/longitude)
  - `routes.txt`: Transit route definitions
  - `trips.txt`: Individual trip instances
  - `stop_times.txt`: Stop-level timing data
- **Processing**:
  - Parsed GTFS format into PostGIS-enabled PostgreSQL database
  - Calculated service frequency metrics (trips per stop per day)
  - Aggregated route diversity (number of unique routes serving each stop)
  - Reprojected stop locations to UTM Zone 16N
  - **Total stops**: 277.0 stops serving candidate locations
  - **System-wide transit capacity**: 1478384.0 daily trips

#### 3.1.3 Census Demographic Data
- **Source**: American Community Survey (ACS) 5-Year Estimates (2019-2023)
- **Geography**: Census block groups
- **Variables**: 
  - Total population
  - Employment by location
  - Household income
  - Commuting patterns (means of transportation, travel time)
  - Vehicle availability
- **Processing**: Joined spatial boundaries with tabular demographic data

#### 3.1.4 Destination Data
- **VW Plant Location**: Manually geocoded based on corporate facility address
  - Latitude: 35.0769491°N
  - Longitude: -85.130555°W
  - Converted to UTM Zone 16N for distance calculations

### 3.2 Data Quality and Limitations

**Parking Capacity Data**: OSM-derived capacity data is crowd-sourced and may contain inaccuracies. Where capacity was missing, conservative estimates were applied based on facility type and area.

**Transit Schedule Data**: GTFS represents scheduled service, not real-time performance. Actual service reliability may vary due to operational factors not captured in the data.

**Temporal Validity**: All data represents conditions as of Q1 2025. Transit service patterns and parking availability may change over time.

---

## 4. METHODOLOGY

### 4.1 Analytical Framework Overview

The analysis employed a four-phase spatial decision support framework:

**Phase 1**: Spatial filtering to identify candidate parking facilities
**Phase 2**: Multi-scenario transit accessibility analysis
**Phase 3**: Multi-criteria scoring and ranking
**Phase 4**: User-specific routing and alternative generation

Each phase is described in detail below.

### 4.2 Phase 1: Spatial Elimination and Candidate Selection

#### 4.2.1 Exclusion Criteria

**Proximity-Based Exclusion**:
Parking facilities located within a **5000m (3.1 mile) exclusion zone** around the VW plant were eliminated from consideration.

*Rationale*: P&R facilities require sufficient spatial separation from the final destination to justify the modal transfer. Sites too close to VW offer minimal advantages over direct driving and would not meaningfully reduce traffic in the destination vicinity. The 5km threshold was selected based on:
- Literature indicating P&R users typically drive 5-15km to facilities (Parkhurst 2000; Holguín-Veras et al. 2012)
- Need to intercept commuters before they enter the immediate plant area
- Buffer size allowing for adequate catchment in suburban Chattanooga context

**Implementation**:
```sql
-- Spatial exclusion using PostGIS
CREATE TABLE vw_exclusion_zone AS
SELECT ST_Buffer(vw_plant_geometry, 5000) as geometry
FROM vw_plant_location;

-- Flag excluded lots
UPDATE parking_lots
SET is_candidate = FALSE
WHERE ST_Intersects(geometry, (SELECT geometry FROM vw_exclusion_zone));
```

**Result**: 50 facilities excluded, 408 retained as candidates.

#### 4.2.2 Transit Availability Requirement

**Minimum Transit Access Criterion**:
Candidate facilities must have at least **1 public transit stop(s)** within walkable distance AND minimum service frequency of **10 trips per day**.

*Rationale*: The fundamental premise of P&R is seamless transfer to public transit. Without proximate transit access, the location fails to function as a P&R facility. The dual criteria (stops + frequency) ensure both spatial access and temporal service reliability.

**Implementation**:
- Three walking distance scenarios tested: 500m, 800m, 1000m
- Used PostGIS `ST_DWithin()` for distance-based spatial queries
- Joined with transit frequency data to calculate service levels

### 4.3 Phase 2: Multi-Scenario Transit Accessibility Analysis

#### 4.3.1 Walking Distance Scenarios

To account for variability in user willingness to walk, three distance scenarios were evaluated:

| Scenario | Distance | Walking Time | Context |
|----------|----------|--------------|---------|
| Conservative | 500m | 5-7 minutes | Typical comfort threshold for most users |
| Moderate | 800m | 8-10 minutes | Acceptable for regular commuters |
| Extended | 1000m | 10-12 minutes | Maximum reasonable walking distance |

These thresholds align with established pedestrian accessibility standards in transportation planning literature (Dill 2003; El-Geneidy et al. 2014).

#### 4.3.2 Accessibility Metrics Calculation

For each parking facility and walking scenario, the following metrics were computed:

**1. Transit Stop Count** ($N_{stops}$):
Number of unique transit stops within walking distance buffer.

**2. Service Frequency** ($F$):
Total number of transit trips per day serving accessible stops:
$$F = \sum_{i=1}^{N_{stops}} \text{trips}_i$$

**3. Service Reliability Score** ($R$):
Categorical score based on headway (time between transit vehicles):
$$R = \begin{cases}
100 & \text{if } F \geq 100 \text{ (≤10 min headway)} \\
80 & \text{if } 50 \leq F < 100 \text{ (≤20 min headway)} \\
60 & \text{if } 30 \leq F < 50 \text{ (≤30 min headway)} \\
40 & \text{if } 15 \leq F < 30 \text{ (≤60 min headway)} \\
20 & \text{if } F < 15 \text{ (>60 min headway)}
\end{cases}$$

*Rationale*: Higher frequency reduces risk that missing one vehicle significantly delays the commute. The thresholds reflect practical service quality levels.

**4. Proximity Score** ($P$):
Inverse distance to nearest stop, normalized to 0-100 scale:
$$P = 100 \times \left(1 - \frac{d_{nearest}}{d_{max}}\right)$$
where $d_{nearest}$ is distance to nearest stop and $d_{max}$ is the maximum observed distance.

**5. Route Diversity Score** ($D$):
Normalized count of unique transit routes serving accessible stops:
$$D = 100 \times \frac{N_{routes}}{\max(N_{routes})}$$

*Rationale*: Multiple routes provide redundancy and more direct paths to various destinations.

#### 4.3.3 Composite Accessibility Score

Individual metrics were combined into a weighted composite accessibility score:

$$A = w_1 \cdot \frac{N_{stops}}{\max(N_{stops})} + w_2 \cdot \frac{F}{\max(F)} + w_3 \cdot R + w_4 \cdot P + w_5 \cdot D$$

**Weights** (summing to 1.0):
- $w_1$ (Number of stops) = 0.25
- $w_2$ (Trip frequency) = 0.3
- $w_3$ (Service reliability) = 0.2
- $w_4$ (Walking distance) = 0.15
- $w_5$ (Route diversity) = 0.1

*Weight Rationale*: 
- **Trip frequency** receives highest weight as it directly determines service availability and wait times
- **Number of stops** important for redundancy (if one stop has issues, others available)
- **Service reliability** captures temporal predictability
- **Walking distance** and **route diversity** are secondary considerations

This weighting scheme was developed through consultation with transportation planning practitioners and literature review.

### 4.4 Phase 3: Multi-Criteria Ranking and Optimization

#### 4.4.1 Ranking Criteria Integration

The final ranking integrated accessibility scores with additional spatial optimization criteria:

**1. Transit Accessibility Score** ($A$): From Phase 2, using best-performing walking scenario for each site

**2. Distance Optimality Score** ($O$):
Preference for locations within optimal distance range from VW plant:
$$O = \begin{cases}
100 & \text{if } d_{VW} \in [8000, 15000]\text{m} \\
100 \times \frac{d_{VW}}{8000} & \text{if } d_{VW} < 8000 \\
\max\left(0, 100 - \frac{d_{VW} - 15000}{10000}\right) & \text{if } d_{VW} > 15000
\end{cases}$$

*Rationale*: 
- Sites < 8.0km are too close (minimal benefit over direct driving)
- Sites 8.0-15.0km offer optimal interception point
- Sites > 15.0km may be too far for practical use

**3. Parking Capacity Score** ($C$):
Normalized parking capacity:
$$C = 100 \times \frac{\text{capacity}}{\max(\text{capacity})}$$

*Rationale*: Larger facilities can serve more users and have lower probability of being full.

#### 4.4.2 Final Composite Score

The final ranking score combined all criteria:

$$S_{final} = \alpha_1 A + \alpha_2 F + \alpha_3 O + \alpha_4 C + \alpha_5 \cdot \mathbb{1}_{optimal}$$

where:
- $\alpha_1$ (Transit accessibility) = 0.4
- $\alpha_2$ (Service frequency) = 0.25
- $\alpha_3$ (Distance optimality) = 0.2
- $\alpha_4$ (Parking capacity) = 0.1
- $\alpha_5$ (Optimal location bonus) = 0.05
- $\mathbb{1}_{optimal}$ is an indicator function (100 if site in optimal distance range, else 50)

**Weight Justification**:
- **Transit accessibility** (40%): Primary determinant of P&R viability
- **Service frequency** (25%): Essential for user convenience and reliability
- **Distance from VW** (20%): Spatial optimization criterion
- **Capacity** (10%): Secondary but important for scalability
- **Optimal location bonus** (5%): Tie-breaker favoring ideal positioning

Sites were ranked in descending order of $S_{final}$ and classified into tiers:
- **Tier 1** (Rank 1-5): Primary recommendations
- **Tier 2** (Rank 6-15): Strong alternatives
- **Tier 3** (Rank 16-30): Viable options
- **Tier 4** (Rank 31+): Marginal sites

**Results**: 288.0 locations ranked, with 5.0 Tier 1 and 10.0 Tier 2 sites identified.

### 4.5 Phase 4: User-Based Routing and Decision Support

#### 4.5.1 Origin-Specific Route Calculation

For personalized recommendations, the system calculates optimal routes from user-specified origins:

**Input**: User residential location (latitude, longitude)

**Process**:
1. Calculate Euclidean distances from origin to all ranked P&R sites
2. Estimate driving time: $t_{drive} = \frac{d_{origin \to P\&R}}{v_{avg}}$ where $v_{avg} = 40$ km/h (average urban speed)
3. Estimate transit time: $t_{transit} = \frac{d_{P\&R \to VW}}{v_{transit}}$ where $v_{transit} = 25$ km/h (average transit speed)
4. Estimate wait time based on service frequency:
   $$t_{wait} = \begin{cases}
   5\text{ min} & F \geq 100 \text{ trips/day} \\
   10\text{ min} & 50 \leq F < 100 \\
   15\text{ min} & 30 \leq F < 50 \\
   20\text{ min} & F < 30
   \end{cases}$$
5. Total travel time: $T_{total} = t_{drive} + t_{wait} + t_{transit}$

**User-Specific Scoring**:
Combines system-wide P&R ranking with origin proximity:
$$S_{user} = 0.70 \times S_{final} + 0.30 \times P_{origin}$$
where $P_{origin} = 100 \times (1 - \frac{d_{origin \to P\&R}}{d_{max}}$ is normalized proximity score.

#### 4.5.2 Alternative Generation

For each user query, the system returns:
1. **Primary recommendation**: Highest $S_{user}$ score
2. **Alternative 1**: Second-highest score
3. **Alternative 2**: Third-highest score

Each alternative includes:
- Route geometry (origin → P&R → VW)
- Estimated travel times for each segment
- Total distance
- Transit service characteristics
- Overall suitability rating

*Rationale*: Multiple alternatives provide user choice and account for personal preferences not captured in the model.

---

## 5. REPRODUCIBILITY CONSIDERATIONS

### 5.1 Software Environment

- **Database**: PostgreSQL 16 with PostGIS 3.4 extension
- **Programming**: Python 3.10+
  - Libraries: `geopandas`, `pandas`, `sqlalchemy`, `numpy`
- **GIS Software**: ArcGIS Pro 3.2 (for visualization and validation)
- **Operating System**: Ubuntu 22.04 LTS (via WSL2 on Windows 11)

### 5.2 Code Availability

All analysis code is version-controlled and documented with inline comments. Key scripts:
- `01_filter_parking_candidates.py`: Spatial filtering
- `02_calculate_accessibility_scores.py`: Multi-scenario accessibility analysis
- `03_rank_and_optimize.py`: Ranking algorithm
- `04_user_routing_system.py`: Personalized routing
- `05_generate_methodology_report.py`: This report generation

### 5.3 Data Availability Statement

- **Public Data**: GTFS transit data, OSM parking data, ACS census data (all publicly accessible)
- **Derived Data**: Processed datasets and analysis results available upon request
- **Proprietary Data**: None used

### 5.4 Replication Protocol

To replicate this analysis for different cities/destinations:

1. Update `config.py` with new destination coordinates and regional parameters
2. Acquire local GTFS and parking data
3. Execute scripts 01-04 in sequence
4. Validate results against local knowledge

Key parameters requiring local calibration:
- Exclusion zone radius (based on urban form)
- Walking distance scenarios (based on local climate/topography)
- Optimal distance range (based on commuting patterns)
- Weight matrices (through stakeholder engagement)

---

## 6. LIMITATIONS AND FUTURE RESEARCH

### 6.1 Study Limitations

**Temporal Dynamics**: Analysis uses static schedule data; does not account for:
- Peak vs. off-peak service variations
- Seasonal schedule changes
- Real-time service disruptions

**Behavioral Assumptions**: 
- Assumes rational site choice based on modeled criteria
- Does not incorporate user preferences for specific amenities (e.g., security, weather protection)
- Walking distance thresholds may not reflect actual behavior for all demographic groups

**Data Quality Dependencies**:
- OSM parking capacity data quality varies
- GTFS represents scheduled, not actual, service
- Does not include emerging mobility services (ride-hailing, microtransit)

**Spatial Abstraction**:
- Uses Euclidean distances and estimated travel times rather than network-based routing
- Does not model actual road network impedances or pedestrian pathways

### 6.2 Future Research Directions

1. **Demand Modeling**: Integrate stated preference surveys or revealed preference data on actual P&R usage
2. **Dynamic Scheduling**: Incorporate real-time transit data and traffic conditions
3. **Cost-Benefit Analysis**: Add economic evaluation of P&R implementation costs vs. benefits
4. **Mode Choice Integration**: Embed within broader regional travel demand models
5. **Equity Analysis**: Assess P&R accessibility across income and demographic groups
6. **Sensitivity Analysis**: Test robustness of rankings to weight variations
7. **Longitudinal Evaluation**: Track actual usage post-implementation to validate predictions

---

## 7. CONCLUSIONS

This research demonstrates a rigorous, reproducible methodology for P&R site evaluation in employment-center contexts. By integrating spatial optimization, transit accessibility analysis, and user-specific routing, the framework provides actionable recommendations for transportation planning agencies and employers seeking to promote sustainable commuting alternatives.

The case study application to VW Chattanooga yielded 5.0 primary candidate sites with excellent transit connectivity and 10.0 strong alternatives, providing a robust foundation for P&R system implementation. The multi-criteria approach ensures that selected sites balance accessibility, convenience, and operational feasibility.

Key methodological contributions include:
1. Integration of multiple walking distance scenarios to account for user heterogeneity
2. Explicit quantification of service reliability as a distinct accessibility dimension
3. User-specific routing system enabling personalized recommendations
4. Comprehensive documentation facilitating replication in other contexts

The framework presented here can guide evidence-based transportation policy development in similar settings where Park-and-Ride interventions are being considered to support sustainable mobility transitions.

---

## REFERENCES

Dill, J. (2003). Transit use and proximity to rail: Results from large employment sites in the San Francisco Bay Area. *Transportation Research Record*, 1835, 19-24.

El-Geneidy, A., Grimsrud, M., Wasfi, R., Tétreault, P., & Surprenant-Legault, J. (2014). New evidence on walking distances to transit stops: identifying redundancies and gaps using variable service areas. *Transportation*, 41(1), 193-210.

Holguín-Veras, J., Reilly, J., Aros-Vera, F., Yushimito, W., & Isa, J. (2012). Park-and-ride facilities in New York City. *Transportation Research Record*, 2276(1), 123-130.

Parkhurst, G. (2000). Link-and-ride: A longer-range strategy for car-bus interchange. *Traffic Engineering and Control*, 41(8), 319-324.

---

## APPENDIX: ANALYSIS SUMMARY STATISTICS

### Spatial Filtering Results
- Total parking facilities in study area: 458
- Facilities excluded (within 5000m of VW): 50
- Candidate facilities retained: 408

### Transit Accessibility Results
- Facilities with adequate transit access (800m scenario): 277.0
- Average stops per accessible facility: 43.9
- Total system transit capacity (trips/day): 1,478,384.0

### Final Rankings
- Sites successfully ranked: 288.0
- Tier 1 (Primary) recommendations: 5.0
- Tier 2 (Strong Alternative) recommendations: 10.0
- Average composite score: 48.98/100
- Score range: 27.16 - 84.77

---

**Report Generated**: 2026-01-26 18:12:10
**Software**: VW Chattanooga P&R Analysis System v1.0
**Analyst**: Automated Methodology Report Generator
