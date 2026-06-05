from __future__ import annotations

import csv
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional
from importlib import metadata


def _read_kv_csv(path: str) -> Dict[str, str]:
    """Lê CSV no formato: metric,value."""
    p = Path(path)
    if not p.exists():
        return {}
    out: Dict[str, str] = {}
    with p.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        _ = next(reader, None)  # header
        for row in reader:
            if len(row) >= 2:
                out[row[0]] = row[1]
    return out


def _read_csv_rows(path: str, limit: int = 10) -> List[List[str]]:
    p = Path(path)
    if not p.exists():
        return []
    rows: List[List[str]] = []
    with p.open("r", encoding="utf-8") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header:
            rows.append(header)
        for i, row in enumerate(reader):
            rows.append(row)
            if i + 1 >= limit:
                break
    return rows


def _read_text(path: str) -> str:
    p = Path(path)
    if not p.exists():
        return ""
    return p.read_text(encoding="utf-8", errors="replace")


def _rename_header(rows: List[List[str]], mapping: Dict[str, str]) -> List[List[str]]:
    """Renomeia somente o cabeçalho (primeira linha) conforme um mapeamento."""
    if not rows:
        return rows
    header = rows[0]
    new_header = [mapping.get(col, col) for col in header]
    return [new_header] + rows[1:]


def _fmt_md_table(rows: List[List[str]]) -> str:
    if not rows:
        return "_(arquivo não encontrado)_"
    header = rows[0]
    body = rows[1:]
    md: List[str] = []
    md.append("| " + " | ".join(header) + " |")
    md.append("| " + " | ".join(["---"] * len(header)) + " |")
    for r in body:
        md.append("| " + " | ".join(r) + " |")
    return "\n".join(md)


def _list_files(root: str) -> List[str]:
    p = Path(root)
    if not p.exists():
        return []
    return sorted(str(x).replace("\\", "/") for x in p.rglob("*") if x.is_file())


def _package_version(package: str) -> str:
    try:
        return metadata.version(package)
    except metadata.PackageNotFoundError:
        return "nao_instalado"


def _git_value(args: list[str]) -> str:
    try:
        return subprocess.check_output(["git", *args], text=True, stderr=subprocess.DEVNULL).strip()
    except Exception:
        return "indisponivel"


def _write_experiment_manifest(city_id: str, outputs_root: str, files: list[str]) -> str:
    manifest_json = f"{outputs_root}/EXPERIMENT_MANIFEST_{city_id}.json"
    payload = {
        "city_id": city_id,
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
        "recommended_command": f"ic report --city {city_id}",
        "python": sys.version.replace("\n", " "),
        "packages": {
            "osmnx": _package_version("osmnx"),
            "networkx": _package_version("networkx"),
            "pandas": _package_version("pandas"),
            "numpy": _package_version("numpy"),
            "scipy": _package_version("scipy"),
            "matplotlib": _package_version("matplotlib"),
            "folium": _package_version("folium"),
        },
        "git": {
            "commit": _git_value(["rev-parse", "HEAD"]),
            "branch": _git_value(["branch", "--show-current"]),
            "dirty_files": _git_value(["status", "--short"]),
        },
        "inputs": {
            "graphml_clean": f"data/graphs/{city_id}_drive_clean.graphml",
            "metadata_raw": f"data/metadata/{city_id}_drive_raw.json",
        },
        "outputs": files,
    }
    Path(manifest_json).write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    return manifest_json


def _rel_to_outputs(path: str, outputs_root: str) -> str:
    """Converte um caminho absoluto/long para relativo a outputs/<city> quando possível."""
    p = Path(path)
    root = Path(outputs_root)
    try:
        return str(p.relative_to(root)).replace("\\", "/")
    except Exception:
        return str(p).replace("\\", "/")


def _last_row(csv_path: str) -> Optional[Dict[str, str]]:
    p = Path(csv_path)
    if not p.exists():
        return None
    with p.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        last = None
        for row in reader:
            last = row
        return last


def gerar_relatorio_final(city_id: str) -> dict:
    """E8: Consolida resultados de E1..E7 em um relatório Markdown + manifest de arquivos."""

    outputs_root = f"outputs/{city_id}"
    metrics_dir = f"{outputs_root}/metrics"
    logs_dir = f"{outputs_root}/logs"
    figs_dir = f"{outputs_root}/figures"
    maps_dir = f"{outputs_root}/maps"

    report_md = f"{outputs_root}/REPORT_{city_id}.md"
    manifest_txt = f"{outputs_root}/MANIFEST_{city_id}.txt"

    # --- Metadados do download (E1) ---
    meta_json_path = f"data/metadata/{city_id}_drive_raw.json"
    meta: Dict[str, object] = {}
    mp = Path(meta_json_path)
    if mp.exists():
        try:
            meta = json.loads(mp.read_text(encoding="utf-8"))
        except Exception:
            meta = {}

    # --- E3 ---
    structural_csv = f"{metrics_dir}/structural_metrics.csv"
    structural = _read_kv_csv(structural_csv)

    # --- E4 ---
    route_summary_csv = f"{metrics_dir}/rota_distancia_resumo.csv"
    route_map = f"{maps_dir}/rota_distancia.html"

    # --- E5 ---
    top_nodes_csv = f"{metrics_dir}/top_nodes.csv"
    centrality_rankings_csv = f"{metrics_dir}/centrality_rankings.csv"
    functional_correlations_csv = f"{metrics_dir}/functional_topology_correlations.csv"
    approximation_validation_csv = f"{metrics_dir}/approximation_validation.csv"
    centrality_report = f"{logs_dir}/centrality_report.txt"
    crit_map = f"{maps_dir}/pontos_criticos.html"

    # --- E6 ---
    comm_summary_csv = f"{metrics_dir}/community_summary.csv"
    comm_report = f"{logs_dir}/communities_report.txt"
    comm_map = f"{maps_dir}/comunidades.html"

    # --- E7 ---
    res_target_csv = f"{metrics_dir}/resilience_curve_targeted.csv"
    res_target_adaptive_csv = f"{metrics_dir}/resilience_curve_targeted_adaptive.csv"
    res_rand_csv = f"{metrics_dir}/resilience_curve_random.csv"
    node_res_target_csv = f"{metrics_dir}/node_resilience_curve_targeted.csv"
    node_res_target_adaptive_csv = f"{metrics_dir}/node_resilience_curve_targeted_adaptive.csv"
    node_res_rand_csv = f"{metrics_dir}/node_resilience_curve_random.csv"
    node_res_removed_target_csv = f"{metrics_dir}/node_resilience_removed_targeted.csv"
    comm_res_target_csv = f"{metrics_dir}/community_resilience_curve_targeted.csv"
    comm_res_target_adaptive_csv = f"{metrics_dir}/community_resilience_curve_targeted_adaptive.csv"
    comm_res_rand_csv = f"{metrics_dir}/community_resilience_curve_random.csv"
    comm_res_top_edges_csv = f"{metrics_dir}/community_resilience_top_edges.csv"
    res_target_plot = f"{figs_dir}/resilience_curve_targeted.png"
    res_target_adaptive_plot = f"{figs_dir}/resilience_curve_targeted_adaptive.png"
    res_rand_plot = f"{figs_dir}/resilience_curve_random.png"
    node_res_target_plot = f"{figs_dir}/node_resilience_curve_targeted.png"
    node_res_target_adaptive_plot = f"{figs_dir}/node_resilience_curve_targeted_adaptive.png"
    node_res_rand_plot = f"{figs_dir}/node_resilience_curve_random.png"
    comm_res_target_plot = f"{figs_dir}/community_resilience_curve_targeted.png"
    comm_res_target_adaptive_plot = f"{figs_dir}/community_resilience_curve_targeted_adaptive.png"
    comm_res_rand_plot = f"{figs_dir}/community_resilience_curve_random.png"
    intra_comm_summary_target = f"{metrics_dir}/intra_community_resilience_summary_targeted.csv"
    intra_comm_summary_target_adaptive = f"{metrics_dir}/intra_community_resilience_summary_targeted_adaptive.csv"
    intra_comm_summary_random = f"{metrics_dir}/intra_community_resilience_summary_random.csv"
    intra_comm_target_plot = f"{figs_dir}/intra_community_resilience_targeted.png"
    intra_comm_target_adaptive_plot = f"{figs_dir}/intra_community_resilience_targeted_adaptive.png"
    intra_comm_random_plot = f"{figs_dir}/intra_community_resilience_random.png"
    vulnerability_nodes_csv = f"{metrics_dir}/vulnerability_nodes.csv"
    vulnerability_edges_csv = f"{metrics_dir}/vulnerability_edges.csv"
    vulnerability_nodes_map = f"{maps_dir}/vulnerability_nodes.html"
    vulnerability_edges_map = f"{maps_dir}/vulnerability_edges.html"
    structural_articulations_csv = f"{metrics_dir}/structural_articulations.csv"
    structural_bridges_csv = f"{metrics_dir}/structural_bridges.csv"
    structural_bottlenecks_csv = f"{metrics_dir}/structural_bottlenecks.csv"
    structural_articulations_map = f"{maps_dir}/structural_articulations.html"
    structural_bridges_map = f"{maps_dir}/structural_bridges.html"
    structural_bottlenecks_map = f"{maps_dir}/structural_bottlenecks.html"
    route_redundancy_summary_csv = f"{metrics_dir}/route_redundancy_summary.csv"
    route_redundancy_pairs_csv = f"{metrics_dir}/route_redundancy_pairs.csv"
    route_redundancy_map = f"{maps_dir}/route_redundancy.html"
    spatial_multiscale_summary_csv = f"{metrics_dir}/spatial_multiscale_summary.csv"
    spatial_multiscale_cells_csv = f"{metrics_dir}/spatial_multiscale_cells.csv"
    spatial_multiscale_vulnerability_map = f"{maps_dir}/spatial_multiscale_vulnerability.html"
    spatial_multiscale_connectivity_map = f"{maps_dir}/spatial_multiscale_connectivity.html"
    spatial_multiscale_redundancy_map = f"{maps_dir}/spatial_multiscale_redundancy.html"
    spatial_robustness_summary_csv = f"{metrics_dir}/spatial_robustness_summary.csv"
    spatial_robustness_cells_csv = f"{metrics_dir}/spatial_robustness_cells.csv"
    spatial_robustness_lcc_map = f"{maps_dir}/spatial_robustness_lcc_drop.html"
    spatial_robustness_efficiency_map = f"{maps_dir}/spatial_robustness_efficiency_drop.html"
    spatial_robustness_fragmentation_map = f"{maps_dir}/spatial_robustness_fragmentation.html"
    road_hierarchy_summary_csv = f"{metrics_dir}/road_hierarchy_summary.csv"
    road_hierarchy_by_class_csv = f"{metrics_dir}/road_hierarchy_by_class.csv"
    road_hierarchy_map = f"{maps_dir}/road_hierarchy_impact.html"
    urban_morphology_summary_csv = f"{metrics_dir}/urban_morphology_summary.csv"
    urban_morphology_cells_csv = f"{metrics_dir}/urban_morphology_cells.csv"
    urban_morphology_class_map = f"{maps_dir}/urban_morphology_classes.html"
    urban_morphology_entropy_map = f"{maps_dir}/urban_morphology_orientation_entropy.html"
    urban_morphology_connectivity_map = f"{maps_dir}/urban_morphology_connectivity.html"
    od_efficiency_summary_csv = f"{metrics_dir}/od_efficiency_summary.csv"
    od_efficiency_pairs_csv = f"{metrics_dir}/od_efficiency_pairs.csv"
    od_efficiency_map = f"{maps_dir}/od_efficiency_routes.html"
    subcenters_summary_csv = f"{metrics_dir}/subcenters_summary.csv"
    subcenters_csv = f"{metrics_dir}/subcenters.csv"
    subcenters_cells_csv = f"{metrics_dir}/subcenters_cells.csv"
    subcenters_map = f"{maps_dir}/subcenters.html"
    urban_barriers_summary_csv = f"{metrics_dir}/urban_barriers_summary.csv"
    urban_barriers_cells_csv = f"{metrics_dir}/urban_barriers_cells.csv"
    urban_barriers_connections_csv = f"{metrics_dir}/urban_barriers_connections.csv"
    urban_barriers_permeability_map = f"{maps_dir}/urban_barriers_permeability.html"
    urban_barriers_connections_map = f"{maps_dir}/urban_barriers_connections.html"
    network_scale_summary_csv = f"{metrics_dir}/network_scale_profile_summary.csv"
    network_scale_scales_csv = f"{metrics_dir}/network_scale_profile_scales.csv"
    network_scale_stability_csv = f"{metrics_dir}/network_scale_profile_stability.csv"
    network_scale_cells_csv = f"{metrics_dir}/network_scale_profile_cells.csv"
    network_scale_metrics_plot = f"{figs_dir}/network_scale_profile_metrics.png"
    network_scale_stability_plot = f"{figs_dir}/network_scale_profile_stability.png"
    network_scale_map = f"{maps_dir}/network_scale_profile_low_permeability.html"

    # --- E3 figura ---
    degree_plot = f"{figs_dir}/degree_distribution_loglog.png"

    # Manifest
    Path(outputs_root).mkdir(parents=True, exist_ok=True)
    files = _list_files(outputs_root)
    Path(manifest_txt).write_text("\n".join(files) + "\n", encoding="utf-8")
    manifest_json = _write_experiment_manifest(city_id, outputs_root, files)

    # Bloco E3
    if structural:
        structural_block = "\n".join(
            [
                f"- **Grafo original direcionado:** {structural.get('directed_nodes_original', '—')} nós / {structural.get('directed_edges_original', '—')} arestas",
                f"- **Grafo analisado:** {structural.get('analysis_graph', '—')}",
                f"- **Nós (n):** {structural.get('nodes', '—')}",
                f"- **Arestas (m):** {structural.get('edges', '—')}",
                f"- **Grau médio:** {structural.get('degree_mean', '—')}",
                f"- **Transitividade:** {structural.get('transitivity', '—')}",
                f"- **Clustering (aprox):** {structural.get('avg_clustering_approx', '—')}",
                f"- **Assortatividade (grau):** {structural.get('assortativity_degree', '—')}",
                f"- **Caminho médio (aprox, hops):** {structural.get('avg_shortest_path_len_approx_hops', '—')}",
                f"- **Diâmetro (aprox, hops):** {structural.get('diameter_approx_hops', '—')}",
                f"- **Caminho médio (aprox, metros):** {structural.get('avg_shortest_path_len_approx_m', '—')}",
                f"- **Diâmetro (aprox, metros):** {structural.get('diameter_approx_m', '—')}",
            ]
        )
    else:
        structural_block = "_(E3 não encontrado: execute `ic structural --city campinas`)_"

    # Tabelas (prévia) — cabeçalhos em português
    top_nodes_rows = _read_csv_rows(top_nodes_csv, limit=10)
    top_nodes_rows = _rename_header(
        top_nodes_rows,
        {
            "node": "nó",
            "lat": "latitude",
            "lon": "longitude",
            "degree_centrality": "centralidade de grau",
            "betweenness": "centralidade de intermediação",
            "closeness_approx": "centralidade de proximidade aproximada",
            "eigenvector": "centralidade de autovetor",
        },
    )
    top_nodes_preview = _fmt_md_table(top_nodes_rows)
    centrality_rankings_preview = _fmt_md_table(_read_csv_rows(centrality_rankings_csv, limit=20))
    functional_correlations_preview = _fmt_md_table(_read_csv_rows(functional_correlations_csv, limit=20))
    approximation_validation_preview = _fmt_md_table(_read_csv_rows(approximation_validation_csv, limit=20))

    comm_rows = _read_csv_rows(comm_summary_csv, limit=10)
    comm_rows = _rename_header(
        comm_rows,
        {
            "community_id": "id da comunidade",
            "size": "tamanho",
        },
    )
    comm_summary_preview = _fmt_md_table(comm_rows)

    route_rows = _read_csv_rows(route_summary_csv, limit=5)
    route_rows = _rename_header(
        route_rows,
        {
            "city_id": "cidade",
            "orig_node": "nó de origem",
            "dest_node": "nó de destino",
            "distance_total_m": "distância total (m)",
            "num_nodes_in_route": "nº de nós na rota",
        },
    )
    route_preview = _fmt_md_table(route_rows)
    vulnerability_nodes_preview = _fmt_md_table(_read_csv_rows(vulnerability_nodes_csv, limit=10))
    vulnerability_edges_preview = _fmt_md_table(_read_csv_rows(vulnerability_edges_csv, limit=10))
    structural_articulations_preview = _fmt_md_table(_read_csv_rows(structural_articulations_csv, limit=10))
    structural_bridges_preview = _fmt_md_table(_read_csv_rows(structural_bridges_csv, limit=10))
    structural_bottlenecks_preview = _fmt_md_table(_read_csv_rows(structural_bottlenecks_csv, limit=10))
    route_redundancy_summary_preview = _fmt_md_table(_read_csv_rows(route_redundancy_summary_csv, limit=20))
    route_redundancy_pairs_preview = _fmt_md_table(_read_csv_rows(route_redundancy_pairs_csv, limit=10))
    spatial_multiscale_summary_preview = _fmt_md_table(_read_csv_rows(spatial_multiscale_summary_csv, limit=20))
    spatial_multiscale_cells_preview = _fmt_md_table(_read_csv_rows(spatial_multiscale_cells_csv, limit=10))
    spatial_robustness_summary_preview = _fmt_md_table(_read_csv_rows(spatial_robustness_summary_csv, limit=20))
    spatial_robustness_cells_preview = _fmt_md_table(_read_csv_rows(spatial_robustness_cells_csv, limit=10))
    road_hierarchy_summary_preview = _fmt_md_table(_read_csv_rows(road_hierarchy_summary_csv, limit=20))
    road_hierarchy_by_class_preview = _fmt_md_table(_read_csv_rows(road_hierarchy_by_class_csv, limit=12))
    urban_morphology_summary_preview = _fmt_md_table(_read_csv_rows(urban_morphology_summary_csv, limit=20))
    urban_morphology_cells_preview = _fmt_md_table(_read_csv_rows(urban_morphology_cells_csv, limit=10))
    od_efficiency_summary_preview = _fmt_md_table(_read_csv_rows(od_efficiency_summary_csv, limit=25))
    od_efficiency_pairs_preview = _fmt_md_table(_read_csv_rows(od_efficiency_pairs_csv, limit=10))
    subcenters_summary_preview = _fmt_md_table(_read_csv_rows(subcenters_summary_csv, limit=20))
    subcenters_preview = _fmt_md_table(_read_csv_rows(subcenters_csv, limit=10))
    subcenters_cells_preview = _fmt_md_table(_read_csv_rows(subcenters_cells_csv, limit=10))
    urban_barriers_summary_preview = _fmt_md_table(_read_csv_rows(urban_barriers_summary_csv, limit=20))
    urban_barriers_cells_preview = _fmt_md_table(_read_csv_rows(urban_barriers_cells_csv, limit=10))
    urban_barriers_connections_preview = _fmt_md_table(_read_csv_rows(urban_barriers_connections_csv, limit=10))
    network_scale_summary_preview = _fmt_md_table(_read_csv_rows(network_scale_summary_csv, limit=20))
    network_scale_scales_preview = _fmt_md_table(_read_csv_rows(network_scale_scales_csv, limit=10))
    network_scale_stability_preview = _fmt_md_table(_read_csv_rows(network_scale_stability_csv, limit=10))
    network_scale_cells_preview = _fmt_md_table(_read_csv_rows(network_scale_cells_csv, limit=10))

    # Trechos de logs
    centrality_text = _read_text(centrality_report).strip()
    comm_text = _read_text(comm_report).strip()

    # Resiliência: último ponto
    last_target = _last_row(res_target_csv)
    last_target_adaptive = _last_row(res_target_adaptive_csv)
    last_random = _last_row(res_rand_csv)
    last_node_target = _last_row(node_res_target_csv)
    last_node_target_adaptive = _last_row(node_res_target_adaptive_csv)
    last_node_random = _last_row(node_res_rand_csv)
    last_comm_target = _last_row(comm_res_target_csv)
    last_comm_target_adaptive = _last_row(comm_res_target_adaptive_csv)
    last_comm_random = _last_row(comm_res_rand_csv)

    res_block: List[str] = []
    if last_target:
        res_block.append("### Direcionada (remoção dirigida)\n")
        res_block.append(
            "- Último ponto: "
            f"fração de arestas removidas={last_target.get('removed_fraction')} | "
            f"fração da maior componente (LCC)={last_target.get('lcc_fraction')} | "
            f"nº de componentes={last_target.get('num_components')} | "
            f"eficiência topológica (aprox)={last_target.get('efficiency_topological_approx', last_target.get('efficiency_approx'))} | "
            f"eficiência topológica retida={last_target.get('efficiency_topological_retained', '—')} | "
            f"eficiência por distância retida={last_target.get('efficiency_length_retained', '—')}"
        )
        if Path(res_target_plot).exists():
            res_block.append(f"- Figura: `{_rel_to_outputs(res_target_plot, outputs_root)}`")
    else:
        res_block.append("### Direcionada\n_(não encontrado — execute `ic resilience --strategy targeted`)_")

    res_block.append("")

    if last_target_adaptive:
        res_block.append("### Direcionada adaptativa\n")
        res_block.append(
            "- Último ponto: "
            f"fração de arestas removidas={last_target_adaptive.get('removed_fraction')} | "
            f"fração da maior componente (LCC)={last_target_adaptive.get('lcc_fraction')} | "
            f"nº de componentes={last_target_adaptive.get('num_components')} | "
            f"eficiência topológica (aprox)={last_target_adaptive.get('efficiency_topological_approx', last_target_adaptive.get('efficiency_approx'))} | "
            f"eficiência topológica retida={last_target_adaptive.get('efficiency_topological_retained', '—')} | "
            f"eficiência por distância retida={last_target_adaptive.get('efficiency_length_retained', '—')}"
        )
        if Path(res_target_adaptive_plot).exists():
            res_block.append(f"- Figura: `{_rel_to_outputs(res_target_adaptive_plot, outputs_root)}`")
    else:
        res_block.append("### Direcionada adaptativa\n_(não encontrado — execute `ic resilience --strategy targeted_adaptive`)_")

    res_block.append("")

    if last_random:
        res_block.append("### Aleatória (baseline)\n")
        res_block.append(
            "- Último ponto: "
            f"fração de arestas removidas={last_random.get('removed_fraction')} | "
            f"fração da maior componente (LCC)={last_random.get('lcc_fraction')} | "
            f"nº de componentes={last_random.get('num_components')} | "
            f"eficiência topológica (aprox)={last_random.get('efficiency_topological_approx', last_random.get('efficiency_approx'))} | "
            f"eficiência topológica retida={last_random.get('efficiency_topological_retained', '—')} | "
            f"eficiência por distância retida={last_random.get('efficiency_length_retained', '—')}"
        )
        if Path(res_rand_plot).exists():
            res_block.append(f"- Figura: `{_rel_to_outputs(res_rand_plot, outputs_root)}`")
    else:
        res_block.append("### Aleatória\n_(não encontrado — execute `ic resilience --strategy random`)_")

    res_block_md = "\n".join(res_block)

    node_res_block: List[str] = []
    for label, last_row, plot_path, command in [
        ("Direcionada", last_node_target, node_res_target_plot, "targeted"),
        ("Direcionada adaptativa", last_node_target_adaptive, node_res_target_adaptive_plot, "targeted_adaptive"),
        ("Aleatória", last_node_random, node_res_rand_plot, "random"),
    ]:
        if last_row:
            node_res_block.append(f"### {label}\n")
            node_res_block.append(
                "- Último ponto: "
                f"fração de vértices removidos={last_row.get('removed_fraction')} | "
                f"fração da maior componente (LCC)={last_row.get('lcc_fraction')} | "
                f"LCC entre nós restantes={last_row.get('lcc_remaining_fraction')} | "
                f"nº de componentes={last_row.get('num_components')} | "
                f"eficiência topológica retida={last_row.get('efficiency_topological_retained', '—')} | "
                f"eficiência por distância retida={last_row.get('efficiency_length_retained', '—')}"
            )
            if Path(plot_path).exists():
                node_res_block.append(f"- Figura: `{_rel_to_outputs(plot_path, outputs_root)}`")
        else:
            node_res_block.append(f"### {label}\n_(não encontrado — execute `ic node-resilience --strategy {command}`)_")
        node_res_block.append("")
    node_res_block.append("### Vértices críticos removidos primeiro\n")
    node_res_block.append(_fmt_md_table(_read_csv_rows(node_res_removed_target_csv, limit=10)))
    node_res_block_md = "\n".join(node_res_block)

    comm_res_block: List[str] = []
    for label, last_row, plot_path, command in [
        ("Direcionada", last_comm_target, comm_res_target_plot, "targeted"),
        ("Direcionada adaptativa", last_comm_target_adaptive, comm_res_target_adaptive_plot, "targeted_adaptive"),
        ("Aleatória", last_comm_random, comm_res_rand_plot, "random"),
    ]:
        if last_row:
            comm_res_block.append(f"### {label}\n")
            comm_res_block.append(
                "- Último ponto: "
                f"fração de conexões removidas={last_row.get('removed_fraction')} | "
                f"LCC comunidades={last_row.get('lcc_communities_fraction')} | "
                f"LCC ponderada por nós={last_row.get('lcc_nodes_fraction')} | "
                f"nº de componentes={last_row.get('num_components')} | "
                f"eficiência topológica retida={last_row.get('efficiency_topological_retained', '—')} | "
                f"eficiência por distância retida={last_row.get('efficiency_length_retained', '—')}"
            )
            if Path(plot_path).exists():
                comm_res_block.append(f"- Figura: `{_rel_to_outputs(plot_path, outputs_root)}`")
        else:
            comm_res_block.append(f"### {label}\n_(não encontrado — execute `ic community-resilience --strategy {command}`)_")
        comm_res_block.append("")

    comm_res_edges_rows = _read_csv_rows(comm_res_top_edges_csv, limit=10)
    comm_res_edges_rows = _rename_header(
        comm_res_edges_rows,
        {
            "source_community": "comunidade origem",
            "target_community": "comunidade destino",
            "source_size": "tamanho origem",
            "target_size": "tamanho destino",
            "edge_count": "conexões viárias",
            "total_length_m": "comprimento total (m)",
            "min_length_m": "menor ligação (m)",
            "edge_betweenness": "edge betweenness",
        },
    )
    comm_res_block.append("### Conexões entre comunidades mais críticas\n")
    comm_res_block.append(_fmt_md_table(comm_res_edges_rows))
    comm_res_block_md = "\n".join(comm_res_block)

    intra_comm_block: List[str] = []
    for label, summary_path, plot_path, command in [
        ("Direcionada", intra_comm_summary_target, intra_comm_target_plot, "targeted"),
        ("Direcionada adaptativa", intra_comm_summary_target_adaptive, intra_comm_target_adaptive_plot, "targeted_adaptive"),
        ("Aleatória", intra_comm_summary_random, intra_comm_random_plot, "random"),
    ]:
        rows = _read_csv_rows(summary_path, limit=10)
        if rows:
            rows = _rename_header(
                rows,
                {
                    "community_id": "comunidade",
                    "nodes": "nós",
                    "internal_edges": "arestas internas",
                    "final_lcc_fraction": "LCC final",
                    "lcc_fraction_drop": "queda LCC",
                    "resilience_auc_lcc": "AUC resiliência LCC",
                },
            )
            intra_comm_block.append(f"### {label}: comunidades mais frágeis\n")
            intra_comm_block.append(_fmt_md_table(rows))
            if Path(plot_path).exists():
                intra_comm_block.append(f"\n- Figura: `{_rel_to_outputs(plot_path, outputs_root)}`")
        else:
            intra_comm_block.append(
                f"### {label}\n_(não encontrado — execute `ic intra-community-resilience --strategy {command}`)_"
            )
        intra_comm_block.append("")
    intra_comm_block_md = "\n".join(intra_comm_block)

    # Links/artefatos (sempre relativos ao outputs/<city>)
    links: List[str] = []
    if Path(degree_plot).exists():
        links.append(f"- Distribuição de graus: `{_rel_to_outputs(degree_plot, outputs_root)}`")
    if Path(crit_map).exists():
        links.append(f"- Mapa de pontos críticos: `{_rel_to_outputs(crit_map, outputs_root)}`")
    if Path(vulnerability_nodes_map).exists():
        links.append(f"- Mapa de vulnerabilidade dos nós: `{_rel_to_outputs(vulnerability_nodes_map, outputs_root)}`")
    if Path(vulnerability_edges_map).exists():
        links.append(f"- Mapa de vulnerabilidade das arestas: `{_rel_to_outputs(vulnerability_edges_map, outputs_root)}`")
    if Path(structural_bottlenecks_map).exists():
        links.append(f"- Mapa de gargalos estruturais: `{_rel_to_outputs(structural_bottlenecks_map, outputs_root)}`")
    if Path(structural_articulations_map).exists():
        links.append(f"- Mapa de articulações estruturais: `{_rel_to_outputs(structural_articulations_map, outputs_root)}`")
    if Path(structural_bridges_map).exists():
        links.append(f"- Mapa de pontes estruturais: `{_rel_to_outputs(structural_bridges_map, outputs_root)}`")
    if Path(route_redundancy_map).exists():
        links.append(f"- Mapa de redundância de rotas: `{_rel_to_outputs(route_redundancy_map, outputs_root)}`")
    if Path(spatial_multiscale_vulnerability_map).exists():
        links.append(f"- Mapa multiescala de vulnerabilidade: `{_rel_to_outputs(spatial_multiscale_vulnerability_map, outputs_root)}`")
    if Path(spatial_multiscale_connectivity_map).exists():
        links.append(f"- Mapa multiescala de conectividade: `{_rel_to_outputs(spatial_multiscale_connectivity_map, outputs_root)}`")
    if Path(spatial_multiscale_redundancy_map).exists():
        links.append(f"- Mapa multiescala de baixa redundância: `{_rel_to_outputs(spatial_multiscale_redundancy_map, outputs_root)}`")
    if Path(spatial_robustness_lcc_map).exists():
        links.append(f"- Mapa de robustez espacial por queda LCC: `{_rel_to_outputs(spatial_robustness_lcc_map, outputs_root)}`")
    if Path(spatial_robustness_efficiency_map).exists():
        links.append(f"- Mapa de robustez espacial por eficiência: `{_rel_to_outputs(spatial_robustness_efficiency_map, outputs_root)}`")
    if Path(spatial_robustness_fragmentation_map).exists():
        links.append(f"- Mapa de robustez espacial por fragmentação: `{_rel_to_outputs(spatial_robustness_fragmentation_map, outputs_root)}`")
    if Path(road_hierarchy_map).exists():
        links.append(f"- Mapa de hierarquia viária: `{_rel_to_outputs(road_hierarchy_map, outputs_root)}`")
    if Path(urban_morphology_class_map).exists():
        links.append(f"- Mapa morfológico por classes urbanas: `{_rel_to_outputs(urban_morphology_class_map, outputs_root)}`")
    if Path(urban_morphology_entropy_map).exists():
        links.append(f"- Mapa morfológico por entropia angular: `{_rel_to_outputs(urban_morphology_entropy_map, outputs_root)}`")
    if Path(urban_morphology_connectivity_map).exists():
        links.append(f"- Mapa morfológico por conectividade local: `{_rel_to_outputs(urban_morphology_connectivity_map, outputs_root)}`")
    if Path(od_efficiency_map).exists():
        links.append(f"- Mapa de eficiência OD por rotas com maior desvio: `{_rel_to_outputs(od_efficiency_map, outputs_root)}`")
    if Path(subcenters_map).exists():
        links.append(f"- Mapa de subcentros e policentralidade: `{_rel_to_outputs(subcenters_map, outputs_root)}`")
    if Path(urban_barriers_permeability_map).exists():
        links.append(f"- Mapa de barreiras urbanas por permeabilidade: `{_rel_to_outputs(urban_barriers_permeability_map, outputs_root)}`")
    if Path(urban_barriers_connections_map).exists():
        links.append(f"- Mapa de conexões e barreiras prováveis: `{_rel_to_outputs(urban_barriers_connections_map, outputs_root)}`")
    if Path(network_scale_metrics_plot).exists():
        links.append(f"- Gráfico do perfil de escala: `{_rel_to_outputs(network_scale_metrics_plot, outputs_root)}`")
    if Path(network_scale_stability_plot).exists():
        links.append(f"- Gráfico de estabilidade multiescalar: `{_rel_to_outputs(network_scale_stability_plot, outputs_root)}`")
    if Path(network_scale_map).exists():
        links.append(f"- Mapa do perfil de escala por baixa permeabilidade: `{_rel_to_outputs(network_scale_map, outputs_root)}`")
    if Path(comm_map).exists():
        links.append(f"- Mapa de comunidades: `{_rel_to_outputs(comm_map, outputs_root)}`")
    if Path(res_target_adaptive_plot).exists():
        links.append(f"- Resiliência adaptativa: `{_rel_to_outputs(res_target_adaptive_plot, outputs_root)}`")
    if Path(node_res_target_plot).exists():
        links.append(f"- Resiliência por remoção de vértices: `{_rel_to_outputs(node_res_target_plot, outputs_root)}`")
    if Path(comm_res_target_plot).exists():
        links.append(f"- Resiliência entre comunidades: `{_rel_to_outputs(comm_res_target_plot, outputs_root)}`")
    if Path(intra_comm_target_plot).exists():
        links.append(f"- Resiliência interna por comunidade: `{_rel_to_outputs(intra_comm_target_plot, outputs_root)}`")
    if Path(route_map).exists():
        links.append(f"- Mapa de rota (E4): `{_rel_to_outputs(route_map, outputs_root)}`")
    links.append(f"- Lista de arquivos gerados (manifest): `{_rel_to_outputs(manifest_txt, outputs_root)}`")

    links_md = "\n".join(links)

    # Montar relatório
    md: List[str] = []
    md.append(f"# Relatório consolidado — {city_id}\n")

    md.append("## 0. Configuração do experimento\n")
    if meta:
        md.append(f"- **Data de geração (E1):** {meta.get('created_at', '—')}")
        md.append(f"- **network_type:** {meta.get('network_type', '—')}")
        md.append(f"- **simplify:** {meta.get('simplify', '—')}")
        md.append(f"- **Recorte (clip):** {meta.get('clip', '—')}")
        md.append(f"- **Nós/Arestas (raw):** {meta.get('nodes', '—')} / {meta.get('edges', '—')}")
    else:
        md.append("_(Metadados do download (E1) não encontrados em `data/metadata/`. Isso não impede o relatório, mas reduz a reprodutibilidade.)_")

    md.append("\n## 1. O que foi feito (pipeline)\n")
    md.append(
        "- **E1:** Download da rede viária (OSMnx)\n"
        "- **E2:** Pré-processamento (maior componente + verificações)\n"
        "- **E3:** Métricas estruturais (topologia / sem pesos)\n"
        "- **E4:** Rotas por distância (ponderado por `length`)\n"
        "- **E5:** Centralidades (pontos críticos)\n"
        "- **E6:** Comunidades (modularidade)\n"
        "- **E7:** Resiliência (remoção de arestas)\n"
        "- **E7V:** Resiliência por remoção de vértices\n"
        "- **E7C:** Resiliência entre comunidades (grafo agregado)\n"
        "- **E7I:** Resiliência interna de cada comunidade\n"
        "- **Vulnerabilidade:** Índice composto de criticidade de nós e arestas\n"
        "- **Gargalos estruturais:** Pontes, articulações e impacto direto de fragmentação\n"
        "- **Redundância de rotas:** Alternativas OD após bloqueio da melhor rota\n"
        "- **Multiescala espacial:** Métricas locais por células regulares\n"
        "- **Robustez espacial:** Impacto global de bloqueios regionais por célula\n"
        "- **Hierarquia viária:** Contribuição de classes `highway` para conectividade e robustez\n"
        "- **Morfologia urbana:** Comparação entre padrões de planejamento e estrutura local da rede\n"
        "- **Eficiência OD:** Estatística de rotas em múltiplos pares origem-destino\n"
        "- **Subcentros:** Detecção de centralidade policêntrica por regiões da rede\n"
        "- **Barreiras urbanas:** Exposição da rede a baixa permeabilidade espacial e travessias frágeis\n"
        "- **Perfil de escala:** Sensibilidade das métricas espaciais a células de tamanhos diferentes\n"
        "- **E8:** Consolidação (este relatório)\n"
    )

    md.append("\n## 2. Métricas estruturais (E3)\n")
    md.append(structural_block)

    md.append("\n## 3. Rotas por distância (E4)\n")
    md.append("### Resumo (prévia)\n")
    md.append(route_preview)
    if Path(route_map).exists():
        md.append(f"\n- Mapa: `{_rel_to_outputs(route_map, outputs_root)}`")

    md.append("\n## 4. Pontos críticos (E5)\n")
    md.append("### Top nós (prévia)\n")
    md.append(top_nodes_preview)
    md.append("\n### Rankings por métrica\n")
    md.append(centrality_rankings_preview)
    if centrality_text:
        md.append("\n### Relatório (trecho)\n")
        md.append("```text\n" + "\n".join(centrality_text.splitlines()[:25]) + "\n```")

    md.append("\n## 5. Comunidades (E6)\n")
    md.append("### Resumo por comunidade (prévia)\n")
    md.append(comm_summary_preview)
    if comm_text:
        md.append("\n### Relatório (trecho)\n")
        md.append("```text\n" + "\n".join(comm_text.splitlines()[:25]) + "\n```")

    md.append("\n## 6. Resiliência (E7)\n")
    md.append(res_block_md)

    md.append("\n## 7. Resiliência por remoção de vértices (E7V)\n")
    md.append("Esta análise remove exclusivamente vértices e permanece separada da remoção de arestas.\n")
    md.append(node_res_block_md)

    md.append("\n## 8. Resiliência entre comunidades (E7C)\n")
    md.append(comm_res_block_md)

    md.append("\n## 9. Resiliência interna por comunidade (E7I)\n")
    md.append(intra_comm_block_md)

    md.append("\n## 10. Pontes, articulações e gargalos estruturais\n")
    md.append(
        "Esta análise identifica elementos cuja remoção aumenta diretamente a fragmentação da maior "
        "componente conectada. Diferente do índice composto de vulnerabilidade, aqui o foco é o impacto "
        "estrutural observável: quantos nós saem da maior componente quando uma ponte ou articulação é removida.\n"
    )
    md.append("\n### Nós de articulação com maior impacto\n")
    md.append(structural_articulations_preview)
    md.append("\n### Pontes estruturais com maior impacto\n")
    md.append(structural_bridges_preview)
    md.append("\n### Ranking combinado de gargalos\n")
    md.append(structural_bottlenecks_preview)

    md.append("\n## 11. Perfil de redundância de rotas\n")
    md.append(
        "Esta análise amostra pares origem-destino, calcula a menor rota por distância, bloqueia "
        "todos os segmentos dessa melhor rota e verifica se ainda existe uma alternativa. Uma "
        "alternativa é considerada razoável quando sua distância não ultrapassa o limiar configurado "
        "em relação à rota original.\n"
    )
    md.append("\n### Resumo\n")
    md.append(route_redundancy_summary_preview)
    md.append("\n### Pares origem-destino analisados\n")
    md.append(route_redundancy_pairs_preview)

    md.append("\n## 12. Análise multiescala espacial\n")
    md.append(
        "Esta análise divide a cidade em células espaciais regulares e calcula métricas locais no "
        "subgrafo de cada célula. O objetivo é revelar desigualdades internas que podem ficar "
        "escondidas quando se observa apenas o grafo inteiro.\n"
    )
    md.append("\n### Resumo\n")
    md.append(spatial_multiscale_summary_preview)
    md.append("\n### Células com maior risco local\n")
    md.append(spatial_multiscale_cells_preview)

    md.append("\n## 13. Robustez espacial por bloqueios regionais\n")
    md.append(
        "Esta análise simula falhas concentradas no espaço. Para cada célula da grade, as vias "
        "associadas à região são removidas e o impacto é medido no grafo inteiro por queda da "
        "maior componente, fragmentação e eficiência retida.\n"
    )
    md.append("\n### Resumo\n")
    md.append(spatial_robustness_summary_preview)
    md.append("\n### Bloqueios regionais de maior impacto\n")
    md.append(spatial_robustness_cells_preview)

    md.append("\n## 14. Hierarquia viária\n")
    md.append(
        "Esta análise agrupa as arestas pelo atributo OSM `highway` e mede como cada classe de via "
        "contribui para extensão, conectividade, centralidade observada, vulnerabilidade e resiliência "
        "global quando a classe é removida.\n"
    )
    md.append("\n### Resumo\n")
    md.append(road_hierarchy_summary_preview)
    md.append("\n### Métricas por classe highway\n")
    md.append(road_hierarchy_by_class_preview)

    md.append("\n## 15. Planejamento urbano x estrutura da rede\n")
    md.append(
        "Esta análise classifica células espaciais como gradeadas, radiais/lineares, orgânicas, "
        "fragmentadas ou mistas usando orientação das vias, entropia angular, conectividade local, "
        "maior componente e comprimento médio dos segmentos. O objetivo é aproximar a leitura de "
        "morfologia urbana a partir da estrutura do grafo viário.\n"
    )
    md.append("\n### Resumo\n")
    md.append(urban_morphology_summary_preview)
    md.append("\n### Células classificadas\n")
    md.append(urban_morphology_cells_preview)

    md.append("\n## 16. Eficiência de rotas em múltiplos pares OD\n")
    md.append(
        "Esta análise amostra vários pares origem-destino no grafo dirigido e calcula a menor "
        "rota por distância. Para cada par, registra distância da rota, distância direta "
        "geográfica, desvio/circuity, eficiência relativa, hops e acessibilidade por limiares "
        "de distância. Isso transforma a rota pontual em uma distribuição estatística comparável.\n"
    )
    md.append("\n### Resumo\n")
    md.append(od_efficiency_summary_preview)
    md.append("\n### Pares com maior desvio\n")
    md.append(od_efficiency_pairs_preview)

    md.append("\n## 17. Subcentros e centralidade policêntrica\n")
    md.append(
        "Esta análise divide a cidade em células espaciais e identifica regiões que concentram "
        "importância estrutural. O score combina centralidade acumulada, centralidade máxima, "
        "densidade local, conectividade, proximidade, autovetor e diversidade de comunidades "
        "tocadas. A distribuição dos scores dos subcentros é usada para estimar policentralidade "
        "ou dependência de um centro dominante.\n"
    )
    md.append("\n### Resumo\n")
    md.append(subcenters_summary_preview)
    md.append("\n### Subcentros detectados\n")
    md.append(subcenters_preview)
    md.append("\n### Ranking de centralidade por região\n")
    md.append(subcenters_cells_preview)

    md.append("\n## 18. Exposição da rede a barreiras urbanas\n")
    md.append(
        "Esta análise infere barreiras urbanas prováveis a partir da própria topologia da rede. "
        "Ela combina baixa conectividade entre células vizinhas, conexões adjacentes ausentes, "
        "travessias longas, pontes estruturais e separação por comunidades. Sem uma camada externa, "
        "o resultado deve ser lido como evidência topológica de baixa permeabilidade, não como "
        "identificação definitiva de rios, ferrovias ou rodovias.\n"
    )
    md.append("\n### Resumo\n")
    md.append(urban_barriers_summary_preview)
    md.append("\n### Células com menor permeabilidade\n")
    md.append(urban_barriers_cells_preview)
    md.append("\n### Conexões entre regiões com maior score de barreira\n")
    md.append(urban_barriers_connections_preview)

    md.append("\n## 19. Perfil de escala da rede viária\n")
    md.append(
        "Esta análise recalcula métricas espaciais usando diferentes tamanhos de célula, por padrão "
        "500 m, 1 km, 2 km e 3 km. O objetivo é medir se conclusões locais são estáveis ou se "
        "dependem fortemente da resolução da grade. Métricas com alta estabilidade são mais "
        "defensáveis; métricas muito sensíveis devem ser interpretadas como dependentes da escala.\n"
    )
    md.append("\n### Resumo\n")
    md.append(network_scale_summary_preview)
    md.append("\n### Métricas por escala\n")
    md.append(network_scale_scales_preview)
    md.append("\n### Estabilidade das métricas\n")
    md.append(network_scale_stability_preview)
    md.append("\n### Células com maior baixa permeabilidade por escala\n")
    md.append(network_scale_cells_preview)

    md.append("\n## 20. Índice composto de vulnerabilidade\n")
    md.append(
        "O índice combina centralidade, participação em ataques por vértices, pontos de articulação, "
        "pontes estruturais, tipo de via, comprimento e fronteiras entre comunidades. Ele é um ranking "
        "descritivo para priorizar elementos que concentram múltiplos sinais de criticidade.\n"
    )
    md.append("\n### Nós mais vulneráveis\n")
    md.append(vulnerability_nodes_preview)
    md.append("\n### Arestas mais vulneráveis\n")
    md.append(vulnerability_edges_preview)

    md.append("\n## 21. Artefatos gerados\n")
    md.append(links_md)

    md.append("\n## 22. Relações entre topologia e características funcionais\n")
    md.append("As correlações são associações descritivas com atributos OSM e não demonstram causalidade.\n")
    md.append(functional_correlations_preview)

    md.append("\n## 23. Validação das aproximações\n")
    md.append("A validação compara aproximações com cálculos exatos em subgrafo conectado controlado.\n")
    md.append(approximation_validation_preview)

    Path(report_md).write_text("\n".join(md) + "\n", encoding="utf-8")

    return {
        "report_md": report_md,
        "manifest_txt": manifest_txt,
        "manifest_json": manifest_json,
    }
