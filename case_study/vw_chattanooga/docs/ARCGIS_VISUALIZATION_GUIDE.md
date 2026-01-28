# ArcGIS Pro Visualization Guide
## VW Chattanooga P&R Case Study

---

## 1. DATABASE CONNECTION

### Step 1: Connect to PostgreSQL Database

1. Open **ArcGIS Pro**
2. **Catalog Pane** → Databases → Right-click → **New Database Connection**
3. Fill in connection details:
```
   Database Platform: PostgreSQL
   Instance: localhost
   Database: chattanooga_parkride
   Authentication: Database authentication
   Username: postgres
   Password: [your_password]
```
4. Click **OK**
5. Connection should appear as `Chattanooga_ParkRide_DB.sde`

---

## 2. ADD VW CASE STUDY LAYERS

### Step 2.1: Add VW Plant Location

1. In Catalog, expand your database connection
2. Find `vw_plant_location`
3. Drag to map
4. **Symbology**:
   - Symbol: Star (large, red)
   - Size: 18
   - Label: "VW Chattanooga Plant"

### Step 2.2: Add Exclusion Zone

1. Find `vw_exclusion_zone`
2. Drag to map
3. **Symbology**:
   - Fill: Red, 30% transparency
   - Outline: Red, dashed, width 2
   - Label: "5km Exclusion Zone"

### Step 2.3: Add Parking Lots with Rankings

1. Find `vw_parkride_final_map`
2. Drag to map
3. **Symbology** → Graduated Colors:
   - Field: `final_composite_score`
   - Method: Natural Breaks
   - Classes: 5
   - Color Scheme: Red-Orange-Yellow-Green (reverse so green = high)
4. **Symbol Size**: Vary by rank
   - Click "Vary symbology by attribute"
   - Size field: `capacity`
   - Min size: 8, Max size: 20

### Step 2.4: Add Transit Stops

1. Find `transit_stops`
2. Drag to map
3. **Symbology**:
   - Symbol: Bus stop icon (or circle)
   - Color: Blue
   - Size: 6

### Step 2.5: Add Census Blocks (Background)

1. Find `census_blocks`
2. Drag to map
3. **Symbology** → Graduated Colors:
   - Field: `pop_density`
   - Method: Natural Breaks
   - Colors: Light yellow to light gray
   - Transparency: 50%

---

## 3. CREATE THEMATIC MAPS

### Map 1: Overview Map with All Candidates

**Purpose**: Show all parking candidates relative to VW plant

**Layers** (top to bottom):
1. VW Plant (star symbol)
2. Top 5 P&R sites (large green circles, labeled)
3. Other ranked sites (graduated colors)
4. Exclusion zone (red boundary)
5. Transit stops (small blue dots)
6. Census blocks (light fill)

**Labels**:
- Label top 10 sites with: `name + " (Rank #" + final_rank + ")"`

### Map 2: Walking Scenario Comparison

**Purpose**: Show how accessibility changes with walking distance

**Create 3 map frames side-by-side**:
1. **Conservative** (500m)
   - Add `parking_walk_400m` buffers
   - Show only sites with transit in 500m
   
2. **Moderate** (800m)
   - Add `parking_walk_800m` buffers
   - Show sites with transit in 800m
   
3. **Extended** (1000m)
   - Add `parking_drive_3km` buffers
   - Show all sites with transit in 1000m

### Map 3: Transit Service Quality

**Purpose**: Classify sites by transit service level

**Symbology**:
- Unique Values on `service_quality`
- Colors:
  - "Excellent" → Dark Green
  - "Good" → Light Green
  - "Fair" → Yellow
  - "Limited" → Orange
  - "Poor" → Red

### Map 4: User Routing Example

**Purpose**: Show example employee routes

1. Add origin points (use example coordinates from routing script)
2. Add route lines (from routing results)
3. Symbolize by recommendation:
   - Primary route: Thick green line
   - Alternative 1: Medium orange line
   - Alternative 2: Thin blue line

---

## 4. CREATE ANALYSIS LAYOUTS

### Layout 1: Executive Summary

**Page**: Letter, Landscape

**Elements**:
1. **Title**: "VW Chattanooga Park-and-Ride Site Analysis"
2. **Main Map**: Overview map (60% of page)
3. **Inset Map**: Regional context (15% of page)
4. **Legend**: Ranked sites, VW plant, exclusion zone
5. **Statistics Box**:
```
   Total Sites Analyzed: [count]
   Tier 1 Recommendations: [count]
   Average Transit Access Score: [avg]
```
6. **Top 5 Table**: 
   | Rank | Location | Score | Distance | Transit |
   |------|----------|-------|----------|---------|

### Layout 2: Methodology Diagram

**Page**: Letter, Portrait

**Elements**:
1. **Flowchart**: 4-phase process
2. **Map examples** for each phase
3. **Text boxes** explaining criteria

### Layout 3: Scenario Comparison

**Page**: Tabloid, Landscape

**Elements**:
1. **Three maps side-by-side** (walking scenarios)
2. **Comparison table** showing site counts
3. **Chart**: Bar graph of accessibility by scenario

---

## 5. EXPORT DELIVERABLES

### Export Maps

1. **Share** → Export Layout
2. Format: PDF
3. Resolution: 300 DPI
4. Save locations:
   - `Executive_Summary_Map.pdf`
   - `Methodology_Diagram.pdf`
   - `Scenario_Comparison.pdf`

### Export Data

1. Right-click `vw_parkride_tiers` → Export
2. Format: Shapefile
3. Location: `case_study/vw_chattanooga/results/shapefiles/`

### Create Map Package

1. **Share** → Map Package
2. Include:
   - All layers
   - Data sources
   - Layout templates
3. Save as: `VW_Chattanooga_ParkRide_Analysis.mpkx`

---

## 6. INTERACTIVE WEB MAP (OPTIONAL)

### Export to ArcGIS Online

1. **Share** → Web Map
2. Set permissions: Organization/Public
3. Configure pop-ups:
   - Show: Rank, Score, Transit Info, Distance
   - Add images if available
4. Publish

### Add Routing Tool

1. In Web Map, add **Directions widget**
2. Configure:
   - Origin: User input
   - Destination: VW Plant
   - Stops: Top 3 P&R sites for that origin
3. Save and share URL

---

## 7. QUALITY CHECKS

### Verify:
- [ ] All layers display correctly
- [ ] Labels are readable at 1:50,000 scale
- [ ] Colors are colorblind-friendly
- [ ] Legend is complete and clear
- [ ] North arrow and scale bar present
- [ ] Metadata is complete
- [ ] Coordinate system is consistent (UTM Zone 16N)

---

## TROUBLESHOOTING

**Issue**: Layers don't display
- **Fix**: Check CRS - all should be EPSG:32616

**Issue**: Database connection fails
- **Fix**: Ensure PostgreSQL is running in WSL: `sudo service postgresql start`

**Issue**: Slow performance
- **Fix**: Create spatial indexes:
```sql
  CREATE INDEX idx_parking_geom ON parking_lots USING GIST(geometry);
```

---

**End of Visualization Guide**