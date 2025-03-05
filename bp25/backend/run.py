import random
import osmnx as ox
import networkx as nx
import geopandas as gpd
import matplotlib.pyplot as plt
from matplotlib.animation import FuncAnimation
import numpy as np

from create_graph import create_graph
from MultiTSP import get_init_solution

# Define bounding box and create graph
north, south, east, west = 34.1418976, 34.13, -118.1330033, -118.14
bbox = (north, south, east, west)

print("Creating Graph")
G = create_graph(bbox)
print("Finished Creating Graph")

# Sample 5 stations from nodes with a 'building' attribute
stations = random.sample([n for n, dat in G.nodes(data=True) if dat.get('node_type') == 'building'], 5)
# stations = [n for n, dat in G.nodes(data=True) if dat.get('node_type') == 'fire_station']

print("Getting Routes")
routes, route_lengths, _ = get_init_solution(G, stations)
for start, route in routes.items():
    print(f"Route starting at {start}: {route}")
    print(f"Total length: {route_lengths[start]}")

################# MAKE ANIMATIONS #################

# Plot the static graph
node_colors = ['royalblue' if G.nodes[node].get('node_type') == 'building' else 'slategray'
               for node in G.nodes]
fig, ax = ox.plot_graph(G, node_size=10, show=False, close=False,
                        filepath='graph.png', bgcolor='white',
                        node_color=node_colors, edge_color='black')

# Plot static station markers (red)
station_xs = [G.nodes[station]['x'] for station in stations]
station_ys = [G.nodes[station]['y'] for station in stations]
ax.scatter(station_xs, station_ys, c='red', s=50, zorder=5, label='Stations')

# Pre-calculate route animation data: for each route, compute the list of (x,y) coordinates
# and cumulative distances along the route (to enable interpolation).
route_anim_data = {}
for start, route in routes.items():
    coords = [(G.nodes[node]['x'], G.nodes[node]['y']) for node in route]
    cumdist = [0]
    for i in range(1, len(coords)):
        x0, y0 = coords[i - 1]
        x1, y1 = coords[i]
        segment_length = np.hypot(x1 - x0, y1 - y0)
        cumdist.append(cumdist[-1] + segment_length)
    total_distance = cumdist[-1]
    route_anim_data[start] = {
        'coords': coords,
        'cumdist': cumdist,
        'total_distance': total_distance,
    }

# Create a moving dot (green marker) for each route, initially at the start of its route.
dots = {}
for start, data in route_anim_data.items():
    x0, y0 = data['coords'][0]
    dot, = ax.plot(x0, y0, 'o', color='green', markersize=10, label=f'Route {start}')
    dots[start] = dot

def interpolate_position(coords, cumdist, d):
    """
    Given a list of coordinates and cumulative distances, return the interpolated position
    for a traveled distance 'd' along the route.
    """
    if d <= 0:
        return coords[0]
    if d >= cumdist[-1]:
        return coords[-1]
    # Find the segment in which 'd' falls and interpolate linearly.
    for i in range(len(cumdist) - 1):
        if cumdist[i] <= d <= cumdist[i + 1]:
            f = (d - cumdist[i]) / (cumdist[i + 1] - cumdist[i])
            x0, y0 = coords[i]
            x1, y1 = coords[i + 1]
            x = x0 + f * (x1 - x0)
            y = y0 + f * (y1 - y0)
            return (x, y)
    return coords[-1]

# Define a slower constant speed (distance units per frame).
speed = 0.00025  # Adjust this value as needed for slower movement

def update(frame):
    """
    For each route, update the marker's position by incrementing the traveled distance by 'speed'
    (wrapping around at the route's end).
    """
    for start, data in route_anim_data.items():
        total = data['total_distance']
        # The traveled distance increases by 'speed' each frame and wraps around using modulo.
        d = (frame * speed) % total
        x, y = interpolate_position(data['coords'], data['cumdist'], d)
        dots[start].set_data(x, y)
    return list(dots.values())

# Create the animation using FuncAnimation.
num_frames = 1000  # Increase for a longer or smoother animation
anim = FuncAnimation(fig, update, frames=num_frames, interval=50, blit=True, repeat=True)

# Save the animation as a GIF (requires pillow installed)
anim.save('routes_animation.gif', writer='pillow')

plt.show()
