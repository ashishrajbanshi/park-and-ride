"""
Configuration file for VW Chattanooga P&R Case Study
"""

# VW Chattanooga Assembly Plant Coordinates
VW_PLANT = {
    'name': 'Volkswagen Chattanooga Assembly Plant',
    'latitude': 35.0769491,
    'longitude': -85.1305550,
    'address': '8001 Volkswagen Dr, Chattanooga, TN 37416'
}

# Database connection
DB_CONNECTION = "postgresql://postgres:qrakken@localhost:5432/chattanooga_parkride"

# Spatial Reference System
CRS_WGS84 = 4326  # GPS coordinates
CRS_UTM = 32616   # UTM Zone 16N (meters) for Chattanooga

# CRITICAL PARAMETERS
EXCLUSION_RADIUS_METERS = 8000  # 5km - parking lots within this distance are too close to VW plant

# Walking distance scenarios (meters)
WALKING_SCENARIOS = {
    'conservative': 500,   # 5-7 min walk
    'moderate': 800,       # 8-10 min walk
    'extended': 1000       # 10-12 min walk
}

# Transit accessibility weights
ACCESSIBILITY_WEIGHTS = {
    'num_stops': 0.25,           # Number of transit stops
    'trip_frequency': 0.30,      # Service frequency (trips/day)
    'service_reliability': 0.20, # Consistency of service
    'walking_distance': 0.15,    # Distance to nearest stop
    'route_diversity': 0.10      # Number of different routes
}

# Ranking criteria weights
RANKING_WEIGHTS = {
    'transit_accessibility': 0.40,  # Primary: can you reach transit?
    'service_frequency': 0.25,      # How often does transit come?
    'distance_from_vw': 0.20,       # Not too far, not too close
    'parking_capacity': 0.10,       # Space availability
    'optimal_distance': 0.05        # Sweet spot: 8-15km from VW
}

# Optimal distance range from VW (meters)
OPTIMAL_DISTANCE_MIN = 8000   # 8km (5 miles)
OPTIMAL_DISTANCE_MAX = 15000  # 15km (9.3 miles)

# Minimum transit requirements
MIN_TRANSIT_STOPS = 1
MIN_DAILY_TRIPS = 10  # At least 10 trips per day for reliability

# Output paths
RESULTS_DIR = 'case_study/vw_chattanooga/results'
MAPS_DIR = 'case_study/vw_chattanooga/maps'