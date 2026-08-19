from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import networkx as nx

from .io_utils import dataset_graph_path, ensure_city_dirs, load_graphml
from .metric_graphs import approximate_global_efficiency, simple_undirected_min_length_graph


def _largest_cc_stats(G: nx.Graph) -> Tuple[int, int]:
    """Retorna (size_lcc, num_components)."""
    if G.number_of_nodes() == 0:
        return 0, 0
    comps = list(nx.connected_components(G))
    if not comps:
        return 0, 0
    size_lcc = max(len(c) for c in comps)
    return size_lcc, len(comps)


def _efficiency_retained(current: float, initial: float) -> float:
    return current / initial if initial > 0 else 0.0


def _static_removal_order(G: nx.Graph, strategy: str, k_edge: int, seed: int, rng: random.Random) -> list[tuple]:
    edges = list(G.edges())
    if not edges:
        return []
    if strategy == "random":
        rng.shuffle(edges)
        print("[E7] Estratégia: random", flush=True)
        return edges

    k = max(1, min(k_edge, G.number_of_nodes()))
    print(f"[E7] Estratégia: targeted (edge betweenness aprox estático, k={k})", flush=True)
    eb = nx.edge_betweenness_centrality(G, k=k, normalized=True, seed=seed)
    return [e for e, _ in sorted(eb.items(), key=lambda x: x[1], reverse=True)]


def _remove_adaptive_batch(G: nx.Graph, batch_size: int, k_edge: int, seed: int) -> int:
    if batch_size <= 0 or G.number_of_edges() == 0:
        return 0

    k = max(1, min(k_edge, G.number_of_nodes()))
    eb = nx.edge_betweenness_centrality(G, k=k, normalized=True, seed=seed)
    selected = [e for e, _ in sorted(eb.items(), key=lambda x: x[1], reverse=True)[:batch_size]]
    G.remove_edges_from(selected)
    return len(selected)


def testar_resiliencia(
    city_id: str,
    strategy: str = "targeted",
    max_fraction: float = 0.15,
    steps: int = 15,
    k_edge: int = 80,
    efficiency_samples: int = 20,
    seed: int = 42,
    evaluation_seed: int | None = None,
    output_suffix: str | None = None,
) -> dict:
    """
    E7: Remove arestas e mede fragmentação.
    strategy:
      - 'targeted': remove arestas com maior edge-betweenness (aprox)
      - 'targeted_adaptive': recalcula edge-betweenness a cada ponto da curva
      - 'random'  : remove arestas aleatórias

    Saídas:
      outputs/<city>/metrics/resilience_curve.csv
      outputs/<city>/figures/resilience_curve.png
      outputs/<city>/logs/resilience_report.txt
    """
    ensure_city_dirs(city_id)
    rng = random.Random(seed)
    evaluation_seed = seed if evaluation_seed is None else evaluation_seed

    grafo_path = str(dataset_graph_path(city_id, "clean"))
    print(f"[E7] Carregando grafo: {grafo_path}", flush=True)
    G_dir = load_graphml(grafo_path)

    if not 0 < max_fraction <= 1:
        raise ValueError("max_fraction deve estar no intervalo (0, 1].")

    # Robustez estrutural -> undirected simples, preservando menor length
    Gu = simple_undirected_min_length_graph(G_dir)
    if not nx.is_connected(Gu):
        largest_cc = max(nx.connected_components(Gu), key=len)
        G0 = Gu.subgraph(largest_cc).copy()
        used_cc = True
    else:
        G0 = Gu
        used_cc = False

    n0 = G0.number_of_nodes()
    m0 = G0.number_of_edges()
    print(f"[E7] Grafo base: nós={n0} arestas={m0} | maior componente? {'SIM' if used_cc else 'NÃO'}", flush=True)

    # Define ordem de remoção de arestas
    if strategy in {"random", "targeted"}:
        removal_order = _static_removal_order(G0, strategy, k_edge, seed, rng)
    elif strategy == "targeted_adaptive":
        removal_order = []
        print(f"[E7] Estratégia: targeted_adaptive (recalcula por ponto, k_edge={k_edge})", flush=True)
    else:
        raise ValueError("strategy deve ser 'random', 'targeted' ou 'targeted_adaptive'.")

    # Pontos na curva
    max_remove = int(max_fraction * m0)
    max_remove = max(1, max_remove)
    steps = max(2, steps)

    removals = [int(round(i * max_remove / (steps - 1))) for i in range(steps)]
    removals = sorted(set(removals))  # remove duplicados

    # Rodar simulação incremental
    G = G0.copy()
    removed = 0

    registros: List[Dict[str, float]] = []

    # estado inicial
    size_lcc, num_comp = _largest_cc_stats(G)
    eff0 = approximate_global_efficiency(G, samples=efficiency_samples, seed=evaluation_seed)
    eff_len0 = approximate_global_efficiency(
        G,
        samples=efficiency_samples,
        seed=evaluation_seed,
        weight="length",
    )
    registros.append(
        {
            "removed_edges": 0,
            "removed_fraction": 0.0,
            "lcc_size": size_lcc,
            "lcc_fraction": size_lcc / n0 if n0 else 0.0,
            "num_components": num_comp,
            "efficiency_approx": eff0,
            "efficiency_topological_approx": eff0,
            "efficiency_topological_retained": 1.0,
            "efficiency_length_approx": eff_len0,
            "efficiency_length_retained": 1.0,
        }
    )

    # remoções
    for target_removed in removals[1:]:
        if strategy == "targeted_adaptive":
            removed += _remove_adaptive_batch(G, target_removed - removed, k_edge, seed)
        else:
            while removed < target_removed and removed < len(removal_order):
                u, v = removal_order[removed]
                if G.has_edge(u, v):
                    G.remove_edge(u, v)
                removed += 1

        size_lcc, num_comp = _largest_cc_stats(G)
        eff = approximate_global_efficiency(G, samples=efficiency_samples, seed=evaluation_seed)
        eff_len = approximate_global_efficiency(
            G,
            samples=efficiency_samples,
            seed=evaluation_seed,
            weight="length",
        )

        registros.append(
            {
                "removed_edges": removed,
                "removed_fraction": removed / m0 if m0 else 0.0,
                "lcc_size": size_lcc,
                "lcc_fraction": size_lcc / n0 if n0 else 0.0,
                "num_components": num_comp,
                "efficiency_approx": eff,
                "efficiency_topological_approx": eff,
                "efficiency_topological_retained": _efficiency_retained(eff, eff0),
                "efficiency_length_approx": eff_len,
                "efficiency_length_retained": _efficiency_retained(eff_len, eff_len0),
            }
        )
        print(
            f"[E7] removidas={removed}/{m0} | LCC={size_lcc} ({size_lcc/n0:.3f}) "
            f"| comps={num_comp} | eff_topo≈{eff:.4f} | eff_len_retida≈{_efficiency_retained(eff_len, eff_len0):.4f}",
            flush=True,
        )

    # salvar outputs
    pasta_metrics = f"outputs/{city_id}/metrics"
    pasta_fig = f"outputs/{city_id}/figures"
    pasta_logs = f"outputs/{city_id}/logs"
    Path(pasta_metrics).mkdir(parents=True, exist_ok=True)
    Path(pasta_fig).mkdir(parents=True, exist_ok=True)
    Path(pasta_logs).mkdir(parents=True, exist_ok=True)

    suffix = output_suffix or strategy
    curve_csv = f"{pasta_metrics}/resilience_curve_{suffix}.csv"
    curve_plot = f"{pasta_fig}/resilience_curve_{suffix}.png"
    report_txt = f"{pasta_logs}/resilience_report_{suffix}.txt"

    with open(curve_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(registros[0].keys()))
        for r in registros:
            w.writerow([r[k] for k in registros[0].keys()])

    # Plot (matplotlib)
    xs = [r["removed_fraction"] for r in registros]
    ys = [r["lcc_fraction"] for r in registros]
    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Fração de arestas removidas")
    plt.ylabel("Fração da maior componente (LCC)")
    plt.title(f"Robustez estrutural por remoção de arestas ({city_id}) — {strategy}")
    plt.grid(True)
    plt.savefig(curve_plot, dpi=150, bbox_inches="tight")
    plt.close()

    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("=== Robustez Estrutural por Remoção de Arestas (E7) ===\n\n")
        f.write(f"Entrada: {grafo_path}\n")
        f.write(f"Grafo analisado: nós={n0} arestas={m0}\n")
        f.write(f"Estratégia: {strategy}\n")
        f.write(f"Max fraction removida: {max_fraction}\n")
        f.write(f"Steps: {steps}\n")
        f.write(f"k_edge (targeted): {k_edge}\n")
        f.write(f"efficiency_samples: {efficiency_samples}\n")
        f.write(f"attack_seed: {seed}\n")
        f.write(f"evaluation_seed: {evaluation_seed}\n\n")
        f.write("Notas metodológicas:\n")
        f.write("  - Grafo: simples, não-direcionado, maior componente conectada.\n")
        f.write("  - Arestas paralelas são colapsadas mantendo o menor length.\n")
        f.write("  - efficiency_approx é topológica e conta pares desconectados como zero.\n")
        f.write("  - efficiency_length_approx usa distância em metros; compare principalmente a fração retida.\n")
        f.write("  - A semente do ataque é separada da semente usada para amostrar a eficiência.\n")
        if strategy == "targeted":
            f.write("  - targeted usa ranking estático de edge betweenness inicial.\n")
        elif strategy == "targeted_adaptive":
            f.write("  - targeted_adaptive recalcula edge betweenness a cada ponto da curva.\n")
        f.write("\n")
        f.write("Último ponto:\n")
        last = registros[-1]
        for k, v in last.items():
            f.write(f"  {k} = {v}\n")

    print("[E7] Pronto ✅", flush=True)

    return {
        "curve_csv": curve_csv,
        "curve_plot": curve_plot,
        "report_txt": report_txt,
    }
