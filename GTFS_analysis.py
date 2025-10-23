import pandas as pd
import zipfile
import numpy as np
from datetime import datetime, timedelta
from math import radians, cos, sin, asin, sqrt
import warnings
warnings.filterwarnings('ignore')

# For Colab environment
#from google.colab import drive
#drive.mount('/content/drive')

# Path to your GTFS file
gtfs_path = r'C:\Users\kpk628\OneDrive - University of Tennessee\Documents\CUIP Projects\TNGO-BOC\GTFS.zip'

# Function to read GTFS files
def read_gtfs_file(zip_path, filename):
    """Read a specific file from GTFS zip archive"""
    with zipfile.ZipFile(zip_path, 'r') as zip_ref:
        if filename in zip_ref.namelist():
            with zip_ref.open(filename) as file:
                return pd.read_csv(file)
    return pd.DataFrame()

# Load all necessary GTFS files
print("Loading GTFS data...")
agency = read_gtfs_file(gtfs_path, 'agency.txt')
stops = read_gtfs_file(gtfs_path, 'stops.txt')
routes = read_gtfs_file(gtfs_path, 'routes.txt')
trips = read_gtfs_file(gtfs_path, 'trips.txt')
stop_times = read_gtfs_file(gtfs_path, 'stop_times.txt')
shapes = read_gtfs_file(gtfs_path, 'shapes.txt')
calendar = read_gtfs_file(gtfs_path, 'calendar.txt')
calendar_dates = read_gtfs_file(gtfs_path, 'calendar_dates.txt')

print(f"✅ Loaded {len(routes)} routes, {len(trips)} trips, {len(stop_times)} stop times")

# ============================================
# HELPER FUNCTIONS
# ============================================

def parse_gtfs_time(time_str):
    """Parse GTFS time format (can be > 24:00:00)"""
    if pd.isna(time_str):
        return None
    parts = str(time_str).split(':')
    if len(parts) != 3:
        return None
    try:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = int(parts[2])
        return hours * 3600 + minutes * 60 + seconds
    except:
        return None

def seconds_to_time_str(seconds):
    """Convert seconds to readable time format"""
    if pd.isna(seconds) or seconds is None:
        return None
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    return f"{hours}h {minutes}m"

def get_hour_from_gtfs_time(time_str):
    """Extract hour from GTFS time string"""
    if pd.isna(time_str):
        return None
    try:
        hour = int(str(time_str).split(':')[0])
        return hour if hour < 24 else hour - 24
    except:
        return None

def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate distance in miles between two coordinates using Haversine formula"""
    R = 3959  # Radius of earth in miles
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    return R * c

# ============================================
# STEP 1: CALCULATE TRIP DETAILS
# ============================================
print("\n📊 Processing trip data...")

trip_details = []

for trip_id in trips['trip_id'].unique():
    trip_stops = stop_times[stop_times['trip_id'] == trip_id].sort_values('stop_sequence')

    if len(trip_stops) > 0:
        trip_info = trips[trips['trip_id'] == trip_id].iloc[0]

        # Parse times
        first_stop_time = parse_gtfs_time(trip_stops.iloc[0]['arrival_time'])
        last_stop_time = parse_gtfs_time(trip_stops.iloc[-1]['arrival_time'])
        start_hour = get_hour_from_gtfs_time(trip_stops.iloc[0]['arrival_time'])

        if first_stop_time and last_stop_time:
            travel_time = last_stop_time - first_stop_time

            # Determine time period
            time_period = 'Off-Peak'
            if start_hour in [6, 7, 8, 9]:
                time_period = 'Morning Peak'
            elif start_hour in [10, 11, 12, 13, 14, 15]:
                time_period = 'Midday'
            elif start_hour in [16, 17, 18, 19]:
                time_period = 'Evening Peak'

            # Determine day type from service_id
            service_id = trip_info['service_id']
            day_type = 'Unknown'
            if len(calendar) > 0:
                service_cal = calendar[calendar['service_id'] == service_id]
                if len(service_cal) > 0:
                    cal_row = service_cal.iloc[0]
                    weekday = cal_row['monday'] or cal_row['tuesday'] or cal_row['wednesday'] or cal_row['thursday'] or cal_row['friday']
                    weekend = cal_row['saturday'] or cal_row['sunday']
                    if weekday and not weekend:
                        day_type = 'Weekday'
                    elif weekend and not weekday:
                        day_type = 'Weekend'
                    elif weekday and weekend:
                        day_type = 'Daily'

            trip_details.append({
                'trip_id': trip_id,
                'route_id': trip_info['route_id'],
                'service_id': service_id,
                'direction_id': trip_info.get('direction_id', 0),
                'num_stops': len(trip_stops),
                'travel_time_seconds': travel_time,
                'start_hour': start_hour,
                'time_period': time_period,
                'day_type': day_type
            })

trip_details_df = pd.DataFrame(trip_details)
print(f"✅ Processed {len(trip_details_df)} trips")

# ============================================
# STEP 2: CALCULATE ROUTE DISTANCES
# ============================================
print("\n📏 Calculating route distances...")

route_distances = {}

# Method 1: Use shapes if available
if len(shapes) > 0:
    for route_id in routes['route_id']:
        route_trips = trips[trips['route_id'] == route_id]
        if len(route_trips) > 0:
            shape_ids = route_trips['shape_id'].unique()
            max_distance = 0

            for shape_id in shape_ids:
                if pd.notna(shape_id):
                    shape_points = shapes[shapes['shape_id'] == shape_id].sort_values('shape_pt_sequence')
                    if len(shape_points) > 1:
                        total_distance = 0
                        for i in range(len(shape_points) - 1):
                            dist = calculate_distance(
                                shape_points.iloc[i]['shape_pt_lat'],
                                shape_points.iloc[i]['shape_pt_lon'],
                                shape_points.iloc[i + 1]['shape_pt_lat'],
                                shape_points.iloc[i + 1]['shape_pt_lon']
                            )
                            total_distance += dist
                        max_distance = max(max_distance, total_distance)

            route_distances[route_id] = round(max_distance, 2)

# Method 2: If no shapes, estimate from stops
if len(route_distances) == 0:
    for route_id in routes['route_id']:
        route_trips = trip_details_df[trip_details_df['route_id'] == route_id]['trip_id']
        if len(route_trips) > 0:
            # Get a sample trip
            sample_trip = route_trips.iloc[0]
            trip_stops = stop_times[stop_times['trip_id'] == sample_trip].sort_values('stop_sequence')

            if len(trip_stops) > 1:
                total_distance = 0
                for i in range(len(trip_stops) - 1):
                    stop1 = stops[stops['stop_id'] == trip_stops.iloc[i]['stop_id']]
                    stop2 = stops[stops['stop_id'] == trip_stops.iloc[i + 1]['stop_id']]

                    if len(stop1) > 0 and len(stop2) > 0:
                        dist = calculate_distance(
                            stop1.iloc[0]['stop_lat'], stop1.iloc[0]['stop_lon'],
                            stop2.iloc[0]['stop_lat'], stop2.iloc[0]['stop_lon']
                        )
                        total_distance += dist * 1.3  # Add 30% for actual road distance

                route_distances[route_id] = round(total_distance, 2)

print(f"✅ Calculated distances for {len(route_distances)} routes")

# ============================================
# STEP 3: COMPREHENSIVE ROUTE ANALYSIS
# ============================================
print("\n📈 Creating comprehensive route analysis...")

comprehensive_table = []

for route_id in routes['route_id']:
    route_info = routes[routes['route_id'] == route_id].iloc[0]
    route_trips = trip_details_df[trip_details_df['route_id'] == route_id]

    if len(route_trips) == 0:
        continue

    # Basic route info
    route_data = {
        'route_id': route_id,
        'route_short_name': route_info.get('route_short_name', ''),
        'route_long_name': route_info.get('route_long_name', ''),
    }

    # Travel time statistics (in minutes for readability)
    route_data['avg_travel_time_min'] = round(route_trips['travel_time_seconds'].mean() / 60, 1)
    route_data['min_travel_time_min'] = round(route_trips['travel_time_seconds'].min() / 60, 1)
    route_data['max_travel_time_min'] = round(route_trips['travel_time_seconds'].max() / 60, 1)
    route_data['travel_time_std_min'] = round(route_trips['travel_time_seconds'].std() / 60, 1)

    # Trip counts
    route_data['total_trips_in_gtfs'] = len(route_trips)
    route_data['avg_stops'] = round(route_trips['num_stops'].mean(), 0)
    route_data['max_stops'] = route_trips['num_stops'].max()

    # Service patterns
    weekday_trips = route_trips[route_trips['day_type'] == 'Weekday']
    weekend_trips = route_trips[route_trips['day_type'] == 'Weekend']
    daily_trips = route_trips[route_trips['day_type'] == 'Daily']

    route_data['weekday_trips'] = len(weekday_trips) + len(daily_trips)
    route_data['weekend_trips'] = len(weekend_trips) + len(daily_trips)

    # Calculate estimated daily trips
    total_days = 7  # Assume weekly schedule
    weekday_days = 5
    weekend_days = 2

    if route_data['weekday_trips'] > 0 and route_data['weekend_trips'] > 0:
        route_data['avg_trips_per_day'] = round(
            (route_data['weekday_trips'] / weekday_days * 5 +
             route_data['weekend_trips'] / weekend_days * 2) / 7, 1
        )
    elif route_data['weekday_trips'] > 0:
        route_data['avg_trips_per_day'] = round(route_data['weekday_trips'] / weekday_days, 1)
    elif route_data['weekend_trips'] > 0:
        route_data['avg_trips_per_day'] = round(route_data['weekend_trips'] / weekend_days, 1)
    else:
        route_data['avg_trips_per_day'] = round(len(route_trips) / 7, 1)

    # Service pattern description
    if route_data['weekday_trips'] > 0 and route_data['weekend_trips'] > 0:
        route_data['service_pattern'] = 'Daily'
    elif route_data['weekday_trips'] > 0:
        route_data['service_pattern'] = 'Weekday'
    elif route_data['weekend_trips'] > 0:
        route_data['service_pattern'] = 'Weekend'
    else:
        route_data['service_pattern'] = 'Unknown'

    # Route length
    route_data['route_length_miles'] = route_distances.get(route_id, 0)

    # Route complexity (number of shape points or stops)
    if len(shapes) > 0:
        route_shapes = shapes[shapes['shape_id'].isin(
            trips[trips['route_id'] == route_id]['shape_id'].unique()
        )]
        route_data['route_complexity'] = len(route_shapes)
    else:
        route_data['route_complexity'] = route_data['avg_stops'] * 10  # Estimate

    # Travel times by period
    for period in ['Morning Peak', 'Midday', 'Evening Peak', 'Off-Peak']:
        period_trips = route_trips[route_trips['time_period'] == period]
        if len(period_trips) > 0:
            route_data[f'{period}_avg_min'] = round(period_trips['travel_time_seconds'].mean() / 60, 1)
            route_data[f'{period}_trips'] = len(period_trips)
        else:
            route_data[f'{period}_avg_min'] = 0
            route_data[f'{period}_trips'] = 0

    # Find longest travel time details
    longest_trip = route_trips.loc[route_trips['travel_time_seconds'].idxmax()]
    route_data['longest_time_min'] = round(longest_trip['travel_time_seconds'] / 60, 1)
    route_data['longest_time_period'] = longest_trip['time_period']
    route_data['longest_time_day_type'] = longest_trip['day_type']

    # Calculate average speed (mph)
    if route_data['route_length_miles'] > 0 and route_data['avg_travel_time_min'] > 0:
        route_data['avg_speed_mph'] = round(
            route_data['route_length_miles'] / (route_data['avg_travel_time_min'] / 60), 1
        )
    else:
        route_data['avg_speed_mph'] = 0

    comprehensive_table.append(route_data)

# Create DataFrame
comprehensive_df = pd.DataFrame(comprehensive_table)

# Sort by route_short_name or route_id
comprehensive_df = comprehensive_df.sort_values(
    by=['route_short_name', 'route_id'],
    na_position='last'
)

# ============================================
# STEP 4: DISPLAY RESULTS
# ============================================
print("\n" + "="*60)
print("📊 COMPREHENSIVE ROUTE ANALYSIS TABLE")
print("="*60)

# Select columns for display
display_columns = [
    'route_id', 'route_short_name', 'route_long_name',
    'avg_travel_time_min', 'min_travel_time_min', 'max_travel_time_min',
    'total_trips_in_gtfs', 'avg_trips_per_day',
    'avg_stops', 'route_length_miles', 'avg_speed_mph',
    'service_pattern', 'weekday_trips', 'weekend_trips',
    'Morning Peak_avg_min', 'Midday_avg_min', 'Evening Peak_avg_min', 'Off-Peak_avg_min',
    'longest_time_min', 'longest_time_day_type', 'route_complexity'
]

# Create display dataframe with renamed columns for clarity
display_df = comprehensive_df[display_columns].copy()
display_df.columns = [
    'Route ID', 'Short Name', 'Long Name',
    'Avg Time (min)', 'Min Time (min)', 'Max Time (min)',
    'Total Trips', 'Daily Trips',
    'Avg Stops', 'Length (mi)', 'Speed (mph)',
    'Service', 'Weekday Trips', 'Weekend Trips',
    'Morning Peak', 'Midday', 'Evening Peak', 'Off-Peak',
    'Longest (min)', 'Longest Day', 'Complexity'
]

print("\n📈 ROUTE SUMMARY TABLE:")
print(display_df.to_string(index=False))

# ============================================
# STEP 5: STATISTICAL SUMMARY
# ============================================
print("\n" + "="*60)
print("📊 SYSTEM-WIDE STATISTICS")
print("="*60)

print(f"\n🚌 OVERALL METRICS:")
print(f"  • Total Routes: {len(comprehensive_df)}")
print(f"  • Total Trips: {comprehensive_df['total_trips_in_gtfs'].sum()}")
print(f"  • Average Route Length: {comprehensive_df['route_length_miles'].mean():.1f} miles")
print(f"  • Average Travel Time: {comprehensive_df['avg_travel_time_min'].mean():.1f} minutes")
print(f"  • Average Speed: {comprehensive_df['avg_speed_mph'].mean():.1f} mph")

print(f"\n📅 SERVICE PATTERNS:")
service_counts = comprehensive_df['service_pattern'].value_counts()
for pattern, count in service_counts.items():
    print(f"  • {pattern}: {count} routes")

print(f"\n⏰ PEAK PERIOD ANALYSIS:")
print(f"  • Morning Peak Avg: {comprehensive_df['Morning Peak_avg_min'].mean():.1f} min")
print(f"  • Evening Peak Avg: {comprehensive_df['Evening Peak_avg_min'].mean():.1f} min")
print(f"  • Off-Peak Avg: {comprehensive_df['Off-Peak_avg_min'].mean():.1f} min")

peak_delay = comprehensive_df['Morning Peak_avg_min'].mean() - comprehensive_df['Off-Peak_avg_min'].mean()
print(f"  • Peak Hour Delay: +{peak_delay:.1f} minutes")

print(f"\n🎯 ROUTES FOR PARK-AND-RIDE CONSIDERATION:")
print("  (High frequency, consistent times, good coverage)")

# Identify best park-and-ride candidates
comprehensive_df['pr_score'] = (
    comprehensive_df['avg_trips_per_day'] / comprehensive_df['avg_trips_per_day'].max() * 40 +  # Frequency
    (1 - comprehensive_df['travel_time_std_min'] / comprehensive_df['avg_travel_time_min']) * 30 +  # Consistency
    comprehensive_df['route_length_miles'] / comprehensive_df['route_length_miles'].max() * 30  # Coverage
)

top_pr_routes = comprehensive_df.nlargest(5, 'pr_score')[
    ['route_short_name', 'route_long_name', 'avg_trips_per_day', 'avg_travel_time_min', 'route_length_miles']
]

for idx, row in top_pr_routes.iterrows():
    print(f"\n  • Route {row['route_short_name']}: {row['route_long_name']}")
    print(f"    - {row['avg_trips_per_day']:.0f} trips/day, {row['avg_travel_time_min']:.0f} min avg, {row['route_length_miles']:.1f} miles")

# ============================================
# STEP 6: SAVE RESULTS
# ============================================
import os

# Create output folder if it doesn't exist
output_folder = 'output'
os.makedirs(output_folder, exist_ok=True)

# Save files to output folder
output_path = os.path.join(output_folder, 'comprehensive_route_analysis.csv')
comprehensive_df.to_csv(output_path, index=False)
print(f"\n✅ Complete analysis saved to: {output_path}")

# Create essential summary with error handling
try:
    essential_df = comprehensive_df[[
        'route_id', 'route_short_name', 'route_long_name',
        'avg_travel_time_min', 'avg_trips_per_day', 'route_length_miles',
        'service_pattern', 'Morning Peak_avg_min', 'Evening Peak_avg_min'
    ]]
    essential_path = os.path.join(output_folder, 'route_analysis_essential.csv')
    essential_df.to_csv(essential_path, index=False)
    print(f"✅ Essential summary saved to: {essential_path}")
except KeyError as e:
    print(f"⚠️ Could not create essential summary - missing column: {e}")
    print("Available columns:", list(comprehensive_df.columns))
except Exception as e:
    print(f"⚠️ Could not create essential summary: {e}")

print("\n" + "="*60)
print("✅ ANALYSIS COMPLETE!")
print("="*60)