# GTFS Transit Route Analysis Tool

## Overview

This Python script performs comprehensive analysis of General Transit Feed Specification (GTFS) data to extract insights about transit routes, including travel times, service patterns, route distances, and system-wide statistics. The tool is particularly useful for transit planning, identifying park-and-ride candidates, and understanding transit system performance.

## High-Level Architecture

The code follows a structured pipeline approach:

```
GTFS ZIP File → Data Loading → Trip Processing → Route Analysis → Statistical Summary → Export Results
```

## Key Features

- **Complete GTFS Analysis**: Processes all standard GTFS files (routes, trips, stops, stop_times, shapes, calendar)
- **Travel Time Calculations**: Computes average, minimum, and maximum travel times for each route
- **Service Pattern Detection**: Identifies weekday, weekend, and daily service patterns
- **Peak Hour Analysis**: Analyzes performance during morning peak, midday, evening peak, and off-peak periods
- **Route Distance Calculation**: Uses shape data or stop coordinates to calculate route lengths
- **Park-and-Ride Scoring**: Identifies optimal routes for park-and-ride implementation
- **Speed Analysis**: Calculates average speeds for routes based on distance and travel time

## Code Structure

### 1. **Data Loading Module** (Lines 1-36)
- Loads GTFS data from a ZIP archive
- Reads standard GTFS files: agency, stops, routes, trips, stop_times, shapes, calendar, and calendar_dates
- Uses `read_gtfs_file()` function to extract CSV files from ZIP

### 2. **Helper Functions** (Lines 39-83)
Essential utility functions for data processing:
- `parse_gtfs_time()`: Handles GTFS time format (supports times > 24:00:00)
- `seconds_to_time_str()`: Converts seconds to human-readable format
- `get_hour_from_gtfs_time()`: Extracts hour for time period classification
- `calculate_distance()`: Implements Haversine formula for geographic distance calculation

### 3. **Trip Detail Processing** (Lines 85-144)
Processes individual trips to extract:
- Number of stops per trip
- Total travel time
- Time period classification (Morning Peak, Midday, Evening Peak, Off-Peak)
- Day type identification (Weekday, Weekend, Daily)
- Service pattern analysis

### 4. **Route Distance Calculation** (Lines 146-202)
Two-method approach for calculating route distances:
- **Method 1**: Uses GTFS shapes data if available (more accurate)
- **Method 2**: Falls back to stop-to-stop distances using coordinates

### 5. **Comprehensive Route Analysis** (Lines 204-309)
Creates detailed metrics for each route:
- Average, minimum, and maximum travel times
- Standard deviation of travel times (consistency measure)
- Total trips and average trips per day
- Weekday vs weekend service levels
- Time period-specific performance metrics
- Route complexity scoring
- Average speed calculations

### 6. **Results Display & Export** (Lines 311-428)
- Generates formatted tables for route analysis
- Calculates system-wide statistics
- Identifies top park-and-ride candidate routes using a scoring algorithm
- Exports results to CSV files

## Key Algorithms

### Park-and-Ride Scoring Algorithm
```python
Score = (Frequency × 0.4) + (Consistency × 0.3) + (Coverage × 0.3)
```
Where:
- **Frequency**: Normalized daily trip count
- **Consistency**: Inverse of travel time variation
- **Coverage**: Normalized route length

### Time Period Classification
- **Morning Peak**: 6:00 AM - 10:00 AM
- **Midday**: 10:00 AM - 4:00 PM  
- **Evening Peak**: 4:00 PM - 8:00 PM
- **Off-Peak**: All other times

## Output Files

The script generates two CSV files in the `output/` directory:

1. **`comprehensive_route_analysis.csv`**: Complete analysis with all metrics
2. **`route_analysis_essential.csv`**: Simplified summary with key metrics

## Output Metrics

### Route-Level Metrics
- Route identification (ID, short name, long name)
- Travel time statistics (average, min, max, standard deviation)
- Trip counts (total, weekday, weekend, by time period)
- Physical characteristics (length, number of stops, complexity)
- Performance metrics (average speed, peak hour delays)

### System-Wide Statistics
- Total routes and trips
- Average route length and travel time
- Service pattern distribution
- Peak vs off-peak performance comparison
- Top park-and-ride candidate routes

## Requirements

### Python Libraries
```python
pandas       # Data manipulation
numpy        # Numerical operations
zipfile      # GTFS ZIP file handling
datetime     # Time calculations
math         # Haversine distance formula
warnings     # Suppress unnecessary warnings
```

### Data Requirements
- Valid GTFS feed in ZIP format
- Minimum required GTFS files:
  - `routes.txt`
  - `trips.txt`
  - `stop_times.txt`
  - `stops.txt`
- Optional but recommended:
  - `shapes.txt` (for accurate distance calculation)
  - `calendar.txt` (for service pattern analysis)
  - `calendar_dates.txt` (for exceptions)

## Installation & Usage

1. **Install required packages**:
```bash
pip install pandas numpy
```

2. **Configure GTFS path**:
```python
gtfs_path = r'path/to/your/GTFS.zip'
```

3. **Run the script**:
```bash
python GTFS_analysis.py
```

## Configuration

The script can be easily modified for different environments:

### For Google Colab
Uncomment lines 10-11:
```python
from google.colab import drive
drive.mount('/content/drive')
```

### Customizing Time Periods
Modify the time period classification in lines 107-113 to match your transit agency's peak definitions.

### Adjusting Park-and-Ride Scoring
Modify the weights in lines 382-386 to prioritize different factors for park-and-ride selection.

## Key Insights Generated

1. **Route Performance**: Identifies which routes have consistent vs variable travel times
2. **Peak Hour Impact**: Quantifies delays during peak periods
3. **Service Gaps**: Highlights routes with limited weekend or off-peak service
4. **Park-and-Ride Opportunities**: Ranks routes by suitability for park-and-ride facilities
5. **System Efficiency**: Calculates average speeds to identify slow corridors

## Limitations & Considerations

- **Distance Accuracy**: Route distances are estimates when shapes.txt is unavailable
- **Time Assumptions**: Assumes scheduled times represent actual performance
- **Service Patterns**: Calendar-based analysis may not capture all service variations
- **Memory Usage**: Large GTFS feeds may require significant RAM

## Future Enhancements

Potential improvements for extended functionality:
- Real-time GTFS integration for actual vs scheduled comparison
- Stop-level boarding analysis
- Transfer pattern detection
- Accessibility analysis
- Geographic visualization of results
- Multi-agency GTFS comparison

## Error Handling

The script includes robust error handling:
- Gracefully handles missing GTFS files
- Falls back to alternative calculation methods when data is incomplete
- Provides informative error messages for debugging
- Continues analysis even if some metrics cannot be calculated

## License

This tool is designed for transit planning and analysis purposes. Please ensure compliance with your GTFS data provider's terms of use.

## Author

This analysis tool was developed for the TNGO-BOC project at the University of Tennessee.

---

For questions or improvements, please refer to the inline documentation in the source code.