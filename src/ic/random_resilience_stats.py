from __future__ import annotations

import csv
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


def _read_rows(path: str, seed: int) -> list[dict[str, Any]]:
    with open(path, newline="", encoding="utf-8") as f:
        rows = []
        for index, row in enumerate(csv.DictReader(f)):
            row["seed"] = seed
            row["step_index"] = index
            rows.append(row)
        return rows


def _as_float(value: Any) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _aggregate_rows(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_step: dict[int, list[dict[str, Any]]] = {}
    for row in rows:
        by_step.setdefault(int(row["step_index"]), []).append(row)

    aggregated = []
    for step_index, step_rows in sorted(by_step.items()):
        out: dict[str, Any] = {
            "step_index": step_index,
            "runs": len(step_rows),
        }
        for field in AGGREGATE_FIELDS:
            values = [value for row in step_rows if (value := _as_float(row.get(field))) is not None]
            if not values:
                continue
            out[f"{field}_mean"] = statistics.mean(values)
            out[f"{field}_std"] = statistics.stdev(values) if len(values) > 1 else 0.0
            out[f"{field}_min"] = min(values)
            out[f"{field}_max"] = max(values)
        aggregated.append(out)
    return aggregated


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
    lcc_min = [float(row["lcc_fraction_min"]) for row in rows]
    lcc_max = [float(row["lcc_fraction_max"]) for row in rows]
    eff = [float(row["efficiency_topological_retained_mean"]) for row in rows]

    plt.figure()
    plt.plot(xs, lcc, marker="o", label="LCC media")
    plt.fill_between(xs, lcc_min, lcc_max, alpha=0.18, label="LCC min-max")
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
            output_suffix=f"random_seed_{seed}",
        )
        all_rows.extend(_read_rows(result["curve_csv"], seed))

    metrics_dir = Path(f"outputs/{city_id}/metrics")
    figures_dir = Path(f"outputs/{city_id}/figures")
    logs_dir = Path(f"outputs/{city_id}/logs")
    detailed_csv = metrics_dir / "resilience_random_repetitions.csv"
    aggregate_csv = metrics_dir / "resilience_random_aggregate.csv"
    plot_path = figures_dir / "resilience_random_aggregate.png"
    report_txt = logs_dir / "resilience_random_aggregate_report.txt"

    aggregate = _aggregate_rows(all_rows)
    _write_dict_rows(detailed_csv, all_rows)
    _write_dict_rows(aggregate_csv, aggregate)
    _plot_aggregate(plot_path, aggregate, f"Resiliência aleatória por arestas ({city_id})")

    report_txt.write_text(
        "\n".join(
            [
                "=== Resiliência Aleatória Agregada por Arestas ===",
                "",
                f"Dataset: {city_id}",
                f"Sementes: {', '.join(str(seed) for seed in seeds)}",
                f"max_fraction: {max_fraction}",
                f"steps: {steps}",
                f"k_edge: {k_edge}",
                f"efficiency_samples: {efficiency_samples}",
                f"CSV detalhado: {detailed_csv}",
                f"CSV agregado: {aggregate_csv}",
                f"Figura: {plot_path}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"detailed_csv": str(detailed_csv), "aggregate_csv": str(aggregate_csv), "plot": str(plot_path), "report": str(report_txt)}


def _run_node(
    city_id: str,
    seeds: list[int],
    max_fraction: float,
    steps: int,
    k_node: int,
    efficiency_samples: int,
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
            output_suffix=f"random_seed_{seed}",
        )
        all_rows.extend(_read_rows(result["curve_csv"], seed))

    metrics_dir = Path(f"outputs/{city_id}/metrics")
    figures_dir = Path(f"outputs/{city_id}/figures")
    logs_dir = Path(f"outputs/{city_id}/logs")
    detailed_csv = metrics_dir / "node_resilience_random_repetitions.csv"
    aggregate_csv = metrics_dir / "node_resilience_random_aggregate.csv"
    plot_path = figures_dir / "node_resilience_random_aggregate.png"
    report_txt = logs_dir / "node_resilience_random_aggregate_report.txt"

    aggregate = _aggregate_rows(all_rows)
    _write_dict_rows(detailed_csv, all_rows)
    _write_dict_rows(aggregate_csv, aggregate)
    _plot_aggregate(plot_path, aggregate, f"Resiliência aleatória por vértices ({city_id})")

    report_txt.write_text(
        "\n".join(
            [
                "=== Resiliência Aleatória Agregada por Vértices ===",
                "",
                f"Dataset: {city_id}",
                f"Sementes: {', '.join(str(seed) for seed in seeds)}",
                f"max_fraction: {max_fraction}",
                f"steps: {steps}",
                f"k_node: {k_node}",
                f"efficiency_samples: {efficiency_samples}",
                f"CSV detalhado: {detailed_csv}",
                f"CSV agregado: {aggregate_csv}",
                f"Figura: {plot_path}",
                "",
            ]
        ),
        encoding="utf-8",
    )
    return {"detailed_csv": str(detailed_csv), "aggregate_csv": str(aggregate_csv), "plot": str(plot_path), "report": str(report_txt)}


def gerar_estatisticas_resiliencia_aleatoria(
    city_id: str,
    mode: str = "both",
    seeds: list[int] | None = None,
    max_fraction: float = 0.15,
    steps: int = 15,
    k_edge: int = 80,
    k_node: int = 80,
    efficiency_samples: int = 20,
) -> dict[str, Any]:
    if mode not in {"edge", "node", "both"}:
        raise ValueError("mode deve ser 'edge', 'node' ou 'both'.")
    seeds = seeds or [42, 43, 44, 45, 46]
    if not seeds:
        raise ValueError("Informe pelo menos uma semente.")

    result: dict[str, Any] = {"city_id": city_id, "mode": mode, "seeds": seeds}
    if mode in {"edge", "both"}:
        result["edge"] = _run_edge(city_id, seeds, max_fraction, steps, k_edge, efficiency_samples)
    if mode in {"node", "both"}:
        result["node"] = _run_node(city_id, seeds, max_fraction, steps, k_node, efficiency_samples)
    return result
