import osmnx as ox
import networkx as nx
import matplotlib.pyplot as plt

# Define your bounding box (example coordinates)
north, south, east, west = 38.0001062, 37.98, -122.5294774, -122.531

# Download the street network (all road types)

print("helo")

G = ox.graph_from_bbox((west, south, east, north), network_type='all')

print("helo2")

# Optionally, download building footprints in the same area
buildings = ox.features_from_bbox((west, south, east, north), tags={'building': True})



print("helo3")

# G is a NetworkX MultiDiGraph; you can now analyze or visualize it
ox.plot_graph(G)