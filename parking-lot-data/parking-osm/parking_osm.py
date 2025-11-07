import pandas as pd
from geopy.geocoders import Nominatim
import time
import folium

df = pd.read_excel('parking-lot-data/parking-osm/Aquarium Count 4-20-17.xlsx')
df['Latitude'] = None
df['Longitude'] = None

geolocator = Nominatim(user_agent="chattanooga_parking_mapper")

def fetch_location(loc_name):
    try:
        full_address = f"{loc_name}, Chattanooga, Tennessee"
        location = geolocator.geocode(full_address)
        time.sleep(1)
        if location:
            return location.latitude, location.longitude
        else:
            return None, None
    except:
        return None, None

for i, loc_name in enumerate(df['Loc Name']):
    lat, lon = fetch_location(loc_name)
    df.at[i, 'Latitude'] = lat
    df.at[i, 'Longitude'] = lon

# Center map over Chattanooga
center_lat, center_lon = 35.0456, -85.3097
m = folium.Map(location=[center_lat, center_lon], zoom_start=14)

# Add labeled markers
for idx, row in df.iterrows():
    if row['Latitude'] and row['Longitude']:
        folium.Marker(
            [row['Latitude'], row['Longitude']],
            popup=row['Loc Name']
        ).add_to(m)

m.save('chattanooga_parking_map.html')
