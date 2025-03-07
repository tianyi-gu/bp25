import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
from shapely.geometry import Point, LineString
from scipy.spatial import cKDTree
import warnings

# Suppress specific runtime warnings from Shapely
warnings.filterwarnings("ignore", category=RuntimeWarning, module="shapely")

def get_closest_perp(G, point):
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

    # return u, v, key, perpendicular_line, projection_point, edge_geom
    return perpendicular_line, projection_point, u, v


def add_perp(G_combined, building_node_id):
    """
    Given a combined graph (with building nodes added) and a building node ID,
    compute the perpendicular edge to the nearest street edge and add it to the graph.
    """
    # Retrieve the building node's coordinates.
    building_data = G_combined.nodes[building_node_id]
    building_point = Point(building_data['x'], building_data['y'])

    # Find nearest street edge and compute the perpendicular line.
    perp_line, proj_point, u, v = get_closest_perp(G_combined, building_point)

    # Create a new node for the projection point.
    # Use a unique id (e.g., a negative number or use a naming scheme).
    projection_node_id = f"proj_{building_node_id}"
    G_combined.add_node(projection_node_id, x=proj_point.x, y=proj_point.y, node_type='projection')

    G_combined.remove_edge(u, v)
    if G_combined.has_edge(v, u):
        G_combined.remove_edge(v, u)
    distU = ((proj_point.x - G_combined.nodes[u]["x"]) ** 2 + (proj_point.y - G_combined.nodes[u]["y"]) ** 2) ** 0.5
    distV = ((proj_point.x - G_combined.nodes[v]["x"]) ** 2 + (proj_point.y - G_combined.nodes[v]["y"]) ** 2) ** 0.5

    G_combined.add_edge(projection_node_id, v, length=distV)
    G_combined.add_edge(v, projection_node_id, length=distV)
    G_combined.add_edge(projection_node_id, u, length=distU)
    G_combined.add_edge(u, projection_node_id, length=distU)

    return building_node_id, projection_node_id, perp_line.length, perp_line


def create_graph(bounding_coords):
    north, south, east, west = bounding_coords[0], bounding_coords[1], bounding_coords[2], bounding_coords[3]

    # Download the street network (all road types) using correct parameter order
    G = ox.graph_from_bbox((west, south, east, north), network_type='all')

    edges_to_add = []

    for edge in G.edges:
        if not G.has_edge(edge[1], edge[0]):
            edges_to_add.append((edge[1], edge[0], edge[2]))

    for edge in edges_to_add:
        G.add_edge(edge[0], edge[1], length=edge[2])

    # print(G.nodes)
    # print("Downloaded street network.")

    # Download building footprints in the same area as a GeoDataFrame
    buildings = ox.features_from_bbox((west, south, east, north), tags={'building': True})
    # print(buildings.geometry.centroid)
    # print("Downloaded building footprints.")

    # Download fire stations in the same area as a GeoDataFrame
    # fire_stations = ox.features_from_bbox((west, south, east, north), tags={'amenity': 'fire_station'})
    # fire_station_coords = set((row.geometry.centroid.x, row.geometry.centroid.y) for idx, row in fire_stations.iterrows())

    # Determine an appropriate UTM CRS for the buildings
    buildings_crs = buildings.to_crs(3857)
    buildings_crs['centroid'] = buildings_crs.geometry.centroid
    buildings['centroid'] = buildings_crs['centroid'].to_crs(buildings.crs)
    # print("Reprojected centroids back to original CRS.")

    # Create a copy of G so we can add building nodes
    G_combined = G.copy()

    next_id = -1

    # Create a list to hold building node ids for further processing
    next_id = -1  # Using negative numbers for building nodes so they don't conflict with OSM node IDs
    building_node_ids = []
    edges_to_add = []

    # iterrr = 0
    # For each building centroid, add it as a node and connect it to the nearest street node
    for idx, row in buildings.iterrows():
        # iterrr += 1
        # if (iterrr % 100 == 0):
        #     print(iterrr)
        centroid = row['centroid']

        # Check if the building is a fire station
        # if (centroid.x, centroid.y) in fire_station_coords:
        #     node_type = 'fire_station'
        # else:
        #     node_type = 'building'
        node_type = 'building'

        # Create a unique node id (e.g., negative id)
        bnode = next_id
        next_id -= 1  # decrement for next unique id
        building_node_ids.append(bnode)

        # Add the building centroid as a node with attributes: geometry, x, y, and a custom tag
        G_combined.add_node(bnode, x=centroid.x, y=centroid.y, node_type=node_type)
        building_node_id, projection_node_id, leng, perp_line = add_perp(G_combined, bnode)
        edges_to_add.append((building_node_id, projection_node_id, leng, perp_line))


    for building_node_id, projection_node_id, leng, perp_line in edges_to_add:
        G_combined.add_edge(building_node_id, projection_node_id,
                            length=1e-10,
                            geometry=perp_line,
                            is_perpendicular_edge=True)
        G_combined.add_edge(projection_node_id, building_node_id,
                            length=1e-10,
                            geometry=perp_line,
                            is_perpendicular_edge=True)

    # print([n for n in G_combined.neighbors(-1)])
    # print("Added building centroids as nodes and connected them to the street network.")

    return G_combined


# Plot the combined graph: For visualization, we can plot street nodes and color building nodes differently.
def display_graph(G, save=False):
    node_colors = ['royalblue' if G.nodes[node].get('node_type') == 'building' else 'red' if G.nodes[node].get('node_type') == 'fire_station' else 'slategray' for node in G.nodes]
    ox.plot_graph(G, node_size=10, show=True, close=False, save=save, filepath='graph.png', bgcolor='white', node_color=node_colors, edge_color='black')


if __name__ == '__main__':
    north, south, east, west = 34.1418976, 34.13, -118.1330033, -118.14
    bbox = (north, south, east, west)
    G_combined = create_graph(bbox)
    display_graph(G_combined, save=True)
