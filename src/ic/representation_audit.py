from __future__ import annotations

import csv
import math
import statistics
from collections import Counter
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml


REPRESENTATION_ORDER = (
    "multidigraph_directed",
    "multigraph_undirected",
    "digraph_min_length",
    "graph_min_length",
)

AUDIT_FIELDS = (
    "city_id",
    "dataset_stage",
    "representation",
    "directed",
    "multigraph",
    "component_definition",
    "nodes",
    "edges",
    "components",
    "largest_component_nodes",
    "largest_component_fraction",
    "strong_components",
    "largest_strong_component_nodes",
    "valid_length_edges",
    "missing_or_invalid_length_edges",
    "total_edge_length_m",
    "directed_length_m",
    "physical_collapsed_length_m",
    "self_loops",
    "parallel_endpoint_pairs",
    "parallel_edge_excess",
    "reciprocal_endpoint_pairs",
    "unreciprocated_endpoint_pairs",
    "oneway_edges_by_attribute",
    "oneway_edge_fraction",
    "raw_to_clean_nodes_lost",
    "raw_to_clean_nodes_loss_fraction",
    "raw_to_clean_edges_lost",
    "raw_to_clean_edges_loss_fraction",
    "raw_to_clean_largest_component_nodes_lost",
    "raw_to_clean_total_edge_length_lost_m",
    "raw_to_clean_total_edge_length_loss_fraction",
    "raw_to_clean_directed_length_lost_m",
    "raw_to_clean_directed_length_loss_fraction",
    "raw_to_clean_physical_length_lost_m",
    "raw_to_clean_physical_length_loss_fraction",
    "raw_to_clean_self_loops_removed",
    "raw_to_clean_parallel_edge_excess_removed",
    "raw_to_clean_reciprocal_pairs_removed",
    "raw_to_clean_oneway_edges_removed",
    "raw_to_clean_components_change",
)

SENSITIVITY_FIELDS = (
    "city_id",
    "comparison_scope",
    "dataset_a",
    "representation_a",
    "dataset_b",
    "representation_b",
    "metric",
    "nodes_a",
    "nodes_b",
    "common_nodes",
    "nodes_excluded_from_spearman",
    "spearman_rank_correlation",
    "top_k_requested",
    "top_k_effective",
    "top_k_overlap",
    "betweenness_samples_a",
    "betweenness_samples_b",
    "betweenness_mode_a",
    "betweenness_mode_b",
    "status",
    "interpretation_note",
)


def _length_m(data: dict[str, Any]) -> float | None:
    """Return a finite, positive edge length without inventing a default."""
    try:
        length = float(data.get("length"))
    except (TypeError, ValueError):
        return None
    return length if math.isfinite(length) and length > 0 else None


def _edge_records(G: nx.Graph) -> Iterable[tuple[Any, Any, Any, dict[str, Any]]]:
    if G.is_multigraph():
        yield from G.edges(keys=True, data=True)
        return
    for u, v, data in G.edges(data=True):
        yield u, v, None, data


def _copy_shortest_edge(H: nx.Graph, u: Any, v: Any, data: dict[str, Any]) -> None:
    candidate = _length_m(data)
    if not H.has_edge(u, v):
        attrs = dict(data)
        if candidate is not None:
            attrs["length"] = candidate
        H.add_edge(u, v, **attrs)
        return

    current = _length_m(H[u][v])
    if candidate is not None and (current is None or candidate < current):
        attrs = dict(data)
        attrs["length"] = candidate
        H[u][v].clear()
        H[u][v].update(attrs)


def _undirected_multigraph(G: nx.MultiDiGraph) -> nx.MultiGraph:
    """Drop direction while retaining every directed arc as a multiedge."""
    H = nx.MultiGraph()
    H.graph.update(G.graph)
    H.add_nodes_from(G.nodes(data=True))
    for u, v, _key, data in _edge_records(G):
        H.add_edge(u, v, **dict(data))
    return H


def _directed_min_length_graph(G: nx.MultiDiGraph) -> nx.DiGraph:
    H = nx.DiGraph()
    H.graph.update(G.graph)
    H.add_nodes_from(G.nodes(data=True))
    for u, v, _key, data in _edge_records(G):
        _copy_shortest_edge(H, u, v, data)
    return H


def _undirected_min_length_graph(G: nx.Graph) -> nx.Graph:
    H = nx.Graph()
    H.graph.update(G.graph)
    H.add_nodes_from(G.nodes(data=True))
    for u, v, _key, data in _edge_records(G):
        _copy_shortest_edge(H, u, v, data)
    return H


def _representations(G: nx.Graph, source: str) -> dict[str, nx.Graph]:
    if not G.is_directed():
        raise TypeError(f"O grafo {source} deve ser direcionado; recebido {type(G).__name__}.")

    # The audit never mutates the source representation, so retaining the
    # loaded MultiDiGraph avoids one full graph copy on city-scale datasets.
    directed_multi = G if isinstance(G, nx.MultiDiGraph) else nx.MultiDiGraph(G)
    return {
        "multidigraph_directed": directed_multi,
        "multigraph_undirected": _undirected_multigraph(directed_multi),
        "digraph_min_length": _directed_min_length_graph(directed_multi),
        "graph_min_length": _undirected_min_length_graph(directed_multi),
    }


def _stable_node_key(node: Any) -> tuple[str, str]:
    return type(node).__name__, repr(node)


def _unordered_pair(u: Any, v: Any) -> tuple[Any, Any]:
    a, b = sorted((u, v), key=_stable_node_key)
    return a, b


def _parallel_counts(G: nx.Graph) -> tuple[int, int]:
    counts: Counter[Any] = Counter()
    for u, v in G.edges():
        pair = (u, v) if G.is_directed() else _unordered_pair(u, v)
        counts[pair] += 1
    parallel_pairs = sum(count > 1 for count in counts.values())
    excess = sum(max(0, count - 1) for count in counts.values())
    return parallel_pairs, excess


def _reciprocity_counts(G: nx.Graph) -> tuple[int | str, int | str]:
    if not G.is_directed():
        return "", ""
    endpoint_pairs = {_unordered_pair(u, v) for u, v in G.edges() if u != v}
    reciprocal = 0
    unreciprocated = 0
    for u, v in endpoint_pairs:
        if G.has_edge(u, v) and G.has_edge(v, u):
            reciprocal += 1
        else:
            unreciprocated += 1
    return reciprocal, unreciprocated


def _is_oneway(value: Any) -> bool:
    if isinstance(value, (list, tuple, set)):
        return any(_is_oneway(item) for item in value)
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return value in {1, -1}
    return str(value).strip().lower() in {"true", "yes", "1", "-1", "t", "y"}


def _component_metrics(G: nx.Graph) -> dict[str, Any]:
    n = G.number_of_nodes()
    if n == 0:
        return {
            "component_definition": "weak" if G.is_directed() else "connected",
            "components": 0,
            "largest_component_nodes": 0,
            "largest_component_fraction": 0.0,
            "strong_components": 0 if G.is_directed() else "",
            "largest_strong_component_nodes": 0 if G.is_directed() else "",
        }

    if G.is_directed():
        weak_sizes = [len(component) for component in nx.weakly_connected_components(G)]
        strong_sizes = [len(component) for component in nx.strongly_connected_components(G)]
        return {
            "component_definition": "weak",
            "components": len(weak_sizes),
            "largest_component_nodes": max(weak_sizes),
            "largest_component_fraction": max(weak_sizes) / n,
            "strong_components": len(strong_sizes),
            "largest_strong_component_nodes": max(strong_sizes),
        }

    component_sizes = [len(component) for component in nx.connected_components(G)]
    largest = max(component_sizes)
    return {
        "component_definition": "connected",
        "components": len(component_sizes),
        "largest_component_nodes": largest,
        "largest_component_fraction": largest / n,
        "strong_components": "",
        "largest_strong_component_nodes": "",
    }


def _audit_metrics(city_id: str, stage: str, name: str, G: nx.Graph) -> dict[str, Any]:
    lengths = [_length_m(data) for _u, _v, _key, data in _edge_records(G)]
    valid_lengths = [length for length in lengths if length is not None]
    physical = _undirected_min_length_graph(G)
    physical_lengths = [
        length
        for _u, _v, _key, data in _edge_records(physical)
        if (length := _length_m(data)) is not None
    ]
    parallel_pairs, parallel_excess = _parallel_counts(G)
    reciprocal_pairs, unreciprocated_pairs = _reciprocity_counts(G)
    oneway_edges = sum(_is_oneway(data.get("oneway")) for _u, _v, _key, data in _edge_records(G))
    edges = G.number_of_edges()

    return {
        "city_id": city_id,
        "dataset_stage": stage,
        "representation": name,
        "directed": int(G.is_directed()),
        "multigraph": int(G.is_multigraph()),
        **_component_metrics(G),
        "nodes": G.number_of_nodes(),
        "edges": edges,
        "valid_length_edges": len(valid_lengths),
        "missing_or_invalid_length_edges": edges - len(valid_lengths),
        "total_edge_length_m": sum(valid_lengths),
        "directed_length_m": sum(valid_lengths) if G.is_directed() else "",
        "physical_collapsed_length_m": sum(physical_lengths),
        "self_loops": nx.number_of_selfloops(G),
        "parallel_endpoint_pairs": parallel_pairs,
        "parallel_edge_excess": parallel_excess,
        "reciprocal_endpoint_pairs": reciprocal_pairs,
        "unreciprocated_endpoint_pairs": unreciprocated_pairs,
        "oneway_edges_by_attribute": oneway_edges,
        "oneway_edge_fraction": oneway_edges / edges if edges else 0.0,
    }


def _loss(raw: Any, clean: Any) -> float | str:
    if raw == "" or clean == "":
        return ""
    return float(raw) - float(clean)


def _loss_fraction(raw: Any, clean: Any) -> float | str:
    if raw == "" or clean == "":
        return ""
    raw_value = float(raw)
    return (raw_value - float(clean)) / raw_value if raw_value else ""


def _add_raw_to_clean_losses(
    rows: list[dict[str, Any]], metrics: dict[tuple[str, str], dict[str, Any]]
) -> None:
    for name in REPRESENTATION_ORDER:
        raw = metrics[("raw", name)]
        clean = metrics[("clean", name)]
        losses = {
            "raw_to_clean_nodes_lost": _loss(raw["nodes"], clean["nodes"]),
            "raw_to_clean_nodes_loss_fraction": _loss_fraction(raw["nodes"], clean["nodes"]),
            "raw_to_clean_edges_lost": _loss(raw["edges"], clean["edges"]),
            "raw_to_clean_edges_loss_fraction": _loss_fraction(raw["edges"], clean["edges"]),
            "raw_to_clean_largest_component_nodes_lost": _loss(
                raw["largest_component_nodes"], clean["largest_component_nodes"]
            ),
            "raw_to_clean_total_edge_length_lost_m": _loss(
                raw["total_edge_length_m"], clean["total_edge_length_m"]
            ),
            "raw_to_clean_total_edge_length_loss_fraction": _loss_fraction(
                raw["total_edge_length_m"], clean["total_edge_length_m"]
            ),
            "raw_to_clean_directed_length_lost_m": _loss(
                raw["directed_length_m"], clean["directed_length_m"]
            ),
            "raw_to_clean_directed_length_loss_fraction": _loss_fraction(
                raw["directed_length_m"], clean["directed_length_m"]
            ),
            "raw_to_clean_physical_length_lost_m": _loss(
                raw["physical_collapsed_length_m"], clean["physical_collapsed_length_m"]
            ),
            "raw_to_clean_physical_length_loss_fraction": _loss_fraction(
                raw["physical_collapsed_length_m"], clean["physical_collapsed_length_m"]
            ),
            "raw_to_clean_self_loops_removed": _loss(raw["self_loops"], clean["self_loops"]),
            "raw_to_clean_parallel_edge_excess_removed": _loss(
                raw["parallel_edge_excess"], clean["parallel_edge_excess"]
            ),
            "raw_to_clean_reciprocal_pairs_removed": _loss(
                raw["reciprocal_endpoint_pairs"], clean["reciprocal_endpoint_pairs"]
            ),
            "raw_to_clean_oneway_edges_removed": _loss(
                raw["oneway_edges_by_attribute"], clean["oneway_edges_by_attribute"]
            ),
            "raw_to_clean_components_change": float(clean["components"]) - float(raw["components"]),
        }
        raw.update(losses)
        clean.update(losses)

    rows.sort(
        key=lambda row: (
            0 if row["dataset_stage"] == "raw" else 1,
            REPRESENTATION_ORDER.index(row["representation"]),
        )
    )


def _rank(values: list[float]) -> list[float]:
    order = sorted(range(len(values)), key=values.__getitem__)
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        average_rank = (i + j - 1) / 2.0 + 1.0
        for index in order[i:j]:
            ranks[index] = average_rank
        i = j
    return ranks


def _spearman(xs: list[float], ys: list[float]) -> float | None:
    if len(xs) != len(ys) or len(xs) < 2:
        return None
    rank_x = _rank(xs)
    rank_y = _rank(ys)
    mean_x = statistics.mean(rank_x)
    mean_y = statistics.mean(rank_y)
    numerator = sum((x - mean_x) * (y - mean_y) for x, y in zip(rank_x, rank_y))
    denominator = math.sqrt(
        sum((x - mean_x) ** 2 for x in rank_x) * sum((y - mean_y) ** 2 for y in rank_y)
    )
    return numerator / denominator if denominator else None


def _top_nodes(values: dict[Any, float], k: int) -> set[Any]:
    ordered = sorted(values.items(), key=lambda item: (-item[1], _stable_node_key(item[0])))
    return {node for node, _value in ordered[:k]}


def _ranking_values(
    G: nx.Graph, top_k: int, seed: int
) -> tuple[dict[str, dict[Any, float]], int, str]:
    degree = {node: float(value) for node, value in G.degree()}
    n = G.number_of_nodes()
    if n == 0:
        return {"degree": degree, "betweenness_unweighted": {}}, 0, "not_computed_empty_graph"

    samples = min(n, max(50, min(200, top_k * 5)))
    betweenness = nx.betweenness_centrality(
        G,
        k=samples,
        normalized=True,
        weight=None,
        endpoints=False,
        seed=seed,
    )
    mode = "exact_all_nodes" if samples == n else "approximate_pivots"
    return {"degree": degree, "betweenness_unweighted": betweenness}, samples, mode


def _comparison_row(
    city_id: str,
    scope: str,
    dataset_a: str,
    representation_a: str,
    dataset_b: str,
    representation_b: str,
    metric: str,
    values_a: dict[Any, float],
    values_b: dict[Any, float],
    top_k: int,
    samples_a: int,
    samples_b: int,
    mode_a: str,
    mode_b: str,
) -> dict[str, Any]:
    common = sorted(set(values_a) & set(values_b), key=_stable_node_key)
    rho = _spearman([values_a[node] for node in common], [values_b[node] for node in common])
    effective_k = min(top_k, len(values_a), len(values_b))
    overlap: float | str = ""
    if effective_k:
        overlap = len(_top_nodes(values_a, effective_k) & _top_nodes(values_b, effective_k)) / effective_k

    if not common:
        status = "undefined_no_common_nodes"
    elif rho is None:
        status = "spearman_undefined_zero_variance_or_small_n"
    else:
        status = "ok"

    if metric == "degree":
        samples_a_out: int | str = ""
        samples_b_out: int | str = ""
        mode_a_out = "not_applicable"
        mode_b_out = "not_applicable"
        note = "Grau total: in+out nos grafos dirigidos e multiplicidade preservada nos multigrafos."
    else:
        samples_a_out = samples_a
        samples_b_out = samples_b
        mode_a_out = mode_a
        mode_b_out = mode_b
        note = "Betweenness de nós sem peso; paralelas não representam demanda nem escolhas independentes de rota."

    return {
        "city_id": city_id,
        "comparison_scope": scope,
        "dataset_a": dataset_a,
        "representation_a": representation_a,
        "dataset_b": dataset_b,
        "representation_b": representation_b,
        "metric": metric,
        "nodes_a": len(values_a),
        "nodes_b": len(values_b),
        "common_nodes": len(common),
        "nodes_excluded_from_spearman": len(set(values_a) | set(values_b)) - len(common),
        "spearman_rank_correlation": "" if rho is None else rho,
        "top_k_requested": top_k,
        "top_k_effective": effective_k,
        "top_k_overlap": overlap,
        "betweenness_samples_a": samples_a_out,
        "betweenness_samples_b": samples_b_out,
        "betweenness_mode_a": mode_a_out,
        "betweenness_mode_b": mode_b_out,
        "status": status,
        "interpretation_note": note,
    }


def _sensitivity_rows(
    city_id: str,
    representations: dict[str, dict[str, nx.Graph]],
    top_k: int,
    seed: int,
) -> list[dict[str, Any]]:
    ranking_values: dict[tuple[str, str], dict[str, dict[Any, float]]] = {}
    sample_metadata: dict[tuple[str, str], tuple[int, str]] = {}
    for stage in ("raw", "clean"):
        for name in REPRESENTATION_ORDER:
            values, samples, mode = _ranking_values(representations[stage][name], top_k, seed)
            ranking_values[(stage, name)] = values
            sample_metadata[(stage, name)] = (samples, mode)

    rows: list[dict[str, Any]] = []
    for stage in ("raw", "clean"):
        for name_a, name_b in combinations(REPRESENTATION_ORDER, 2):
            samples_a, mode_a = sample_metadata[(stage, name_a)]
            samples_b, mode_b = sample_metadata[(stage, name_b)]
            for metric in ("degree", "betweenness_unweighted"):
                rows.append(
                    _comparison_row(
                        city_id,
                        f"representations_within_{stage}",
                        stage,
                        name_a,
                        stage,
                        name_b,
                        metric,
                        ranking_values[(stage, name_a)][metric],
                        ranking_values[(stage, name_b)][metric],
                        top_k,
                        samples_a,
                        samples_b,
                        mode_a,
                        mode_b,
                    )
                )

    for name in REPRESENTATION_ORDER:
        samples_raw, mode_raw = sample_metadata[("raw", name)]
        samples_clean, mode_clean = sample_metadata[("clean", name)]
        for metric in ("degree", "betweenness_unweighted"):
            rows.append(
                _comparison_row(
                    city_id,
                    "preprocessing_raw_to_clean",
                    "raw",
                    name,
                    "clean",
                    name,
                    metric,
                    ranking_values[("raw", name)][metric],
                    ranking_values[("clean", name)][metric],
                    top_k,
                    samples_raw,
                    samples_clean,
                    mode_raw,
                    mode_clean,
                )
            )
    return rows


def _write_csv(path: Path, rows: list[dict[str, Any]], fieldnames: tuple[str, ...]) -> None:
    with path.open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _fmt(value: Any, digits: int = 4) -> str:
    if value == "" or value is None:
        return "NA"
    if isinstance(value, float):
        return f"{value:.{digits}f}"
    return str(value)


def _write_report(
    path: Path,
    city_id: str,
    raw_path: str,
    clean_path: str,
    rows: list[dict[str, Any]],
    sensitivity_rows: list[dict[str, Any]],
    top_k: int,
    seed: int,
) -> None:
    by_key = {(row["dataset_stage"], row["representation"]): row for row in rows}
    with path.open("w", encoding="utf-8") as stream:
        stream.write("=== Auditoria de Representação do Grafo ===\n\n")
        stream.write(f"Cidade/dataset: {city_id}\n")
        stream.write(f"Grafo raw: {raw_path}\n")
        stream.write(f"Grafo clean: {clean_path}\n")
        stream.write(f"Top-k solicitado: {top_k}; semente: {seed}\n\n")

        stream.write("Definições operacionais\n")
        stream.write("- multidigraph_directed: arcos, direção e paralelas preservados.\n")
        stream.write("- multigraph_undirected: direção removida, mas cada arco original permanece como multiaresta.\n")
        stream.write("- digraph_min_length: um arco por par ordenado, escolhendo o menor length válido.\n")
        stream.write("- graph_min_length: um segmento por par não ordenado, escolhendo o menor length válido.\n")
        stream.write("- Componentes/LCC usam componentes fracas nos grafos dirigidos e conectadas nos não dirigidos.\n")
        stream.write("- Comprimento dirigido soma arcos com length válido; ida e volta podem contar duas vezes.\n")
        stream.write("- Comprimento físico colapsado é uma aproximação pelo menor length por par não ordenado.\n\n")

        for stage in ("raw", "clean"):
            stream.write(f"Resumo {stage}\n")
            for name in REPRESENTATION_ORDER:
                row = by_key[(stage, name)]
                stream.write(
                    f"- {name}: nós={row['nodes']}; arestas={row['edges']}; "
                    f"componentes={row['components']}; LCC={row['largest_component_nodes']} "
                    f"({_fmt(row['largest_component_fraction'])}); length total={_fmt(row['total_edge_length_m'], 2)} m; "
                    f"length dirigido={_fmt(row['directed_length_m'], 2)} m; "
                    f"length físico colapsado={_fmt(row['physical_collapsed_length_m'], 2)} m; "
                    f"loops={row['self_loops']}; excesso paralelo={row['parallel_edge_excess']}; "
                    f"pares recíprocos={_fmt(row['reciprocal_endpoint_pairs'])}; "
                    f"arestas oneway={row['oneway_edges_by_attribute']}.\n"
                )
            stream.write("\n")

        stream.write("Perdas raw -> clean\n")
        for name in REPRESENTATION_ORDER:
            row = by_key[("clean", name)]
            stream.write(
                f"- {name}: nós perdidos={_fmt(row['raw_to_clean_nodes_lost'])} "
                f"({_fmt(row['raw_to_clean_nodes_loss_fraction'])}); "
                f"arestas perdidas={_fmt(row['raw_to_clean_edges_lost'])} "
                f"({_fmt(row['raw_to_clean_edges_loss_fraction'])}); "
                f"length total perdido={_fmt(row['raw_to_clean_total_edge_length_lost_m'], 2)} m; "
                f"length físico perdido={_fmt(row['raw_to_clean_physical_length_lost_m'], 2)} m.\n"
            )
        stream.write("Valores negativos indicariam ganho no clean; a diferença descreve o pré-processamento, não qualidade causal.\n\n")

        stream.write("Sensibilidade dos rankings\n")
        stream.write(
            "Spearman usa somente nós comuns. A sobreposição top-k usa os rankings completos de cada lado; "
            "empates no corte são desempatados deterministicamente pelo identificador do nó.\n"
        )
        for row in sensitivity_rows:
            stream.write(
                f"- {row['comparison_scope']} | {row['dataset_a']}:{row['representation_a']} x "
                f"{row['dataset_b']}:{row['representation_b']} | {row['metric']}: "
                f"n comum={row['common_nodes']}; rho={_fmt(row['spearman_rank_correlation'])}; "
                f"top-{row['top_k_effective']} overlap={_fmt(row['top_k_overlap'])}; status={row['status']}.\n"
            )

        stream.write("\nLimitações de interpretação\n")
        stream.write("- O comprimento físico colapsado não é uma reconstrução geométrica de ruas: pode subcontar pistas separadas e vias paralelas reais.\n")
        stream.write("- A soma dirigida não deve ser apresentada como extensão física da malha, pois pares recíprocos podem duplicar o trecho.\n")
        stream.write("- oneway_edges_by_attribute depende da completude da tag OSM; pares sem recíproca também podem refletir modelagem ou dados ausentes.\n")
        stream.write("- Grau não tem a mesma semântica nas quatro representações: direção e multiplicidade alteram a contagem.\n")
        stream.write("- Betweenness é topológica, sem peso, e aproximada quando o número de pivôs é menor que o de nós; a mesma seed não constitui IC.\n")
        stream.write("- Em multigrafos, a betweenness de nós do NetworkX não transforma cada aresta paralela em demanda ou alternativa independente.\n")
        stream.write("- Spearman indefinido por n pequeno ou ranking constante é gravado vazio, nunca como correlação zero.\n")
        stream.write("- A seleção raw -> clean pode remover componentes inteiras; comparações posteriores descrevem outra população de nós e arestas.\n")


def analisar_representacoes(city_id: str, top_k: int = 20, seed: int = 42) -> dict[str, Any]:
    """Audit how preprocessing and graph representation alter structural results.

    The routine intentionally does not choose a single "correct" representation.
    It records the information retained or collapsed by four explicit models and
    compares degree and unweighted node-betweenness rankings.
    """
    if top_k < 1:
        raise ValueError("top_k deve ser pelo menos 1.")

    ensure_city_dirs(city_id)
    raw_path = str(dataset_graph_path(city_id, "raw"))
    clean_path = str(dataset_graph_path(city_id, "clean"))
    raw_graph = load_graphml(raw_path)
    clean_graph = load_graphml(clean_path)

    representations = {
        "raw": _representations(raw_graph, raw_path),
        "clean": _representations(clean_graph, clean_path),
    }
    metrics_by_key: dict[tuple[str, str], dict[str, Any]] = {}
    audit_rows: list[dict[str, Any]] = []
    for stage in ("raw", "clean"):
        for name in REPRESENTATION_ORDER:
            row = _audit_metrics(city_id, stage, name, representations[stage][name])
            metrics_by_key[(stage, name)] = row
            audit_rows.append(row)
    _add_raw_to_clean_losses(audit_rows, metrics_by_key)

    sensitivity_rows = _sensitivity_rows(city_id, representations, top_k, seed)
    metrics_dir = Path(f"outputs/{city_id}/metrics")
    logs_dir = Path(f"outputs/{city_id}/logs")
    audit_csv = metrics_dir / "graph_representation_audit.csv"
    sensitivity_csv = metrics_dir / "representation_metric_sensitivity.csv"
    report_txt = logs_dir / "graph_representation_report.txt"

    _write_csv(audit_csv, audit_rows, AUDIT_FIELDS)
    _write_csv(sensitivity_csv, sensitivity_rows, SENSITIVITY_FIELDS)
    _write_report(
        report_txt,
        city_id,
        raw_path,
        clean_path,
        audit_rows,
        sensitivity_rows,
        top_k,
        seed,
    )
    return {
        "audit_csv": str(audit_csv),
        "sensitivity_csv": str(sensitivity_csv),
        "report_txt": str(report_txt),
        "representations": list(REPRESENTATION_ORDER),
        "ranking_comparisons": len(sensitivity_rows),
    }
