from __future__ import annotations

import ast
import csv
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import simple_undirected_min_length_graph


PAVED_SURFACES = {
    "asphalt",
    "concrete",
    "concrete:lanes",
    "concrete:plates",
    "paved",
    "paving_stones",
    "sett",
    "cobblestone",
    "unhewn_cobblestone",
    "bricks",
}

UNPAVED_SURFACES = {
    "unpaved",
    "dirt",
    "earth",
    "ground",
    "gravel",
    "fine_gravel",
    "compacted",
    "sand",
    "grass",
    "grass_paver",
    "mud",
    "woodchips",
    "pebblestone",
    "rock",
}


def _values(value: Any) -> list[Any]:
    if value in (None, "", "nan"):
        return []

    if isinstance(value, (list, tuple, set)):
        return list(value)

    if isinstance(value, str):
        text = value.strip()
        if text.startswith("[") and text.endswith("]"):
            try:
                parsed = ast.literal_eval(text)
                if isinstance(parsed, (list, tuple, set)):
                    return list(parsed)
            except (SyntaxError, ValueError):
                pass
        return [text]

    return [value]


def _first_value(value: Any) -> str:
    vals = _values(value)
    if not vals:
        return "desconhecido"
    return str(vals[0]).strip() or "desconhecido"


def _length_m(data: dict[str, Any]) -> float:
    try:
        return float(data.get("length", 0.0))
    except (TypeError, ValueError):
        return 0.0


def _as_bool_label(value: Any) -> str:
    text = str(value).strip().lower()
    if text in {"true", "1", "yes", "sim"}:
        return "sim"
    if text in {"false", "0", "no", "nao", "não"}:
        return "nao"
    return "desconhecido"


def _parse_float_values(value: Any) -> list[float]:
    parsed = []
    for raw in _values(value):
        text = str(raw).lower().replace("km/h", "").strip()
        try:
            parsed.append(float(text))
        except ValueError:
            continue
    return parsed


def _surface_category(value: Any) -> str:
    vals = {str(v).strip().lower() for v in _values(value)}
    vals.discard("")
    if not vals:
        return "desconhecido"
    if vals & PAVED_SURFACES:
        return "pavimentado"
    if vals & UNPAVED_SURFACES:
        return "terra_sem_pavimento"
    return "outro_surface"


def _unique_names(edges: Iterable[tuple[Any, Any, dict[str, Any]]]) -> set[str]:
    names: set[str] = set()
    for _, _, data in edges:
        for name in _values(data.get("name")):
            text = str(name).strip()
            if text:
                names.add(text)
    return names


def _write_rows(path: str, header: list[str], rows: list[list[Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.writer(f)
        writer.writerow(header)
        writer.writerows(rows)


def _add_metric(rows: list[list[Any]], group: str, metric: str, value: Any, unit: str, description: str) -> None:
    rows.append([group, metric, value, unit, description])


def _read_csv_dicts(path: str) -> list[dict[str, str]]:
    if not Path(path).exists():
        return []

    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_metric_value_csv(path: str) -> dict[str, str]:
    rows = _read_csv_dicts(path)
    result = {}
    for row in rows:
        metric = row.get("metric")
        if metric:
            result[metric] = row.get("value", "")
    return result


def _add_existing_pipeline_outputs(summary_rows: list[list[Any]], city_id: str) -> None:
    metrics_dir = f"outputs/{city_id}/metrics"

    structural = _read_metric_value_csv(f"{metrics_dir}/structural_metrics.csv")
    if structural:
        for metric, value in structural.items():
            _add_metric(
                summary_rows,
                "metricas_estruturais",
                f"structural_{metric}",
                value,
                "valor",
                "Metrica gerada pela etapa structural_metrics.csv.",
            )
    else:
        _add_metric(summary_rows, "metricas_estruturais", "structural_available", "nao", "booleano", "Arquivo structural_metrics.csv nao encontrado.")

    route_rows = _read_csv_dicts(f"{metrics_dir}/rota_distancia_resumo.csv")
    if route_rows:
        row = route_rows[0]
        for metric in ["orig_node", "dest_node", "distance_total_m", "num_nodes_in_route"]:
            _add_metric(summary_rows, "rota", f"route_{metric}", row.get(metric, ""), "valor", "Resumo da rota de menor distancia gerada pela etapa paths.")
    else:
        _add_metric(summary_rows, "rota", "route_available", "nao", "booleano", "Arquivo rota_distancia_resumo.csv nao encontrado.")

    top_nodes = _read_csv_dicts(f"{metrics_dir}/top_nodes.csv")
    if top_nodes:
        best = top_nodes[0]
        _add_metric(summary_rows, "centralidade", "centrality_top_nodes_count", len(top_nodes), "linhas", "Quantidade de nos listados em top_nodes.csv.")
        _add_metric(summary_rows, "centralidade", "centrality_top_node", best.get("node", ""), "node_id", "No com maior betweenness no arquivo top_nodes.csv.")
        _add_metric(summary_rows, "centralidade", "centrality_top_node_betweenness", best.get("betweenness", ""), "razao", "Betweenness do principal no critico.")
        _add_metric(summary_rows, "centralidade", "centrality_top_node_degree_centrality", best.get("degree_centrality", ""), "razao", "Degree centrality do principal no critico.")
    else:
        _add_metric(summary_rows, "centralidade", "centrality_available", "nao", "booleano", "Arquivo top_nodes.csv nao encontrado.")

    top_edges = _read_csv_dicts(f"{metrics_dir}/top_edges.csv")
    if top_edges:
        best = top_edges[0]
        _add_metric(summary_rows, "centralidade", "centrality_top_edges_count", len(top_edges), "linhas", "Quantidade de arestas listadas em top_edges.csv.")
        _add_metric(summary_rows, "centralidade", "centrality_top_edge_u", best.get("u", ""), "node_id", "No inicial da aresta com maior edge betweenness.")
        _add_metric(summary_rows, "centralidade", "centrality_top_edge_v", best.get("v", ""), "node_id", "No final da aresta com maior edge betweenness.")
        _add_metric(summary_rows, "centralidade", "centrality_top_edge_betweenness", best.get("edge_betweenness", ""), "razao", "Maior edge betweenness encontrada.")

    communities = _read_csv_dicts(f"{metrics_dir}/community_summary.csv")
    if communities:
        sizes = []
        for row in communities:
            try:
                sizes.append(int(row.get("size", "0")))
            except ValueError:
                pass
        total_nodes = sum(sizes)
        _add_metric(summary_rows, "comunidades", "communities_count", len(communities), "comunidades", "Quantidade de comunidades detectadas.")
        _add_metric(summary_rows, "comunidades", "communities_largest_size", max(sizes) if sizes else 0, "nos", "Tamanho da maior comunidade.")
        _add_metric(summary_rows, "comunidades", "communities_largest_pct", (max(sizes) / total_nodes) if sizes and total_nodes else 0.0, "percentual", "Participacao da maior comunidade no total de nos classificados.")
    else:
        _add_metric(summary_rows, "comunidades", "communities_available", "nao", "booleano", "Arquivo community_summary.csv nao encontrado.")

    for strategy in ["targeted", "targeted_adaptive", "random"]:
        resilience = _read_csv_dicts(f"{metrics_dir}/resilience_curve_{strategy}.csv")
        if not resilience:
            _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_available", "nao", "booleano", f"Arquivo resilience_curve_{strategy}.csv nao encontrado.")
            continue

        first = resilience[0]
        last = resilience[-1]
        _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_points", len(resilience), "pontos", f"Quantidade de pontos da curva de resiliencia {strategy}.")
        for metric in ["removed_edges", "removed_fraction", "lcc_size", "lcc_fraction", "num_components", "efficiency_approx"]:
            _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_initial_{metric}", first.get(metric, ""), "valor", f"Valor inicial de {metric} na curva de resiliencia {strategy}.")
            _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_final_{metric}", last.get(metric, ""), "valor", f"Valor final de {metric} na curva de resiliencia {strategy}.")

        try:
            initial_lcc = float(first.get("lcc_fraction", "nan"))
            final_lcc = float(last.get("lcc_fraction", "nan"))
            _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_lcc_fraction_drop", initial_lcc - final_lcc, "pontos_percentuais", f"Queda da fracao da maior componente na curva {strategy}.")
        except ValueError:
            pass

    for strategy in ["targeted", "targeted_adaptive", "random"]:
        resilience = _read_csv_dicts(f"{metrics_dir}/community_resilience_curve_{strategy}.csv")
        if not resilience:
            _add_metric(summary_rows, "resiliencia_comunidades", f"community_resilience_{strategy}_available", "nao", "booleano", f"Arquivo community_resilience_curve_{strategy}.csv nao encontrado.")
            continue

        first = resilience[0]
        last = resilience[-1]
        _add_metric(summary_rows, "resiliencia_comunidades", f"community_resilience_{strategy}_points", len(resilience), "pontos", f"Quantidade de pontos da curva de resiliencia por comunidades {strategy}.")
        for metric in [
            "removed_edges",
            "removed_fraction",
            "lcc_communities",
            "lcc_communities_fraction",
            "lcc_nodes_fraction",
            "num_components",
            "efficiency_topological_retained",
            "efficiency_length_retained",
        ]:
            _add_metric(summary_rows, "resiliencia_comunidades", f"community_resilience_{strategy}_initial_{metric}", first.get(metric, ""), "valor", f"Valor inicial de {metric} na curva de resiliencia por comunidades {strategy}.")
            _add_metric(summary_rows, "resiliencia_comunidades", f"community_resilience_{strategy}_final_{metric}", last.get(metric, ""), "valor", f"Valor final de {metric} na curva de resiliencia por comunidades {strategy}.")

        try:
            initial_lcc = float(first.get("lcc_nodes_fraction", "nan"))
            final_lcc = float(last.get("lcc_nodes_fraction", "nan"))
            _add_metric(summary_rows, "resiliencia_comunidades", f"community_resilience_{strategy}_lcc_nodes_fraction_drop", initial_lcc - final_lcc, "pontos_percentuais", f"Queda da fracao ponderada por nos na curva de comunidades {strategy}.")
        except ValueError:
            pass

    for strategy in ["targeted", "targeted_adaptive", "random"]:
        summaries = _read_csv_dicts(f"{metrics_dir}/intra_community_resilience_summary_{strategy}.csv")
        if not summaries:
            _add_metric(
                summary_rows,
                "resiliencia_interna_comunidades",
                f"intra_community_resilience_{strategy}_available",
                "nao",
                "booleano",
                f"Arquivo intra_community_resilience_summary_{strategy}.csv nao encontrado.",
            )
            continue

        def numeric_values(key: str) -> list[float]:
            values = []
            for row in summaries:
                try:
                    values.append(float(row.get(key, "")))
                except ValueError:
                    pass
            return values

        auc_values = numeric_values("resilience_auc_lcc")
        final_lcc_values = numeric_values("final_lcc_fraction")
        _add_metric(
            summary_rows,
            "resiliencia_interna_comunidades",
            f"intra_community_resilience_{strategy}_communities",
            len(summaries),
            "comunidades",
            f"Quantidade de comunidades com resiliência interna calculada na estratégia {strategy}.",
        )
        if auc_values:
            _add_metric(
                summary_rows,
                "resiliencia_interna_comunidades",
                f"intra_community_resilience_{strategy}_auc_lcc_mean",
                sum(auc_values) / len(auc_values),
                "razao",
                f"Média da AUC normalizada da LCC entre comunidades na estratégia {strategy}.",
            )
            _add_metric(
                summary_rows,
                "resiliencia_interna_comunidades",
                f"intra_community_resilience_{strategy}_auc_lcc_min",
                min(auc_values),
                "razao",
                f"Menor AUC normalizada da LCC entre comunidades na estratégia {strategy}.",
            )
        if final_lcc_values:
            _add_metric(
                summary_rows,
                "resiliencia_interna_comunidades",
                f"intra_community_resilience_{strategy}_final_lcc_mean",
                sum(final_lcc_values) / len(final_lcc_values),
                "percentual",
                f"Média da fração final da LCC entre comunidades na estratégia {strategy}.",
            )


def _counter_rows(counter: dict[str, dict[str, float]], total_edges: int, total_length_m: float) -> list[list[Any]]:
    rows = []
    for label, values in sorted(counter.items(), key=lambda item: (-item[1]["length_m"], item[0])):
        edge_count = int(values["edges"])
        length_m = float(values["length_m"])
        rows.append([
            label,
            edge_count,
            edge_count / total_edges if total_edges else 0.0,
            length_m,
            length_m / 1000.0,
            length_m / total_length_m if total_length_m else 0.0,
        ])
    return rows


def gerar_planilha_grafo(city_id: str) -> dict:
    ensure_city_dirs(city_id)

    graph_path = f"data/graphs/{city_id}_drive_clean.graphml"
    metrics_dir = f"outputs/{city_id}/metrics"
    logs_dir = f"outputs/{city_id}/logs"

    G_dir = load_graphml(graph_path)
    edges = list(G_dir.edges(data=True))
    nodes = list(G_dir.nodes(data=True))

    total_edges = len(edges)
    total_nodes = len(nodes)
    total_length_m = sum(_length_m(data) for _, _, data in edges)
    names = _unique_names(edges)

    Gu = simple_undirected_min_length_graph(G_dir)
    components = list(nx.connected_components(Gu))
    components_count = len(components)
    largest_component_nodes = max((len(c) for c in components), default=0)
    used_largest_component = components_count > 1
    Gc = Gu.subgraph(max(components, key=len)).copy() if components else Gu

    degrees = [degree for _, degree in Gc.degree()]
    degree_counter = Counter(degrees)

    highway_counter: dict[str, dict[str, float]] = defaultdict(lambda: {"edges": 0, "length_m": 0.0})
    surface_counter: dict[str, dict[str, float]] = defaultdict(lambda: {"edges": 0, "length_m": 0.0})
    maxspeed_counter: dict[str, dict[str, float]] = defaultdict(lambda: {"edges": 0, "length_m": 0.0})
    lanes_counter: dict[str, dict[str, float]] = defaultdict(lambda: {"edges": 0, "length_m": 0.0})
    oneway_counter: dict[str, dict[str, float]] = defaultdict(lambda: {"edges": 0, "length_m": 0.0})

    maxspeed_values = []
    lanes_values = []
    missing = Counter()

    for _, _, data in edges:
        length_m = _length_m(data)

        for attr in ["name", "surface", "maxspeed", "lanes", "highway", "oneway", "bridge", "tunnel"]:
            if not _values(data.get(attr)):
                missing[attr] += 1

        for highway in _values(data.get("highway")) or ["desconhecido"]:
            key = str(highway).strip() or "desconhecido"
            highway_counter[key]["edges"] += 1
            highway_counter[key]["length_m"] += length_m

        surface_key = _surface_category(data.get("surface"))
        surface_counter[surface_key]["edges"] += 1
        surface_counter[surface_key]["length_m"] += length_m

        maxspeed_key = _first_value(data.get("maxspeed"))
        maxspeed_counter[maxspeed_key]["edges"] += 1
        maxspeed_counter[maxspeed_key]["length_m"] += length_m
        maxspeed_values.extend(_parse_float_values(data.get("maxspeed")))

        lanes_key = _first_value(data.get("lanes"))
        lanes_counter[lanes_key]["edges"] += 1
        lanes_counter[lanes_key]["length_m"] += length_m
        lanes_values.extend(_parse_float_values(data.get("lanes")))

        oneway_key = _as_bool_label(data.get("oneway"))
        oneway_counter[oneway_key]["edges"] += 1
        oneway_counter[oneway_key]["length_m"] += length_m

    summary_rows: list[list[Any]] = []
    _add_metric(summary_rows, "identificacao", "city_id", city_id, "texto", "Identificador do dataset analisado.")
    _add_metric(summary_rows, "identificacao", "graph_path", graph_path, "arquivo", "Arquivo GraphML limpo usado como entrada.")
    _add_metric(summary_rows, "tamanho", "nodes", total_nodes, "nos", "Quantidade de intersecoes/pontos do grafo direcionado.")
    _add_metric(summary_rows, "tamanho", "edges", total_edges, "arestas", "Quantidade de segmentos direcionados de via.")
    _add_metric(summary_rows, "tamanho", "total_length_km", total_length_m / 1000.0, "km", "Soma dos comprimentos dos segmentos direcionados.")
    _add_metric(summary_rows, "tamanho", "named_streets_unique", len(names), "nomes", "Quantidade de nomes distintos de vias presentes no atributo OSM name.")
    _add_metric(summary_rows, "conectividade", "weak_components_undirected", components_count, "componentes", "Quantidade de componentes conectadas ao ignorar direcao.")
    _add_metric(summary_rows, "conectividade", "largest_component_nodes", largest_component_nodes, "nos", "Quantidade de nos na maior componente conectada.")
    _add_metric(summary_rows, "conectividade", "used_largest_component", "sim" if used_largest_component else "nao", "booleano", "Indica se havia mais de uma componente conectada.")
    _add_metric(summary_rows, "topologia", "degree_min", min(degrees) if degrees else math.nan, "grau", "Menor grau observado na maior componente.")
    _add_metric(summary_rows, "topologia", "degree_max", max(degrees) if degrees else math.nan, "grau", "Maior grau observado na maior componente.")
    _add_metric(summary_rows, "topologia", "degree_mean", statistics.mean(degrees) if degrees else math.nan, "grau", "Media do grau dos nos na maior componente.")
    _add_metric(summary_rows, "topologia", "degree_median", statistics.median(degrees) if degrees else math.nan, "grau", "Mediana do grau dos nos na maior componente.")
    _add_metric(summary_rows, "topologia", "density", nx.density(Gc) if Gc.number_of_nodes() else math.nan, "razao", "Densidade do grafo nao direcionado na maior componente.")
    _add_metric(summary_rows, "topologia", "transitivity", nx.transitivity(Gc) if Gc.number_of_nodes() else math.nan, "razao", "Coeficiente de transitividade global.")

    paved_edges = surface_counter["pavimentado"]["edges"]
    unpaved_edges = surface_counter["terra_sem_pavimento"]["edges"]
    unknown_surface_edges = surface_counter["desconhecido"]["edges"]
    other_surface_edges = surface_counter["outro_surface"]["edges"]
    paved_length = surface_counter["pavimentado"]["length_m"]
    unpaved_length = surface_counter["terra_sem_pavimento"]["length_m"]
    unknown_surface_length = surface_counter["desconhecido"]["length_m"]
    other_surface_length = surface_counter["outro_surface"]["length_m"]
    known_surface_edges = total_edges - unknown_surface_edges
    known_surface_length = total_length_m - unknown_surface_length
    known_paved_unpaved_edges = paved_edges + unpaved_edges
    known_paved_unpaved_length = paved_length + unpaved_length
    observed_paved_share_edges = paved_edges / known_paved_unpaved_edges if known_paved_unpaved_edges else 0.0
    observed_unpaved_share_edges = unpaved_edges / known_paved_unpaved_edges if known_paved_unpaved_edges else 0.0
    observed_paved_share_length = paved_length / known_paved_unpaved_length if known_paved_unpaved_length else 0.0
    observed_unpaved_share_length = unpaved_length / known_paved_unpaved_length if known_paved_unpaved_length else 0.0
    estimated_paved_edges = paved_edges + (unknown_surface_edges + other_surface_edges) * observed_paved_share_edges
    estimated_unpaved_edges = unpaved_edges + (unknown_surface_edges + other_surface_edges) * observed_unpaved_share_edges
    estimated_paved_length = paved_length + (unknown_surface_length + other_surface_length) * observed_paved_share_length
    estimated_unpaved_length = unpaved_length + (unknown_surface_length + other_surface_length) * observed_unpaved_share_length

    _add_metric(summary_rows, "superficie", "paved_edges", int(paved_edges), "arestas", "Segmentos com surface classificado como pavimentado/asfaltado.")
    _add_metric(summary_rows, "superficie", "paved_edges_pct", paved_edges / total_edges if total_edges else 0.0, "percentual", "Porcentagem de segmentos pavimentados entre as arestas.")
    _add_metric(summary_rows, "superficie", "paved_length_km", paved_length / 1000.0, "km", "Extensao pavimentada/asfaltada conhecida.")
    _add_metric(summary_rows, "superficie", "paved_length_pct", paved_length / total_length_m if total_length_m else 0.0, "percentual", "Porcentagem da extensao pavimentada/asfaltada conhecida.")
    _add_metric(summary_rows, "superficie", "unpaved_edges", int(unpaved_edges), "arestas", "Segmentos com surface classificado como terra/sem pavimento.")
    _add_metric(summary_rows, "superficie", "unpaved_edges_pct", unpaved_edges / total_edges if total_edges else 0.0, "percentual", "Porcentagem de segmentos de terra/sem pavimento entre as arestas.")
    _add_metric(summary_rows, "superficie", "unpaved_length_km", unpaved_length / 1000.0, "km", "Extensao de terra/sem pavimento conhecida.")
    _add_metric(summary_rows, "superficie", "unpaved_length_pct", unpaved_length / total_length_m if total_length_m else 0.0, "percentual", "Porcentagem da extensao de terra/sem pavimento conhecida.")
    _add_metric(summary_rows, "superficie", "unknown_surface_edges", int(unknown_surface_edges), "arestas", "Segmentos sem atributo OSM surface no grafo.")
    _add_metric(summary_rows, "superficie", "unknown_surface_edges_pct", unknown_surface_edges / total_edges if total_edges else 0.0, "percentual", "Porcentagem sem informacao de superficie.")
    _add_metric(summary_rows, "superficie", "surface_known_edges_pct", known_surface_edges / total_edges if total_edges else 0.0, "percentual", "Cobertura do atributo surface no OSM por arestas.")
    _add_metric(summary_rows, "superficie", "surface_known_length_pct", known_surface_length / total_length_m if total_length_m else 0.0, "percentual", "Cobertura do atributo surface no OSM por extensao.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_paved_edges", estimated_paved_edges, "arestas", "Estimativa: arestas pavimentadas assumindo que trechos sem surface seguem a mesma proporcao dos trechos com surface conhecido.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_paved_edges_pct", estimated_paved_edges / total_edges if total_edges else 0.0, "percentual", "Estimativa da porcentagem de arestas pavimentadas. Nao e dado observado direto; depende da cobertura de surface.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_paved_length_km", estimated_paved_length / 1000.0, "km", "Estimativa da extensao pavimentada em km usando a proporcao observada nos trechos conhecidos.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_paved_length_pct", estimated_paved_length / total_length_m if total_length_m else 0.0, "percentual", "Estimativa da porcentagem da extensao pavimentada. Nao e dado observado direto.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_unpaved_edges", estimated_unpaved_edges, "arestas", "Estimativa: arestas de terra/sem pavimento assumindo a mesma proporcao dos trechos conhecidos.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_unpaved_edges_pct", estimated_unpaved_edges / total_edges if total_edges else 0.0, "percentual", "Estimativa da porcentagem de arestas de terra/sem pavimento.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_unpaved_length_km", estimated_unpaved_length / 1000.0, "km", "Estimativa da extensao de terra/sem pavimento em km usando a proporcao observada nos trechos conhecidos.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_unpaved_length_pct", estimated_unpaved_length / total_length_m if total_length_m else 0.0, "percentual", "Estimativa da porcentagem da extensao de terra/sem pavimento.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_surface_method", "proporcao_surface_conhecido", "metodo", "Metodo: distribui trechos sem surface conforme a proporcao pavimentado/terra observada nos trechos com surface conhecido.")
    _add_metric(summary_rows, "superficie_estimativa", "estimated_surface_reliability_note", "menor_cobertura_maior_incerteza", "observacao", "Quanto menor a cobertura de surface no OSM, maior a incerteza da estimativa.")

    if maxspeed_values:
        _add_metric(summary_rows, "velocidade", "maxspeed_mean", statistics.mean(maxspeed_values), "km/h", "Media dos valores numericos de maxspeed presentes no OSM.")
        _add_metric(summary_rows, "velocidade", "maxspeed_median", statistics.median(maxspeed_values), "km/h", "Mediana dos valores numericos de maxspeed presentes no OSM.")
    _add_metric(summary_rows, "velocidade", "maxspeed_known_edges_pct", 1 - (missing["maxspeed"] / total_edges if total_edges else 0.0), "percentual", "Porcentagem de segmentos com maxspeed informado.")

    if lanes_values:
        _add_metric(summary_rows, "faixas", "lanes_mean", statistics.mean(lanes_values), "faixas", "Media dos valores numericos de lanes presentes no OSM.")
        _add_metric(summary_rows, "faixas", "lanes_median", statistics.median(lanes_values), "faixas", "Mediana dos valores numericos de lanes presentes no OSM.")
    _add_metric(summary_rows, "faixas", "lanes_known_edges_pct", 1 - (missing["lanes"] / total_edges if total_edges else 0.0), "percentual", "Porcentagem de segmentos com lanes informado.")

    for attr in ["name", "surface", "maxspeed", "lanes", "bridge", "tunnel"]:
        _add_metric(summary_rows, "completude_osm", f"missing_{attr}_edges", missing[attr], "arestas", f"Quantidade de segmentos sem o atributo OSM {attr}.")
        _add_metric(summary_rows, "completude_osm", f"missing_{attr}_edges_pct", missing[attr] / total_edges if total_edges else 0.0, "percentual", f"Porcentagem de segmentos sem o atributo OSM {attr}.")

    _add_existing_pipeline_outputs(summary_rows, city_id)

    summary_csv = f"{metrics_dir}/graph_inventory_summary.csv"
    _write_rows(summary_csv, ["grupo", "indicador", "valor", "unidade", "descricao"], summary_rows)

    breakdown_header = ["categoria", "arestas", "arestas_pct", "comprimento_m", "comprimento_km", "comprimento_pct"]
    highway_csv = f"{metrics_dir}/graph_inventory_highway.csv"
    surface_csv = f"{metrics_dir}/graph_inventory_surface.csv"
    maxspeed_csv = f"{metrics_dir}/graph_inventory_maxspeed.csv"
    lanes_csv = f"{metrics_dir}/graph_inventory_lanes.csv"
    oneway_csv = f"{metrics_dir}/graph_inventory_oneway.csv"
    degree_csv = f"{metrics_dir}/graph_inventory_degree.csv"

    _write_rows(highway_csv, breakdown_header, _counter_rows(highway_counter, total_edges, total_length_m))
    _write_rows(surface_csv, breakdown_header, _counter_rows(surface_counter, total_edges, total_length_m))
    _write_rows(maxspeed_csv, breakdown_header, _counter_rows(maxspeed_counter, total_edges, total_length_m))
    _write_rows(lanes_csv, breakdown_header, _counter_rows(lanes_counter, total_edges, total_length_m))
    _write_rows(oneway_csv, breakdown_header, _counter_rows(oneway_counter, total_edges, total_length_m))
    _write_rows(
        degree_csv,
        ["grau", "nos", "nos_pct", "descricao"],
        [[degree, count, count / len(degrees) if degrees else 0.0, "Distribuicao de graus da maior componente conectada."] for degree, count in sorted(degree_counter.items())],
    )

    report_txt = f"{logs_dir}/graph_inventory_report.txt"
    Path(report_txt).parent.mkdir(parents=True, exist_ok=True)
    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("=== Planilha de Inventario do Grafo ===\n\n")
        f.write(f"Entrada: {graph_path}\n")
        f.write(f"Resumo principal: {summary_csv}\n")
        f.write("Tabelas auxiliares:\n")
        for path in [highway_csv, surface_csv, maxspeed_csv, lanes_csv, oneway_csv, degree_csv]:
            f.write(f"- {path}\n")
        f.write("\nObservacao: porcentagens sao gravadas como razao de 0 a 1 para facilitar comparacoes.\n")
        f.write("Quando surface estiver ausente, asfalto/terra fica como desconhecido; novos downloads preservam surface.\n")

    return {
        "summary_csv": summary_csv,
        "highway_csv": highway_csv,
        "surface_csv": surface_csv,
        "maxspeed_csv": maxspeed_csv,
        "lanes_csv": lanes_csv,
        "oneway_csv": oneway_csv,
        "degree_csv": degree_csv,
        "report_txt": report_txt,
    }
