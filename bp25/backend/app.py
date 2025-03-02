from flask import Flask, jsonify, request
from flask_cors import CORS  
from bp25.backend.create_graph import create_graph
import networkx as nx
from bp25.backend.MultiTSP import get_init_solution
import random

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
        bbox = data['bbox']  # [north, south, east, west]
        location_name = data.get('location_name', 'Unknown location')
        
        # Create graph using the provided bounding box
        graph = create_graph(bbox)
        
        # Get building nodes for starting points
        building_nodes = [n for n, dat in graph.nodes(data=True) if dat.get('node_type') == 'building']
        
        # Use up to 5 random building nodes as starting points
        num_routes = min(5, len(building_nodes))
        if num_routes > 0:
            starting_pts = random.sample(building_nodes, num_routes)
            
            # Get routes using MultiTSP
            routes, route_lengths, node_to_route = get_init_solution(graph, starting_pts)
            
            # Generate colors for each route
            route_colors = {}
            for route_id in routes.keys():
                # Generate vibrant colors by using higher saturation and value
                # Avoid very light colors by ensuring RGB values aren't all too high
                while True:
                    # Generate a random color
                    r = random.randint(50, 200)
                    g = random.randint(50, 200)
                    b = random.randint(50, 200)
                    
                    # Ensure at least one component is strong (for vibrancy)
                    if max(r, g, b) < 150:
                        continue
                        
                    # Ensure the color isn't too light overall
                    if (r + g + b) > 550:
                        continue
                        
                    # Convert to hex
                    color = "#{:02x}{:02x}{:02x}".format(r, g, b)
                    route_colors[route_id] = color
                    break
        else:
            routes = {}
            route_lengths = {}
            node_to_route = {}
            route_colors = {}
        
        # Convert graph to a format suitable for frontend visualization
        nodes_data = []
        for node_id, node_data in graph.nodes(data=True):
            if 'x' in node_data and 'y' in node_data:
                node_type = node_data.get('node_type', 'street')
                node_info = {
                    'id': str(node_id),
                    'lat': node_data['y'],  # Note: y is latitude
                    'lng': node_data['x'],  # x is longitude
                    'type': node_type
                }
                
                # Add route information if this node is part of a route
                if node_id in node_to_route:
                    route_id = node_to_route[node_id]
                    node_info['route_id'] = str(route_id)
                    node_info['route_color'] = route_colors[route_id]
                
                nodes_data.append(node_info)
        
        # Extract edges (simplified - no geometry)
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
                # Check if either end is a building node
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
                # Check if it connects to a building that's in a route but doesn't have a colored connection
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
                'nodes': [str(node) for node in node_list],
                'color': route_colors[route_id],
                'length': len(node_list)
            })
        
        return jsonify({
            "status": "success",
            "message": f"Processed allocation for {location_name}",
            "bbox": bbox,
            "nodes_count": len(graph.nodes),
            "edges_count": len(graph.edges),
            "routes_count": len(routes),
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
 