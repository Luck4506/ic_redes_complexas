from __future__ import annotations

from pathlib import Path
from typing import Any

from .graph_inventory import gerar_planilha_grafo
from .html_report import _as_float, _e, _format_value, _read_csv_dicts


COMPARISON_METRICS = [
    ("tamanho", "nodes", "Nos", "Quantidade de intersecoes/pontos do grafo."),
    ("tamanho", "edges", "Arestas", "Quantidade de segmentos direcionados."),
    ("tamanho", "total_length_km", "Extensao total", "Soma dos comprimentos das arestas, em km."),
    ("tamanho", "named_streets_unique", "Vias nomeadas", "Nomes distintos de vias no OSM."),
    ("topologia", "degree_mean", "Grau medio", "Media do grau dos nos na maior componente."),
    ("topologia", "degree_max", "Grau maximo", "Maior grau observado."),
    ("topologia", "density", "Densidade", "Densidade do grafo nao direcionado."),
    ("topologia", "transitivity", "Transitividade", "Coeficiente global de transitividade."),
    ("superficie", "paved_edges_pct", "Pavimentado informado", "Percentual das arestas totais com surface pavimentado no OSM."),
    ("superficie_estimativa", "estimated_paved_edges_pct", "Pavimentado estimado", "Estimativa: aplica aos trechos sem surface a proporcao observada nos trechos com surface conhecido."),
    ("superficie_estimativa", "estimated_paved_length_pct", "Extensao pavimentada estimada", "Estimativa por extensao; nao e dado observado direto."),
    ("superficie", "unpaved_edges_pct", "Terra informado", "Percentual das arestas totais com surface de terra/sem pavimento no OSM."),
    ("superficie_estimativa", "estimated_unpaved_edges_pct", "Terra estimada", "Estimativa de terra/sem pavimento usando a proporcao observada nos trechos conhecidos."),
    ("superficie", "unknown_surface_edges_pct", "Surface desconhecido", "Percentual das arestas sem surface no OSM."),
    ("superficie", "surface_known_edges_pct", "Surface conhecido", "Cobertura do atributo surface no OSM por arestas."),
    ("velocidade", "maxspeed_mean", "Velocidade media informada", "Media dos valores numericos de maxspeed conhecidos."),
    ("velocidade", "maxspeed_known_edges_pct", "Maxspeed conhecido", "Percentual das arestas com maxspeed informado."),
    ("faixas", "lanes_mean", "Faixas medias informadas", "Media dos valores numericos de lanes conhecidos."),
    ("faixas", "lanes_known_edges_pct", "Lanes conhecido", "Percentual das arestas com lanes informado."),
    ("comunidades", "communities_count", "Comunidades", "Quantidade de comunidades detectadas."),
    ("comunidades", "communities_largest_size", "Maior comunidade", "Tamanho da maior comunidade."),
    ("comunidades", "communities_largest_pct", "Maior comunidade (%)", "Participacao da maior comunidade no total classificado."),
    ("centralidade", "centrality_top_node_betweenness", "Maior betweenness de no", "Betweenness do no mais critico salvo em top_nodes.csv."),
    ("centralidade", "centrality_top_edge_betweenness", "Maior edge betweenness", "Edge betweenness da aresta mais critica."),
    ("resiliencia", "resilience_targeted_final_lcc_fraction", "LCC final dirigida", "Fracao da maior componente no fim da remocao dirigida."),
    ("resiliencia", "resilience_targeted_lcc_fraction_drop", "Queda LCC dirigida", "Queda da fracao da maior componente na remocao dirigida."),
    ("resiliencia", "resilience_targeted_final_efficiency_topological_retained", "Eficiencia topologica retida dirigida", "Fracao da eficiencia topologica preservada no fim da remocao dirigida."),
    ("resiliencia", "resilience_targeted_final_efficiency_length_retained", "Eficiencia por distancia retida dirigida", "Fracao da eficiencia ponderada por distancia preservada no fim da remocao dirigida."),
    ("resiliencia", "resilience_targeted_adaptive_final_lcc_fraction", "LCC final dirigida adaptativa", "Fracao da maior componente no fim da remocao dirigida adaptativa."),
    ("resiliencia", "resilience_targeted_adaptive_lcc_fraction_drop", "Queda LCC dirigida adaptativa", "Queda da fracao da maior componente na remocao dirigida adaptativa."),
    ("resiliencia", "resilience_targeted_adaptive_final_efficiency_topological_retained", "Eficiencia topologica retida adaptativa", "Fracao da eficiencia topologica preservada no fim da remocao dirigida adaptativa."),
    ("resiliencia", "resilience_targeted_adaptive_final_efficiency_length_retained", "Eficiencia por distancia retida adaptativa", "Fracao da eficiencia ponderada por distancia preservada no fim da remocao dirigida adaptativa."),
    ("resiliencia", "resilience_random_final_lcc_fraction", "LCC final aleatoria", "Fracao da maior componente no fim da remocao aleatoria."),
    ("resiliencia", "resilience_random_lcc_fraction_drop", "Queda LCC aleatoria", "Queda da fracao da maior componente na remocao aleatoria."),
    ("resiliencia", "resilience_random_final_efficiency_topological_retained", "Eficiencia topologica retida aleatoria", "Fracao da eficiencia topologica preservada no fim da remocao aleatoria."),
    ("resiliencia", "resilience_random_final_efficiency_length_retained", "Eficiencia por distancia retida aleatoria", "Fracao da eficiencia ponderada por distancia preservada no fim da remocao aleatoria."),
    ("resiliencia_comunidades", "community_resilience_targeted_final_lcc_nodes_fraction", "LCC final comunidades dirigida", "Fracao ponderada por nos na maior componente do grafo de comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_lcc_nodes_fraction_drop", "Queda LCC comunidades dirigida", "Queda da fracao ponderada por nos no grafo de comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_final_efficiency_topological_retained", "Eficiencia comunidades dirigida", "Fracao da eficiencia topologica retida no grafo de comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_adaptive_final_lcc_nodes_fraction", "LCC final comunidades adaptativa", "Fracao ponderada por nos na maior componente apos remocao adaptativa."),
    ("resiliencia_comunidades", "community_resilience_targeted_adaptive_lcc_nodes_fraction_drop", "Queda LCC comunidades adaptativa", "Queda da fracao ponderada por nos no ataque adaptativo entre comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_adaptive_final_efficiency_topological_retained", "Eficiencia comunidades adaptativa", "Fracao da eficiencia topologica retida no ataque adaptativo entre comunidades."),
    ("resiliencia_comunidades", "community_resilience_random_final_lcc_nodes_fraction", "LCC final comunidades aleatoria", "Fracao ponderada por nos na maior componente com remocao aleatoria."),
    ("resiliencia_comunidades", "community_resilience_random_lcc_nodes_fraction_drop", "Queda LCC comunidades aleatoria", "Queda da fracao ponderada por nos no grafo de comunidades."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_auc_lcc_mean", "AUC media interna dirigida", "Media da resiliencia interna das comunidades sob remocao dirigida."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_auc_lcc_min", "Menor AUC interna dirigida", "Comunidade mais fragil sob remocao dirigida."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_final_lcc_mean", "LCC final interna media dirigida", "Media da fracao final da maior componente dentro de cada comunidade."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_adaptive_auc_lcc_mean", "AUC media interna adaptativa", "Media da resiliencia interna das comunidades sob remocao adaptativa."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_random_auc_lcc_mean", "AUC media interna aleatoria", "Baseline aleatorio medio da resiliencia interna das comunidades."),
]


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)


def _summary_for_dataset(dataset: str) -> dict[str, dict[str, str]]:
    graph_path = Path(f"data/graphs/{dataset}_drive_clean.graphml")
    if not graph_path.exists():
        raise FileNotFoundError(f"Grafo limpo nao encontrado para '{dataset}': {graph_path}")

    gerar_planilha_grafo(dataset)
    rows = _read_csv_dicts(f"outputs/{dataset}/metrics/graph_inventory_summary.csv")
    return {row.get("indicador", ""): row for row in rows if row.get("indicador")}


def _value(summary: dict[str, dict[str, str]], metric: str) -> str:
    row = summary.get(metric)
    if not row:
        return ""
    return row.get("valor", "")


def _unit(summary: dict[str, dict[str, str]], metric: str) -> str:
    row = summary.get(metric)
    if not row:
        return ""
    return row.get("unidade", "")


def _delta(first: str, second: str, unit: str, metric: str) -> str:
    a = _as_float(first)
    b = _as_float(second)
    if a is None or b is None:
        return "-"

    diff = b - a
    formatted = _format_value(diff, unit, metric)
    if diff > 0:
        return f"+{formatted}"
    return formatted


def _comparison_table(datasets: list[str], summaries: dict[str, dict[str, dict[str, str]]]) -> str:
    include_delta = len(datasets) == 2
    headers = ["Grupo", "Indicador", *datasets]
    if include_delta:
        headers.append(f"Delta {datasets[1]} - {datasets[0]}")
    headers.append("Descricao")

    rows = []
    for group, metric, label, description in COMPARISON_METRICS:
        cells = [f"<td>{_e(group)}</td>", f"<td><strong>{_e(label)}</strong><br><code>{_e(metric)}</code></td>"]
        raw_values = []
        unit = ""
        for dataset in datasets:
            summary = summaries[dataset]
            raw = _value(summary, metric)
            unit = _unit(summary, metric) or unit
            raw_values.append(raw)
            cells.append(f"<td class=\"numeric\">{_format_value(raw, unit, metric) if raw != '' else '<span class=\"missing\">nao encontrado</span>'}</td>")
        if include_delta:
            cells.append(f"<td class=\"numeric delta\">{_e(_delta(raw_values[0], raw_values[1], unit, metric))}</td>")
        cells.append(f"<td>{_e(description)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    return f"""
    <section class="panel wide">
      <h2>Comparacao Consolidada</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>{header_html}</tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </section>
    """


def _dataset_cards(datasets: list[str], summaries: dict[str, dict[str, dict[str, str]]]) -> str:
    cards = []
    for dataset in datasets:
        summary = summaries[dataset]
        nodes = _format_value(_value(summary, "nodes"), _unit(summary, "nodes"), "nodes")
        edges = _format_value(_value(summary, "edges"), _unit(summary, "edges"), "edges")
        length = _format_value(_value(summary, "total_length_km"), _unit(summary, "total_length_km"), "total_length_km")
        lcc_drop = _format_value(
            _value(summary, "resilience_targeted_lcc_fraction_drop"),
            _unit(summary, "resilience_targeted_lcc_fraction_drop"),
            "resilience_targeted_lcc_fraction_drop",
        )
        paved_est = _format_value(
            _value(summary, "estimated_paved_edges_pct"),
            _unit(summary, "estimated_paved_edges_pct"),
            "estimated_paved_edges_pct",
        )
        surface_known = _format_value(
            _value(summary, "surface_known_edges_pct"),
            _unit(summary, "surface_known_edges_pct"),
            "surface_known_edges_pct",
        )
        cards.append(
            f"""
            <article class="card">
              <div class="card-title">{_e(dataset)}</div>
              <div class="mini-grid">
                <div><strong>{nodes}</strong><span>Nos</span></div>
                <div><strong>{edges}</strong><span>Arestas</span></div>
                <div><strong>{length} km</strong><span>Extensao</span></div>
                <div><strong>{paved_est}</strong><span>Asfalto estimado</span></div>
                <div><strong>{surface_known}</strong><span>Surface conhecido</span></div>
                <div><strong>{lcc_drop}</strong><span>Queda LCC dirigida</span></div>
              </div>
            </article>
            """
        )
    return f"<section class=\"cards\">{''.join(cards)}</section>"


def _link_grid(datasets: list[str]) -> str:
    items = []
    for dataset in datasets:
        dashboard = Path(f"outputs/{dataset}/dashboard_{dataset}.html")
        inventory = Path(f"outputs/{dataset}/metrics/graph_inventory_summary.csv")
        report = Path(f"outputs/{dataset}/REPORT_{dataset}.md")
        links = []
        if dashboard.exists():
            links.append(f"<a href=\"../{_e(dataset)}/dashboard_{_e(dataset)}.html\">Dashboard</a>")
        if inventory.exists():
            links.append(f"<a href=\"../{_e(dataset)}/metrics/graph_inventory_summary.csv\">Inventario CSV</a>")
        if report.exists():
            links.append(f"<a href=\"../{_e(dataset)}/REPORT_{_e(dataset)}.md\">Relatorio MD</a>")
        items.append(
            f"""
            <div class="link-box">
              <strong>{_e(dataset)}</strong>
              <span>{' · '.join(links) if links else 'Sem links auxiliares encontrados'}</span>
            </div>
            """
        )
    return f"""
    <section class="panel wide">
      <h2>Arquivos de Origem</h2>
      <div class="link-grid">{''.join(items)}</div>
    </section>
    """


def _artifact_path(dataset: str, kind: str) -> Path:
    if kind == "roads":
        return Path(f"outputs/{dataset}/figures/grafo_{dataset}_clean_ruas.png")
    if kind == "roads_nodes":
        return Path(f"outputs/{dataset}/figures/grafo_{dataset}_clean_ruas_nos.png")
    if kind == "communities_graph":
        return Path(f"outputs/{dataset}/figures/grafo_{dataset}_clean_comunidades.png")
    if kind == "degree":
        return Path(f"outputs/{dataset}/figures/degree_distribution_loglog.png")
    if kind == "resilience_targeted":
        return Path(f"outputs/{dataset}/figures/resilience_curve_targeted.png")
    if kind == "resilience_targeted_adaptive":
        return Path(f"outputs/{dataset}/figures/resilience_curve_targeted_adaptive.png")
    if kind == "resilience_random":
        return Path(f"outputs/{dataset}/figures/resilience_curve_random.png")
    if kind == "community_resilience_targeted":
        return Path(f"outputs/{dataset}/figures/community_resilience_curve_targeted.png")
    if kind == "community_resilience_targeted_adaptive":
        return Path(f"outputs/{dataset}/figures/community_resilience_curve_targeted_adaptive.png")
    if kind == "community_resilience_random":
        return Path(f"outputs/{dataset}/figures/community_resilience_curve_random.png")
    if kind == "intra_community_resilience_targeted":
        return Path(f"outputs/{dataset}/figures/intra_community_resilience_targeted.png")
    if kind == "intra_community_resilience_targeted_adaptive":
        return Path(f"outputs/{dataset}/figures/intra_community_resilience_targeted_adaptive.png")
    if kind == "intra_community_resilience_random":
        return Path(f"outputs/{dataset}/figures/intra_community_resilience_random.png")
    if kind == "route_map":
        return Path(f"outputs/{dataset}/maps/rota_distancia.html")
    if kind == "critical_map":
        return Path(f"outputs/{dataset}/maps/pontos_criticos.html")
    if kind == "communities_map":
        return Path(f"outputs/{dataset}/maps/comunidades.html")
    raise ValueError(f"Tipo de artefato desconhecido: {kind}")


def _artifact_src(path: Path, output_path: str) -> str:
    try:
        return path.relative_to(Path(output_path).parent).as_posix()
    except ValueError:
        try:
            return Path("../") / path.relative_to("outputs")
        except ValueError:
            return path.as_posix()


def _visual_compare_block(title: str, datasets: list[str], kind: str, media_type: str, output_path: str) -> str:
    cells = []
    found_any = False
    for dataset in datasets:
        path = _artifact_path(dataset, kind)
        if path.exists():
            found_any = True
            if media_type == "iframe":
                media = f'<iframe src="{_e(_artifact_src(path, output_path))}" loading="lazy"></iframe>'
            else:
                media = f'<img class="visual-img" src="{_e(_artifact_src(path, output_path))}" alt="{_e(title)} - {_e(dataset)}">'
        else:
            media = '<div class="missing-visual">Artefato nao encontrado</div>'

        cells.append(
            f"""
            <article class="visual-card">
              <h3>{_e(dataset)}</h3>
              {media}
            </article>
            """
        )

    if not found_any:
        return ""

    return f"""
    <section class="panel wide">
      <h2>{_e(title)}</h2>
      <div class="visual-grid" style="--cols: {len(datasets)}">
        {''.join(cells)}
      </div>
    </section>
    """


def _side_by_side_dashboard(datasets: list[str], output_path: str) -> str:
    blocks = [
        _visual_compare_block("Grafo de Ruas", datasets, "roads", "image", output_path),
        _visual_compare_block("Grafo de Ruas + Nos", datasets, "roads_nodes", "image", output_path),
        _visual_compare_block("Grafo por Comunidades", datasets, "communities_graph", "image", output_path),
        _visual_compare_block("Distribuicao de Grau", datasets, "degree", "image", output_path),
        _visual_compare_block("Resiliencia - Remocao Dirigida", datasets, "resilience_targeted", "image", output_path),
        _visual_compare_block("Resiliencia - Remocao Dirigida Adaptativa", datasets, "resilience_targeted_adaptive", "image", output_path),
        _visual_compare_block("Resiliencia - Remocao Aleatoria", datasets, "resilience_random", "image", output_path),
        _visual_compare_block("Resiliencia por Comunidades - Dirigida", datasets, "community_resilience_targeted", "image", output_path),
        _visual_compare_block("Resiliencia por Comunidades - Dirigida Adaptativa", datasets, "community_resilience_targeted_adaptive", "image", output_path),
        _visual_compare_block("Resiliencia por Comunidades - Aleatoria", datasets, "community_resilience_random", "image", output_path),
        _visual_compare_block("Resiliencia Interna por Comunidade - Dirigida", datasets, "intra_community_resilience_targeted", "image", output_path),
        _visual_compare_block("Resiliencia Interna por Comunidade - Dirigida Adaptativa", datasets, "intra_community_resilience_targeted_adaptive", "image", output_path),
        _visual_compare_block("Resiliencia Interna por Comunidade - Aleatoria", datasets, "intra_community_resilience_random", "image", output_path),
        _visual_compare_block("Mapa de Rota", datasets, "route_map", "iframe", output_path),
        _visual_compare_block("Mapa de Pontos Criticos", datasets, "critical_map", "iframe", output_path),
        _visual_compare_block("Mapa de Comunidades", datasets, "communities_map", "iframe", output_path),
    ]
    return "".join(blocks)


def gerar_comparacao_html(datasets: list[str], output_path: str | None = None) -> dict:
    if len(datasets) < 2:
        raise ValueError("Passe pelo menos dois datasets para comparar.")

    datasets = [_safe_name(dataset) for dataset in datasets]
    summaries = {dataset: _summary_for_dataset(dataset) for dataset in datasets}

    compare_dir = Path("outputs/comparisons")
    compare_dir.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = str(compare_dir / f"compare_{'_vs_'.join(datasets)}.html")

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
    header h1 { margin: 0 0 8px; font-size: 32px; letter-spacing: 0; }
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
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }
    .card, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(20, 30, 45, 0.04);
    }
    .card { padding: 16px; }
    .card-title {
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 12px;
    }
    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .mini-grid strong { display: block; font-size: 22px; }
    .mini-grid span { display: block; color: var(--muted); font-size: 13px; }
    .panel {
      grid-column: span 6;
      padding: 18px;
      min-width: 0;
    }
    .panel.wide { grid-column: 1 / -1; }
    h2 { margin: 0 0 14px; font-size: 19px; letter-spacing: 0; }
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
    td.numeric {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    td.delta {
      font-weight: 700;
      color: #0f5c37;
    }
    code {
      background: #eef1f5;
      padding: 2px 5px;
      border-radius: 4px;
      color: #314255;
    }
    .missing { color: var(--muted); }
    .link-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }
    .link-box {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #f9fafb;
    }
    .link-box strong, .link-box span { display: block; }
    .link-box span { color: var(--muted); margin-top: 4px; }
    .visual-grid {
      display: grid;
      grid-template-columns: repeat(var(--cols), minmax(360px, 1fr));
      gap: 14px;
      overflow-x: auto;
      padding-bottom: 4px;
    }
    .visual-card {
      min-width: 360px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f9fafb;
      padding: 12px;
    }
    .visual-card h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    .visual-img {
      display: block;
      width: 100%;
      height: 420px;
      object-fit: contain;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    iframe {
      width: 100%;
      height: 460px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    .missing-visual {
      display: grid;
      place-items: center;
      min-height: 180px;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 6px;
      background: #fff;
    }
    a { color: var(--accent); text-decoration: none; font-weight: 600; }
    a:hover { text-decoration: underline; }
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
  <title>Comparacao de Grafos - {_e(' vs '.join(datasets))}</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <h1>Comparacao de Grafos</h1>
    <p>{_e(' vs '.join(datasets))}</p>
  </header>
  <main>
    {_dataset_cards(datasets, summaries)}
    {_side_by_side_dashboard(datasets, output_path)}
    {_comparison_table(datasets, summaries)}
    {_link_grid(datasets)}
  </main>
</body>
</html>
"""

    Path(output_path).write_text(html_doc, encoding="utf-8")
    return {
        "compare_html": output_path,
        "datasets": datasets,
    }
