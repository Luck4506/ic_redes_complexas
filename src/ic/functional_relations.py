from __future__ import annotations

import csv
import math
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

from .graph_inventory import _first_value, _parse_float_values, _surface_category, _values
from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph


CENTRALITY_FIELDS = ["degree_centrality", "betweenness", "closeness_approx", "eigenvector"]


def _read_centralities(path: str) -> dict[str, dict[str, float]]:
    rows: dict[str, dict[str, float]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            rows[str(row["node"])] = {field: float(row[field]) for field in CENTRALITY_FIELDS}
    return rows


def _mean(values: list[float]) -> float:
    return statistics.mean(values) if values else math.nan


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        rank = (i + j - 1) / 2.0 + 1.0
        for index in order[i:j]:
            ranks[index] = rank
        i = j
    return ranks


def spearman_correlation(xs: list[float], ys: list[float]) -> float:
    if len(xs) != len(ys) or len(xs) < 2:
        return math.nan
    rx, ry = _rank(xs), _rank(ys)
    mx, my = statistics.mean(rx), statistics.mean(ry)
    numerator = sum((x - mx) * (y - my) for x, y in zip(rx, ry))
    denominator = math.sqrt(sum((x - mx) ** 2 for x in rx) * sum((y - my) ** 2 for y in ry))
    return numerator / denominator if denominator else math.nan


def analisar_relacoes_funcionais(city_id: str) -> dict:
    """Relaciona atributos funcionais OSM à posição topológica das arestas."""
    ensure_city_dirs(city_id)
    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    centrality_path = f"outputs/{city_id}/metrics/node_centralities.csv"
    if not Path(centrality_path).exists():
        raise FileNotFoundError(f"Execute antes: ic centrality --city {city_id}")

    G = simple_undirected_min_length_graph(load_graphml(graph_path))
    centralities = _read_centralities(centrality_path)
    groups: dict[tuple[str, str], dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))
    numeric: dict[str, dict[str, list[float]]] = defaultdict(lambda: defaultdict(list))

    for u, v, data in G.edges(data=True):
        cu, cv = centralities.get(str(u)), centralities.get(str(v))
        if not cu or not cv:
            continue
        edge_scores = {field: (cu[field] + cv[field]) / 2.0 for field in CENTRALITY_FIELDS}
        categories = {
            "highway": str((_values(data.get("highway")) or ["desconhecido"])[0]),
            "surface": _surface_category(data.get("surface")),
            "oneway": str(data.get("oneway", "desconhecido")).lower(),
        }
        for attribute, category in categories.items():
            bucket = groups[(attribute, category)]
            bucket["length_m"].append(float(data.get("length", 0.0)))
            for field, value in edge_scores.items():
                bucket[field].append(value)
        for attribute, values in {
            "maxspeed": _parse_float_values(data.get("maxspeed")),
            "lanes": _parse_float_values(data.get("lanes")),
        }.items():
            if values:
                value = statistics.mean(values)
                for field, score in edge_scores.items():
                    numeric[attribute][field].append(score)
                numeric[attribute]["attribute_value"].append(value)

    metrics_dir = Path(f"outputs/{city_id}/metrics")
    logs_dir = Path(f"outputs/{city_id}/logs")
    grouped_csv = metrics_dir / "functional_topology_groups.csv"
    correlations_csv = metrics_dir / "functional_topology_correlations.csv"
    report_txt = logs_dir / "functional_topology_report.txt"

    grouped_rows = []
    for (attribute, category), values in sorted(groups.items()):
        grouped_rows.append({
            "attribute": attribute,
            "category": category,
            "edges": len(values["length_m"]),
            "mean_length_m": _mean(values["length_m"]),
            **{f"mean_{field}": _mean(values[field]) for field in CENTRALITY_FIELDS},
        })
    with grouped_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(grouped_rows[0].keys()))
        writer.writeheader()
        writer.writerows(grouped_rows)

    correlation_rows = []
    for attribute, values in sorted(numeric.items()):
        for field in CENTRALITY_FIELDS:
            correlation_rows.append({
                "attribute": attribute,
                "topology_metric": field,
                "observations": len(values["attribute_value"]),
                "spearman_correlation": spearman_correlation(values["attribute_value"], values[field]),
            })
    with correlations_csv.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(correlation_rows[0].keys()))
        writer.writeheader()
        writer.writerows(correlation_rows)

    with report_txt.open("w", encoding="utf-8") as f:
        f.write("=== Relações entre Topologia e Características Funcionais ===\n\n")
        f.write("Unidade analisada: aresta do grafo simples não direcionado.\n")
        f.write("A posição topológica da aresta é a média das centralidades de seus extremos.\n")
        f.write("Grupos categóricos: highway, surface e oneway.\n")
        f.write("Relações numéricas: correlação de Spearman de maxspeed e lanes com centralidades.\n")
        f.write("Atributos ausentes no OSM são excluídos das correlações numéricas.\n\n")
        for row in correlation_rows:
            f.write(
                f"{row['attribute']} x {row['topology_metric']}: "
                f"n={row['observations']} rho={row['spearman_correlation']}\n"
            )
    return {
        "grouped_csv": str(grouped_csv),
        "correlations_csv": str(correlations_csv),
        "report_txt": str(report_txt),
    }
