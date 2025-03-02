from flask import Flask, jsonify, request
from flask_cors import CORS
import os
import sys

current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.append(current_dir)

try:
    from create_graph import create_graph
    from MultiTSP import get_actual_solution
except ImportError:
    from bp25.backend.create_graph import create_graph
    from bp25.backend.MultiTSP import get_actual_solution

import networkx as nx
import random
import osmnx as ox

app = Flask(__name__)
CORS(app)

@app.route('/api/health')
def health_check():
    return jsonify({"status": "healthy"})

@app.route('/api/process-allocation', methods=['POST'])
def process_allocation():
    data = request.json
    
    if not data or 'bbox' not in data:
        return jsonify({"error": "Missing bounding box coordinates"}), 400
    
    try:
        # Extract bounding box coordinates
        bbox = data['bbox']
        location_name = data.get('location_name', 'Unknown location')
        
        # Get fire data if provided
        fires = data.get('fires', [])
        
        graph = create_graph(bbox)
        
        # Remove nodes that are too close to fires
        if fires and len(fires) > 0:
            DANGER_RADIUS = 0.0005
            nodes_to_remove = []
            
            for node_id, node_data in graph.nodes(data=True):
                if 'x' not in node_data or 'y' not in node_data:
                    continue
                    
                for fire in fires:
                    fire_lat = fire.get('latitude')
                    fire_lng = fire.get('longitude')
                    
                    if fire_lat is None or fire_lng is None:
                        continue
                        
                    if isinstance(fire_lat, str):
                        fire_lat = float(fire_lat)
                    if isinstance(fire_lng, str):
                        fire_lng = float(fire_lng)
                    
                    distance = ((node_data['y'] - fire_lat) ** 2 + 
                               (node_data['x'] - fire_lng) ** 2) ** 0.5
                    
                    # If node is too close to any fire, mark for removal
                    if distance < DANGER_RADIUS:
                        nodes_to_remove.append(node_id)
                        break
            
            # Remove the marked nodes from the graph
            for node_id in nodes_to_remove:
                if graph.has_node(node_id):
                    graph.remove_node(node_id)
            
            print(f"Removed {len(nodes_to_remove)} nodes due to proximity to fires")
        
        # Get building nodes for starting points
        building_nodes = [n for n, dat in graph.nodes(data=True) if dat.get('node_type') == 'building']
        
        num_routes = min(5, len(building_nodes))
        if num_routes > 0:
            starting_pts = random.sample(building_nodes, num_routes)
            
            # Get routes using MultiTSP
            routes, pure_routes, route_lengths = get_actual_solution(graph, starting_pts)
            
            routes_converted = {}
            pure_routes_converted = {}
            route_lengths_converted = {}

            for key in routes:
                python_key = float(key) if hasattr(key, 'dtype') else key
                routes_converted[python_key] = routes[key]
                pure_routes_converted[python_key] = pure_routes[key]
                route_lengths_converted[python_key] = route_lengths[key]

            routes = routes_converted
            pure_routes = pure_routes_converted
            route_lengths = route_lengths_converted
            
            node_to_route = {}
            for route_id, nodes in routes.items():
                for node in nodes:
                    node_to_route[node] = route_id

            # Generate colors for each route
            route_colors = {}
            for route_id in routes.keys():
              
                while True:
                    # Generate a random color with more saturated values
                    r = random.randint(20, 180)
                    g = random.randint(20, 180)
                    b = random.randint(20, 180)
                    
                    if max(r, g, b) < 120:
                        continue
                        
                    # Make sure the color isn't too light overall (lower threshold)
                    if (r + g + b) > 450:
                        continue
            
                    color = "#{:02x}{:02x}{:02x}".format(r, g, b)
                    route_colors[route_id] = color
                    break
        else:
            routes = {}
            route_lengths = {}
            node_to_route = {}
            route_colors = {}
        
        route_display_ids = {}
        for i, route_id in enumerate(routes.keys(), 1):
            route_display_ids[route_id] = i
        
        nodes_data = []
        for node_id, node_data in graph.nodes(data=True):
            if 'x' in node_data and 'y' in node_data:
                node_type = node_data.get('node_type', 'street')
                node_info = {
                    'id': str(node_id),
                    'lat': node_data['y'],
                    'lng': node_data['x'],
                    'type': node_type
                }
                
                if node_id in node_to_route:
                    route_id = node_to_route[node_id]
                    node_info['route_id'] = str(route_id)
                    node_info['route_color'] = route_colors[route_id]
                
                nodes_data.append(node_info)
        
        # Extract edges
        edges_data = []
        edges_with_route_color = 0
        for u, v, data in graph.edges(data=True):
            # Skip edges without both nodes having coordinates
            if ('x' in graph.nodes[u] and 'y' in graph.nodes[u] and 
                'x' in graph.nodes[v] and 'y' in graph.nodes[v]):
                edge_type = 'perpendicular' if data.get('is_perpendicular_edge', False) else 'street'
                
                edge_info = {
                    'source': str(u),
                    'target': str(v),
                    'type': edge_type
                }
                
                # Check if either node is a building in a route
                building_node = None
                for node in [u, v]:
                    if node in node_to_route and graph.nodes[node].get('node_type') == 'building':
                        building_node = node
                        break

                if building_node is not None:
                    # This edge connects to a building in a route, color it
                    route_id = node_to_route[building_node]
                    edge_info['route_id'] = str(route_id)
                    edge_info['route_color'] = route_colors[route_id]
                    edges_with_route_color += 1
                
                edges_data.append(edge_info)
        
        # After processing all edges, check if any building nodes in routes don't have colored connections
        building_nodes_in_routes = {node_id for node_id, node_data in graph.nodes(data=True) 
                                   if node_data.get('node_type') == 'building' and node_id in node_to_route}

        # Track which building nodes have colored connections
        buildings_with_colored_connections = set()

        # First pass: check which buildings already have colored connections
        for edge in edges_data:
            source = edge['source']
            target = edge['target']
            
            # If this edge has a route color and connects to a building
            if 'route_color' in edge:
                source_node = next((n for n in graph.nodes(data=True) if str(n[0]) == source), None)
                target_node = next((n for n in graph.nodes(data=True) if str(n[0]) == target), None)
                
                if source_node and source_node[1].get('node_type') == 'building':
                    buildings_with_colored_connections.add(source)
                if target_node and target_node[1].get('node_type') == 'building':
                    buildings_with_colored_connections.add(target)

        # Second pass: color any remaining building connections
        for i, edge in enumerate(edges_data):
            source = edge['source']
            target = edge['target']
            
            # If this edge doesn't have a route color yet
            if 'route_color' not in edge:
                source_id = source.lstrip('-') if source.startswith('-') else source
                target_id = target.lstrip('-') if target.startswith('-') else target
                
                source_in_route = source in node_to_route
                target_in_route = target in node_to_route
                
                # If one end is a building in a route
                if (source_in_route and source not in buildings_with_colored_connections and 
                    graph.nodes[int(source_id) if source_id.isdigit() else source].get('node_type') == 'building'):
                    route_id = node_to_route[source]
                    edges_data[i]['route_id'] = str(route_id)
                    edges_data[i]['route_color'] = route_colors[route_id]
                    buildings_with_colored_connections.add(source)
                    
                elif (target_in_route and target not in buildings_with_colored_connections and 
                      graph.nodes[int(target_id) if target_id.isdigit() else target].get('node_type') == 'building'):
                    route_id = node_to_route[target]
                    edges_data[i]['route_id'] = str(route_id)
                    edges_data[i]['route_color'] = route_colors[route_id]
                    buildings_with_colored_connections.add(target)
        
        # Prepare route data for frontend
        routes_data = []
        for route_id, node_list in routes.items():
            routes_data.append({
                'id': str(route_id),
                'display_id': route_display_ids[route_id],
                'nodes': [str(node) for node in node_list],
                'color': route_colors[route_id],
                'length': len(node_list)
            })
        
        # Find fire stations within the bounding box
        try:
            # Query for fire stations using OSM tags
            fire_stations = ox.features.features_from_bbox(
                bbox[0], bbox[1], bbox[2], bbox[3],
                tags={'amenity': 'fire_station'}
            )
            
            fire_station_data = []
            if not fire_stations.empty:
                for idx, station in fire_stations.iterrows():
                    if hasattr(station.geometry, 'centroid'):
                        point = station.geometry.centroid
                    else:
                        point = station.geometry
                        
                    name = station.get('name', 'Fire Station')
                    
                    fire_station_data.append({
                        'id': str(idx),
                        'lat': point.y,
                        'lng': point.x,
                        'name': name
                    })
        except Exception as e:
            print(f"Error fetching fire stations: {e}")
            fire_station_data = []
        
        return jsonify({
            "status": "success",
            "message": f"Processed allocation for {location_name}",
            "bbox": bbox,
            "nodes_count": len(graph.nodes),
            "edges_count": len(graph.edges),
            "routes_count": len(routes),
            "fire_stations": fire_station_data,
            "graph_data": {
                "nodes": nodes_data,
                "edges": edges_data,
                "routes": routes_data
            }
        })
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
 