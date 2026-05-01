from __future__ import annotations

import csv
import random
import statistics
from collections import Counter
from pathlib import Path

import matplotlib.pyplot as plt
import networkx as nx

from .io_utils import ensure_city_dirs, load_graphml


def structural_metrics(city_id: str, samples_for_paths: int = 30, seed: int = 42) -> dict:
    ensure_city_dirs(city_id)
    random.seed(seed)

    clean_path = f"data/graphs/{city_id}_drive_clean.graphml"

    out_metrics_csv = f"outputs/{city_id}/metrics/structural_metrics.csv"
    out_degree_csv = f"outputs/{city_id}/metrics/degree_distribution.csv"
    out_degree_plot = f"outputs/{city_id}/figures/degree_distribution_loglog.png"
    out_report_txt = f"outputs/{city_id}/logs/structural_report.txt"

    G = load_graphml(clean_path)

    Gu = nx.Graph(G.to_undirected())

    if nx.is_connected(Gu):
        Gc = Gu
        used_cc = False
    else:
        largest_cc = max(nx.connected_components(Gu), key=len)
        Gc = Gu.subgraph(largest_cc).copy()
        used_cc = True

    n = Gc.number_of_nodes()
    m = Gc.number_of_edges()

    degrees = dict(Gc.degree())
    degree_list = list(degrees.values())

    degree_min = min(degree_list)
    degree_max = max(degree_list)
    degree_mean = statistics.mean(degree_list)
    degree_median = statistics.median(degree_list)

    density = nx.density(Gc)

    transitivity = nx.transitivity(Gc)
    trials = min(2000, n)
    avg_clustering_approx = nx.approximation.average_clustering(Gc, trials=trials, seed=seed)

    assortativity = nx.degree_assortativity_coefficient(Gc)

    sample_k = min(samples_for_paths, n)
    sample_nodes = random.sample(list(Gc.nodes()), k=sample_k)

    all_distances = []
    eccentricities = []
    for s in sample_nodes:
        dist = nx.single_source_shortest_path_length(Gc, s)
        vals = [d for d in dist.values() if d > 0]
        if vals:
            all_distances.extend(vals)
            eccentricities.append(max(vals))

    avg_shortest_path_len_approx = statistics.mean(all_distances) if all_distances else float("nan")
    diameter_approx = max(eccentricities) if eccentricities else float("nan")

    counter = Counter(degree_list)
    sorted_items = sorted(counter.items(), key=lambda x: x[0])

    Path(out_degree_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_degree_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["degree", "count", "probability"])
        for k_deg, count in sorted_items:
            w.writerow([k_deg, count, count / n])

    x = [k for k, _ in sorted_items]
    y = [c for _, c in sorted_items]
    plt.figure()
    plt.loglog(x, y, marker="o", linestyle="None")
    plt.xlabel("Grau (k)")
    plt.ylabel("Quantidade de nós com grau k")
    plt.title(f"Distribuição de graus (log-log) — {city_id}")
    plt.savefig(out_degree_plot, dpi=200, bbox_inches="tight")
    plt.close()

    Path(out_metrics_csv).parent.mkdir(parents=True, exist_ok=True)
    with open(out_metrics_csv, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(["metric", "value"])
        w.writerow(["nodes", n])
        w.writerow(["edges", m])
        w.writerow(["used_largest_connected_component", "yes" if used_cc else "no"])
        w.writerow(["degree_min", degree_min])
        w.writerow(["degree_max", degree_max])
        w.writerow(["degree_mean", degree_mean])
        w.writerow(["degree_median", degree_median])
        w.writerow(["density", density])
        w.writerow(["transitivity", transitivity])
        w.writerow(["avg_clustering_approx", avg_clustering_approx])
        w.writerow(["assortativity_degree", assortativity])
        w.writerow(["avg_shortest_path_len_approx_hops", avg_shortest_path_len_approx])
        w.writerow(["diameter_approx_hops", diameter_approx])
        w.writerow(["samples_for_paths", sample_k])
        w.writerow(["seed", seed])

    Path(out_report_txt).parent.mkdir(parents=True, exist_ok=True)
    with open(out_report_txt, "w", encoding="utf-8") as f:
        f.write("=== Métricas Estruturais (E3) — Unweighted/Topologia ===\n\n")
        f.write(f"Entrada: {clean_path}\n")
        f.write(f"Nós: {n} | Arestas: {m}\n")
        f.write(f"Usou maior componente conectada? {'SIM' if used_cc else 'NÃO'}\n\n")
        f.write("Grau:\n")
        f.write(f"  min={degree_min}  max={degree_max}  mean={degree_mean:.4f}  median={degree_median}\n\n")
        f.write("Estrutura:\n")
        f.write(f"  density={density:.8f}\n")
        f.write(f"  transitivity={transitivity:.8f}\n")
        f.write(f"  avg_clustering_approx={avg_clustering_approx:.8f} (trials={trials})\n")
        f.write(f"  assortativity_degree={assortativity:.8f}\n\n")
        f.write("Caminhos (aprox em hops):\n")
        f.write(f"  avg_shortest_path_len_approx={avg_shortest_path_len_approx:.4f}\n")
        f.write(f"  diameter_approx={diameter_approx}\n")
        f.write(f"  samples_for_paths={sample_k}  seed={seed}\n")

    return {
        "metrics_csv": out_metrics_csv,
        "degree_csv": out_degree_csv,
        "degree_plot": out_degree_plot,
        "report_txt": out_report_txt,
    }