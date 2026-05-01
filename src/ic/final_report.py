from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Dict, List, Optional


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
    centrality_report = f"{logs_dir}/centrality_report.txt"
    crit_map = f"{maps_dir}/pontos_criticos.html"

    # --- E6 ---
    comm_summary_csv = f"{metrics_dir}/community_summary.csv"
    comm_report = f"{logs_dir}/communities_report.txt"
    comm_map = f"{maps_dir}/comunidades.html"

    # --- E7 ---
    res_target_csv = f"{metrics_dir}/resilience_curve_targeted.csv"
    res_rand_csv = f"{metrics_dir}/resilience_curve_random.csv"
    res_target_plot = f"{figs_dir}/resilience_curve_targeted.png"
    res_rand_plot = f"{figs_dir}/resilience_curve_random.png"

    # --- E3 figura ---
    degree_plot = f"{figs_dir}/degree_distribution_loglog.png"

    # Manifest
    Path(outputs_root).mkdir(parents=True, exist_ok=True)
    files = _list_files(outputs_root)
    Path(manifest_txt).write_text("\n".join(files) + "\n", encoding="utf-8")

    # Bloco E3
    if structural:
        structural_block = "\n".join(
            [
                f"- **Nós (n):** {structural.get('nodes', '—')}",
                f"- **Arestas (m):** {structural.get('edges', '—')}",
                f"- **Grau médio:** {structural.get('degree_mean', '—')}",
                f"- **Transitividade:** {structural.get('transitivity', '—')}",
                f"- **Clustering (aprox):** {structural.get('avg_clustering_approx', '—')}",
                f"- **Assortatividade (grau):** {structural.get('assortativity_degree', '—')}",
                f"- **Caminho médio (aprox, hops):** {structural.get('avg_shortest_path_len_approx_hops', '—')}",
                f"- **Diâmetro (aprox, hops):** {structural.get('diameter_approx_hops', '—')}",
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
        },
    )
    top_nodes_preview = _fmt_md_table(top_nodes_rows)

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

    # Trechos de logs
    centrality_text = _read_text(centrality_report).strip()
    comm_text = _read_text(comm_report).strip()

    # Resiliência: último ponto
    last_target = _last_row(res_target_csv)
    last_random = _last_row(res_rand_csv)

    res_block: List[str] = []
    if last_target:
        res_block.append("### Direcionada (remoção dirigida)\n")
        res_block.append(
            "- Último ponto: "
            f"fração de arestas removidas={last_target.get('removed_fraction')} | "
            f"fração da maior componente (LCC)={last_target.get('lcc_fraction')} | "
            f"nº de componentes={last_target.get('num_components')} | "
            f"eficiência (aprox)={last_target.get('efficiency_approx')}"
        )
        if Path(res_target_plot).exists():
            res_block.append(f"- Figura: `{_rel_to_outputs(res_target_plot, outputs_root)}`")
    else:
        res_block.append("### Direcionada\n_(não encontrado — execute `ic resilience --strategy targeted`)_")

    res_block.append("")

    if last_random:
        res_block.append("### Aleatória (baseline)\n")
        res_block.append(
            "- Último ponto: "
            f"fração de arestas removidas={last_random.get('removed_fraction')} | "
            f"fração da maior componente (LCC)={last_random.get('lcc_fraction')} | "
            f"nº de componentes={last_random.get('num_components')} | "
            f"eficiência (aprox)={last_random.get('efficiency_approx')}"
        )
        if Path(res_rand_plot).exists():
            res_block.append(f"- Figura: `{_rel_to_outputs(res_rand_plot, outputs_root)}`")
    else:
        res_block.append("### Aleatória\n_(não encontrado — execute `ic resilience --strategy random`)_")

    res_block_md = "\n".join(res_block)

    # Links/artefatos (sempre relativos ao outputs/<city>)
    links: List[str] = []
    if Path(degree_plot).exists():
        links.append(f"- Distribuição de graus: `{_rel_to_outputs(degree_plot, outputs_root)}`")
    if Path(crit_map).exists():
        links.append(f"- Mapa de pontos críticos: `{_rel_to_outputs(crit_map, outputs_root)}`")
    if Path(comm_map).exists():
        links.append(f"- Mapa de comunidades: `{_rel_to_outputs(comm_map, outputs_root)}`")
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

    md.append("\n## 7. Artefatos gerados\n")
    md.append(links_md)

    Path(report_md).write_text("\n".join(md) + "\n", encoding="utf-8")

    return {
        "report_md": report_md,
        "manifest_txt": manifest_txt,
    }
