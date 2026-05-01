from __future__ import annotations

import math
import random
from typing import Any

import networkx as nx


def edge_length_m(data: dict[str, Any], default: float = 1.0) -> float:
    try:
        value = float(data.get("length", default))
    except (TypeError, ValueError):
        return default
    return value if math.isfinite(value) and value > 0 else default


def simple_undirected_min_length_graph(G: nx.Graph) -> nx.Graph:
    """Collapse a road MultiDiGraph into a simple undirected graph.

    Parallel directed edges are represented by one undirected edge whose
    ``length`` is the shortest available segment length between the endpoints.
    """
    Gu = nx.Graph()
    Gu.add_nodes_from(G.nodes(data=True))

    for u, v, data in G.edges(data=True):
        length = edge_length_m(data)
        if Gu.has_edge(u, v):
            if length < Gu[u][v].get("length", math.inf):
                Gu[u][v].update(data)
                Gu[u][v]["length"] = length
        else:
            attrs = dict(data)
            attrs["length"] = length
            Gu.add_edge(u, v, **attrs)

    return Gu


def approximate_global_efficiency(
    G: nx.Graph,
    samples: int = 20,
    seed: int = 42,
    weight: str | None = None,
) -> float:
    """Approximate global efficiency with disconnected pairs contributing zero."""
    n = G.number_of_nodes()
    if n < 2:
        return 0.0

    samples = max(1, samples)
    rng = random.Random(seed)
    nodes = list(G.nodes())
    sample_nodes = nodes if len(nodes) <= samples else rng.sample(nodes, samples)

    total = 0.0
    for source in sample_nodes:
        if weight is None:
            distances = nx.single_source_shortest_path_length(G, source)
        else:
            distances = nx.single_source_dijkstra_path_length(G, source, weight=weight)

        for target, distance in distances.items():
            if target != source and distance > 0:
                total += 1.0 / float(distance)

    denominator = len(sample_nodes) * (n - 1)
    return total / denominator if denominator else 0.0
