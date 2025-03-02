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
    return shortest_path_length(G, source=a, target=b)

def anneal(G : MultiDiGraph, routes, route_lengths, T):
    #here, routes are pure routes (all buildings)
    import random
    if random.random() < 0.2:
        #reverse range
        n = random.sample(routes.keys(), 1)
        l = random.randint(1, routes[n]-2)
        r = random.randint(l, routes[n]-2)

        delta = -(dist(G.nodes[routes[n][r]], G.nodes[routes[n][min(r+1, len(routes)-1)]]) + dist(G.nodes[l-1], G.nodes[l])) \
                + (dist(G.nodes[l-1], G.nodes[r]) +
                   (dist(G.nodes[l], G.nodes[r+1]) if r+1 != n else 0))

        if delta < 0:
            routes[n][l:r+1] = routes[n][r:l-1:-1]
            route_lengths[n] += delta
        else:
            if random.random() < exp(-delta / T):
                routes[n][l:r + 1] = routes[n][r:l - 1:-1]
                route_lengths[n] += delta

    else:
        #take smth from largest path, move to another path in a random loc

        largest_path = max(route_lengths, key=lambda pt: route_lengths[pt])
        if random.random() < 0.7:
            n = random.sample(routes.keys(), 1)
        else:
            n = largest_path
        loc = random.randint(1, len(routes[n])-2)
        orig_loc = random.randint(1, len(routes[largest_path])-2)

        delta = -(dist(G.nodes[routes[largest_path][orig_loc-1]], G.nodes[routes[largest_path][orig_loc]])
                  + dist(G.nodes[routes[largest_path][orig_loc]], G.nodes[routes[largest_path][orig_loc+1]])
                  - dist(G.nodes[routes[largest_path][orig_loc-1]], G.nodes[routes[largest_path][orig_loc+1]]))

        if delta < 0:
            del routes[largest_path][orig_loc]
            routes[n].insert(loc)
            route_lengths[largest_path] += -(dist(G.nodes[routes[largest_path][orig_loc-1]], G.nodes[routes[largest_path][orig_loc]])
                                            + dist(G.nodes[routes[largest_path][orig_loc]], G.nodes[routes[largest_path][orig_loc+1]])
                                             - dist(G.nodes[routes[largest_path][orig_loc-1]], G.nodes[routes[largest_path][orig_loc+1]]))
            route_lengths[n] += -(dist(G.nodes[routes[n][loc-1]], G.nodes[routes[n][loc]])
                                  - dist(G.nodes[routes[largest_path][orig_loc]], G.nodes[routes][n][loc-1])
                                  - dist(G.nodes[routes[largest_path][orig_loc]], G.nodes[routes[n][loc]]))
        else:
            if random.random() < exp(-delta / T):
                del routes[largest_path][orig_loc]
                routes[n].insert(loc)
                route_lengths[largest_path] += -(
                            dist(G.nodes[routes[largest_path][orig_loc - 1]], G.nodes[routes[largest_path][orig_loc]])
                            + dist(G.nodes[routes[largest_path][orig_loc]], G.nodes[routes[largest_path][orig_loc + 1]])
                            - dist(G.nodes[routes[largest_path][orig_loc - 1]],
                                   G.nodes[routes[largest_path][orig_loc + 1]]))
                route_lengths[n] += -(dist(G.nodes[routes[n][loc - 1]], G.nodes[routes[n][loc]])
                                      - dist(G.nodes[routes[largest_path][orig_loc]], G.nodes[routes][n][loc - 1])
                                      - dist(G.nodes[routes[largest_path][orig_loc]], G.nodes[routes[n][loc]]))

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
        print(i)
        if i % 10 == 0:
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
    for i in range(len(pure_routes)):
        print(pure_routes[i])
        print(route_lengths[i])