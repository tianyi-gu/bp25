import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point

def create_graph(bounding_coords):

    north, south, east, west = bounding_coords[0], bounding_coords[1], bounding_coords[2], bounding_coords[3]

    # Download the street network (all road types) using correct parameter order
    G = ox.graph_from_bbox((west, south, east, north), network_type='all')

    print(G.nodes)
    print(G.nodes[110436101]['x'], G.nodes[110436101]['y'])

    print("Downloaded street network.")

    # Download building footprints in the same area as a GeoDataFrame
    buildings = ox.features_from_bbox((west, south, east, north), tags={'building': True})

    print(buildings.geometry.centroid)

    print("Downloaded building footprints.")

    # Determine an appropriate UTM CRS for the buildings
    buildings_crs = buildings.to_crs(3857)
    buildings_crs['centroid'] = buildings_crs.geometry.centroid

    buildings['centroid'] = buildings_crs['centroid'].to_crs(buildings.crs)

    # buildings['centroid'] = buildings.geometry.centroid

    print("Reprojected centroids back to original CRS.")

    # Compute centroids of each building footprint
    # (If a geometry is not a Polygon/MultiPolygon, the centroid might be empty)
    # buildings['centroid'] = buildings.geometry.centroid

    # Create a copy of G so we can add building nodes
    G_combined = G.copy()

    # For generating unique IDs for building nodes, start with an offset
    # (Using negative numbers for building nodes so they don't conflict with OSM node IDs)
    building_id_offset = -1

    # Optional: Create a list to hold building node ids for further processing
    building_node_ids = []

    # For each building centroid, add it as a node and connect it to the nearest street node
    for idx, row in buildings.iterrows():
        centroid = row['centroid']
        # Create a unique node id (e.g., negative id)
        bnode = building_id_offset
        building_id_offset -= 1  # decrement for next unique id
        building_node_ids.append(bnode)

        # Add the building centroid as a node with attributes: geometry, x, y, and a custom tag
        G_combined.add_node(bnode, x=centroid.x, y=centroid.y, node_type='building')

        # Snap the building centroid to the nearest street node in G_combined
        # Note: the nearest_nodes function expects the coordinates in (x, y) order (i.e., lon, lat)
        nearest_street_node = ox.distance.nearest_nodes(G_combined, X=centroid.x, Y=centroid.y)

        # Add an edge from the building node to the nearest street node.
        # Here, we add a bidirectional connection so that the building is connected to the network.
        # You can also add attributes like 'length' (using the Euclidean distance) if needed.
        distance = centroid.distance(Point(G_combined.nodes[nearest_street_node]['x'],
                                           G_combined.nodes[nearest_street_node]['y']))
        # Add edge in both directions
        G_combined.add_edge(bnode, nearest_street_node, length=distance, is_building_edge=True)
        G_combined.add_edge(nearest_street_node, bnode, length=distance, is_building_edge=True)

    print("Added building centroids as nodes and connected them to the street network.")

    # return G_combined

    # Plot the combined graph
    # For visualization, we can plot street nodes and color building nodes differently.
    fig, ax = ox.plot_graph(G, node_size=10, show=False, close=False)

    # Extract building nodes from the graph (those we tagged as 'building')
    # building_nodes = [n for n, data in G_combined.nodes(data=True) if data.get('node_type') == 'building']

    # Plot the building nodes on top of the graph in a different color

    # x_buildings = [G_combined.nodes[n]['x'] for n in building_nodes]
    # y_buildings = [G_combined.nodes[n]['y'] for n in building_nodes]
    # ax.scatter(x_buildings, y_buildings, c='red', s=30, label='Building Centroid', zorder=3)
    # ax.legend()

    plt.show()

if __name__ == '__main__':
    north, south, east, west = 38.0001062, 37.98, -122.5294774, -122.531
    print("hello")
    create_graph((north, south, east, west))
