"""
Interactive P&R Route Calculator for VW Chattanooga Employees

Usage:
    python calculate_my_route.py <latitude> <longitude> <origin_name>

Example:
    python calculate_my_route.py 35.0456 -85.3097 "My Home"
"""

import sys
sys.path.append('../../scripts')

from config import *
from sqlalchemy import create_engine
import pandas as pd

if len(sys.argv) < 3:
    print("Usage: python calculate_my_route.py <latitude> <longitude> [origin_name]")
    print("Example: python calculate_my_route.py 35.0456 -85.3097 'My Home'")
    sys.exit(1)

lat = float(sys.argv[1])
lon = float(sys.argv[2])
name = sys.argv[3] if len(sys.argv) > 3 else "My Location"

# Import routing function
import importlib
routing = importlib.import_module('04_user_routing_system')

# Calculate routes
result = routing.calculate_routes_from_origin(lat, lon, name)

if result is not None:
    print("\n✅ Route calculation complete!")
    print("Check the output above for your personalized P&R recommendations.")
else:
    print("\n❌ No suitable routes found. Try a different origin location.")
