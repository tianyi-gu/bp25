from flask import Flask, jsonify, request
from flask_cors import CORS  
from bp25.backend.create_graph import create_graph

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
        
        # placeholder for allocation algorithm
        
        return jsonify({
            "status": "success",
            "message": f"Processed allocation for {location_name}",
            "bbox": bbox,
            "nodes_count": len(graph.nodes),
            "edges_count": len(graph.edges),
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
 