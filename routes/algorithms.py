"""
Graph algorithms for network route optimization.

This module provides a pure-Python implementation of Dijkstra's algorithm
optimized with a min-heap (heapq) for O((V + E) log V) time complexity.
It is deliberately decoupled from Django/ORM so it can be unit-tested
independently and swapped out without touching view logic.
"""

import heapq
from typing import Optional

# Type alias: adjacency list mapping node_name -> list of (neighbour, latency)
Graph = dict[str, list[tuple[str, float]]]


def build_graph(edges: list[dict]) -> Graph:
    """
    Build an adjacency-list representation from a list of edge dicts.

    Args:
        edges: Sequence of dicts with keys 'source', 'destination', 'latency'.
               Each dict represents a *directed* edge.

    Returns:
        A dict mapping each node name to its outbound (neighbour, latency) pairs.

    Example:
        >>> build_graph([
        ...     {"source": "A", "destination": "B", "latency": 5},
        ...     {"source": "B", "destination": "C", "latency": 3},
        ... ])
        {'A': [('B', 5)], 'B': [('C', 3)]}
    """
    graph: Graph = {}
    for edge in edges:
        src = edge["source"]
        dst = edge["destination"]
        lat = edge["latency"]
        graph.setdefault(src, []).append((dst, lat))
        # Ensure destination node exists even if it has no outbound edges
        graph.setdefault(dst, [])
    return graph


def dijkstra(
    graph: Graph,
    source: str,
    destination: str,
) -> tuple[Optional[float], Optional[list[str]]]:
    """
    Find the shortest (lowest-latency) path using Dijkstra's algorithm.

    Uses a binary min-heap for efficient extraction of the next-best node.
    Handles disconnected graphs gracefully.

    Args:
        graph:       Adjacency list produced by :func:`build_graph`.
        source:      Name of the starting node.
        destination: Name of the target node.

    Returns:
        A tuple ``(total_latency, path)`` where:
        - ``total_latency`` is the sum of edge latencies on the optimal path.
        - ``path`` is an ordered list of node names from source to destination.
        Returns ``(None, None)`` when no path exists or a node is absent.

    Complexity:
        Time:  O((V + E) log V)
        Space: O(V)

    Example:
        >>> g = build_graph([
        ...     {"source": "A", "destination": "B", "latency": 10},
        ...     {"source": "B", "destination": "C", "latency": 5},
        ...     {"source": "A", "destination": "C", "latency": 20},
        ... ])
        >>> dijkstra(g, "A", "C")
        (15.0, ['A', 'B', 'C'])
    """
    if source not in graph or destination not in graph:
        return None, None

    # dist[node] = best known distance from source
    dist: dict[str, float] = {source: 0.0}
    # prev[node] = predecessor on the best path
    prev: dict[str, Optional[str]] = {source: None}

    # Min-heap entries: (current_cost, node_name)
    heap: list[tuple[float, str]] = [(0.0, source)]

    visited: set[str] = set()

    while heap:
        cost, node = heapq.heappop(heap)

        if node in visited:
            continue
        visited.add(node)

        if node == destination:
            break

        for neighbour, latency in graph.get(node, []):
            new_cost = cost + latency
            if new_cost < dist.get(neighbour, float("inf")):
                dist[neighbour] = new_cost
                prev[neighbour] = node
                heapq.heappush(heap, (new_cost, neighbour))

    if destination not in dist:
        return None, None  # No path found

    # Reconstruct path by walking backwards through prev[]
    path: list[str] = []
    current: Optional[str] = destination
    while current is not None:
        path.append(current)
        current = prev.get(current)
    path.reverse()

    return dist[destination], path