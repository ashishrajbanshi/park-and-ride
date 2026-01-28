import pandas as pd
import json

# Function to convert row to GeoJSON Feature
def row_to_feature(row):
    return {
        "type": "Feature",
        "geometry": {
            "type": "Point",
            "coordinates": [row['Longitude'], row['Latitude']]
        },
        "properties": {
            "Name": row['Name'],
            "Capacity": row['Capacity'],
            "Type": row['Type']
        }
    }

if __name__ == '__main__':
    # Load the CSV file
    df = pd.read_csv('top_100_parking_lots.csv')

    # Verify columns
    print(df.head())
    print(df.columns)

    # Create Feature Collection
    geojson = {
        "type": "FeatureCollection",
        "features": df.apply(row_to_feature, axis=1).tolist()
    }

    # Save to file
    output_filename = 'top_100_parking_lots.geojson'
    with open(output_filename, 'w') as f:
        json.dump(geojson, f)

    print(f"File saved as {output_filename}")