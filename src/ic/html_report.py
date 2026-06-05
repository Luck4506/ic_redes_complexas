from __future__ import annotations

import csv
import html
import json
from pathlib import Path
from typing import Any

from .graph_inventory import gerar_planilha_grafo


def _read_csv_dicts(path: str) -> list[dict[str, str]]:
    p = Path(path)
    if not p.exists():
        return []
    with p.open(newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _read_json(path: str) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        return {}
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _rel(path: str, root: str) -> str:
    try:
        return Path(path).relative_to(root).as_posix()
    except Exception:
        return path


def _e(value: Any) -> str:
    return html.escape(str(value))


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _format_value(value: Any, unit: str = "", indicator: str = "") -> str:
    number = _as_float(value)
    if number is None:
        return _e(value)

    if unit == "percentual" or indicator.endswith("_pct") or "fraction" in indicator:
        return f"{number * 100:.2f}%"

    if number.is_integer():
        return f"{int(number):,}".replace(",", ".")

    if abs(number) >= 1000:
        return f"{number:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

    return f"{number:.4f}".rstrip("0").rstrip(".").replace(".", ",")


def _summary_map(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    return {row.get("indicador", ""): row for row in rows if row.get("indicador")}


def _metric(summary: dict[str, dict[str, str]], key: str, fallback: str = "nao encontrado") -> str:
    row = summary.get(key)
    if not row:
        return fallback
    return _format_value(row.get("valor", ""), row.get("unidade", ""), key)


def _card(title: str, value: str, subtitle: str) -> str:
    return f"""
      <article class="card">
        <div class="card-title">{_e(title)}</div>
        <div class="card-value">{value}</div>
        <div class="card-subtitle">{_e(subtitle)}</div>
      </article>
    """


def _table(title: str, rows: list[dict[str, str]], limit: int = 12) -> str:
    if not rows:
        return f"""
        <section class="panel">
          <h2>{_e(title)}</h2>
          <p class="empty">Dados nao encontrados.</p>
        </section>
        """

    headers = list(rows[0].keys())
    body = []
    for row in rows[:limit]:
        cells = []
        for header in headers:
            value = row.get(header, "")
            if header.endswith("_pct") or header in {"comprimento_pct", "arestas_pct", "nos_pct"}:
                value = _format_value(value, "percentual", header)
            elif header in {"comprimento_km", "comprimento_m"}:
                value = _format_value(value)
            cells.append(f"<td>{_e(value)}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")

    header_html = "".join(f"<th>{_e(h)}</th>" for h in headers)
    return f"""
    <section class="panel">
      <h2>{_e(title)}</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>{header_html}</tr></thead>
          <tbody>{''.join(body)}</tbody>
        </table>
      </div>
    </section>
    """


def _inventory_rows_by_group(rows: list[dict[str, str]], group: str) -> list[dict[str, str]]:
    return [row for row in rows if row.get("grupo") == group]


def _metric_list(title: str, rows: list[dict[str, str]], limit: int = 20) -> str:
    if not rows:
        return ""

    items = []
    for row in rows[:limit]:
        indicator = row.get("indicador", "")
        value = _format_value(row.get("valor", ""), row.get("unidade", ""), indicator)
        desc = row.get("descricao", "")
        items.append(
            f"""
            <tr>
              <td><code>{_e(indicator)}</code></td>
              <td class="numeric">{value}</td>
              <td>{_e(row.get("unidade", ""))}</td>
              <td>{_e(desc)}</td>
            </tr>
            """
        )

    return f"""
    <section class="panel wide">
      <h2>{_e(title)}</h2>
      <div class="table-wrap">
        <table>
          <thead><tr><th>Indicador</th><th>Valor</th><th>Unidade</th><th>Descricao</th></tr></thead>
          <tbody>{''.join(items)}</tbody>
        </table>
      </div>
    </section>
    """


def _image_panel(title: str, path: str, outputs_root: str) -> str:
    if not Path(path).exists():
        return ""
    return f"""
    <section class="panel">
      <h2>{_e(title)}</h2>
      <img class="figure" src="{_e(_rel(path, outputs_root))}" alt="{_e(title)}">
    </section>
    """


def _iframe_panel(title: str, path: str, outputs_root: str) -> str:
    if not Path(path).exists():
        return ""
    return f"""
    <section class="panel wide">
      <h2>{_e(title)}</h2>
      <iframe src="{_e(_rel(path, outputs_root))}" loading="lazy"></iframe>
    </section>
    """


def gerar_dashboard_html(city_id: str) -> dict:
    outputs_root = f"outputs/{city_id}"
    metrics_dir = f"{outputs_root}/metrics"
    figures_dir = f"{outputs_root}/figures"
    maps_dir = f"{outputs_root}/maps"
    dashboard_path = f"{outputs_root}/dashboard_{city_id}.html"

    inventory = gerar_planilha_grafo(city_id)
    summary_rows = _read_csv_dicts(inventory["summary_csv"])
    summary = _summary_map(summary_rows)

    meta = _read_json(f"data/metadata/{city_id}_drive_raw.json")
    highway_rows = _read_csv_dicts(f"{metrics_dir}/graph_inventory_highway.csv")
    surface_rows = _read_csv_dicts(f"{metrics_dir}/graph_inventory_surface.csv")
    maxspeed_rows = _read_csv_dicts(f"{metrics_dir}/graph_inventory_maxspeed.csv")
    lanes_rows = _read_csv_dicts(f"{metrics_dir}/graph_inventory_lanes.csv")
    degree_rows = _read_csv_dicts(f"{metrics_dir}/graph_inventory_degree.csv")
    communities_rows = _read_csv_dicts(f"{metrics_dir}/community_summary.csv")
    top_nodes_rows = _read_csv_dicts(f"{metrics_dir}/top_nodes.csv")
    top_edges_rows = _read_csv_dicts(f"{metrics_dir}/top_edges.csv")
    centrality_rankings_rows = _read_csv_dicts(f"{metrics_dir}/centrality_rankings.csv")
    functional_groups_rows = _read_csv_dicts(f"{metrics_dir}/functional_topology_groups.csv")
    functional_correlations_rows = _read_csv_dicts(f"{metrics_dir}/functional_topology_correlations.csv")
    approximation_validation_rows = _read_csv_dicts(f"{metrics_dir}/approximation_validation.csv")
    res_target_rows = _read_csv_dicts(f"{metrics_dir}/resilience_curve_targeted.csv")
    res_target_adaptive_rows = _read_csv_dicts(f"{metrics_dir}/resilience_curve_targeted_adaptive.csv")
    res_random_rows = _read_csv_dicts(f"{metrics_dir}/resilience_curve_random.csv")
    node_res_target_rows = _read_csv_dicts(f"{metrics_dir}/node_resilience_curve_targeted.csv")
    node_res_target_adaptive_rows = _read_csv_dicts(f"{metrics_dir}/node_resilience_curve_targeted_adaptive.csv")
    node_res_random_rows = _read_csv_dicts(f"{metrics_dir}/node_resilience_curve_random.csv")
    node_res_removed_target_rows = _read_csv_dicts(f"{metrics_dir}/node_resilience_removed_targeted.csv")
    comm_res_summary_rows = _read_csv_dicts(f"{metrics_dir}/community_resilience_summary.csv")
    comm_res_top_edges_rows = _read_csv_dicts(f"{metrics_dir}/community_resilience_top_edges.csv")
    comm_res_target_rows = _read_csv_dicts(f"{metrics_dir}/community_resilience_curve_targeted.csv")
    comm_res_target_adaptive_rows = _read_csv_dicts(f"{metrics_dir}/community_resilience_curve_targeted_adaptive.csv")
    comm_res_random_rows = _read_csv_dicts(f"{metrics_dir}/community_resilience_curve_random.csv")
    intra_comm_target_rows = _read_csv_dicts(f"{metrics_dir}/intra_community_resilience_summary_targeted.csv")
    intra_comm_target_adaptive_rows = _read_csv_dicts(
        f"{metrics_dir}/intra_community_resilience_summary_targeted_adaptive.csv"
    )
    intra_comm_random_rows = _read_csv_dicts(f"{metrics_dir}/intra_community_resilience_summary_random.csv")
    vulnerability_nodes_rows = _read_csv_dicts(f"{metrics_dir}/vulnerability_nodes.csv")
    vulnerability_edges_rows = _read_csv_dicts(f"{metrics_dir}/vulnerability_edges.csv")
    structural_articulations_rows = _read_csv_dicts(f"{metrics_dir}/structural_articulations.csv")
    structural_bridges_rows = _read_csv_dicts(f"{metrics_dir}/structural_bridges.csv")
    structural_bottlenecks_rows = _read_csv_dicts(f"{metrics_dir}/structural_bottlenecks.csv")
    route_redundancy_pairs_rows = _read_csv_dicts(f"{metrics_dir}/route_redundancy_pairs.csv")
    route_redundancy_summary_rows = _read_csv_dicts(f"{metrics_dir}/route_redundancy_summary.csv")
    spatial_multiscale_cells_rows = _read_csv_dicts(f"{metrics_dir}/spatial_multiscale_cells.csv")
    spatial_multiscale_summary_rows = _read_csv_dicts(f"{metrics_dir}/spatial_multiscale_summary.csv")
    spatial_robustness_cells_rows = _read_csv_dicts(f"{metrics_dir}/spatial_robustness_cells.csv")
    spatial_robustness_summary_rows = _read_csv_dicts(f"{metrics_dir}/spatial_robustness_summary.csv")
    road_hierarchy_rows = _read_csv_dicts(f"{metrics_dir}/road_hierarchy_by_class.csv")
    road_hierarchy_summary_rows = _read_csv_dicts(f"{metrics_dir}/road_hierarchy_summary.csv")
    urban_morphology_cells_rows = _read_csv_dicts(f"{metrics_dir}/urban_morphology_cells.csv")
    urban_morphology_summary_rows = _read_csv_dicts(f"{metrics_dir}/urban_morphology_summary.csv")
    od_efficiency_pairs_rows = _read_csv_dicts(f"{metrics_dir}/od_efficiency_pairs.csv")
    od_efficiency_summary_rows = _read_csv_dicts(f"{metrics_dir}/od_efficiency_summary.csv")
    subcenters_rows = _read_csv_dicts(f"{metrics_dir}/subcenters.csv")
    subcenters_summary_rows = _read_csv_dicts(f"{metrics_dir}/subcenters_summary.csv")
    subcenters_cells_rows = _read_csv_dicts(f"{metrics_dir}/subcenters_cells.csv")
    urban_barriers_cells_rows = _read_csv_dicts(f"{metrics_dir}/urban_barriers_cells.csv")
    urban_barriers_connections_rows = _read_csv_dicts(f"{metrics_dir}/urban_barriers_connections.csv")
    urban_barriers_summary_rows = _read_csv_dicts(f"{metrics_dir}/urban_barriers_summary.csv")
    network_scale_summary_rows = _read_csv_dicts(f"{metrics_dir}/network_scale_profile_summary.csv")
    network_scale_scales_rows = _read_csv_dicts(f"{metrics_dir}/network_scale_profile_scales.csv")
    network_scale_stability_rows = _read_csv_dicts(f"{metrics_dir}/network_scale_profile_stability.csv")
    network_scale_cells_rows = _read_csv_dicts(f"{metrics_dir}/network_scale_profile_cells.csv")

    cards = [
        _card("Nos", _metric(summary, "nodes"), "Intersecoes/pontos do grafo"),
        _card("Arestas", _metric(summary, "edges"), "Segmentos direcionados"),
        _card("Extensao", f"{_metric(summary, 'total_length_km')} km", "Soma dos comprimentos"),
        _card("Vias nomeadas", _metric(summary, "named_streets_unique"), "Nomes distintos no OSM"),
        _card("Asfaltado informado", _metric(summary, "paved_edges_pct"), "Dado observado no OSM"),
        _card("Asfaltado estimado", _metric(summary, "estimated_paved_edges_pct"), "Estimativa, nao dado observado"),
        _card("Surface conhecido", _metric(summary, "surface_known_edges_pct"), "Cobertura do atributo surface"),
        _card("Terra informada", _metric(summary, "unpaved_edges_pct"), "Dado observado no OSM"),
        _card("Grau medio", _metric(summary, "degree_mean"), "Maior componente"),
        _card("Transitividade", _metric(summary, "transitivity"), "Fechamento de triangulos"),
    ]

    if meta:
        meta_block = f"""
        <section class="panel wide">
          <h2>Configuracao do Download</h2>
          <div class="meta-grid">
            <div><strong>Dataset</strong><span>{_e(city_id)}</span></div>
            <div><strong>Cidade base</strong><span>{_e(meta.get('city_id', city_id))}</span></div>
            <div><strong>Data historica</strong><span>{_e(meta.get('historical_date', 'OSM atual'))}</span></div>
            <div><strong>Tipo de rede</strong><span>{_e(meta.get('network_type', ''))}</span></div>
            <div><strong>Nos raw</strong><span>{_e(meta.get('nodes', ''))}</span></div>
            <div><strong>Arestas raw</strong><span>{_e(meta.get('edges', ''))}</span></div>
          </div>
        </section>
        """
    else:
        meta_block = """
        <section class="panel wide">
          <h2>Configuracao do Download</h2>
          <p class="empty">Metadados do download nao encontrados.</p>
        </section>
        """

    reading_guide = """
    <section class="panel wide">
      <h2>Guia de Leitura</h2>
      <p><strong>Topologia:</strong> descreve a estrutura das conexoes. <strong>Funcao:</strong> usa atributos OSM das vias e apresenta associacoes descritivas, nao causalidade.</p>
      <p><strong>Aproximacoes:</strong> closeness, betweenness, caminhos, diametro e eficiencia podem usar amostragem. Consulte a tabela de validacao antes de interpretar diferencas pequenas.</p>
      <p><strong>Resiliencia:</strong> remocao de arestas e remocao de vertices sao experimentos separados. Na remocao de vertices, os nos retirados contam como desconectados e as fontes amostradas permanecem fixas durante a curva.</p>
      <p><strong>Comparacoes:</strong> cidades com recortes, datas ou cobertura experimental diferentes devem ser tratadas como comparacoes exploratorias.</p>
    </section>
    """

    sections = [
        reading_guide,
        meta_block,
        _metric_list("Resumo Consolidado", summary_rows, limit=80),
        _table("Superficie da Rede", surface_rows),
        _table("Tipos de Via", highway_rows),
        _table("Velocidades Maximas", maxspeed_rows),
        _table("Faixas", lanes_rows),
        _table("Distribuicao de Grau", degree_rows),
        _table("Comunidades", communities_rows),
        _table("Top Nos Criticos", top_nodes_rows),
        _table("Top Arestas Criticas", top_edges_rows),
        _table("Rankings de Centralidade", centrality_rankings_rows),
        _table("Topologia x Caracteristicas Funcionais - Grupos", functional_groups_rows),
        _table("Topologia x Caracteristicas Funcionais - Correlacoes", functional_correlations_rows),
        _table("Validacao das Aproximacoes", approximation_validation_rows),
        _table("Resiliencia - Remocao Dirigida", res_target_rows),
        _table("Resiliencia - Remocao Dirigida Adaptativa", res_target_adaptive_rows),
        _table("Resiliencia - Remocao Aleatoria", res_random_rows),
        _table("Resiliencia por Vertices - Dirigida", node_res_target_rows),
        _table("Resiliencia por Vertices - Dirigida Adaptativa", node_res_target_adaptive_rows),
        _table("Resiliencia por Vertices - Aleatoria", node_res_random_rows),
        _table("Vertices Criticos Removidos - Dirigida", node_res_removed_target_rows),
        _table("Resiliencia por Comunidades - Resumo", comm_res_summary_rows),
        _table("Resiliencia por Comunidades - Conexoes Criticas", comm_res_top_edges_rows),
        _table("Resiliencia por Comunidades - Dirigida", comm_res_target_rows),
        _table("Resiliencia por Comunidades - Dirigida Adaptativa", comm_res_target_adaptive_rows),
        _table("Resiliencia por Comunidades - Aleatoria", comm_res_random_rows),
        _table("Resiliencia Interna por Comunidade - Dirigida", intra_comm_target_rows),
        _table("Resiliencia Interna por Comunidade - Dirigida Adaptativa", intra_comm_target_adaptive_rows),
        _table("Resiliencia Interna por Comunidade - Aleatoria", intra_comm_random_rows),
        _table("Indice de Vulnerabilidade - Nos", vulnerability_nodes_rows),
        _table("Indice de Vulnerabilidade - Arestas", vulnerability_edges_rows),
        _table("Gargalos Estruturais - Articulacoes", structural_articulations_rows),
        _table("Gargalos Estruturais - Pontes", structural_bridges_rows),
        _table("Gargalos Estruturais - Ranking Combinado", structural_bottlenecks_rows),
        _table("Redundancia de Rotas - Resumo", route_redundancy_summary_rows),
        _table("Redundancia de Rotas - Pares OD", route_redundancy_pairs_rows),
        _table("Multiescala Espacial - Resumo", spatial_multiscale_summary_rows),
        _table("Multiescala Espacial - Celulas", spatial_multiscale_cells_rows),
        _table("Robustez Espacial - Resumo", spatial_robustness_summary_rows),
        _table("Robustez Espacial - Bloqueios por Celula", spatial_robustness_cells_rows),
        _table("Hierarquia Viaria - Resumo", road_hierarchy_summary_rows),
        _table("Hierarquia Viaria - Classes Highway", road_hierarchy_rows),
        _table("Planejamento Urbano x Rede - Resumo Morfologico", urban_morphology_summary_rows),
        _table("Planejamento Urbano x Rede - Celulas", urban_morphology_cells_rows),
        _table("Eficiencia OD - Resumo Estatistico", od_efficiency_summary_rows),
        _table("Eficiencia OD - Pares com Maior Desvio", od_efficiency_pairs_rows),
        _table("Subcentros e Policentralidade - Resumo", subcenters_summary_rows),
        _table("Subcentros Detectados", subcenters_rows),
        _table("Ranking de Centralidade por Regiao", subcenters_cells_rows),
        _table("Barreiras Urbanas - Resumo", urban_barriers_summary_rows),
        _table("Barreiras Urbanas - Celulas com Baixa Permeabilidade", urban_barriers_cells_rows),
        _table("Barreiras Urbanas - Conexoes entre Regioes", urban_barriers_connections_rows),
        _table("Perfil de Escala - Resumo", network_scale_summary_rows),
        _table("Perfil de Escala - Metricas por Escala", network_scale_scales_rows),
        _table("Perfil de Escala - Estabilidade das Metricas", network_scale_stability_rows),
        _table("Perfil de Escala - Celulas", network_scale_cells_rows),
        _image_panel("Distribuicao de Graus", f"{figures_dir}/degree_distribution_loglog.png", outputs_root),
        _image_panel("Perfil de Escala - Metricas", f"{figures_dir}/network_scale_profile_metrics.png", outputs_root),
        _image_panel("Perfil de Escala - Estabilidade", f"{figures_dir}/network_scale_profile_stability.png", outputs_root),
        _image_panel("Resiliencia - Dirigida", f"{figures_dir}/resilience_curve_targeted.png", outputs_root),
        _image_panel("Resiliencia - Dirigida Adaptativa", f"{figures_dir}/resilience_curve_targeted_adaptive.png", outputs_root),
        _image_panel("Resiliencia - Aleatoria", f"{figures_dir}/resilience_curve_random.png", outputs_root),
        _image_panel("Resiliencia - Aleatoria Agregada", f"{figures_dir}/resilience_random_aggregate.png", outputs_root),
        _image_panel("Resiliencia por Vertices - Dirigida", f"{figures_dir}/node_resilience_curve_targeted.png", outputs_root),
        _image_panel("Resiliencia por Vertices - Dirigida Adaptativa", f"{figures_dir}/node_resilience_curve_targeted_adaptive.png", outputs_root),
        _image_panel("Resiliencia por Vertices - Aleatoria", f"{figures_dir}/node_resilience_curve_random.png", outputs_root),
        _image_panel("Resiliencia por Vertices - Aleatoria Agregada", f"{figures_dir}/node_resilience_random_aggregate.png", outputs_root),
        _image_panel("Resiliencia por Comunidades - Dirigida", f"{figures_dir}/community_resilience_curve_targeted.png", outputs_root),
        _image_panel("Resiliencia por Comunidades - Dirigida Adaptativa", f"{figures_dir}/community_resilience_curve_targeted_adaptive.png", outputs_root),
        _image_panel("Resiliencia por Comunidades - Aleatoria", f"{figures_dir}/community_resilience_curve_random.png", outputs_root),
        _image_panel("Resiliencia Interna por Comunidade - Dirigida", f"{figures_dir}/intra_community_resilience_targeted.png", outputs_root),
        _image_panel("Resiliencia Interna por Comunidade - Dirigida Adaptativa", f"{figures_dir}/intra_community_resilience_targeted_adaptive.png", outputs_root),
        _image_panel("Resiliencia Interna por Comunidade - Aleatoria", f"{figures_dir}/intra_community_resilience_random.png", outputs_root),
        _image_panel("Grafo - Ruas", f"{figures_dir}/grafo_{city_id}_clean_ruas.png", outputs_root),
        _image_panel("Grafo - Ruas e Nos", f"{figures_dir}/grafo_{city_id}_clean_ruas_nos.png", outputs_root),
        _image_panel("Grafo - Comunidades", f"{figures_dir}/grafo_{city_id}_clean_comunidades.png", outputs_root),
        _iframe_panel("Mapa de Rota", f"{maps_dir}/rota_distancia.html", outputs_root),
        _iframe_panel("Mapa de Pontos Criticos", f"{maps_dir}/pontos_criticos.html", outputs_root),
        _iframe_panel("Mapa de Arestas Criticas", f"{maps_dir}/arestas_criticas.html", outputs_root),
        _iframe_panel("Mapa de Vulnerabilidade - Nos", f"{maps_dir}/vulnerability_nodes.html", outputs_root),
        _iframe_panel("Mapa de Vulnerabilidade - Arestas", f"{maps_dir}/vulnerability_edges.html", outputs_root),
        _iframe_panel("Mapa de Gargalos - Articulacoes", f"{maps_dir}/structural_articulations.html", outputs_root),
        _iframe_panel("Mapa de Gargalos - Pontes", f"{maps_dir}/structural_bridges.html", outputs_root),
        _iframe_panel("Mapa de Gargalos - Ranking Combinado", f"{maps_dir}/structural_bottlenecks.html", outputs_root),
        _iframe_panel("Mapa de Redundancia de Rotas", f"{maps_dir}/route_redundancy.html", outputs_root),
        _iframe_panel("Mapa Multiescala - Vulnerabilidade", f"{maps_dir}/spatial_multiscale_vulnerability.html", outputs_root),
        _iframe_panel("Mapa Multiescala - Conectividade", f"{maps_dir}/spatial_multiscale_connectivity.html", outputs_root),
        _iframe_panel("Mapa Multiescala - Baixa Redundancia", f"{maps_dir}/spatial_multiscale_redundancy.html", outputs_root),
        _iframe_panel("Mapa Robustez Espacial - Queda LCC", f"{maps_dir}/spatial_robustness_lcc_drop.html", outputs_root),
        _iframe_panel("Mapa Robustez Espacial - Queda Eficiencia", f"{maps_dir}/spatial_robustness_efficiency_drop.html", outputs_root),
        _iframe_panel("Mapa Robustez Espacial - Fragmentacao", f"{maps_dir}/spatial_robustness_fragmentation.html", outputs_root),
        _iframe_panel("Mapa de Hierarquia Viaria", f"{maps_dir}/road_hierarchy_impact.html", outputs_root),
        _iframe_panel("Mapa Morfologico - Classes Urbanas", f"{maps_dir}/urban_morphology_classes.html", outputs_root),
        _iframe_panel("Mapa Morfologico - Entropia Angular", f"{maps_dir}/urban_morphology_orientation_entropy.html", outputs_root),
        _iframe_panel("Mapa Morfologico - Conectividade", f"{maps_dir}/urban_morphology_connectivity.html", outputs_root),
        _iframe_panel("Mapa Eficiencia OD - Rotas com Maior Desvio", f"{maps_dir}/od_efficiency_routes.html", outputs_root),
        _iframe_panel("Mapa de Subcentros e Policentralidade", f"{maps_dir}/subcenters.html", outputs_root),
        _iframe_panel("Mapa de Barreiras Urbanas - Permeabilidade", f"{maps_dir}/urban_barriers_permeability.html", outputs_root),
        _iframe_panel("Mapa de Barreiras Urbanas - Conexoes", f"{maps_dir}/urban_barriers_connections.html", outputs_root),
        _iframe_panel("Mapa Perfil de Escala - Baixa Permeabilidade", f"{maps_dir}/network_scale_profile_low_permeability.html", outputs_root),
        _iframe_panel("Mapa de Comunidades", f"{maps_dir}/comunidades.html", outputs_root),
    ]

    css = """
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #687385;
      --line: #d9dee7;
      --accent: #1769aa;
      --accent-soft: #e8f2fb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }
    header {
      padding: 32px 40px 20px;
      background: #fff;
      border-bottom: 1px solid var(--line);
    }
    header h1 {
      margin: 0 0 8px;
      font-size: 32px;
      letter-spacing: 0;
    }
    header p { margin: 0; color: var(--muted); }
    main {
      padding: 24px 40px 48px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }
    .cards {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
      gap: 14px;
    }
    .card, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(20, 30, 45, 0.04);
    }
    .card { padding: 16px; min-height: 118px; }
    .card-title {
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .04em;
    }
    .card-value {
      font-size: 28px;
      font-weight: 700;
      margin: 8px 0 6px;
    }
    .card-subtitle { color: var(--muted); font-size: 13px; }
    .panel {
      grid-column: span 6;
      padding: 18px;
      min-width: 0;
    }
    .panel.wide { grid-column: 1 / -1; }
    h2 {
      margin: 0 0 14px;
      font-size: 19px;
      letter-spacing: 0;
    }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      background: #fff;
    }
    th, td {
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
    }
    th {
      background: var(--accent-soft);
      color: #123a5b;
      font-weight: 650;
    }
    td.numeric { font-variant-numeric: tabular-nums; }
    code {
      background: #eef1f5;
      padding: 2px 5px;
      border-radius: 4px;
    }
    .figure {
      display: block;
      width: 100%;
      max-height: 620px;
      object-fit: contain;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    iframe {
      width: 100%;
      height: 520px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    .meta-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 12px;
    }
    .meta-grid div {
      background: #f9fafb;
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
    }
    .meta-grid strong {
      display: block;
      color: var(--muted);
      font-size: 12px;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 4px;
    }
    .empty { color: var(--muted); }
    @media (max-width: 900px) {
      header, main { padding-left: 18px; padding-right: 18px; }
      .panel { grid-column: 1 / -1; }
      header h1 { font-size: 26px; }
    }
    """

    html_doc = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Dashboard do Grafo - {_e(city_id)}</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <h1>Dashboard do Grafo - {_e(city_id)}</h1>
    <p>Relatorio visual gerado a partir dos arquivos de metricas, inventario, mapas e figuras da pipeline.</p>
  </header>
  <main>
    <section class="cards">{''.join(cards)}</section>
    {''.join(sections)}
  </main>
</body>
</html>
"""

    Path(outputs_root).mkdir(parents=True, exist_ok=True)
    Path(dashboard_path).write_text(html_doc, encoding="utf-8")

    return {
        "dashboard_html": dashboard_path,
        "inventory_summary_csv": inventory["summary_csv"],
    }
