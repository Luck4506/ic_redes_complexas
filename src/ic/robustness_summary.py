from __future__ import annotations

import csv
import html
import math
import statistics
from decimal import Decimal
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .random_resilience_stats import _bootstrap_mean_interval, _derived_seed


STRATEGIES = ("random", "targeted", "targeted_adaptive")
STRATEGY_LABELS = {
    "random": "Aleatória",
    "targeted": "Dirigida",
    "targeted_adaptive": "Dirigida adaptativa",
}
MODALITIES = {
    "edge": {
        "label": "Arestas",
        "prefix": "resilience",
        "metrics": (
            ("lcc", "lcc_fraction", "Maior componente"),
            ("efficiency_topological", "efficiency_topological_retained", "Eficiência topológica"),
            ("efficiency_length", "efficiency_length_retained", "Eficiência por distância"),
        ),
    },
    "node": {
        "label": "Vértices",
        "prefix": "node_resilience",
        "metrics": (
            ("lcc", "lcc_fraction", "Maior componente"),
            ("efficiency_topological", "efficiency_topological_retained", "Eficiência topológica"),
            ("efficiency_length", "efficiency_length_retained", "Eficiência por distância"),
        ),
    },
    "community": {
        "label": "Entre comunidades",
        "prefix": "community_resilience",
        "metrics": (
            ("lcc", "lcc_weighted_fraction", "Maior componente ponderada por nós"),
            ("lcc_communities", "lcc_communities_fraction", "Maior componente de comunidades"),
            ("efficiency_topological", "efficiency_topological_retained", "Eficiência topológica"),
            ("efficiency_length", "efficiency_length_retained", "Eficiência por distância"),
        ),
    },
}
PRIMARY_METRICS = ("lcc", "efficiency_topological", "efficiency_length")


def _as_float(value: Any) -> float | None:
    try:
        parsed = float(value)
    except (TypeError, ValueError):
        return None
    return parsed if math.isfinite(parsed) else None


def _percentage_text(fraction: float) -> str:
    """Format a fraction as an exact, compact percentage without rounding it."""

    percentage = Decimal(str(fraction)) * Decimal("100")
    text = format(percentage, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _percentage_field_label(fraction: float) -> str:
    """Return a CSV-safe percentage token while preserving common legacy names."""

    token = _percentage_text(fraction).replace("-", "m").replace(".", "p")
    return f"{token}pct"


def _percentage_display(fraction: float) -> str:
    return f"{_percentage_text(fraction).replace('.', ',')}%"


def _read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def _write_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fields: list[str] = []
    for row in rows:
        for field in row:
            if field not in fields:
                fields.append(field)
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fields)
        writer.writeheader()
        writer.writerows(rows)


def _series(rows: list[dict[str, Any]], field: str) -> list[tuple[float, float]]:
    by_x: dict[float, float] = {}
    for row in rows:
        x = _as_float(row.get("removed_fraction"))
        y = _as_float(row.get(field))
        if x is not None and y is not None:
            by_x[x] = y
    return sorted(by_x.items())


def _value_at(points: list[tuple[float, float]], x: float, endpoint_tolerance: float = 0.001) -> float | None:
    if not points:
        return None
    if x < points[0][0]:
        return None
    if x > points[-1][0]:
        if x - points[-1][0] <= endpoint_tolerance:
            return points[-1][1]
        return None
    for left, right in zip(points, points[1:]):
        if math.isclose(x, left[0], abs_tol=1e-12):
            return left[1]
        if left[0] <= x <= right[0]:
            width = right[0] - left[0]
            if width <= 0:
                return right[1]
            weight = (x - left[0]) / width
            return left[1] + weight * (right[1] - left[1])
    return points[-1][1] if math.isclose(x, points[-1][0], abs_tol=1e-12) else None


def _normalized_auc(points: list[tuple[float, float]], max_fraction: float) -> float | None:
    if max_fraction <= 0 or not points:
        return None
    start = _value_at(points, 0.0)
    end = _value_at(points, max_fraction)
    if start is None or end is None:
        return None
    clipped = [(0.0, start)]
    clipped.extend((x, y) for x, y in points if 0.0 < x < max_fraction)
    clipped.append((max_fraction, end))
    area = sum(
        (right_x - left_x) * (left_y + right_y) / 2.0
        for (left_x, left_y), (right_x, right_y) in zip(clipped, clipped[1:])
    )
    return area / max_fraction


def _threshold_crossing(points: list[tuple[float, float]], threshold: float, max_fraction: float) -> float | None:
    if not points:
        return None
    start = _value_at(points, 0.0)
    if start is None:
        return None
    if start <= threshold:
        return 0.0
    clipped = [(0.0, start)]
    clipped.extend((x, y) for x, y in points if 0.0 < x < max_fraction)
    end = _value_at(points, max_fraction)
    if end is None:
        return None
    clipped.append((max_fraction, end))
    for (left_x, left_y), (right_x, right_y) in zip(clipped, clipped[1:]):
        if right_y <= threshold < left_y:
            if math.isclose(left_y, right_y):
                return right_x
            ratio = (left_y - threshold) / (left_y - right_y)
            return left_x + ratio * (right_x - left_x)
    return None


def _group_repetitions(rows: list[dict[str, Any]]) -> list[list[dict[str, Any]]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for row in rows:
        seed = str(row.get("seed", ""))
        if seed:
            groups.setdefault(seed, []).append(row)
    return list(groups.values())


def _curve_path(dataset: str, modality: str, strategy: str) -> Path:
    prefix = str(MODALITIES[modality]["prefix"])
    return Path(f"outputs/{dataset}/metrics/{prefix}_curve_{strategy}.csv")


def _random_repetitions_path(dataset: str, modality: str) -> Path | None:
    if modality == "edge":
        return Path(f"outputs/{dataset}/metrics/resilience_random_repetitions.csv")
    if modality == "node":
        return Path(f"outputs/{dataset}/metrics/node_resilience_random_repetitions.csv")
    return None


def _load_curves(datasets: list[str]) -> dict[tuple[str, str, str], list[list[dict[str, Any]]]]:
    curves: dict[tuple[str, str, str], list[list[dict[str, Any]]]] = {}
    for dataset in datasets:
        for modality in MODALITIES:
            for strategy in STRATEGIES:
                runs: list[list[dict[str, Any]]] = []
                repetitions_path = _random_repetitions_path(dataset, modality) if strategy == "random" else None
                if repetitions_path is not None:
                    runs = _group_repetitions(_read_csv(repetitions_path))
                if not runs:
                    rows = _read_csv(_curve_path(dataset, modality, strategy))
                    if rows:
                        runs = [rows]
                if runs:
                    curves[(dataset, modality, strategy)] = runs
    return curves


def _missing_curve_keys(
    datasets: list[str],
    curves: dict[tuple[str, str, str], list[list[dict[str, Any]]]],
) -> list[tuple[str, str, str]]:
    return [
        (dataset, modality, strategy)
        for dataset in datasets
        for modality in MODALITIES
        for strategy in STRATEGIES
        if (dataset, modality, strategy) not in curves
    ]


def _curve_contract_errors(
    curves: dict[tuple[str, str, str], list[list[dict[str, Any]]]],
) -> list[str]:
    errors: list[str] = []
    for (dataset, modality, strategy), runs in sorted(curves.items()):
        required_fields = ["removed_fraction", *(field for _metric, field, _label in MODALITIES[modality]["metrics"])]
        for run_index, run in enumerate(runs, start=1):
            label = f"{dataset}/{modality}/{strategy}/run-{run_index}"
            if len(run) < 2:
                errors.append(f"{label}: curva com menos de dois pontos")
                continue
            fractions = [_as_float(row.get("removed_fraction")) for row in run]
            if any(value is None for value in fractions):
                errors.append(f"{label}: campo obrigatório ausente ou inválido: removed_fraction")
            valid_fractions = [value for value in fractions if value is not None]
            if valid_fractions != sorted(valid_fractions) or len(set(valid_fractions)) != len(valid_fractions):
                errors.append(f"{label}: removed_fraction deve ser estritamente crescente")
            if valid_fractions and not math.isclose(valid_fractions[0], 0.0, abs_tol=1e-12):
                errors.append(f"{label}: a curva deve começar em removed_fraction=0")
            if any(value < 0 or value > 1 for value in valid_fractions):
                errors.append(f"{label}: removed_fraction deve permanecer em [0,1]")
            for field in required_fields[1:]:
                values = [_as_float(row.get(field)) for row in run]
                if any(value is None for value in values):
                    errors.append(f"{label}: campo obrigatório ausente ou inválido: {field}")
                    continue
                valid_values = [value for value in values if value is not None]
                if any(value < -1e-9 or value > 1 + 1e-9 for value in valid_values):
                    errors.append(f"{label}: {field} deve permanecer em [0,1]")
                absolute_community_lcc = modality == "community" and field in {
                    "lcc_weighted_fraction",
                    "lcc_communities_fraction",
                }
                if valid_values and absolute_community_lcc and valid_values[0] <= 0:
                    errors.append(f"{label}: {field} deve iniciar em (0,1] no baseline")
                elif valid_values and not absolute_community_lcc and not math.isclose(
                    valid_values[0],
                    1.0,
                    abs_tol=1e-6,
                ):
                    errors.append(f"{label}: {field} deve iniciar em 1 no baseline")
                if any(right > left + 1e-9 for left, right in zip(valid_values, valid_values[1:])):
                    errors.append(f"{label}: {field} não pode aumentar após remoções")
    return errors


def _common_fractions(
    curves: dict[tuple[str, str, str], list[list[dict[str, Any]]]],
    requested_max_fraction: float | None,
) -> dict[str, float]:
    result: dict[str, float] = {}
    for modality in MODALITIES:
        maxima = []
        for (dataset_key, modality_key, strategy_key), runs in curves.items():
            del dataset_key, strategy_key
            if modality_key != modality:
                continue
            for run in runs:
                xs = [_as_float(row.get("removed_fraction")) for row in run]
                valid = [value for value in xs if value is not None]
                if valid:
                    maxima.append(max(valid))
        if maxima:
            common = min(maxima)
            if requested_max_fraction is not None:
                common = min(common, requested_max_fraction)
            if common > 0:
                result[modality] = common
    return result


def _mean_or_blank(values: list[float]) -> float | str:
    return statistics.mean(values) if values else ""


def _std_or_blank(values: list[float]) -> float | str:
    return statistics.stdev(values) if len(values) > 1 else ""


def _summarize(
    curves: dict[tuple[str, str, str], list[list[dict[str, Any]]]],
    common_fractions: dict[str, float],
    checkpoints: list[float],
    thresholds: list[float],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    for (dataset, modality, strategy), runs in sorted(curves.items()):
        max_fraction = common_fractions.get(modality)
        if max_fraction is None:
            continue
        for metric, field, metric_label in MODALITIES[modality]["metrics"]:
            candidate_points = [_series(run, field) for run in runs]
            cohort = [
                (points, auc)
                for points in candidate_points
                if points and (auc := _normalized_auc(points, max_fraction)) is not None
            ]
            run_points = [points for points, _auc in cohort]
            aucs = [auc for _points, auc in cohort]
            if not aucs:
                continue
            out: dict[str, Any] = {
                "dataset": dataset,
                "modality": modality,
                "modality_label": MODALITIES[modality]["label"],
                "strategy": strategy,
                "strategy_label": STRATEGY_LABELS[strategy],
                "metric": metric,
                "metric_label": metric_label,
                "analysis_max_fraction": max_fraction,
                "repetitions": len(aucs),
                "uncertainty_status": "estimated" if len(aucs) > 1 else "not_estimated",
                "auc_normalized_mean": statistics.mean(aucs),
                "auc_normalized_std": statistics.stdev(aucs) if len(aucs) > 1 else "",
                "auc_normalized_min": min(aucs),
                "auc_normalized_max": max(aucs),
            }
            ci_low, ci_high = _bootstrap_mean_interval(
                aucs,
                resamples=2000,
                seed=_derived_seed(42, dataset, modality, strategy, metric),
            )
            out["auc_ci95_bootstrap_low"] = ci_low if ci_low is not None else ""
            out["auc_ci95_bootstrap_high"] = ci_high if ci_high is not None else ""
            for checkpoint in checkpoints:
                label = _percentage_field_label(checkpoint)
                actual = min(checkpoint, max_fraction) if checkpoint - max_fraction <= 0.001 else None
                values = [
                    value
                    for points in run_points
                    if actual is not None and (value := _value_at(points, actual)) is not None
                ]
                initial_values = [value for points in run_points if (value := _value_at(points, 0.0)) is not None]
                losses = [initial - value for initial, value in zip(initial_values, values)] if len(initial_values) == len(values) else []
                out[f"checkpoint_{label}_actual_fraction"] = actual if actual is not None else ""
                out[f"value_at_{label}_mean"] = _mean_or_blank(values)
                out[f"value_at_{label}_std"] = _std_or_blank(values)
                out[f"loss_at_{label}_mean"] = _mean_or_blank(losses)
            for threshold in thresholds:
                label = f"{round(threshold * 100):g}pct"
                crossings = [
                    value
                    for points in run_points
                    if (value := _threshold_crossing(points, threshold, max_fraction)) is not None
                ]
                out[f"fraction_to_below_{label}_mean"] = _mean_or_blank(crossings)
                out[f"fraction_to_below_{label}_std"] = _std_or_blank(crossings)
                out[f"threshold_{label}_reached_runs"] = len(crossings)
            rows.append(out)
    random_auc = {
        (row["dataset"], row["modality"], row["metric"]): float(row["auc_normalized_mean"])
        for row in rows
        if row["strategy"] == "random"
    }
    for row in rows:
        baseline = random_auc.get((row["dataset"], row["modality"], row["metric"]))
        current = float(row["auc_normalized_mean"])
        if baseline is None:
            row["auc_delta_vs_random"] = ""
            row["auc_ratio_vs_random"] = ""
            row["damage_amplification_vs_random"] = ""
            continue
        row["auc_delta_vs_random"] = current - baseline
        row["auc_ratio_vs_random"] = current / baseline if baseline else ""
        row["damage_amplification_vs_random"] = (baseline - current) / baseline if baseline else ""
    return rows


def _plot_auc(path: Path, rows: list[dict[str, Any]], title: str) -> None:
    primary_rows = [row for row in rows if row["metric"] in PRIMARY_METRICS]
    if not primary_rows:
        return
    groups = sorted({(row["dataset"], row["modality"]) for row in primary_rows})
    fig, axes = plt.subplots(len(PRIMARY_METRICS), 1, figsize=(max(12, len(groups) * 1.7), 11), sharex=True)
    width = 0.25
    colors = {"random": "#4c78a8", "targeted": "#e45756", "targeted_adaptive": "#f2a541"}
    for axis, metric in zip(axes, PRIMARY_METRICS):
        metric_rows = [row for row in primary_rows if row["metric"] == metric]
        labels = []
        for index, (dataset, modality) in enumerate(groups):
            labels.append(f"{dataset}\n{MODALITIES[modality]['label']}")
            for offset, strategy in enumerate(STRATEGIES):
                selected = [
                    row for row in metric_rows
                    if row["dataset"] == dataset and row["modality"] == modality and row["strategy"] == strategy
                ]
                if not selected:
                    continue
                row = selected[0]
                x = index + (offset - 1) * width
                y = float(row["auc_normalized_mean"])
                error = _as_float(row.get("auc_normalized_std")) or 0.0
                axis.bar(
                    x,
                    y,
                    width=width,
                    color=colors[strategy],
                    label=STRATEGY_LABELS[strategy] if index == 0 else None,
                    yerr=error if error > 0 else None,
                    capsize=3,
                )
        label = next((row["metric_label"] for row in metric_rows), metric)
        axis.set_ylabel(f"AUC normalizada\n{label}")
        axis.set_ylim(0, 1.05)
        axis.grid(axis="y", alpha=0.25)
    axes[0].legend(ncol=3, loc="lower left")
    axes[-1].set_xticks(range(len(groups)), labels, rotation=35, ha="right")
    axes[-1].set_xlabel("Dataset e modalidade de remoção")
    fig.suptitle(title)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _plot_losses(path: Path, rows: list[dict[str, Any]], title: str, checkpoints: list[float]) -> None:
    primary_rows = [row for row in rows if row["metric"] in PRIMARY_METRICS]
    selected_checkpoints = sorted(set(checkpoints))
    if not primary_rows or not selected_checkpoints:
        return
    groups = sorted({(row["dataset"], row["modality"]) for row in primary_rows})
    fig, axes = plt.subplots(
        len(PRIMARY_METRICS),
        len(selected_checkpoints),
        figsize=(max(16, len(groups) * 1.8), 11),
        sharex=True,
        sharey="row",
        squeeze=False,
    )
    width = 0.25
    colors = {"random": "#4c78a8", "targeted": "#e45756", "targeted_adaptive": "#f2a541"}
    for row_index, metric in enumerate(PRIMARY_METRICS):
        metric_rows = [row for row in primary_rows if row["metric"] == metric]
        metric_label = next((row["metric_label"] for row in metric_rows), metric)
        for col_index, checkpoint in enumerate(selected_checkpoints):
            axis = axes[row_index][col_index]
            label = _percentage_field_label(checkpoint)
            field = f"loss_at_{label}_mean"
            std_field = f"value_at_{label}_std"
            for index, (dataset, modality) in enumerate(groups):
                for offset, strategy in enumerate(STRATEGIES):
                    selected = [
                        row for row in metric_rows
                        if row["dataset"] == dataset and row["modality"] == modality and row["strategy"] == strategy
                    ]
                    if not selected:
                        continue
                    value = _as_float(selected[0].get(field))
                    if value is None:
                        continue
                    error = _as_float(selected[0].get(std_field)) or 0.0
                    x = index + (offset - 1) * width
                    axis.bar(
                        x,
                        value,
                        width=width,
                        color=colors[strategy],
                        label=STRATEGY_LABELS[strategy] if row_index == 0 and col_index == 0 and index == 0 else None,
                        yerr=error if error > 0 else None,
                        capsize=3,
                    )
            axis.set_title(f"Remoção de {_percentage_display(checkpoint)}")
            axis.grid(axis="y", alpha=0.25)
            if col_index == 0:
                axis.set_ylabel(f"Perda\n{metric_label}")
            if row_index == len(PRIMARY_METRICS) - 1:
                axis.set_xticks(
                    range(len(groups)),
                    [f"{dataset}\n{MODALITIES[modality]['label']}" for dataset, modality in groups],
                    rotation=40,
                    ha="right",
                )
    axes[0][0].legend(ncol=3, loc="upper left")
    fig.suptitle(title)
    fig.tight_layout()
    path.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(path, dpi=180, bbox_inches="tight")
    plt.close(fig)


def _format_number(value: Any) -> str:
    parsed = _as_float(value)
    return f"{parsed:.4f}" if parsed is not None else "—"


def _write_html(
    path: Path,
    rows: list[dict[str, Any]],
    figure_path: Path,
    losses_path: Path,
    checkpoints: list[float],
) -> None:
    selected_checkpoints = sorted(set(checkpoints))
    checkpoint_headers = "".join(
        f"<th>Perda {html.escape(_percentage_display(checkpoint))}</th>"
        for checkpoint in selected_checkpoints
    )
    table_rows = []
    for row in rows:
        checkpoint_cells = "".join(
            f"<td>{_format_number(row.get(f'loss_at_{_percentage_field_label(checkpoint)}_mean'))}</td>"
            for checkpoint in selected_checkpoints
        )
        table_rows.append(
            "<tr>"
            f"<td>{html.escape(str(row['dataset']))}</td>"
            f"<td>{html.escape(str(row['modality_label']))}</td>"
            f"<td>{html.escape(str(row['strategy_label']))}</td>"
            f"<td>{html.escape(str(row['metric_label']))}</td>"
            f"<td>{_format_number(row['analysis_max_fraction'])}</td>"
            f"<td>{row['repetitions']}</td>"
            f"<td>{_format_number(row['auc_normalized_mean'])}</td>"
            f"<td>{_format_number(row['auc_normalized_std'])}</td>"
            f"<td>{html.escape(str(row['uncertainty_status']))}</td>"
            f"<td>{_format_number(row.get('auc_delta_vs_random'))}</td>"
            f"{checkpoint_cells}"
            f"<td>{_format_number(row.get('fraction_to_below_90pct_mean'))}</td>"
            "</tr>"
        )
    relative_figure = figure_path.name
    relative_losses = losses_path.name
    content = f"""<!doctype html>
<html lang="pt-BR"><head><meta charset="utf-8"><title>Síntese quantitativa da robustez</title>
<style>
body{{font-family:Arial,sans-serif;margin:32px;color:#1f2933}} table{{border-collapse:collapse;width:100%;font-size:13px}}
th,td{{border:1px solid #d8dee4;padding:7px;text-align:right}} th{{background:#eef2f6}} td:first-child,th:first-child{{text-align:left}}
.note{{background:#fff8db;border-left:4px solid #d5a000;padding:12px}} img{{max-width:100%;height:auto}}
</style></head><body>
<h1>Síntese quantitativa das curvas de robustez</h1>
<p>AUC normalizada maior indica maior retenção média da resposta no intervalo comum analisado. Modalidades são comparadas separadamente, pois usam frações máximas distintas.</p>
<div class="note">As barras de erro representam o desvio-padrão da AUC quando há repetições aleatórias. Ausência de barra não significa ausência de incerteza: estratégias dirigidas aproximadas ainda dependem dos parâmetros de amostragem.</div>
<p><img src="{html.escape(relative_figure)}" alt="Comparação das AUCs de robustez"></p>
<h2>Perdas em frações padronizadas</h2>
<p><img src="{html.escape(relative_losses)}" alt="Perdas de robustez em frações padronizadas"></p>
<table><thead><tr><th>Dataset</th><th>Modalidade</th><th>Estratégia</th><th>Resposta</th><th>Fração máxima</th><th>Repetições</th><th>AUC média</th><th>DP AUC</th><th>Incerteza</th><th>Delta vs. aleatória</th>{checkpoint_headers}<th>Fração até &lt;90%</th></tr></thead>
<tbody>{''.join(table_rows)}</tbody></table>
</body></html>"""
    path.write_text(content, encoding="utf-8")


def _write_city_report(path: Path, dataset: str, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "=== Síntese Quantitativa das Curvas de Robustez ===",
        "",
        f"Dataset: {dataset}",
        "AUC normalizada: média da resposta retida no intervalo comum analisado.",
        "Valores maiores indicam maior robustez estrutural para a resposta e estratégia consideradas.",
        "",
    ]
    for modality in MODALITIES:
        selected = [row for row in rows if row["modality"] == modality and row["metric"] in PRIMARY_METRICS]
        if not selected:
            continue
        lines.append(f"[{MODALITIES[modality]['label']}]")
        for row in selected:
            std_text = _format_number(row.get("auc_normalized_std"))
            lines.append(
                f"- {row['strategy_label']} | {row['metric_label']} | "
                f"AUC={float(row['auc_normalized_mean']):.4f} | "
                f"DP={std_text} | n={row['repetitions']} | "
                f"incerteza={row['uncertainty_status']}"
            )
        lines.append("")
    lines.extend(
        [
            "Notas metodológicas:",
            "- A integração é trapezoidal com interpolação linear.",
            "- Cada modalidade usa a maior fração comum entre todos os datasets e estratégias incluídos.",
            "- A incerteza é estimada somente quando existem curvas repetidas, atualmente nos ataques aleatórios por nós/arestas.",
            "- Campo vazio de DP/IC significa incerteza não estimada; não significa variância zero.",
            "- Robustez de nós, arestas e comunidades não deve ser combinada em um único ranking sem justificativa.",
            "",
        ]
    )
    path.write_text("\n".join(lines), encoding="utf-8")


def gerar_sintese_robustez(
    datasets: list[str],
    output_dir: str = "outputs/comparisons",
    max_fraction: float | None = None,
    checkpoints: list[float] | None = None,
    thresholds: list[float] | None = None,
    allow_incomplete: bool = False,
    city_output_root: str | None = None,
) -> dict[str, Any]:
    if not datasets:
        raise ValueError("Informe pelo menos um dataset.")
    checkpoints = checkpoints or [0.01, 0.05, 0.10, 0.15]
    thresholds = thresholds or [0.90, 0.75, 0.50]
    if max_fraction is not None and not 0 < max_fraction <= 1:
        raise ValueError("max_fraction deve estar no intervalo (0, 1].")
    if any(not 0 < value <= 1 for value in checkpoints + thresholds):
        raise ValueError("Checkpoints e limiares devem estar no intervalo (0, 1].")

    curves = _load_curves(datasets)
    if not curves:
        raise RuntimeError("Nenhuma curva de robustez foi encontrada para os datasets informados.")
    missing_curves = _missing_curve_keys(datasets, curves)
    if missing_curves and not allow_incomplete:
        preview = ", ".join("/".join(key) for key in missing_curves[:12])
        suffix = " ..." if len(missing_curves) > 12 else ""
        raise RuntimeError(
            "Matriz de curvas incompleta; gere todas as modalidades/estratégias ou use "
            f"allow_incomplete=True de forma explícita. Ausentes: {preview}{suffix}"
        )
    contract_errors = _curve_contract_errors(curves)
    if contract_errors:
        preview = "; ".join(contract_errors[:12])
        suffix = " ..." if len(contract_errors) > 12 else ""
        raise RuntimeError(f"Curvas de robustez inválidas: {preview}{suffix}")
    common_fractions = _common_fractions(curves, max_fraction)
    rows = _summarize(curves, common_fractions, sorted(set(checkpoints)), sorted(set(thresholds), reverse=True))

    output_root = Path(output_dir)
    canonical_comparison_root = Path("outputs/comparisons").resolve()
    if city_output_root is not None:
        city_root = Path(city_output_root)
    elif output_root.resolve() == canonical_comparison_root:
        city_root = Path("outputs")
    else:
        city_root = output_root / "datasets"
    comparison_csv = output_root / "robustness_comparison.csv"
    comparison_plot = output_root / "robustness_comparison.png"
    comparison_losses_plot = output_root / "robustness_losses.png"
    comparison_html = output_root / "robustness_comparison.html"
    _write_rows(comparison_csv, rows)
    _plot_auc(comparison_plot, rows, "Síntese quantitativa da robustez estrutural")
    _plot_losses(comparison_losses_plot, rows, "Perdas de robustez em frações padronizadas", checkpoints)
    _write_html(comparison_html, rows, comparison_plot, comparison_losses_plot, checkpoints)

    city_outputs: dict[str, dict[str, str]] = {}
    for dataset in datasets:
        city_rows = [row for row in rows if row["dataset"] == dataset]
        dataset_root = city_root / dataset
        metrics_path = dataset_root / "metrics/robustness_summary.csv"
        plot_path = dataset_root / "figures/robustness_summary_auc.png"
        losses_path = dataset_root / "figures/robustness_summary_losses.png"
        report_path = dataset_root / "logs/robustness_summary_report.txt"
        _write_rows(metrics_path, city_rows)
        _plot_auc(plot_path, city_rows, f"Síntese quantitativa da robustez - {dataset}")
        _plot_losses(losses_path, city_rows, f"Perdas de robustez - {dataset}", checkpoints)
        _write_city_report(report_path, dataset, city_rows)
        city_outputs[dataset] = {
            "summary_csv": str(metrics_path),
            "plot": str(plot_path),
            "losses_plot": str(losses_path),
            "report": str(report_path),
        }

    return {
        "datasets": datasets,
        "common_fractions": common_fractions,
        "missing_curves": ["/".join(key) for key in missing_curves],
        "curve_contract_errors": contract_errors,
        "complete_matrix": not missing_curves,
        "city_output_root": str(city_root),
        "comparison_csv": str(comparison_csv),
        "comparison_plot": str(comparison_plot),
        "comparison_losses_plot": str(comparison_losses_plot),
        "comparison_html": str(comparison_html),
        "city_outputs": city_outputs,
        "rows": len(rows),
    }
