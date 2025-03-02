def generate_osm_map(bbox, output_file="osm_map.html"):
    """
    Generates an interactive OpenStreetMap HTML file using Leaflet.js.
    
    :param bbox: Tuple of (min_lat, min_lon, max_lat, max_lon)
    :param output_file: Output HTML filename
    """
    north, south, east, west = bbox
    min_lat, min_lon, max_lat, max_lon = south, east, north, west
    center_lat = (min_lat + max_lat) / 2
    center_lon = (min_lon + max_lon) / 2

    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <title>OSM Map</title>
        <meta charset="utf-8" />
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <style>
            #map {{ height: 600px; width: 100%; }}
        </style>
    </head>
    <body>
        <div id="map"></div>
        <script>
            var map = L.map('map').setView([{center_lat}, {center_lon}], 12);
            L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
                attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            }}).addTo(map);
            
            var bounds = L.latLngBounds(
                [[{min_lat}, {min_lon}], [{max_lat}, {max_lon}]]
            );
            
            L.rectangle(bounds, {{color: "red", weight: 1}}).addTo(map);
            map.fitBounds(bounds);
        </script>
    </body>
    </html>
    """
    
    with open(output_file, "w") as f:
        f.write(html_content)
    print(f"Map saved to {output_file}. Open this file in a web browser to view the map.")

north, south, east, west = 34.1418976, 34.13, -118.1330033, -118.14

# Generate OSM map as HTML
generate_osm_map((north, south, east, west))
