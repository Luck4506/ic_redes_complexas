from __future__ import annotations

import csv
import math
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
from scipy.cluster.hierarchy import dendrogram, linkage
from scipy.spatial.distance import squareform

from .compare_report import COMPARISON_METRICS
from .graph_inventory import gerar_planilha_grafo
from .html_report import _as_float, _e, _format_value, _read_csv_dicts


THEORY_CORE_METRICS = {
    "physical_collapsed_length_km_per_km2",
    "nodes_per_km2",
    "degree_mean",
    "transitivity",
    "communities_largest_pct",
    "robustness_edge_random_lcc_auc_normalized_mean",
    "robustness_edge_targeted_lcc_auc_normalized_mean",
    "robustness_node_random_lcc_auc_normalized_mean",
    "robustness_node_targeted_lcc_auc_normalized_mean",
    "robustness_community_targeted_lcc_auc_normalized_mean",
    "route_redundancy_reasonable_rate",
    "spatial_robustness_mean_lcc_fraction_drop",
    "road_hierarchy_arterial_length_fraction",
    "od_efficiency_circuity_ratio_mean",
    "network_scale_least_stable_cv",
}


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)


def _write_rows(path: str, rows: list[dict[str, Any]]) -> None:
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        Path(path).write_text("", encoding="utf-8")
        return
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)


def _summary_for_dataset(dataset: str) -> dict[str, dict[str, str]]:
    gerar_planilha_grafo(dataset)
    rows = _read_csv_dicts(f"outputs/{dataset}/metrics/graph_inventory_summary.csv")
    return {row.get("indicador", ""): row for row in rows if row.get("indicador")}


def _numeric_metric_keys(
    summaries: dict[str, dict[str, dict[str, str]]],
    min_coverage: float,
    metric_profile: str = "theory_core",
) -> list[tuple[str, str, str]]:
    candidates: list[tuple[str, str, str]] = []
    for group, key, label, _description in COMPARISON_METRICS:
        if metric_profile == "theory_core" and key not in THEORY_CORE_METRICS:
            continue
        values = [_as_float(summaries[dataset].get(key, {}).get("valor")) for dataset in summaries]
        present = [value for value in values if value is not None and math.isfinite(value)]
        if len(present) / len(summaries) < min_coverage:
            continue
        if len(set(round(value, 12) for value in present)) <= 1:
            continue
        candidates.append((group, key, label))
    return candidates


def _raw_matrix(
    datasets: list[str],
    summaries: dict[str, dict[str, dict[str, str]]],
    metrics: list[tuple[str, str, str]],
) -> np.ndarray:
    matrix = np.full((len(datasets), len(metrics)), np.nan, dtype=float)
    for i, dataset in enumerate(datasets):
        for j, (_group, key, _label) in enumerate(metrics):
            value = _as_float(summaries[dataset].get(key, {}).get("valor"))
            if value is not None and math.isfinite(value):
                matrix[i, j] = value
    return matrix


def _standardize_matrix(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    means = np.nanmean(matrix, axis=0)
    filled = np.where(np.isnan(matrix), means, matrix)
    stds = np.std(filled, axis=0)
    keep = stds > 1e-12
    standardized = (filled[:, keep] - means[keep]) / stds[keep]
    return standardized, means[keep], stds[keep]


def _euclidean_distances(matrix: np.ndarray) -> np.ndarray:
    n = matrix.shape[0]
    distances = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            distances[i, j] = float(np.linalg.norm(matrix[i] - matrix[j]))
    return distances


def _cosine_similarity(matrix: np.ndarray) -> np.ndarray:
    norms = np.linalg.norm(matrix, axis=1)
    n = matrix.shape[0]
    sims = np.zeros((n, n), dtype=float)
    for i in range(n):
        for j in range(n):
            denom = norms[i] * norms[j]
            sims[i, j] = float(np.dot(matrix[i], matrix[j]) / denom) if denom > 0 else 0.0
    return sims


def _pca(matrix: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
    if matrix.size == 0:
        return np.zeros((matrix.shape[0], 0)), np.array([])
    centered = matrix - np.mean(matrix, axis=0)
    _u, singular_values, vt = np.linalg.svd(centered, full_matrices=False)
    scores = centered @ vt.T
    variances = (singular_values**2) / max(1, matrix.shape[0] - 1)
    explained = variances / variances.sum() if variances.sum() > 0 else np.zeros_like(variances)
    return scores, explained


def _matrix_rows(datasets: list[str], matrix: np.ndarray, value_name: str) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, source in enumerate(datasets):
        for j, target in enumerate(datasets):
            rows.append({"source": source, "target": target, value_name: matrix[i, j]})
    return rows


def _nearest_rows(datasets: list[str], distances: np.ndarray, similarities: np.ndarray) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, dataset in enumerate(datasets):
        candidates = [(j, distances[i, j]) for j in range(len(datasets)) if j != i]
        if not candidates:
            continue
        nearest, distance = min(candidates, key=lambda item: item[1])
        rows.append(
            {
                "dataset": dataset,
                "nearest_dataset": datasets[nearest],
                "euclidean_distance": distance,
                "cosine_similarity": similarities[i, nearest],
            }
        )
    return rows


def _cluster_rows(datasets: list[str], distances: np.ndarray) -> list[dict[str, Any]]:
    if len(datasets) < 2:
        return []
    condensed = squareform(distances, checks=False)
    z = linkage(condensed, method="average")
    rows = []
    for step, (left, right, distance, count) in enumerate(z, start=1):
        rows.append(
            {
                "step": step,
                "left_cluster": int(left),
                "right_cluster": int(right),
                "distance": float(distance),
                "merged_items": int(count),
            }
        )
    return rows


def _vectors_rows(
    datasets: list[str],
    metrics: list[tuple[str, str, str]],
    raw: np.ndarray,
    standardized: np.ndarray,
    kept_indices: list[int],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for i, dataset in enumerate(datasets):
        for out_j, metric_index in enumerate(kept_indices):
            group, key, label = metrics[metric_index]
            rows.append(
                {
                    "dataset": dataset,
                    "group": group,
                    "metric": key,
                    "label": label,
                    "raw_value": raw[i, metric_index],
                    "z_score": standardized[i, out_j],
                }
            )
    return rows


def _heatmap(path: str, datasets: list[str], matrix: np.ndarray, title: str, cmap: str) -> None:
    fig, ax = plt.subplots(figsize=(max(6, len(datasets) * 1.2), max(5, len(datasets) * 1.0)))
    image = ax.imshow(matrix, cmap=cmap)
    ax.set_xticks(range(len(datasets)), datasets, rotation=35, ha="right")
    ax.set_yticks(range(len(datasets)), datasets)
    ax.set_title(title)
    for i in range(len(datasets)):
        for j in range(len(datasets)):
            ax.text(j, i, f"{matrix[i, j]:.2f}", ha="center", va="center", fontsize=8)
    fig.colorbar(image, ax=ax, shrink=0.75)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _pca_plot(path: str, datasets: list[str], scores: np.ndarray, explained: np.ndarray) -> None:
    fig, ax = plt.subplots(figsize=(7, 5))
    x = scores[:, 0] if scores.shape[1] >= 1 else np.zeros(len(datasets))
    y = scores[:, 1] if scores.shape[1] >= 2 else np.zeros(len(datasets))
    ax.scatter(x, y, s=70, color="#1769aa")
    for dataset, px, py in zip(datasets, x, y):
        ax.annotate(dataset, (px, py), textcoords="offset points", xytext=(6, 5), fontsize=9)
    pc1 = explained[0] * 100 if len(explained) >= 1 else 0.0
    pc2 = explained[1] * 100 if len(explained) >= 2 else 0.0
    ax.set_xlabel(f"PC1 ({pc1:.1f}% var.)")
    ax.set_ylabel(f"PC2 ({pc2:.1f}% var.)")
    ax.set_title("PCA dos vetores de métricas")
    ax.axhline(0, color="#d9dee7", linewidth=1)
    ax.axvline(0, color="#d9dee7", linewidth=1)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _dendrogram_plot(path: str, datasets: list[str], distances: np.ndarray) -> None:
    if len(datasets) < 2:
        return
    z = linkage(squareform(distances, checks=False), method="average")
    fig, ax = plt.subplots(figsize=(8, 5))
    dendrogram(z, labels=datasets, ax=ax)
    ax.set_title("Cluster hierárquico por similaridade estrutural")
    ax.set_ylabel("Distância euclidiana em z-score")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def _html_table(rows: list[dict[str, Any]], limit: int | None = None) -> str:
    selected = rows if limit is None else rows[:limit]
    if not selected:
        return "<p class=\"empty\">Sem dados.</p>"
    headers = list(selected[0].keys())
    body = []
    for row in selected:
        cells = []
        for header in headers:
            value = row.get(header, "")
            cls = " class=\"numeric\"" if isinstance(value, (int, float, np.floating)) else ""
            shown = _format_value(value) if cls else _e(value)
            cells.append(f"<td{cls}>{shown}</td>")
        body.append("<tr>" + "".join(cells) + "</tr>")
    return (
        "<div class=\"table-wrap\"><table><thead><tr>"
        + "".join(f"<th>{_e(header)}</th>" for header in headers)
        + "</tr></thead><tbody>"
        + "".join(body)
        + "</tbody></table></div>"
    )


def _write_html(
    path: str,
    datasets: list[str],
    metrics_used: int,
    nearest: list[dict[str, Any]],
    pca_rows: list[dict[str, Any]],
    distance_plot: str,
    similarity_plot: str,
    pca_plot: str,
    dendrogram_plot: str,
) -> None:
    rel = lambda p: Path(p).relative_to(Path(path).parent).as_posix()
    css = """
    body { margin: 0; background: #f6f7f9; color: #1f2933; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif; line-height: 1.45; }
    header { padding: 32px 40px 20px; background: #fff; border-bottom: 1px solid #d9dee7; }
    main { padding: 24px 40px 48px; display: grid; grid-template-columns: repeat(12, 1fr); gap: 18px; }
    .panel { grid-column: span 6; background: #fff; border: 1px solid #d9dee7; border-radius: 8px; padding: 18px; min-width: 0; }
    .wide { grid-column: 1 / -1; }
    h1 { margin: 0 0 8px; }
    h2 { margin: 0 0 14px; font-size: 19px; }
    p { color: #687385; }
    img { max-width: 100%; border: 1px solid #d9dee7; border-radius: 6px; background: #fff; }
    .table-wrap { overflow: auto; border: 1px solid #d9dee7; border-radius: 6px; }
    table { width: 100%; border-collapse: collapse; font-size: 13px; }
    th, td { padding: 9px 10px; border-bottom: 1px solid #d9dee7; text-align: left; white-space: nowrap; }
    th { background: #e8f2fb; color: #123a5b; }
    td.numeric { text-align: right; font-variant-numeric: tabular-nums; }
    code { background: #eef1f5; padding: 2px 5px; border-radius: 4px; }
    @media (max-width: 900px) { header, main { padding-left: 18px; padding-right: 18px; } .panel { grid-column: 1 / -1; } }
    """
    html = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Similaridade Entre Cidades</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <h1>Similaridade Entre Cidades</h1>
    <p>{_e(', '.join(datasets))}</p>
  </header>
  <main>
    <section class="panel wide">
      <h2>Metodologia</h2>
      <p>Foram usadas {metrics_used} métricas numéricas, padronizadas por z-score. Distâncias menores indicam perfis mais próximos apenas dentro deste conjunto e desta seleção de métricas. PCA, clusters e vizinhos são descrições exploratórias, não uma tipologia urbana confirmada. O cosseno em dados centrados pode ser negativo e não é um percentual de semelhança.</p>
    </section>
    <section class="panel">
      <h2>Distância Euclidiana</h2>
      <img src="{_e(rel(distance_plot))}" alt="Matriz de distância">
    </section>
    <section class="panel">
      <h2>Similaridade Cosseno</h2>
      <img src="{_e(rel(similarity_plot))}" alt="Matriz de similaridade">
    </section>
    <section class="panel">
      <h2>PCA</h2>
      <img src="{_e(rel(pca_plot))}" alt="PCA">
    </section>
    <section class="panel">
      <h2>Cluster Hierárquico</h2>
      <img src="{_e(rel(dendrogram_plot))}" alt="Dendrograma">
    </section>
    <section class="panel wide">
      <h2>Cidade Mais Parecida Para Cada Dataset</h2>
      {_html_table(nearest)}
    </section>
    <section class="panel wide">
      <h2>Coordenadas PCA</h2>
      {_html_table(pca_rows)}
    </section>
  </main>
</body>
</html>
"""
    Path(path).write_text(html, encoding="utf-8")


def analisar_similaridade_cidades(
    datasets: list[str],
    output_dir: str = "outputs/comparisons",
    min_coverage: float = 1.0,
    metric_profile: str = "theory_core",
    minimum_datasets: int = 8,
    allow_small_sample_exploration: bool = False,
) -> dict[str, Any]:
    if len(datasets) < 2:
        raise ValueError("Passe pelo menos dois datasets para calcular similaridade.")
    datasets = [_safe_name(dataset) for dataset in datasets]
    if len(set(datasets)) != len(datasets):
        raise ValueError("Cada dataset deve aparecer uma única vez.")
    if metric_profile not in {"theory_core", "all"}:
        raise ValueError("metric_profile deve ser 'theory_core' ou 'all'.")
    if not 0 < min_coverage <= 1:
        raise ValueError("min_coverage deve estar no intervalo (0, 1].")
    if minimum_datasets < 3:
        raise ValueError("minimum_datasets deve ser pelo menos 3.")
    if len(datasets) < minimum_datasets and not allow_small_sample_exploration:
        raise ValueError(
            f"Amostra insuficiente para PCA, clustering e vizinho mais próximo: {len(datasets)} "
            f"datasets, mínimo configurado {minimum_datasets}. Amplie a amostra ou passe "
            "allow_small_sample_exploration=True e trate todos os resultados como descritivos."
        )
    Path(output_dir).mkdir(parents=True, exist_ok=True)
    suffix = "_vs_".join(datasets)

    summaries = {dataset: _summary_for_dataset(dataset) for dataset in datasets}
    metrics = _numeric_metric_keys(
        summaries,
        min_coverage=min_coverage,
        metric_profile=metric_profile,
    )
    if not metrics:
        raise ValueError("Nenhuma métrica numérica com cobertura suficiente foi encontrada.")
    raw = _raw_matrix(datasets, summaries, metrics)
    standardized_all, _means, _stds = _standardize_matrix(raw)
    kept = []
    for j in range(raw.shape[1]):
        col = raw[:, j]
        filled = np.where(np.isnan(col), np.nanmean(col), col)
        if np.std(filled) > 1e-12:
            kept.append(j)
    metrics = [metrics[j] for j in kept]
    raw = raw[:, kept]
    standardized = standardized_all

    distances = _euclidean_distances(standardized)
    similarities = _cosine_similarity(standardized)
    pca_scores, explained = _pca(standardized)

    vectors_csv = f"{output_dir}/city_similarity_vectors_{suffix}.csv"
    distances_csv = f"{output_dir}/city_similarity_distances_{suffix}.csv"
    similarities_csv = f"{output_dir}/city_similarity_cosine_{suffix}.csv"
    pca_csv = f"{output_dir}/city_similarity_pca_{suffix}.csv"
    clusters_csv = f"{output_dir}/city_similarity_clusters_{suffix}.csv"
    nearest_csv = f"{output_dir}/city_similarity_nearest_{suffix}.csv"
    html_path = f"{output_dir}/city_similarity_{suffix}.html"
    distance_plot = f"{output_dir}/city_similarity_distance_heatmap_{suffix}.png"
    similarity_plot = f"{output_dir}/city_similarity_cosine_heatmap_{suffix}.png"
    pca_plot = f"{output_dir}/city_similarity_pca_{suffix}.png"
    dendrogram_path = f"{output_dir}/city_similarity_dendrogram_{suffix}.png"

    _write_rows(vectors_csv, _vectors_rows(datasets, metrics, raw, standardized, list(range(len(metrics)))))
    _write_rows(distances_csv, _matrix_rows(datasets, distances, "euclidean_distance"))
    _write_rows(similarities_csv, _matrix_rows(datasets, similarities, "cosine_similarity"))
    nearest = _nearest_rows(datasets, distances, similarities)
    _write_rows(nearest_csv, nearest)
    pca_rows = [
        {
            "dataset": dataset,
            "pc1": float(pca_scores[i, 0]) if pca_scores.shape[1] >= 1 else 0.0,
            "pc2": float(pca_scores[i, 1]) if pca_scores.shape[1] >= 2 else 0.0,
            "pc1_explained_variance": float(explained[0]) if len(explained) >= 1 else 0.0,
            "pc2_explained_variance": float(explained[1]) if len(explained) >= 2 else 0.0,
        }
        for i, dataset in enumerate(datasets)
    ]
    _write_rows(pca_csv, pca_rows)
    _write_rows(clusters_csv, _cluster_rows(datasets, distances))

    _heatmap(distance_plot, datasets, distances, "Distância euclidiana dos vetores padronizados", "Blues")
    _heatmap(similarity_plot, datasets, similarities, "Similaridade cosseno dos vetores padronizados", "YlGn")
    _pca_plot(pca_plot, datasets, pca_scores, explained)
    _dendrogram_plot(dendrogram_path, datasets, distances)
    _write_html(
        html_path,
        datasets,
        len(metrics),
        nearest,
        pca_rows,
        distance_plot,
        similarity_plot,
        pca_plot,
        dendrogram_path,
    )

    report_txt = f"{output_dir}/city_similarity_report_{suffix}.txt"
    inference_status = (
        "descritivo_exploratorio_amostra_pequena"
        if len(datasets) < minimum_datasets
        else "descritivo_amostra_minima_atendida"
    )
    nearest_text = "\n".join(
        f"- {row['dataset']} mais parecida com {row['nearest_dataset']} "
        f"(distância={float(row['euclidean_distance']):.4f}, cosseno={float(row['cosine_similarity']):.4f})"
        for row in nearest
    )
    Path(report_txt).write_text(
        "\n".join(
            [
                "Similaridade Entre Cidades",
                f"Datasets: {', '.join(datasets)}",
                f"Métricas numéricas usadas: {len(metrics)}",
                f"Perfil de métricas: {metric_profile}",
                f"Status de inferência: {inference_status}",
                f"Regra de amostra mínima: {minimum_datasets} datasets",
                "",
                "ATENÇÃO: distâncias, PCA, vizinhos e clusters são descrições dependentes das métricas e do conjunto; não constituem tipologia urbana confirmada.",
                "A similaridade cosseno é calculada em z-scores centrados e pode ser negativa; não deve ser lida como percentual de semelhança.",
                "",
                "Dataset mais próximo por distância euclidiana no conjunto:",
                nearest_text,
                "",
                "Arquivos:",
                f"- Vetores: {vectors_csv}",
                f"- Distâncias: {distances_csv}",
                f"- Similaridade cosseno: {similarities_csv}",
                f"- PCA: {pca_csv}",
                f"- Clustering: {clusters_csv}",
                f"- HTML: {html_path}",
            ]
        )
        + "\n",
        encoding="utf-8",
    )

    return {
        "html": html_path,
        "vectors_csv": vectors_csv,
        "distances_csv": distances_csv,
        "similarities_csv": similarities_csv,
        "pca_csv": pca_csv,
        "clusters_csv": clusters_csv,
        "nearest_csv": nearest_csv,
        "report_txt": report_txt,
        "metrics_used": len(metrics),
        "metric_profile": metric_profile,
        "minimum_datasets": minimum_datasets,
        "inference_status": inference_status,
    }
