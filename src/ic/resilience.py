from __future__ import annotations

import csv
import math
import random
from pathlib import Path
from typing import Dict, List, Tuple

import matplotlib.pyplot as plt
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml


def _largest_cc_stats(G: nx.Graph) -> Tuple[int, int]:
    """Retorna (size_lcc, num_components)."""
    if G.number_of_nodes() == 0:
        return 0, 0
    comps = list(nx.connected_components(G))
    if not comps:
        return 0, 0
    size_lcc = max(len(c) for c in comps)
    return size_lcc, len(comps)


def _approx_efficiency(G: nx.Graph, samples: int = 20, seed: int = 42) -> float:
    """
    Eficiência global aproximada:
      E = média_{i!=j} 1/d(i,j)
    Aproximamos amostrando alguns nós e rodando BFS (unweighted).
    """
    if G.number_of_nodes() < 2:
        return 0.0
    rng = random.Random(seed)
    nodes = list(G.nodes())
    sample_nodes = nodes if len(nodes) <= samples else rng.sample(nodes, samples)

    total = 0.0
    count = 0

    for s in sample_nodes:
        dist = nx.single_source_shortest_path_length(G, s)
        for t, d in dist.items():
            if t == s:
                continue
            if d > 0:
                total += 1.0 / float(d)
                count += 1

    return total / count if count else 0.0


def testar_resiliencia(
    city_id: str,
    strategy: str = "targeted",
    max_fraction: float = 0.15,
    steps: int = 15,
    k_edge: int = 80,
    efficiency_samples: int = 20,
    seed: int = 42,
) -> dict:
    """
    E7: Remove arestas e mede fragmentação.
    strategy:
      - 'targeted': remove arestas com maior edge-betweenness (aprox)
      - 'random'  : remove arestas aleatórias

    Saídas:
      outputs/<city>/metrics/resilience_curve.csv
      outputs/<city>/figures/resilience_curve.png
      outputs/<city>/logs/resilience_report.txt
    """
    ensure_city_dirs(city_id)
    rng = random.Random(seed)

    grafo_path = f"data/graphs/{city_id}_drive_clean.graphml"
    print(f"[E7] Carregando grafo: {grafo_path}", flush=True)
    G_dir = load_graphml(grafo_path)

    # Resiliência estrutural -> undirected simples
    Gu = nx.Graph(G_dir.to_undirected())
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
    edges = list(G0.edges())
    if strategy == "random":
        rng.shuffle(edges)
        removal_order = edges
        print("[E7] Estratégia: random", flush=True)
    elif strategy == "targeted":
        # Edge betweenness é pesado -> usamos aproximação por amostra
        k = min(k_edge, n0)
        print(f"[E7] Estratégia: targeted (edge betweenness aprox, k={k})", flush=True)
        eb = nx.edge_betweenness_centrality(G0, k=k, normalized=True, seed=seed)
        # Ordena do maior para o menor
        removal_order = [e for e, _ in sorted(eb.items(), key=lambda x: x[1], reverse=True)]
    else:
        raise ValueError("strategy deve ser 'random' ou 'targeted'.")

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
    eff0 = _approx_efficiency(G, samples=efficiency_samples, seed=seed)
    registros.append(
        {
            "removed_edges": 0,
            "removed_fraction": 0.0,
            "lcc_size": size_lcc,
            "lcc_fraction": size_lcc / n0 if n0 else 0.0,
            "num_components": num_comp,
            "efficiency_approx": eff0,
        }
    )

    # remoções
    for target_removed in removals[1:]:
        while removed < target_removed and removed < len(removal_order):
            u, v = removal_order[removed]
            if G.has_edge(u, v):
                G.remove_edge(u, v)
            removed += 1

        size_lcc, num_comp = _largest_cc_stats(G)
        eff = _approx_efficiency(G, samples=efficiency_samples, seed=seed)

        registros.append(
            {
                "removed_edges": removed,
                "removed_fraction": removed / m0 if m0 else 0.0,
                "lcc_size": size_lcc,
                "lcc_fraction": size_lcc / n0 if n0 else 0.0,
                "num_components": num_comp,
                "efficiency_approx": eff,
            }
        )
        print(f"[E7] removidas={removed}/{m0} | LCC={size_lcc} ({size_lcc/n0:.3f}) | comps={num_comp} | eff≈{eff:.4f}", flush=True)

    # salvar outputs
    pasta_metrics = f"outputs/{city_id}/metrics"
    pasta_fig = f"outputs/{city_id}/figures"
    pasta_logs = f"outputs/{city_id}/logs"
    Path(pasta_metrics).mkdir(parents=True, exist_ok=True)
    Path(pasta_fig).mkdir(parents=True, exist_ok=True)
    Path(pasta_logs).mkdir(parents=True, exist_ok=True)

    curve_csv = f"{pasta_metrics}/resilience_curve_{strategy}.csv"
    curve_plot = f"{pasta_fig}/resilience_curve_{strategy}.png"
    report_txt = f"{pasta_logs}/resilience_report_{strategy}.txt"

    with open(curve_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(list(registros[0].keys()))
        for r in registros:
            w.writerow([r[k] for k in registros[0].keys()])

    # Plot (matplotlib)
    xs = [r["removed_fraction"] for r in registros]
    ys = [r["lcc_fraction"] for r in registros]
    effs = [r["efficiency_approx"] for r in registros]

    plt.figure()
    plt.plot(xs, ys, marker="o")
    plt.xlabel("Fração de arestas removidas")
    plt.ylabel("Fração da maior componente (LCC)")
    plt.title(f"Resiliência ({city_id}) — {strategy}")
    plt.grid(True)
    plt.savefig(curve_plot, dpi=150, bbox_inches="tight")
    plt.close()

    with open(report_txt, "w", encoding="utf-8") as f:
        f.write("=== Resiliência (E7) ===\n\n")
        f.write(f"Entrada: {grafo_path}\n")
        f.write(f"Grafo analisado: nós={n0} arestas={m0}\n")
        f.write(f"Estratégia: {strategy}\n")
        f.write(f"Max fraction removida: {max_fraction}\n")
        f.write(f"Steps: {steps}\n")
        f.write(f"k_edge (targeted): {k_edge}\n")
        f.write(f"efficiency_samples: {efficiency_samples}\n\n")
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