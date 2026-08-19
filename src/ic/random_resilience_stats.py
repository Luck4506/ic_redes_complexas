from __future__ import annotations

import csv
import hashlib
import math
import random
import statistics
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt

from .node_resilience import testar_resiliencia_vertices
from .resilience import testar_resiliencia


AGGREGATE_FIELDS = [
    "removed_fraction",
    "lcc_fraction",
    "num_components",
    "efficiency_topological_retained",
    "efficiency_length_retained",
]


def _read_rows(path: str, seed: int, evaluation_seed: int) -> list[dict[str, Any]]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for index, row in enumerate(csv.DictReader(f)):
            row["seed"] = seed
            row["attack_seed"] = seed
            row["evaluation_seed"] = evaluation_seed
            row["step_index"] = index
            rows.append(row)
        return rows


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _quantile(values: list[float], probability: float) -> float:
    if not values:
        raise ValueError("Nao e possivel calcular quantil de uma lista vazia.")
    ordered = sorted(values)
    if len(ordered) == 1:
        return ordered[0]
    position = (len(ordered) - 1) * probability
    left = math.floor(position)
    right = math.ceil(position)
    if left == right:
        return ordered[left]
    weight = position - left
    return ordered[left] * (1.0 - weight) + ordered[right] * weight


def _derived_seed(base_seed: int, *parts: Any) -> int:
    payload = ":".join([str(base_seed), *(str(part) for part in parts)])
    digest = hashlib.sha256(payload.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big")


def _bootstrap_mean_interval(
    values: list[float],
    resamples: int,
    seed: int,
    confidence: float = 0.95,
) -> tuple[float | None, float | None]:
    if len(values) < 2 or resamples <= 0:
        return None, None
    rng = random.Random(seed)
    sample_size = len(values)
    means = [
        sum(rng.choice(values) for _ in range(sample_size)) / sample_size
        for _ in range(resamples)
    ]
    tail = (1.0 - confidence) / 2.0
    return _quantile(means, tail), _quantile(means, 1.0 - tail)


def _distribution_summary(
    values: list[float],
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, Any]:
    if not values:
        return {}
    std = statistics.stdev(values) if len(values) > 1 else None
    ci_low, ci_high = _bootstrap_mean_interval(values, bootstrap_resamples, bootstrap_seed)
    return {
        "mean": statistics.mean(values),
        "std": std if std is not None else "",
        "sem": (std / math.sqrt(len(values))) if std is not None else "",
        "median": statistics.median(values),
        "q025": _quantile(values, 0.025),
        "q25": _quantile(values, 0.25),
        "q75": _quantile(values, 0.75),
        "q975": _quantile(values, 0.975),
        "min": min(values),
        "max": max(values),
        "ci95_bootstrap_low": ci_low if ci_low is not None else "",
        "ci95_bootstrap_high": ci_high if ci_high is not None else "",
    }


def _aggregate_rows(
    rows: list[dict[str, Any]],
    bootstrap_resamples: int = 2000,
    bootstrap_seed: int = 42,
) -> list[dict[str, Any]]:
    by_step: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_step.setdefault(int(row["step_index"]), []).append(row)

    aggregated = []
    for step_index, step_rows in sorted(by_step.items()):
        out: dict[str, Any] = {
            "step_index": step_index,
            "runs": len(step_rows),
            "uncertainty_available": "yes" if len(step_rows) > 1 else "no",
            "recommended_min_runs": 30,
            "meets_recommended_runs": "yes" if len(step_rows) >= 30 else "no",
        }
        for field in AGGREGATE_FIELDS:
            values = [value for row in step_rows if (value := _as_float(row.get(field))) is not None]
            if not values:
                continue
            summary = _distribution_summary(
                values,
                bootstrap_resamples,
                _derived_seed(bootstrap_seed, step_index, field),
            )
            for statistic_name, value in summary.items():
                out[f"{field}_{statistic_name}"] = value
        aggregated.append(out)
    return aggregated


def _normalized_auc(rows: list[dict[str, Any]], field: str) -> float | None:
    points: dict[float, float] = {}
    for row in rows:
        x = _as_float(row.get("removed_fraction"))
        y = _as_float(row.get(field))
        if x is not None and y is not None:
            points[x] = y
    ordered = sorted(points.items())
    if len(ordered) < 2 or ordered[-1][0] <= ordered[0][0]:
        return None
    area = sum(
        (right_x - left_x) * (left_y + right_y) / 2.0
        for (left_x, left_y), (right_x, right_y) in zip(ordered, ordered[1:])
    )
    return area / (ordered[-1][0] - ordered[0][0])


def _auc_rows(
    rows: list[dict[str, Any]],
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> list[dict[str, Any]]:
    by_seed: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_seed.setdefault(int(row["attack_seed"]), []).append(row)

    metrics = [
        ("lcc_fraction", "lcc"),
        ("efficiency_topological_retained", "efficiency_topological"),
        ("efficiency_length_retained", "efficiency_length"),
    ]
    output: list[dict[str, Any]] = []
    values_by_metric: dict[str, list[float]] = {metric: [] for _field, metric in metrics}
    for attack_seed, run_rows in sorted(by_seed.items()):
        evaluation_seed = run_rows[0].get("evaluation_seed", "")
        for field, metric in metrics:
            value = _normalized_auc(run_rows, field)
            if value is None:
                continue
            values_by_metric[metric].append(value)
            output.append(
                {
                    "row_type": "run",
                    "metric": metric,
                    "attack_seed": attack_seed,
                    "evaluation_seed": evaluation_seed,
                    "runs": 1,
                    "auc_normalized": value,
                    "mean": "",
                    "std": "",
                    "sem": "",
                    "median": "",
                    "q025": "",
                    "q25": "",
                    "q75": "",
                    "q975": "",
                    "min": "",
                    "max": "",
                    "ci95_bootstrap_low": "",
                    "ci95_bootstrap_high": "",
                }
            )
    for metric, values in values_by_metric.items():
        summary = _distribution_summary(
            values,
            bootstrap_resamples,
            _derived_seed(bootstrap_seed, "auc", metric),
        )
        if not summary:
            continue
        output.append(
            {
                "row_type": "summary",
                "metric": metric,
                "attack_seed": "",
                "evaluation_seed": next(iter(by_seed.values()))[0].get("evaluation_seed", "") if by_seed else "",
                "runs": len(values),
                "auc_normalized": "",
                **summary,
            }
        )
    return output


def _resolve_attack_seeds(
    seeds: list[int] | None,
    repetitions: int | None,
    master_seed: int,
) -> list[int]:
    if seeds is not None:
        if repetitions is not None:
            raise ValueError("Use seeds explícitas ou repetitions, não ambos.")
        if not seeds:
            raise ValueError("Informe pelo menos uma semente.")
        if len(set(seeds)) != len(seeds):
            raise ValueError("As sementes de ataque devem ser únicas.")
        return list(seeds)
    count = 30 if repetitions is None else repetitions
    if not 1 <= count <= 10_000:
        raise ValueError("repetitions deve estar entre 1 e 10000.")
    return random.Random(master_seed).sample(range(1, 2**31 - 1), count)


def _write_dict_rows(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def _plot_aggregate(path: Path, rows: list[dict[str, Any]], title: str) -> None:
    xs = [float(row["removed_fraction_mean"]) for row in rows]
    lcc = [float(row["lcc_fraction_mean"]) for row in rows]
    eff = [float(row["efficiency_topological_retained_mean"]) for row in rows]

    plt.figure()
    plt.plot(xs, lcc, marker="o", label="LCC media")
    if all(row.get("lcc_fraction_ci95_bootstrap_low") not in (None, "") for row in rows):
        lcc_low = [float(row["lcc_fraction_ci95_bootstrap_low"]) for row in rows]
        lcc_high = [float(row["lcc_fraction_ci95_bootstrap_high"]) for row in rows]
        plt.fill_between(xs, lcc_low, lcc_high, alpha=0.18, label="IC 95% bootstrap da media da LCC")
    plt.plot(xs, eff, marker="s", label="Eficiencia topologica media")
    plt.xlabel("Fração removida")
    plt.ylabel("Fração retida")
    plt.title(title)
    plt.grid(True, alpha=0.3)
    plt.legend()
    plt.savefig(path, dpi=150, bbox_inches="tight")
    plt.close()


def _run_edge(
    city_id: str,
    seeds: list[int],
    max_fraction: float,
    steps: int,
    k_edge: int,
    efficiency_samples: int,
    evaluation_seed: int,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, str]:
    all_rows: list[dict[str, Any]] = []
    for seed in seeds:
        result = testar_resiliencia(
            city_id=city_id,
            strategy="random",
            max_fraction=max_fraction,
            steps=steps,
            k_edge=k_edge,
            efficiency_samples=efficiency_samples,
            seed=seed,
            evaluation_seed=evaluation_seed,
            output_suffix=f"random_seed_{seed}",
        )
        all_rows.extend(_read_rows(result["curve_csv"], seed, evaluation_seed))

    metrics_dir = Path(f"outputs/{city_id}/metrics")
    figures_dir = Path(f"outputs/{city_id}/figures")
    logs_dir = Path(f"outputs/{city_id}/logs")
    detailed_csv = metrics_dir / "resilience_random_repetitions.csv"
    aggregate_csv = metrics_dir / "resilience_random_aggregate.csv"
    auc_csv = metrics_dir / "resilience_random_auc.csv"
    plot_path = figures_dir / "resilience_random_aggregate.png"
    report_txt = logs_dir / "resilience_random_aggregate_report.txt"

    aggregate = _aggregate_rows(all_rows, bootstrap_resamples, bootstrap_seed)
    auc_rows = _auc_rows(all_rows, bootstrap_resamples, bootstrap_seed)
    _write_dict_rows(detailed_csv, all_rows)
    _write_dict_rows(aggregate_csv, aggregate)
    _write_dict_rows(auc_csv, auc_rows)
    _plot_aggregate(plot_path, aggregate, f"Robustez estrutural aleatória por arestas ({city_id})")

    report_txt.write_text(
        "\n".join(
            [
                "=== Robustez Estrutural Aleatória Agregada por Arestas ===",
                "",
                f"Dataset: {city_id}",
                f"Sementes: {', '.join(str(seed) for seed in seeds)}",
                f"Repetições: {len(seeds)}",
                f"evaluation_seed fixa: {evaluation_seed}",
                f"max_fraction: {max_fraction}",
                f"steps: {steps}",
                f"k_edge: {k_edge}",
                f"efficiency_samples: {efficiency_samples}",
                f"bootstrap_resamples: {bootstrap_resamples}",
                f"CSV detalhado: {detailed_csv}",
                f"CSV agregado: {aggregate_csv}",
                f"CSV AUC: {auc_csv}",
                f"Figura: {plot_path}",
                "A incerteza reflete a ordem aleatória do ataque; as fontes da eficiência ficam fixas.",
                (
                    "AVISO: menos de 30 repetições; trate os intervalos como exploratórios."
                    if len(seeds) < 30
                    else "Mínimo recomendado de 30 repetições atendido."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "detailed_csv": str(detailed_csv),
        "aggregate_csv": str(aggregate_csv),
        "auc_csv": str(auc_csv),
        "plot": str(plot_path),
        "report": str(report_txt),
    }


def _run_node(
    city_id: str,
    seeds: list[int],
    max_fraction: float,
    steps: int,
    k_node: int,
    efficiency_samples: int,
    evaluation_seed: int,
    bootstrap_resamples: int,
    bootstrap_seed: int,
) -> dict[str, str]:
    all_rows: list[dict[str, Any]] = []
    for seed in seeds:
        result = testar_resiliencia_vertices(
            city_id=city_id,
            strategy="random",
            max_fraction=max_fraction,
            steps=steps,
            k_node=k_node,
            efficiency_samples=efficiency_samples,
            seed=seed,
            evaluation_seed=evaluation_seed,
            output_suffix=f"random_seed_{seed}",
        )
        all_rows.extend(_read_rows(result["curve_csv"], seed, evaluation_seed))

    metrics_dir = Path(f"outputs/{city_id}/metrics")
    figures_dir = Path(f"outputs/{city_id}/figures")
    logs_dir = Path(f"outputs/{city_id}/logs")
    detailed_csv = metrics_dir / "node_resilience_random_repetitions.csv"
    aggregate_csv = metrics_dir / "node_resilience_random_aggregate.csv"
    auc_csv = metrics_dir / "node_resilience_random_auc.csv"
    plot_path = figures_dir / "node_resilience_random_aggregate.png"
    report_txt = logs_dir / "node_resilience_random_aggregate_report.txt"

    aggregate = _aggregate_rows(all_rows, bootstrap_resamples, bootstrap_seed)
    auc_rows = _auc_rows(all_rows, bootstrap_resamples, bootstrap_seed)
    _write_dict_rows(detailed_csv, all_rows)
    _write_dict_rows(aggregate_csv, aggregate)
    _write_dict_rows(auc_csv, auc_rows)
    _plot_aggregate(plot_path, aggregate, f"Robustez estrutural aleatória por vértices ({city_id})")

    report_txt.write_text(
        "\n".join(
            [
                "=== Robustez Estrutural Aleatória Agregada por Vértices ===",
                "",
                f"Dataset: {city_id}",
                f"Sementes: {', '.join(str(seed) for seed in seeds)}",
                f"Repetições: {len(seeds)}",
                f"evaluation_seed fixa: {evaluation_seed}",
                f"max_fraction: {max_fraction}",
                f"steps: {steps}",
                f"k_node: {k_node}",
                f"efficiency_samples: {efficiency_samples}",
                f"bootstrap_resamples: {bootstrap_resamples}",
                f"CSV detalhado: {detailed_csv}",
                f"CSV agregado: {aggregate_csv}",
                f"CSV AUC: {auc_csv}",
                f"Figura: {plot_path}",
                "A incerteza reflete a ordem aleatória do ataque; as fontes da eficiência ficam fixas.",
                (
                    "AVISO: menos de 30 repetições; trate os intervalos como exploratórios."
                    if len(seeds) < 30
                    else "Mínimo recomendado de 30 repetições atendido."
                ),
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {
        "detailed_csv": str(detailed_csv),
        "aggregate_csv": str(aggregate_csv),
        "auc_csv": str(auc_csv),
        "plot": str(plot_path),
        "report": str(report_txt),
    }


def gerar_estatisticas_resiliencia_aleatoria(
    city_id: str,
    mode: str = "both",
    seeds: list[int] | None = None,
    repetitions: int | None = None,
    master_seed: int = 42,
    evaluation_seed: int = 104729,
    max_fraction: float = 0.15,
    steps: int = 15,
    k_edge: int = 80,
    k_node: int = 80,
    efficiency_samples: int = 20,
    bootstrap_resamples: int = 2000,
) -> dict[str, Any]:
    if mode not in {"edge", "node", "both"}:
        raise ValueError("mode deve ser 'edge', 'node' ou 'both'.")
    seeds = _resolve_attack_seeds(seeds, repetitions, master_seed)
    if bootstrap_resamples < 0:
        raise ValueError("bootstrap_resamples deve ser maior ou igual a zero.")

    result: dict[str, Any] = {
        "city_id": city_id,
        "mode": mode,
        "seeds": seeds,
        "repetitions": len(seeds),
        "master_seed": master_seed,
        "evaluation_seed": evaluation_seed,
        "bootstrap_resamples": bootstrap_resamples,
    }
    if mode in {"edge", "both"}:
        result["edge"] = _run_edge(
            city_id,
            seeds,
            max_fraction,
            steps,
            k_edge,
            efficiency_samples,
            evaluation_seed,
            bootstrap_resamples,
            master_seed,
        )
    if mode in {"node", "both"}:
        result["node"] = _run_node(
            city_id,
            seeds,
            max_fraction,
            steps,
            k_node,
            efficiency_samples,
            evaluation_seed,
            bootstrap_resamples,
            master_seed,
        )
    return result
