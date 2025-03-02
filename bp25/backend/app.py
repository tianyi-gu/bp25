from flask import Flask, jsonify, request
from flask_cors import CORS  
from bp25.backend.create_graph import create_graph
import networkx as nx

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
        # use plot=True to visualize the graph
        graph = create_graph(bbox, plot=False)
        
        # Convert graph to a format suitable for frontend visualization
        nodes_data = []
        for node_id, node_data in graph.nodes(data=True):
            if 'x' in node_data and 'y' in node_data:
                node_type = node_data.get('node_type', 'street')
                nodes_data.append({
                    'id': str(node_id),
                    'lat': node_data['y'],  # Note: y is latitude
                    'lng': node_data['x'],  # x is longitude
                    'type': node_type
                })
        
        # Extract edges (simplified - no geometry)
        edges_data = []
        for u, v, data in graph.edges(data=True):
            # Skip edges without both nodes having coordinates
            if ('x' in graph.nodes[u] and 'y' in graph.nodes[u] and 
                'x' in graph.nodes[v] and 'y' in graph.nodes[v]):
                edge_type = 'perpendicular' if data.get('is_perpendicular_edge', False) else 'street'
                edges_data.append({
                    'source': str(u),
                    'target': str(v),
                    'type': edge_type
                })
        
        return jsonify({
            "status": "success",
            "message": f"Processed allocation for {location_name}",
            "bbox": bbox,
            "nodes_count": len(graph.nodes),
            "edges_count": len(graph.edges),
            "graph_data": {
                "nodes": nodes_data,
                "edges": edges_data
            }
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
 