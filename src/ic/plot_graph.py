from __future__ import annotations

from pathlib import Path
from typing import Dict, Optional

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import osmnx as ox
import pandas as pd


def _ensure_fig_dir(city_id: str) -> Path:
    out_dir = Path(f"outputs/{city_id}/figures")
    out_dir.mkdir(parents=True, exist_ok=True)
    return out_dir


def _save_plot_graph(
    G,
    filepath: str,
    node_size: float,
    edge_linewidth: float,
    edge_color: str | None = None,
):
    """
    Wrapper para salvar PNG do grafo.
    - Se edge_color for None, OSMnx usa a cor padrão.
    - Não abre janela (show=False) e fecha figura (close=True).
    """
    ox.plot_graph(
        G,
        node_size=node_size,
        edge_linewidth=edge_linewidth,
        edge_color=edge_color,
        bgcolor="white",
        show=False,
        close=True,
        save=True,
        filepath=filepath,
    )


def _load_communities(city_id: str) -> Optional[Dict[int, int]]:
    """
    Carrega nodes_communities.csv (E6) e retorna dict {node_id: community_id}.
    """
    path = Path(f"outputs/{city_id}/metrics/nodes_communities.csv")
    if not path.exists():
        return None

    df = pd.read_csv(path)
    # garante tipo int
    node_to_comm = {int(row["node"]): int(row["community_id"]) for _, row in df.iterrows()}
    return node_to_comm


def plotar_grafos_png(city_id: str, which: str = "clean") -> dict:
    """
    Gera 3 PNGs:
      1) ruas apenas
      2) ruas + nós
      3) ruas coloridas por comunidade (E6)

    which:
      - 'raw'   -> data/graphs/<city>_drive_raw.graphml
      - 'clean' -> data/graphs/<city>_drive_clean.graphml
    """
    if which not in {"raw", "clean"}:
        raise ValueError("which deve ser 'raw' ou 'clean'.")

    out_dir = _ensure_fig_dir(city_id)

    graph_path = f"data/graphs/{city_id}_drive_{which}.graphml"
    G = ox.load_graphml(graph_path)

    # 1) RUAS APENAS
    png_roads = str(out_dir / f"grafo_{city_id}_{which}_ruas.png")
    _save_plot_graph(
        G,
        filepath=png_roads,
        node_size=0,
        edge_linewidth=0.7,
        edge_color="black",
    )

    # 2) RUAS + NÓS
    png_roads_nodes = str(out_dir / f"grafo_{city_id}_{which}_ruas_nos.png")
    _save_plot_graph(
        G,
        filepath=png_roads_nodes,
        node_size=2,       # bolinhas pequenas
        edge_linewidth=0.6,
        edge_color="black",
    )

    # 3) RUAS COLORIDAS POR COMUNIDADE (E6)
    node_to_comm = _load_communities(city_id)
    png_comm = str(out_dir / f"grafo_{city_id}_{which}_comunidades.png")

    if node_to_comm is None:
        # Não existe E6 ainda → gera um PNG “placeholder” (igual ruas) e avisa
        _save_plot_graph(
            G,
            filepath=png_comm,
            node_size=0,
            edge_linewidth=0.7,
            edge_color="black",
        )
        comm_note = "nodes_communities.csv não encontrado (rode E6: ic communities ...). PNG de comunidades gerado como ruas."
    else:
        # Para colorir ruas por comunidade, pegamos a comunidade do nó de origem da aresta (u)
        # e mapeamos para uma cor via colormap.
        edges = list(G.edges(keys=False))
        comm_ids = []
        for u, v in edges:
            comm_ids.append(node_to_comm.get(int(u), -1))

        # Normaliza ids para 0..(k-1) para colormap funcionar bem
        unique = sorted(set(comm_ids))
        remap = {cid: i for i, cid in enumerate(unique)}
        values = [remap[c] for c in comm_ids]

        cmap = plt.get_cmap("tab20")  # colormap com cores bem distintas
        edge_colors = [cmap(v % 20) for v in values]

        # Agora desenhamos manualmente usando o plot_graph com ax/fig para controlar edge_colors.
        fig, ax = ox.plot_graph(
            G,
            node_size=0,
            edge_linewidth=0.9,
            bgcolor="white",
            show=False,
            close=False,
        )
        # OSMnx desenha as arestas; a forma mais segura é replotar arestas via geometria
        # → porém, para manter simples, usamos uma chamada alternativa:
        ax.clear()

        # Desenha as arestas com cores
        ox.plot_graph(
            G,
            node_size=0,
            edge_linewidth=0.9,
            edge_color=edge_colors,
            bgcolor="white",
            show=False,
            close=False,
            ax=ax,
        )

        fig.savefig(png_comm, dpi=200, bbox_inches="tight")
        plt.close(fig)

        comm_note = "OK"

    return {
        "graph_path": graph_path,
        "png_roads": png_roads,
        "png_roads_nodes": png_roads_nodes,
        "png_communities": png_comm,
        "communities_status": comm_note,
    }
