from __future__ import annotations

import ast
import csv
import json
from pathlib import Path
from typing import Any

import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml
from .metric_graphs import edge_length_m, simple_undirected_min_length_graph


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


def _way_ids_from_edge(data: dict[str, Any]) -> set[str]:
    ids = set()
    for value in _values(data.get("osmid")):
        text = str(value).strip()
        if text:
            ids.add(text)
    return ids


def _way_ids(G: nx.Graph) -> set[str]:
    ids = set()
    for _, _, data in G.edges(data=True):
        ids.update(_way_ids_from_edge(data))
    return ids


def _total_length_km(G: nx.Graph) -> float:
    return sum(edge_length_m(data, default=0.0) for _, _, data in G.edges(data=True)) / 1000.0


def _edge_attribute_coverage(G: nx.Graph, attribute: str) -> float:
    total = G.number_of_edges()
    if total == 0:
        return 0.0
    known = sum(1 for _, _, data in G.edges(data=True) if _values(data.get(attribute)))
    return known / total


def _filter_edges_by_way_ids(G: nx.Graph, allowed_ids: set[str]) -> nx.MultiDiGraph:
    H = nx.MultiDiGraph()
    H.add_nodes_from(G.nodes(data=True))
    for u, v, key, data in G.edges(keys=True, data=True):
        if _way_ids_from_edge(data) & allowed_ids:
            H.add_edge(u, v, key=key, **data)
    isolated = [node for node, degree in H.degree() if degree == 0]
    H.remove_nodes_from(isolated)
    return H


def _largest_component_fraction(G: nx.Graph) -> float:
    if G.number_of_nodes() == 0:
        return 0.0
    Gu = simple_undirected_min_length_graph(G)
    if Gu.number_of_nodes() == 0:
        return 0.0
    largest = max((len(component) for component in nx.connected_components(Gu)), default=0)
    return largest / Gu.number_of_nodes()


def _read_metadata(dataset: str) -> dict[str, Any]:
    path = Path(f"data/metadata/{dataset}_drive_raw.json")
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _dataset_row(dataset: str, G: nx.MultiDiGraph, reference_way_ids: set[str]) -> dict[str, Any]:
    ids = _way_ids(G)
    common = ids & reference_way_ids
    meta = _read_metadata(dataset)
    total_length = _total_length_km(G)
    status, reason = _historical_status(
        reference_coverage=(len(common) / len(reference_way_ids)) if reference_way_ids else 0.0,
        mapped_way_ratio=(len(common) / len(ids)) if ids else 0.0,
        dropped=meta.get("dropped_incomplete_historical_ways", 0) or 0,
        is_reference=not meta.get("historical_date"),
    )
    return {
        "dataset": dataset,
        "historical_date": meta.get("historical_date") or "OSM_atual",
        "nodes": G.number_of_nodes(),
        "edges": G.number_of_edges(),
        "total_length_km": total_length,
        "unique_osm_way_ids": len(ids),
        "common_way_ids_with_reference": len(common),
        "reference_way_coverage": (len(common) / len(reference_way_ids)) if reference_way_ids else 0.0,
        "dataset_way_shared_ratio": (len(common) / len(ids)) if ids else 0.0,
        "surface_known_edges_pct": _edge_attribute_coverage(G, "surface"),
        "maxspeed_known_edges_pct": _edge_attribute_coverage(G, "maxspeed"),
        "dropped_incomplete_historical_ways": meta.get("dropped_incomplete_historical_ways", 0),
        "historical_interpretation_status": status,
        "status_reason": reason,
    }


def _historical_status(reference_coverage: float, mapped_way_ratio: float, dropped: int, is_reference: bool) -> tuple[str, str]:
    if is_reference:
        return "referencia", "dataset usado como referência atual"
    if reference_coverage < 0.40:
        return "nao_confiavel", "cobertura muito baixa das vias atuais; diferença provavelmente dominada por evolução do mapeamento OSM"
    if reference_coverage < 0.70:
        return "exploratorio", "cobertura parcial; interpretar tendências históricas com forte cautela"
    if mapped_way_ratio < 0.70:
        return "exploratorio", "muitas vias históricas não aparecem na referência por ID; pode haver edição/split de OSM ways"
    if dropped:
        return "exploratorio", "download histórico descartou ways incompletas"
    return "comparavel_com_cautela", "cobertura suficiente para análise histórica descritiva, não causal"


def auditar_qualidade_historica(reference: str, datasets: list[str], output_dir: str = "outputs/comparisons") -> dict:
    """Audita se uma comparação temporal OSM parece refletir cidade ou cobertura de mapeamento."""
    all_datasets = [reference, *[dataset for dataset in datasets if dataset != reference]]
    for dataset in all_datasets:
        ensure_city_dirs(dataset)

    graphs = {
        dataset: load_graphml(f"data/graphs/{dataset}_drive_clean.graphml")
        for dataset in all_datasets
    }
    reference_ids = _way_ids(graphs[reference])
    rows = [_dataset_row(dataset, graphs[dataset], reference_ids) for dataset in all_datasets]

    core_rows = []
    for dataset in all_datasets:
        common_ids = _way_ids(graphs[dataset]) & reference_ids
        dataset_core = _filter_edges_by_way_ids(graphs[dataset], common_ids)
        reference_core = _filter_edges_by_way_ids(graphs[reference], common_ids)
        core_rows.append({
            "dataset": dataset,
            "historical_date": _read_metadata(dataset).get("historical_date") or "OSM_atual",
            "common_way_ids": len(common_ids),
            "dataset_core_nodes": dataset_core.number_of_nodes(),
            "dataset_core_edges": dataset_core.number_of_edges(),
            "dataset_core_length_km": _total_length_km(dataset_core),
            "dataset_core_lcc_fraction": _largest_component_fraction(dataset_core),
            "reference_core_nodes": reference_core.number_of_nodes(),
            "reference_core_edges": reference_core.number_of_edges(),
            "reference_core_length_km": _total_length_km(reference_core),
            "reference_core_lcc_fraction": _largest_component_fraction(reference_core),
        })

    output = Path(output_dir)
    output.mkdir(parents=True, exist_ok=True)
    safe = f"{reference}_historical_{len(all_datasets) - 1}_datasets"
    audit_csv = output / f"historical_quality_{safe}.csv"
    core_csv = output / f"historical_common_core_{safe}.csv"
    report_txt = output / f"historical_quality_{safe}.txt"
    _write_rows(audit_csv, rows)
    _write_rows(core_csv, core_rows)
    _write_report(report_txt, reference, rows, core_csv)
    return {"audit_csv": str(audit_csv), "common_core_csv": str(core_csv), "report_txt": str(report_txt), "rows": rows}


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _write_report(path: Path, reference: str, rows: list[dict[str, Any]], core_csv: Path) -> None:
    with path.open("w", encoding="utf-8") as f:
        f.write("=== Auditoria de Qualidade Histórica OSM ===\n\n")
        f.write(f"Referência atual: {reference}\n")
        f.write(f"Núcleo comum por OSM way id: {core_csv}\n\n")
        f.write("Interpretação:\n")
        f.write("- nao_confiavel: a comparação bruta provavelmente mede evolução do mapeamento OSM.\n")
        f.write("- exploratorio: pode haver sinal urbano, mas a cobertura não sustenta conclusão forte.\n")
        f.write("- comparavel_com_cautela: cobertura suficiente para análise descritiva controlada.\n\n")
        for row in rows:
            f.write(
                f"{row['dataset']}: status={row['historical_interpretation_status']} | "
                f"cobertura_ref={float(row['reference_way_coverage']):.3f} | "
                f"vias={row['unique_osm_way_ids']} | motivo={row['status_reason']}\n"
            )
