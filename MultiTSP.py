import networkx as nx
from networkx import MultiDiGraph
from CreateGraph import create_graph
import heapq

def nearest_unvisited_node(grf : MultiDiGraph, start, visited):
    #dijkstra out
    distances = {node: float('infinity') for node in grf.nodes()}
    prev = [{node : -1 for node in grf.nodes()}]
    pq = [(0, start)]

    while pq:
        curr_dist, curr_node = heapq.heappop(pq)

        if curr_node not in visited:
            

        if curr_dist > distances[curr_node]:
            continue

        for next_node in grf.neighbors(curr_node):
            edge_dat = grf.get_edge_data(curr_node, next_node)
            if (edge_dat['length'] + curr_dist < distances[next_node]):
                distances[next_node] = edge_dat['length'] + curr_dist
                prev[next_node] = curr_node
                heapq.heappush(pq, (distances[next_node], next_node))


def get_init_solution(grf, starting_pts):
    # Greedy solution. Take the point with the min length so far, find nearest unvisited node, connect using shortest path

