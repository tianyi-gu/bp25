import networkx as nx
from networkx import MultiDiGraph, shortest_path_length, shortest_path
from create_graph import create_graph
import heapq
from math import *

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
        try:
            curr_node = int(curr_node)
        except:
            pass

        # print(curr_dist, curr_node)

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
                try:
                    heapq.heappush(pq, (new_dist, str(next_node)))
                except:
                    # print(new_dist, next_node)
                    pass
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
    pure_routes = {pt: [pt] for pt in starting_pts}
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
        pure_routes[best_start].append(next_node)
        # sub_path is the shortest path from last_node to next_node.
        # To avoid duplication, remove the first node (which equals last_node).
        extension = sub_path[1:]

        # Extend the chosen route.l
        routes[best_start].extend(extension)
        route_lengths[best_start] += dist

        # Mark all newly added nodes as visited.
        visited.update(extension)

    return routes, route_lengths, pure_routes

def dist(G, a, b):
    try:
        return shortest_path_length(G, source=a, target=b, weight='length')
    except:
        return 1e18

def anneal(G : MultiDiGraph, routes, route_lengths, T):
    #here, routes are pure routes (all buildings)
    import random

    # Reverse a subsegment within one route with probability 0.2.
    if random.random() < 0.2:
        # Choose a random route key.
        route_key = random.choice(list(routes.keys()))
        route = routes[route_key]
        L = len(route)
        # Ensure the route is long enough to reverse a nontrivial segment.
        if L >= 4:
            # Choose indices l and r so that 0 < l < r < L-1.
            l = random.randint(1, L - 3)
            r = random.randint(l + 1, L - 2)

            # Calculate change in route length if we reverse the segment route[l:r+1].
            # Edges to be removed: between route[l-1] and route[l], and between route[r] and route[r+1].
            removed = dist(G, route[l - 1], route[l]) + dist(G, route[r], route[r + 1])
            # Edges to be added: between route[l-1] and route[r], and between route[l] and route[r+1].
            added = dist(G, route[l - 1], route[r]) + dist(G, route[l], route[r + 1])
            delta = added - removed

            # Accept the move if it improves or probabilistically if not.
            if delta < 0 or random.random() < exp(-delta / T):
                # Reverse the subsegment.
                routes[route_key][l:r + 1] = routes[route_key][l:r + 1][::-1]
                route_lengths[route_key] += delta

    # Otherwise, perform a move of a node between routes.
    else:
        # Identify the route with the largest current length.
        largest_key = max(route_lengths, key=lambda k: route_lengths[k])
        # With probability 0.7, choose a random destination route; otherwise, use the largest route.
        if random.random() < 0.7:
            dest_key = random.choice(list(routes.keys()))
        else:
            dest_key = largest_key

        # For safety, ensure the source route (largest) has at least 3 nodes (so that we can remove one from its interior).
        if len(routes[largest_key]) >= 3:
            # Choose a random index (not the first or last) in the largest route to remove.
            orig_idx = random.randint(1, len(routes[largest_key]) - 2)
            node_to_move = routes[largest_key][orig_idx]

            # Choose a random insertion index in the destination route (not at the very beginning or end).
            dest_route = routes[dest_key]
            if len(dest_route) < 2:
                dest_idx = 1
            else:
                dest_idx = random.randint(1, len(dest_route) - 1)

            # Calculate the change in the source route's length (removing the node):
            # Removal: remove edges (prev -> node) and (node -> next)
            # Addition: add edge (prev -> next)
            source_route = routes[largest_key]
            removed_source = dist(G, source_route[orig_idx - 1], source_route[orig_idx]) \
                             + dist(G, source_route[orig_idx], source_route[orig_idx + 1])
            added_source = dist(G, source_route[orig_idx - 1], source_route[orig_idx + 1])
            delta_remove = added_source - removed_source  # negative if removal shortens the route

            # Calculate the change in the destination route's length (inserting the node):
            # Removal: remove edge (dest_route[dest_idx-1] -> dest_route[dest_idx])
            # Addition: add edges (dest_route[dest_idx-1] -> node) and (node -> dest_route[dest_idx])
            removed_dest = dist(G, dest_route[dest_idx - 1], dest_route[dest_idx])
            added_dest = dist(G, dest_route[dest_idx - 1], node_to_move) \
                         + dist(G, node_to_move, dest_route[dest_idx])
            delta_insert = added_dest - removed_dest

            delta = delta_remove + delta_insert

            # Accept the move if improvement or probabilistically.
            if delta < 0 or random.random() < exp(-delta / T):
                # Update route lengths.
                route_lengths[largest_key] += delta_remove
                route_lengths[dest_key] += delta_insert
                # Remove the node from the source route.
                del routes[largest_key][orig_idx]
                # Insert it into the destination route at dest_idx.
                routes[dest_key].insert(dest_idx, node_to_move)


def gen_route_from_pure(G, pure_routes):
    routes = [[] for _ in range(len(pure_routes))]
    route_lengths = [0 for _ in range(len(pure_routes))]
    for i in range(len(pure_routes)):
        for j in range(len(pure_routes[i]) - 1):
            routes[i].extend(shortest_path(G, source=pure_routes[i][j], target=pure_routes[i][j+1]))
            if j != len(pure_routes[i]) - 1:
                routes[i].pop()
            route_lengths[i] += dist(pure_routes[i][j], pure_routes[i][j+1])
    return routes, route_lengths

def simulated_annealing(G, pure_routes, route_lengths, T=10):
    c = 0.9
    for i in range(1000):
        if i % 10 == 0:
            print(i)
            print(route_lengths)
            T *= c
        anneal(G, pure_routes, route_lengths, T)
    return pure_routes, route_lengths


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
    routes, route_lengths, pure_routes = get_init_solution(grf, starting_pts)
    for start, route in routes.items():
        print(f"Route starting at {start}: {route}")
        print(f"Total length: {route_lengths[start]}")

    print("STARTING SIMULATED ANNEALING")
    pure_routes, route_lengths = simulated_annealing(grf, pure_routes, route_lengths)
    for i in pure_routes:
        print(pure_routes[i])
        print(route_lengths[i])