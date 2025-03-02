import networkx as nx
from networkx import MultiDiGraph
from create_graph import create_graph
import heapq


def nearest_unvisited_node(grf: MultiDiGraph, start, visited):
    # Dijkstra: initialize distances and predecessors
    distances = {node: float('infinity') for node in grf.nodes()}
    # prev[node] will store the previous node along the shortest path
    prev = {node: None for node in grf.nodes()}
    distances[start] = 0
    # Priority queue of (distance, node)
    pq = [(0, start)]

    while pq:
        curr_dist, curr_node = heapq.heappop(pq)
        print(curr_dist, curr_node)

        # If this node is a building and not yet visited, we've found a candidate.
        if (curr_node not in visited) and (grf.nodes[curr_node].get("node_type") == "building"):
            # Reconstruct path from start to curr_node:
            path = []
            node = curr_node
            while node is not None:
                path.append(node)
                node = prev[node]
            # The path is currently from curr_node back to start, so reverse it.
            path.reverse()
            return curr_node, curr_dist, path

        # If we already found a shorter distance to curr_node, skip.
        if curr_dist > distances[curr_node]:
            continue

        for next_node in grf.neighbors(curr_node):
            edge_data = grf.get_edge_data(curr_node, next_node)[0]
            # Assume each edge has a key 'length'

            new_dist = curr_dist + edge_data['length']
            if new_dist < distances[next_node]:
                distances[next_node] = new_dist
                prev[next_node] = curr_node
                heapq.heappush(pq, (new_dist, next_node))
    # If no unvisited building is found:
    return None


def get_init_solution(grf: MultiDiGraph, starting_pts):
    """
    Greedy initialization for multi-party TSP.
    starting_pts: list of nodes that serve as initial starting points for separate routes.

    The algorithm works by maintaining one route per starting point.
    At each iteration, the route with the smallest current length is chosen,
    and extended by connecting (via the shortest path) its last node to the nearest unvisited building.
    """
    # Initialize routes and route lengths.
    # routes: dict mapping starting_pt to list of nodes in that route.
    routes = {pt: [pt] for pt in starting_pts}
    route_lengths = {pt: 0 for pt in starting_pts}

    # All nodes with node_type "building" that we want to cover.
    building_nodes = {node for node in grf.nodes() if grf.nodes[node].get("node_type") == "building"}
    # Mark starting points as visited.
    visited = set(starting_pts)

    # Continue until all building nodes are visited or no extension is possible.
    while visited != building_nodes:
        # Choose the route with minimal current length.
        best_start = min(route_lengths, key=lambda pt: route_lengths[pt])
        current_route = routes[best_start]
        last_node = current_route[-1]

        # Find the nearest unvisited building from the last node.
        result = nearest_unvisited_node(grf, last_node, visited)
        if result is None:
            # No reachable unvisited building found; break out.
            break
        next_node, dist, sub_path = result
        # sub_path is the shortest path from last_node to next_node.
        # To avoid duplication, remove the first node (which equals last_node).
        extension = sub_path[1:]

        # Extend the chosen route.
        routes[best_start].extend(extension)
        route_lengths[best_start] += dist

        # Mark all newly added nodes as visited.
        visited.update(extension)

    return routes, route_lengths


# Example usage:
if __name__ == "__main__":
    # Assume create_graph() creates a networkx.MultiDiGraph with proper "node_type" attributes
    north, south, east, west = 34.1418976, 34.13, -118.1330033, -118.14
    bbox = (north, south, east, west)

    print("Creating Graph")

    grf = create_graph(bbox)

    print("Finished Creating Graph")
    # List of starting points (for instance, predetermined nodes)

    import random

    starting_pts = random.sample([n for n, dat in grf.nodes(data=True) if dat.get('node_type') == 'building'], 5)

    print("Getting Routes")
    routes, route_lengths = get_init_solution(grf, starting_pts)
    for start, route in routes.items():
        print(f"Route starting at {start}: {route}")
        print(f"Total length: {route_lengths[start]}")
