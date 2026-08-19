from __future__ import annotations

import ast
import csv
import json
import math
import statistics
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any, Iterable

import networkx as nx

from .io_utils import dataset_graph_path, dataset_metadata_path, ensure_city_dirs, load_graphml
from .metric_graphs import collapsed_physical_length_m, simple_undirected_min_length_graph


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
        _add_metric(summary_rows, "centralidade", "centrality_top_node_closeness_approx", best.get("closeness_approx", ""), "razao", "Closeness aproximada do principal no critico por betweenness.")
        _add_metric(summary_rows, "centralidade", "centrality_top_node_eigenvector", best.get("eigenvector", ""), "razao", "Eigenvector centrality do principal no critico por betweenness.")
    else:
        _add_metric(summary_rows, "centralidade", "centrality_available", "nao", "booleano", "Arquivo top_nodes.csv nao encontrado.")

    top_edges = _read_csv_dicts(f"{metrics_dir}/top_edges.csv")
    if top_edges:
        best = top_edges[0]
        _add_metric(summary_rows, "centralidade", "centrality_top_edges_count", len(top_edges), "linhas", "Quantidade de arestas listadas em top_edges.csv.")
        _add_metric(summary_rows, "centralidade", "centrality_top_edge_u", best.get("u", ""), "node_id", "No inicial da aresta com maior edge betweenness.")
        _add_metric(summary_rows, "centralidade", "centrality_top_edge_v", best.get("v", ""), "node_id", "No final da aresta com maior edge betweenness.")
        _add_metric(summary_rows, "centralidade", "centrality_top_edge_betweenness", best.get("edge_betweenness", ""), "razao", "Maior edge betweenness encontrada.")

    rankings = _read_csv_dicts(f"{metrics_dir}/centrality_rankings.csv")
    for row in rankings:
        if row.get("rank") == "1":
            metric = row.get("metric", "")
            _add_metric(summary_rows, "centralidade", f"centrality_top_{metric}_node", row.get("node", ""), "node_id", f"No com maior {metric}.")
            _add_metric(summary_rows, "centralidade", f"centrality_top_{metric}_value", row.get("value", ""), "razao", f"Maior valor de {metric}.")

    correlations = _read_csv_dicts(f"{metrics_dir}/functional_topology_correlations.csv")
    for row in correlations:
        attribute = row.get("attribute", "")
        metric = row.get("topology_metric", "")
        _add_metric(
            summary_rows,
            "topologia_funcao",
            f"functional_{attribute}_{metric}_spearman",
            row.get("spearman_correlation", ""),
            "correlacao",
            f"Correlação de Spearman entre {attribute} e {metric}; associação descritiva, não causal.",
        )

    validation = _read_csv_dicts(f"{metrics_dir}/approximation_validation.csv")
    if validation:
        _add_metric(summary_rows, "validacao", "approximation_validation_rows", len(validation), "linhas", "Quantidade de resultados da validação de aproximações.")
        sample_sizes = []
        for row in validation:
            try:
                sample_sizes.append(int(row.get("sample_size", "0")))
            except ValueError:
                pass
        largest_sample = max(sample_sizes, default=0)
        for metric in sorted({row.get("metric", "") for row in validation}):
            selected = [row for row in validation if row.get("metric") == metric and row.get("sample_size") == str(largest_sample)]
            for field in ["relative_error", "rank_spearman", "top20_overlap"]:
                values = []
                for row in selected:
                    try:
                        values.append(float(row.get(field, "")))
                    except ValueError:
                        pass
                if values:
                    _add_metric(
                        summary_rows,
                        "validacao",
                        f"validation_{metric}_{field}_mean_at_{largest_sample}",
                        sum(values) / len(values),
                        "razao",
                        f"Média de {field} para {metric} com amostra {largest_sample}.",
                    )

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
        for metric in [
            "removed_edges",
            "removed_fraction",
            "lcc_size",
            "lcc_fraction",
            "num_components",
            "efficiency_approx",
            "efficiency_topological_retained",
            "efficiency_length_retained",
        ]:
            _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_initial_{metric}", first.get(metric, ""), "valor", f"Valor inicial de {metric} na curva de resiliencia {strategy}.")
            _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_final_{metric}", last.get(metric, ""), "valor", f"Valor final de {metric} na curva de resiliencia {strategy}.")

        try:
            initial_lcc = float(first.get("lcc_fraction", "nan"))
            final_lcc = float(last.get("lcc_fraction", "nan"))
            _add_metric(summary_rows, "resiliencia", f"resilience_{strategy}_lcc_fraction_drop", initial_lcc - final_lcc, "pontos_percentuais", f"Queda da fracao da maior componente na curva {strategy}.")
        except ValueError:
            pass

    for prefix, group, label in [
        ("resilience", "resiliencia_aleatoria_agregada", "arestas"),
        ("node_resilience", "resiliencia_vertices_aleatoria_agregada", "vértices"),
    ]:
        aggregate = _read_csv_dicts(f"{metrics_dir}/{prefix}_random_aggregate.csv")
        if not aggregate:
            _add_metric(
                summary_rows,
                group,
                f"{prefix}_random_aggregate_available",
                "nao",
                "booleano",
                f"Arquivo {prefix}_random_aggregate.csv nao encontrado.",
            )
            continue
        last = aggregate[-1]
        _add_metric(summary_rows, group, f"{prefix}_random_aggregate_runs", last.get("runs", ""), "execucoes", f"Quantidade de execuções aleatórias agregadas por {label}.")
        for metric in [
            "lcc_fraction",
            "efficiency_topological_retained",
            "efficiency_length_retained",
        ]:
            for stat in ["mean", "std", "min", "max"]:
                key = f"{metric}_{stat}"
                _add_metric(
                    summary_rows,
                    group,
                    f"{prefix}_random_final_{key}",
                    last.get(key, ""),
                    "valor",
                    f"Estatística final {stat} de {metric} nas execuções aleatórias por {label}.",
                )

    for strategy in ["targeted", "targeted_adaptive", "random"]:
        resilience = _read_csv_dicts(f"{metrics_dir}/node_resilience_curve_{strategy}.csv")
        if not resilience:
            _add_metric(summary_rows, "resiliencia_vertices", f"node_resilience_{strategy}_available", "nao", "booleano", f"Arquivo node_resilience_curve_{strategy}.csv nao encontrado.")
            continue

        first = resilience[0]
        last = resilience[-1]
        _add_metric(summary_rows, "resiliencia_vertices", f"node_resilience_{strategy}_points", len(resilience), "pontos", f"Quantidade de pontos da curva de remoção de vértices {strategy}.")
        for metric in [
            "removed_nodes",
            "removed_fraction",
            "remaining_nodes_fraction",
            "lcc_size",
            "lcc_fraction",
            "lcc_remaining_fraction",
            "num_components",
            "efficiency_topological_retained",
            "efficiency_length_retained",
        ]:
            _add_metric(summary_rows, "resiliencia_vertices", f"node_resilience_{strategy}_initial_{metric}", first.get(metric, ""), "valor", f"Valor inicial de {metric} na remoção de vértices {strategy}.")
            _add_metric(summary_rows, "resiliencia_vertices", f"node_resilience_{strategy}_final_{metric}", last.get(metric, ""), "valor", f"Valor final de {metric} na remoção de vértices {strategy}.")
        try:
            initial_lcc = float(first.get("lcc_fraction", "nan"))
            final_lcc = float(last.get("lcc_fraction", "nan"))
            _add_metric(summary_rows, "resiliencia_vertices", f"node_resilience_{strategy}_lcc_fraction_drop", initial_lcc - final_lcc, "pontos_percentuais", f"Queda da LCC na remoção de vértices {strategy}.")
        except ValueError:
            pass

    robustness_summary = _read_csv_dicts(f"{metrics_dir}/robustness_summary.csv")
    if robustness_summary:
        _add_metric(
            summary_rows,
            "sintese_robustez",
            "robustness_summary_rows",
            len(robustness_summary),
            "linhas",
            "Quantidade de respostas sintetizadas por modalidade, estratégia e métrica.",
        )
        for row in robustness_summary:
            modality = row.get("modality", "")
            strategy = row.get("strategy", "")
            metric = row.get("metric", "")
            if not modality or not strategy or not metric:
                continue
            prefix = f"robustness_{modality}_{strategy}_{metric}"
            _add_metric(
                summary_rows,
                "sintese_robustez",
                f"{prefix}_auc_normalized_mean",
                row.get("auc_normalized_mean", ""),
                "razao",
                "AUC normalizada da resposta retida; valores maiores indicam maior robustez no intervalo comum.",
            )
            _add_metric(
                summary_rows,
                "sintese_robustez",
                f"{prefix}_analysis_max_fraction",
                row.get("analysis_max_fraction", ""),
                "fracao",
                "Maior fração removida comum usada na integração da curva.",
            )
            _add_metric(
                summary_rows,
                "sintese_robustez",
                f"{prefix}_repetitions",
                row.get("repetitions", ""),
                "execucoes",
                "Quantidade de curvas usadas para estimar a AUC e sua dispersão.",
            )
    else:
        _add_metric(
            summary_rows,
            "sintese_robustez",
            "robustness_summary_available",
            "nao",
            "booleano",
            "Arquivo robustness_summary.csv nao encontrado.",
        )

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
            f"Quantidade de comunidades com robustez estrutural interna calculada na estratégia {strategy}.",
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

    vulnerability_nodes = _read_csv_dicts(f"{metrics_dir}/vulnerability_nodes.csv")
    if vulnerability_nodes:
        top = vulnerability_nodes[0]
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_nodes_count", len(vulnerability_nodes), "nos", "Quantidade de nós ranqueados pelo índice composto de vulnerabilidade.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_top_node", top.get("node", ""), "node_id", "Nó com maior índice composto de vulnerabilidade.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_top_node_score", top.get("vulnerability_score", ""), "razao", "Maior score composto de vulnerabilidade entre nós.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_top_node_articulation", top.get("articulation", ""), "booleano", "Indica se o nó mais vulnerável é ponto de articulação.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_articulation_nodes", sum(1 for row in vulnerability_nodes if row.get("articulation") == "1.0"), "nos", "Quantidade de nós classificados como pontos de articulação.")
    else:
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_nodes_available", "nao", "booleano", "Arquivo vulnerability_nodes.csv nao encontrado.")

    vulnerability_edges = _read_csv_dicts(f"{metrics_dir}/vulnerability_edges.csv")
    if vulnerability_edges:
        top = vulnerability_edges[0]
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_edges_count", len(vulnerability_edges), "arestas", "Quantidade de arestas ranqueadas pelo índice composto de vulnerabilidade.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_top_edge_u", top.get("u", ""), "node_id", "Nó inicial da aresta com maior vulnerabilidade composta.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_top_edge_v", top.get("v", ""), "node_id", "Nó final da aresta com maior vulnerabilidade composta.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_top_edge_score", top.get("vulnerability_score", ""), "razao", "Maior score composto de vulnerabilidade entre arestas.")
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_bridge_edges", sum(1 for row in vulnerability_edges if row.get("bridge") == "1.0"), "arestas", "Quantidade de arestas classificadas como pontes estruturais.")
    else:
        _add_metric(summary_rows, "vulnerabilidade", "vulnerability_edges_available", "nao", "booleano", "Arquivo vulnerability_edges.csv nao encontrado.")

    structural_articulations = _read_csv_dicts(f"{metrics_dir}/structural_articulations.csv")
    if structural_articulations:
        top = structural_articulations[0]
        _add_metric(summary_rows, "gargalos_estruturais", "structural_articulation_nodes", len(structural_articulations), "nos", "Quantidade de nós de articulação cuja remoção aumenta a fragmentação da rede.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_articulation_node", top.get("node", ""), "node_id", "Nó de articulação com maior impacto de fragmentação.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_articulation_detached_nodes", top.get("detached_nodes_after_removal", ""), "nos", "Quantidade de nós destacados da maior componente pela remoção do principal nó de articulação.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_articulation_detached_fraction", top.get("detached_fraction_after_removal", ""), "percentual", "Fração de nós destacados pela remoção do principal nó de articulação.")
    else:
        _add_metric(summary_rows, "gargalos_estruturais", "structural_articulations_available", "nao", "booleano", "Arquivo structural_articulations.csv nao encontrado.")

    structural_bridges = _read_csv_dicts(f"{metrics_dir}/structural_bridges.csv")
    if structural_bridges:
        top = structural_bridges[0]
        _add_metric(summary_rows, "gargalos_estruturais", "structural_bridge_edges", len(structural_bridges), "arestas", "Quantidade de pontes estruturais cuja remoção aumenta a fragmentação da rede.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_bridge_u", top.get("u", ""), "node_id", "Nó inicial da ponte estrutural com maior impacto.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_bridge_v", top.get("v", ""), "node_id", "Nó final da ponte estrutural com maior impacto.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_bridge_detached_nodes", top.get("detached_nodes_after_removal", ""), "nos", "Quantidade de nós destacados da maior componente pela remoção da principal ponte estrutural.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_bridge_detached_fraction", top.get("detached_fraction_after_removal", ""), "percentual", "Fração de nós destacados pela remoção da principal ponte estrutural.")
    else:
        _add_metric(summary_rows, "gargalos_estruturais", "structural_bridges_available", "nao", "booleano", "Arquivo structural_bridges.csv nao encontrado.")

    structural_bottlenecks = _read_csv_dicts(f"{metrics_dir}/structural_bottlenecks.csv")
    if structural_bottlenecks:
        top = structural_bottlenecks[0]
        _add_metric(summary_rows, "gargalos_estruturais", "structural_bottleneck_elements", len(structural_bottlenecks), "elementos", "Quantidade total de gargalos estruturais no ranking combinado.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_bottleneck_type", top.get("type", ""), "categoria", "Tipo do gargalo estrutural de maior impacto.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_bottleneck_score", top.get("bottleneck_score", ""), "razao", "Score composto do gargalo estrutural de maior impacto.")
        _add_metric(summary_rows, "gargalos_estruturais", "structural_top_bottleneck_detached_nodes", top.get("detached_nodes_after_removal", ""), "nos", "Quantidade de nós destacados pelo gargalo estrutural de maior impacto.")
    else:
        _add_metric(summary_rows, "gargalos_estruturais", "structural_bottlenecks_available", "nao", "booleano", "Arquivo structural_bottlenecks.csv nao encontrado.")

    route_redundancy = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/route_redundancy_summary.csv")}
    if route_redundancy:
        _add_metric(summary_rows, "redundancia_rotas", "route_redundancy_sampled_pairs", route_redundancy.get("sampled_pairs", ""), "pares_od", "Quantidade de pares origem-destino analisados na redundância de rotas.")
        _add_metric(summary_rows, "redundancia_rotas", "route_redundancy_alternative_rate", route_redundancy.get("alternative_rate", ""), "percentual", "Fração dos pares que mantêm alguma rota alternativa após bloqueio da melhor rota.")
        _add_metric(summary_rows, "redundancia_rotas", "route_redundancy_reasonable_rate", route_redundancy.get("reasonable_alternative_rate", ""), "percentual", "Fração dos pares com alternativa razoável dentro do limiar configurado.")
        _add_metric(summary_rows, "redundancia_rotas", "route_redundancy_disconnected_rate", route_redundancy.get("disconnected_after_block_rate", ""), "percentual", "Fração dos pares que ficam sem rota após bloqueio da melhor rota.")
        _add_metric(summary_rows, "redundancia_rotas", "route_redundancy_alternative_ratio_mean", route_redundancy.get("alternative_ratio_mean", ""), "razao", "Razão média entre rota alternativa e melhor rota para pares com alternativa.")
        _add_metric(summary_rows, "redundancia_rotas", "route_redundancy_detour_distance_m_mean", route_redundancy.get("detour_distance_m_mean", ""), "metros", "Acréscimo médio de distância quando existe rota alternativa.")
    else:
        _add_metric(summary_rows, "redundancia_rotas", "route_redundancy_available", "nao", "booleano", "Arquivo route_redundancy_summary.csv nao encontrado.")

    spatial = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/spatial_multiscale_summary.csv")}
    if spatial:
        _add_metric(summary_rows, "multiescala_espacial", "spatial_cell_size_m", spatial.get("cell_size_m", ""), "metros", "Tamanho da célula usada na grade espacial.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_populated_cells", spatial.get("populated_cells", ""), "celulas", "Quantidade de células espaciais com pelo menos um nó.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_mean_nodes_per_cell", spatial.get("mean_nodes_per_cell", ""), "nos", "Média de nós por célula povoada.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_mean_degree_by_cell", spatial.get("mean_degree_by_cell", ""), "grau", "Média do grau médio local entre células.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_mean_vulnerability_by_cell", spatial.get("mean_vulnerability_by_cell", ""), "razao", "Média da vulnerabilidade média local entre células.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_mean_route_redundancy_reasonable_rate", spatial.get("mean_route_redundancy_reasonable_rate", ""), "percentual", "Média da taxa local de alternativas razoáveis nas células com pares OD.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_mean_route_redundancy_disconnected_rate", spatial.get("mean_route_redundancy_disconnected_rate", ""), "percentual", "Média da taxa local de desconexão após bloqueio nas células com pares OD.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_top_vulnerability_cell", spatial.get("top_vulnerability_cell", ""), "cell_id", "Célula com maior vulnerabilidade máxima.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_top_vulnerability_value", spatial.get("top_vulnerability_value", ""), "razao", "Maior vulnerabilidade observada em uma célula.")
        _add_metric(summary_rows, "multiescala_espacial", "spatial_lowest_redundancy_cell", spatial.get("lowest_redundancy_cell", ""), "cell_id", "Célula com maior taxa local de desconexão entre pares OD amostrados.")
    else:
        _add_metric(summary_rows, "multiescala_espacial", "spatial_multiscale_available", "nao", "booleano", "Arquivo spatial_multiscale_summary.csv nao encontrado.")

    spatial_robustness = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/spatial_robustness_summary.csv")}
    if spatial_robustness:
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_tested_cells", spatial_robustness.get("tested_cells", ""), "celulas", "Quantidade de células com bloqueio espacial simulado.")
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_mean_removed_edges", spatial_robustness.get("mean_removed_edges", ""), "arestas", "Média de arestas removidas por bloqueio regional.")
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_mean_lcc_fraction_drop", spatial_robustness.get("mean_lcc_fraction_drop", ""), "percentual", "Queda média da maior componente após bloqueios regionais.")
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_max_lcc_fraction_drop", spatial_robustness.get("max_lcc_fraction_drop", ""), "percentual", "Maior queda da maior componente causada por uma célula.")
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_top_lcc_impact_cell", spatial_robustness.get("top_lcc_impact_cell", ""), "cell_id", "Célula cujo bloqueio causa maior queda da maior componente.")
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_mean_efficiency_retained", spatial_robustness.get("mean_efficiency_topological_retained", ""), "razao", "Eficiência topológica média retida após bloqueios regionais.")
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_min_efficiency_retained", spatial_robustness.get("min_efficiency_topological_retained", ""), "razao", "Menor eficiência topológica retida após um bloqueio regional.")
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_max_components_increase", spatial_robustness.get("max_components_increase", ""), "componentes", "Maior aumento no número de componentes após um bloqueio regional.")
    else:
        _add_metric(summary_rows, "robustez_espacial", "spatial_robustness_available", "nao", "booleano", "Arquivo spatial_robustness_summary.csv nao encontrado.")

    road_hierarchy = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/road_hierarchy_summary.csv")}
    if road_hierarchy:
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_classes", road_hierarchy.get("road_classes", ""), "classes", "Quantidade de classes highway observadas.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_arterial_edge_fraction", road_hierarchy.get("arterial_edge_fraction", ""), "percentual", "Fração de arestas nas classes motorway, trunk, primary e secondary.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_arterial_length_fraction", road_hierarchy.get("arterial_length_fraction", ""), "percentual", "Fração da extensão viária nas classes arteriais.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_local_edge_fraction", road_hierarchy.get("local_edge_fraction", ""), "percentual", "Fração de arestas nas classes residencial, living_street e service.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_top_lcc_dependency_class", road_hierarchy.get("top_lcc_dependency_class", ""), "classe", "Classe highway cuja remoção mais reduz a maior componente.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_top_lcc_dependency_drop", road_hierarchy.get("top_lcc_dependency_drop", ""), "percentual", "Maior queda da maior componente causada pela remoção de uma classe highway.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_top_efficiency_dependency_class", road_hierarchy.get("top_efficiency_dependency_class", ""), "classe", "Classe highway cuja remoção mais reduz a eficiência topológica.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_top_efficiency_retained", road_hierarchy.get("top_efficiency_retained", ""), "razao", "Eficiência topológica retida após remoção da classe mais crítica por eficiência.")
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_top_centrality_class", road_hierarchy.get("top_centrality_class", ""), "classe", "Classe highway com maior edge betweenness observado no ranking de arestas críticas.")
    else:
        _add_metric(summary_rows, "hierarquia_viaria", "road_hierarchy_available", "nao", "booleano", "Arquivo road_hierarchy_summary.csv nao encontrado.")

    urban_morphology = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/urban_morphology_summary.csv")}
    if urban_morphology:
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_cell_size_m", urban_morphology.get("cell_size_m", ""), "metros", "Tamanho da célula usada na análise morfológica.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_populated_cells", urban_morphology.get("populated_cells", ""), "celulas", "Quantidade de células com pelo menos um nó viário.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_classified_cells", urban_morphology.get("classified_cells", ""), "celulas", "Quantidade de células com elementos suficientes para classificação morfológica.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_dominant_class", urban_morphology.get("dominant_morphology_class", ""), "classe", "Classe morfológica mais frequente na cidade.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_dominant_fraction", urban_morphology.get("dominant_morphology_fraction", ""), "percentual", "Fração de células classificadas ocupada pela classe morfológica dominante.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_insufficient_fraction", urban_morphology.get("insufficient_fraction", ""), "percentual", "Fração de células povoadas com poucos elementos para classificação morfológica.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_grid_fraction", urban_morphology.get("grid_fraction", ""), "percentual", "Fração das células classificadas com padrão gradeado.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_radial_linear_fraction", urban_morphology.get("radial_linear_fraction", ""), "percentual", "Fração das células classificadas com padrão radial ou linear.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_organic_fraction", urban_morphology.get("organic_fraction", ""), "percentual", "Fração das células classificadas com padrão orgânico.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_fragmented_fraction", urban_morphology.get("fragmented_fraction", ""), "percentual", "Fração das células classificadas como fragmentadas.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_mean_orientation_entropy", urban_morphology.get("mean_orientation_entropy", ""), "razao", "Entropia angular média das vias nas células classificadas.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_mean_orthogonal_share", urban_morphology.get("mean_orthogonal_orientation_share", ""), "razao", "Participação média dos eixos ortogonais dominantes.")
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_mean_segment_length_m", urban_morphology.get("mean_segment_length_m", ""), "metros", "Comprimento médio dos segmentos viários nas células classificadas.")
    else:
        _add_metric(summary_rows, "morfologia_urbana", "urban_morphology_available", "nao", "booleano", "Arquivo urban_morphology_summary.csv nao encontrado.")

    od_efficiency = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/od_efficiency_summary.csv")}
    if od_efficiency:
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_sampled_pairs", od_efficiency.get("sampled_pairs", ""), "pares_od", "Quantidade de pares origem-destino amostrados para eficiência estatística.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_route_distance_m_mean", od_efficiency.get("route_distance_m_mean", ""), "metros", "Distância média das rotas mínimas entre pares OD.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_route_distance_m_p90", od_efficiency.get("route_distance_m_p90", ""), "metros", "Percentil 90 da distância das rotas mínimas.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_hops_mean", od_efficiency.get("hops_mean", ""), "arestas", "Quantidade média de segmentos por rota OD.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_circuity_ratio_mean", od_efficiency.get("circuity_ratio_mean", ""), "razao", "Desvio médio: distância da rota dividida pela distância direta geográfica.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_circuity_ratio_p90", od_efficiency.get("circuity_ratio_p90", ""), "razao", "Percentil 90 do desvio das rotas.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_route_efficiency_mean", od_efficiency.get("route_efficiency_mean", ""), "razao", "Eficiência média: distância direta dividida pela distância da rota.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_accessibility_within_2km_rate", od_efficiency.get("accessibility_within_2km_rate", ""), "percentual", "Fração dos pares OD com rota até 2 km.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_accessibility_within_5km_rate", od_efficiency.get("accessibility_within_5km_rate", ""), "percentual", "Fração dos pares OD com rota até 5 km.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_accessibility_within_10km_rate", od_efficiency.get("accessibility_within_10km_rate", ""), "percentual", "Fração dos pares OD com rota até 10 km.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_low_detour_rate", od_efficiency.get("low_detour_rate_circuity_le_1_25", ""), "percentual", "Fração dos pares com desvio baixo, circuity até 1,25.")
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_high_detour_rate", od_efficiency.get("high_detour_rate_circuity_gt_1_75", ""), "percentual", "Fração dos pares com desvio alto, circuity acima de 1,75.")
    else:
        _add_metric(summary_rows, "eficiencia_od", "od_efficiency_available", "nao", "booleano", "Arquivo od_efficiency_summary.csv nao encontrado.")

    subcenters = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/subcenters_summary.csv")}
    if subcenters:
        _add_metric(summary_rows, "subcentros", "subcenters_count", subcenters.get("subcenters_count", ""), "candidatos", "Quantidade de células candidatas de alta centralidade topológica.")
        _add_metric(summary_rows, "subcentros", "subcenters_fraction", subcenters.get("subcenters_fraction", ""), "percentual", "Fração de células povoadas selecionadas como candidatas topológicas.")
        _add_metric(summary_rows, "subcentros", "subcenters_polycentricity_index", subcenters.get("polycentricity_index", ""), "razao", "Índice exploratório de dispersão dos scores entre células candidatas.")
        _add_metric(summary_rows, "subcentros", "subcenters_monocentricity_index", subcenters.get("monocentricity_index", ""), "razao", "Participação da principal célula candidata no score total.")
        _add_metric(summary_rows, "subcentros", "subcenters_score_entropy", subcenters.get("subcenter_score_entropy", ""), "razao", "Entropia normalizada dos scores das células candidatas.")
        _add_metric(summary_rows, "subcentros", "subcenters_top_score_share", subcenters.get("top_subcenter_score_share", ""), "percentual", "Participação da principal célula candidata no score total.")
        _add_metric(summary_rows, "subcentros", "subcenters_top_cell", subcenters.get("top_subcenter_cell", ""), "cell_id", "Célula com maior score de candidatura.")
        _add_metric(summary_rows, "subcentros", "subcenters_top_score", subcenters.get("top_subcenter_score", ""), "razao", "Maior score de candidatura observado.")
    else:
        _add_metric(summary_rows, "subcentros", "subcenters_available", "nao", "booleano", "Arquivo subcenters_summary.csv nao encontrado.")

    urban_barriers = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/urban_barriers_summary.csv")}
    if urban_barriers:
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_spatial_permeability_index", urban_barriers.get("spatial_permeability_index", ""), "razao", "Permeabilidade média entre células espaciais vizinhas.")
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_exposure_index", urban_barriers.get("barrier_exposure_index", ""), "razao", "Índice composto de exposição da rede a barreiras topológicas.")
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_low_permeability_cells", urban_barriers.get("low_permeability_cells_lt_0_50", ""), "celulas", "Quantidade de células com permeabilidade inferior a 0,50.")
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_missing_adjacent_connections", urban_barriers.get("missing_adjacent_connections", ""), "conexoes", "Quantidade de pares de células vizinhas sem conexão viária direta.")
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_critical_structural_connections", urban_barriers.get("critical_structural_connections", ""), "conexoes", "Conexões entre regiões que passam por pontes estruturais.")
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_top_low_permeability_cell", urban_barriers.get("top_low_permeability_cell", ""), "cell_id", "Célula com maior score de baixa permeabilidade.")
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_top_barrier_connection", urban_barriers.get("top_barrier_connection", ""), "cell_pair", "Par de células com maior score de barreira provável.")
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_top_barrier_score", urban_barriers.get("top_barrier_score", ""), "razao", "Maior score de barreira provável observado.")
    else:
        _add_metric(summary_rows, "barreiras_urbanas", "urban_barriers_available", "nao", "booleano", "Arquivo urban_barriers_summary.csv nao encontrado.")

    network_scale = {row.get("metric", ""): row.get("value", "") for row in _read_csv_dicts(f"{metrics_dir}/network_scale_profile_summary.csv")}
    if network_scale:
        _add_metric(summary_rows, "perfil_escala", "network_scale_tested_scales_count", network_scale.get("tested_scales_count", ""), "escalas", "Quantidade de escalas espaciais testadas.")
        _add_metric(summary_rows, "perfil_escala", "network_scale_multiscale_robustness_index", network_scale.get("multiscale_robustness_index", ""), "razao", "Estabilidade média das principais métricas locais entre escalas.")
        _add_metric(summary_rows, "perfil_escala", "network_scale_least_stable_metric", network_scale.get("least_stable_metric", ""), "indicador", "Métrica mais sensível à escala espacial.")
        _add_metric(summary_rows, "perfil_escala", "network_scale_least_stable_score", network_scale.get("least_stable_score", ""), "razao", "Score de estabilidade da métrica mais sensível à escala.")
        _add_metric(summary_rows, "perfil_escala", "network_scale_least_stable_cv", network_scale.get("least_stable_cv", ""), "razao", "Coeficiente de variação da métrica mais sensível à escala.")
        _add_metric(summary_rows, "perfil_escala", "network_scale_most_stable_metric", network_scale.get("most_stable_metric", ""), "indicador", "Métrica mais estável entre escalas.")
        _add_metric(summary_rows, "perfil_escala", "network_scale_most_stable_score", network_scale.get("most_stable_score", ""), "razao", "Score de estabilidade da métrica mais estável entre escalas.")
    else:
        _add_metric(summary_rows, "perfil_escala", "network_scale_available", "nao", "booleano", "Arquivo network_scale_profile_summary.csv nao encontrado.")


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

    graph_path = str(dataset_graph_path(city_id, "clean"))
    metrics_dir = f"outputs/{city_id}/metrics"
    logs_dir = f"outputs/{city_id}/logs"

    G_dir = load_graphml(graph_path)
    edges = list(G_dir.edges(data=True))
    nodes = list(G_dir.nodes(data=True))

    total_edges = len(edges)
    total_nodes = len(nodes)
    total_length_m = sum(_length_m(data) for _, _, data in edges)
    physical_length_m = collapsed_physical_length_m(G_dir)
    names = _unique_names(edges)
    metadata_path = dataset_metadata_path(city_id, "raw")
    metadata = json.loads(metadata_path.read_text(encoding="utf-8")) if metadata_path.exists() else {}
    area_km2 = metadata.get("clip", {}).get("area_km2")
    area_km2 = float(area_km2) if area_km2 not in (None, "") else None

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
    _add_metric(summary_rows, "identificacao", "resilience_term_scope", "robustez_estrutural_sob_remocao", "definicao", "Arquivos e indicadores com prefixo resilience medem degradação sob remoção; não incluem recuperação no tempo.")
    _add_metric(summary_rows, "identificacao", "graph_path", graph_path, "arquivo", "Arquivo GraphML limpo usado como entrada.")
    _add_metric(summary_rows, "tamanho", "nodes", total_nodes, "nos", "Quantidade de intersecoes/pontos do grafo direcionado.")
    _add_metric(summary_rows, "tamanho", "edges", total_edges, "arestas", "Quantidade de segmentos direcionados de via.")
    _add_metric(summary_rows, "tamanho", "total_length_km", total_length_m / 1000.0, "km", "Alias legado: soma dos comprimentos dos arcos direcionados; não representa extensão física única.")
    _add_metric(summary_rows, "tamanho", "directed_routing_length_km", total_length_m / 1000.0, "km", "Soma dos comprimentos dos arcos direcionados, adequada ao inventário de roteamento.")
    _add_metric(summary_rows, "tamanho", "physical_collapsed_length_km", physical_length_m / 1000.0, "km", "Proxy de extensão física: menor segmento válido por par de nós não ordenado, sem duplicar automaticamente arcos recíprocos.")
    _add_metric(summary_rows, "tamanho", "directed_to_physical_length_ratio", total_length_m / physical_length_m if physical_length_m else math.nan, "razao", "Razão entre extensão de roteamento dirigida e proxy de extensão física colapsada.")
    _add_metric(summary_rows, "tamanho", "named_streets_unique", len(names), "nomes", "Quantidade de nomes distintos de vias presentes no atributo OSM name.")
    if area_km2:
        _add_metric(summary_rows, "normalizacao", "clip_area_km2", area_km2, "km2", "Area do limite administrativo usada para normalizar a comparacao.")
        _add_metric(summary_rows, "normalizacao", "nodes_per_km2", total_nodes / area_km2, "nos/km2", "Quantidade de nos do grafo por km2 do recorte.")
        _add_metric(summary_rows, "normalizacao", "edges_per_km2", total_edges / area_km2, "arestas/km2", "Quantidade de arestas direcionadas por km2 do recorte.")
        _add_metric(summary_rows, "normalizacao", "total_length_km_per_km2", (total_length_m / 1000.0) / area_km2, "km/km2", "Alias legado: extensão de roteamento dirigida por km2 do recorte.")
        _add_metric(summary_rows, "normalizacao", "directed_routing_length_km_per_km2", (total_length_m / 1000.0) / area_km2, "km/km2", "Extensão de roteamento dirigida por km2 do recorte.")
        _add_metric(summary_rows, "normalizacao", "physical_collapsed_length_km_per_km2", (physical_length_m / 1000.0) / area_km2, "km/km2", "Proxy de extensão física colapsada por km2; preferir esta métrica em comparações de densidade viária.")
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
