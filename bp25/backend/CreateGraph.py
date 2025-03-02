import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString
from scipy.spatial import cKDTree


def get_nearest_edge_perpendicular_line(G, point):
    """
    Given a graph G and a shapely Point, find the nearest edge to the point,
    compute the projection of the point onto that edge, and return the line (as a LineString)
    connecting the point to its projection on the edge.
    """
    # Get the nearest edge (u, v, key) to the point using OSMnx's built-in function.
    u, v, key = ox.distance.nearest_edges(G, point.x, point.y)

    # Retrieve the edge geometry. If the edge has no geometry attribute, create a LineString from node coordinates.
    edge_data = G.edges[u, v, key]
    if 'geometry' in edge_data:
        edge_geom = edge_data['geometry']
    else:
        point_u = Point(G.nodes[u]['x'], G.nodes[u]['y'])
        point_v = Point(G.nodes[v]['x'], G.nodes[v]['y'])
        edge_geom = LineString([point_u, point_v])

    # Compute the projection of the point onto the edge geometry.
    projected_distance = edge_geom.project(point)
    projection_point = edge_geom.interpolate(projected_distance)

    # Create the perpendicular line segment from the point (building centroid) to the projection point.
    perpendicular_line = LineString([point, projection_point])

    return u, v, key, perpendicular_line, projection_point, edge_geom


# Example usage inside your workflow:
def add_perpendicular_edge(G_combined, building_node_id):
    """
    Given a combined graph (with building nodes added) and a building node ID,
    compute the perpendicular edge to the nearest street edge and add it to the graph.
    """
    # Retrieve the building node's coordinates.
    building_data = G_combined.nodes[building_node_id]
    building_point = Point(building_data['x'], building_data['y'])

    # Find nearest street edge and compute the perpendicular line.
    u, v, key, perp_line, proj_point, edge_geom = get_nearest_edge_perpendicular_line(G_combined, building_point)

    # Create a new node for the projection point.
    # Use a unique id (e.g., a negative number or use a naming scheme).
    projection_node_id = f"proj_{building_node_id}"
    G_combined.add_node(projection_node_id, x=proj_point.x, y=proj_point.y, node_type='projection')

    # Add a new edge from the building node to the projection node.
    # You may want to store attributes such as length and geometry.
    # G_combined.add_edge(building_node_id, projection_node_id,
    #                     length=perp_line.length,
    #                     geometry=perp_line,
    #                     is_perpendicular_edge=True)
    # G_combined.add_edge(projection_node_id, building_node_id,
    #                     length=perp_line.length,
    #                     geometry=perp_line,
    #                     is_perpendicular_edge=True)

    return building_node_id, projection_node_id, perp_line.length, perp_line

    # print(f"Added perpendicular edge from building node {building_node_id} to projection node {projection_node_id}.")
    # return projection_node_id

def create_graph(bounding_coords):

    north, south, east, west = bounding_coords[0], bounding_coords[1], bounding_coords[2], bounding_coords[3]

    # Download the street network (all road types) using correct parameter order
    G = ox.graph_from_bbox((west, south, east, north), network_type='all')

    print(G.nodes)
    # print(G.nodes[110436101]['x'], G.nodes[110436101]['y'])

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

    edges_to_add = []

    iterrr = 0
    # For each building centroid, add it as a node and connect it to the nearest street node
    for idx, row in buildings.iterrows():
        iterrr += 1

        if (iterrr % 100 == 0):
            print(iterrr)
        centroid = row['centroid']
        # Create a unique node id (e.g., negative id)
        bnode = building_id_offset
        building_id_offset -= 1  # decrement for next unique id
        building_node_ids.append(bnode)

        # Add the building centroid as a node with attributes: geometry, x, y, and a custom tag

        # nearest_street_node = ox.distance.nearest_nodes(G_combined, X=centroid.x, Y=centroid.y)

        G_combined.add_node(bnode, x=centroid.x, y=centroid.y, node_type='building')
        building_node_id, projection_node_id, leng, perp_line = add_perpendicular_edge(G_combined, bnode)
        edges_to_add.append((building_node_id, projection_node_id, leng, perp_line))


    for building_node_id, projection_node_id, leng, perp_line in edges_to_add:
        G_combined.add_edge(building_node_id, projection_node_id,
                            length=0,
                            geometry=perp_line,
                            is_perpendicular_edge=True)
        G_combined.add_edge(projection_node_id, building_node_id,
                            length=0,
                            geometry=perp_line,
                            is_perpendicular_edge=True)



        # Snap the building centroid to the nearest street node in G_combined
        # Note: the nearest_nodes function expects the coordinates in (x, y) order (i.e., lon, lat)

        # Add an edge from the building node to the nearest street node.
        # Here, we add a bidirectional connection so that the building is connected to the network.
        # You can also add attributes like 'length' (using the Euclidean distance) if needed.
        # distance = centroid.distance(Point(G_combined.nodes[nearest_street_node]['x'],
        #                                    G_combined.nodes[nearest_street_node]['y']))


        # edges_to_add.append((bnode, nearest_street_node, distance, centroid))

    # for bnode, nearest_street_node, distance, centroid in edges_to_add:
    #
    #     G_combined.add_edge(bnode, nearest_street_node, length=distance, is_building_edge=True)
    #     G_combined.add_edge(nearest_street_node, bnode, length=distance, is_building_edge=True)

    print([n for n in G_combined.neighbors(-1)])

    print("Added building centroids as nodes and connected them to the street network.")

    # for idx, dat in G_combined.nodes(data=True):
    #     if (dat.get('node_type') == 'building'):
    #         print(dat['x'], dat['y'])
    #
    # for idx, dat in G_combined.nodes(data=True):
    #     if (dat.get('node_type') != 'building'):
    #         print(dat['x'], dat['y'])
    # return G_combined

    # Plot the combined graph
    # For visualization, we can plot street nodes and color building nodes differently.
    fig, ax = ox.plot_graph(G_combined, node_size=10, show=True, close=False)

    # Extract building nodes from the graph (those we tagged as 'building')
    # building_nodes = [n for n, data in G_combined.nodes(data=True) if data.get('node_type') == 'building']

    # Plot the building nodes on top of the graph in a different color

    # x_buildings = [G_combined.nodes[n]['x'] for n in building_nodes]
    # y_buildings = [G_combined.nodes[n]['y'] for n in building_nodes]
    # ax.scatter(x_buildings, y_buildings, c='red', s=30, label='Building Centroid', zorder=3)
    # ax.legend()

    # plt.show()

if __name__ == '__main__':
    north, south, east, west = 34.1418976, 34.13, -118.1330033, -118.14
    print("hello")
    create_graph((north, south, east, west))
