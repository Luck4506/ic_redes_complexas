from __future__ import annotations

import argparse

from .download import download_from_config
from .io_utils import dataset_id_for_year
from .preprocess import preprocess_city
from .metrics_structural import structural_metrics
from .communities import detectar_comunidades
from .resilience import testar_resiliencia
from .community_resilience import testar_resiliencia_comunidades
from .final_report import gerar_relatorio_final
from .plot_graph import plotar_grafos_png
from .paths_accessibility import gerar_rota_distancia, Coordenada
from .centrality import calcular_centralidades
from .kepler_export import exportar_para_kepler
from .graph_inventory import gerar_planilha_grafo
from .html_report import gerar_dashboard_html
from .compare_report import gerar_comparacao_html


def _add_year_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--year", type=int, help="Ano histórico. Ex.: 2021. Se omitido, usa o OSM atual.")


def _dataset_city(args: argparse.Namespace) -> str:
    return dataset_id_for_year(args.city, getattr(args, "year", None))


def main() -> None:
    parser = argparse.ArgumentParser(prog="ic", description="IC — Redes Complexas (CLI)")
    sub = parser.add_subparsers(dest="cmd", required=True)

    # --- Teste ---
    sub.add_parser("ping", help="Teste rápido do CLI.")

    # --- Download do grafo ---
    p_download = sub.add_parser("download", help="E1: baixar grafo via cidade/config YAML (bbox/radius).")
    p_download.add_argument("--city", help="Ex.: campinas. Usa config/<cidade>.yaml se --config não for passado.")
    p_download.add_argument("--config", help="Ex.: config/campinas.yaml")
    _add_year_argument(p_download)

    # --- Preprocessamento ---
    p_pre = sub.add_parser("preprocess", help="E2: limpar grafo (maior componente + checks).")
    p_pre.add_argument("--city", required=True, help="Ex.: campinas")
    _add_year_argument(p_pre)

    # --- Estrutura ---
    p_str = sub.add_parser("structural", help="E3: métricas estruturais (unweighted).")
    p_str.add_argument("--city", required=True, help="Ex.: campinas")
    _add_year_argument(p_str)
    p_str.add_argument("--samples", type=int, default=30)
    p_str.add_argument("--seed", type=int, default=42)

    # --- Visualização de caminhos ---
    p_paths = sub.add_parser("paths", help="E4: rota por menor distância (length) + mapa.")
    p_paths.add_argument("--city", required=True)
    _add_year_argument(p_paths)
    p_paths.add_argument("--random", action="store_true")
    p_paths.add_argument("--orig-lat", type=float)
    p_paths.add_argument("--orig-lon", type=float)
    p_paths.add_argument("--dest-lat", type=float)
    p_paths.add_argument("--dest-lon", type=float)
    p_paths.add_argument("--seed", type=int, default=42)

    # --- Centralidade ---
    p_cent = sub.add_parser("centrality", help="E5: centralidades + pontos críticos.")
    p_cent.add_argument("--city", required=True)
    _add_year_argument(p_cent)
    p_cent.add_argument("--top-k", type=int, default=30)
    p_cent.add_argument("--k-b", type=int, default=120)  # deixe menor no dev
    p_cent.add_argument("--k-e", type=int, default=60)   # deixe menor no dev
    p_cent.add_argument("--seed", type=int, default=42)

    # --- Detecção de comunidades ---
    p_comm = sub.add_parser("communities", help="E6: detecção de comunidades + mapa.")
    p_comm.add_argument("--city", required=True)
    _add_year_argument(p_comm)
    p_comm.add_argument("--method", choices=["greedy", "louvain"], default="greedy")
    p_comm.add_argument("--min-size", type=int, default=30)
    p_comm.add_argument("--seed", type=int, default=42)

    # --- Teste de resiliência ---
    p_res = sub.add_parser("resilience", help="E7: teste de resiliência removendo arestas.")
    p_res.add_argument("--city", required=True)
    _add_year_argument(p_res)
    p_res.add_argument("--strategy", choices=["random", "targeted", "targeted_adaptive"], default="targeted")
    p_res.add_argument("--max-fraction", type=float, default=0.15)
    p_res.add_argument("--steps", type=int, default=15)
    p_res.add_argument("--k-edge", type=int, default=80)
    p_res.add_argument("--eff-samples", type=int, default=20)
    p_res.add_argument("--seed", type=int, default=42)

    # --- Teste de resiliência no grafo agregado de comunidades ---
    p_res_comm = sub.add_parser("community-resilience", help="E7C: resiliência entre comunidades detectadas.")
    p_res_comm.add_argument("--city", required=True)
    _add_year_argument(p_res_comm)
    p_res_comm.add_argument("--strategy", choices=["random", "targeted", "targeted_adaptive"], default="targeted")
    p_res_comm.add_argument("--max-fraction", type=float, default=0.30)
    p_res_comm.add_argument("--steps", type=int, default=15)
    p_res_comm.add_argument("--min-size", type=int, default=30)
    p_res_comm.add_argument("--seed", type=int, default=42)

    #--- Relatório final ---   
    p_rep = sub.add_parser("report", help="E8: gerar relatório consolidado (Markdown) + manifest.")
    p_rep.add_argument("--city", required=True)
    _add_year_argument(p_rep)

    # --- Grafo para PNG ---
    p_plot = sub.add_parser("plot-graphs", help="Gera 3 PNGs do grafo: ruas, ruas+nós, comunidades.")
    p_plot.add_argument("--city", required=True)
    _add_year_argument(p_plot)
    p_plot.add_argument("--which", choices=["raw", "clean"], default="clean")

    # --- Exportar para Kepler.gl ---
    p_kepler = sub.add_parser("export-kepler", help="Exporta arquivos (GeoJSON/CSV) para usar no kepler.gl.")
    p_kepler.add_argument("--city", required=True)
    _add_year_argument(p_kepler)
    p_kepler.add_argument("--which", choices=["raw", "clean"], default="clean")

    # --- Planilha de inventário do grafo ---
    p_inventory = sub.add_parser("inventory", help="Gera planilhas CSV explicativas com atributos e métricas do grafo.")
    p_inventory.add_argument("--city", required=True)
    _add_year_argument(p_inventory)

    # --- Dashboard HTML ---
    p_dashboard = sub.add_parser("dashboard", help="Gera um HTML visual com as métricas e artefatos da pipeline.")
    p_dashboard.add_argument("--city", required=True)
    _add_year_argument(p_dashboard)

    # --- Comparação de datasets ---
    p_compare = sub.add_parser("compare", help="Gera um HTML comparativo entre dois ou mais datasets já processados.")
    p_compare.add_argument("datasets", nargs="+", help="Ex.: campinas_2021 campinas_2024 sorocaba")
    p_compare.add_argument("--output", help="Caminho opcional do HTML de saída.")

    args = parser.parse_args()

    if args.cmd == "ping":
        print("ic: ok, funcionando...")
        return

    if args.cmd == "download":
        config_path = args.config
        if config_path is None:
            if args.city is None:
                raise SystemExit("Use --city campinas ou --config config/campinas.yaml.")
            config_path = f"config/{args.city}.yaml"

        result = download_from_config(config_path, year=args.year)
        print("\n[E1] Download concluído ✅")
        print("GraphML:", result["graph_path"])
        print("Metadata:", result["meta_path"])
        print("Nós:", result["nodes"], "| Arestas:", result["edges"])
        print("Recorte:", result["clip"])
        return

    if args.cmd == "preprocess":
        result = preprocess_city(_dataset_city(args))
        print("\n[E2] Pré-processamento concluído ✅")
        print("Clean GraphML:", result["clean_path"])
        print("Log:", result["log_path"])
        print("Nós:", result["nodes_after"], "| Arestas:", result["edges_after"])
        print("Arestas sem length:", result["missing_length_edges"])
        return

    if args.cmd == "structural":
        result = structural_metrics(_dataset_city(args), samples_for_paths=args.samples, seed=args.seed)
        print("\n[E3] Métricas estruturais concluídas ✅")
        for k, v in result.items():
            print(f"{k}: {v}")
        return

    if args.cmd == "paths":
        city_id = _dataset_city(args)
        if args.random:
            res = gerar_rota_distancia(city_id=city_id, usar_aleatorio=True, seed=args.seed)
        else:
            if None in (args.orig_lat, args.orig_lon, args.dest_lat, args.dest_lon):
                raise SystemExit("Use --random ou passe --orig-lat --orig-lon --dest-lat --dest-lon.")
            res = gerar_rota_distancia(
                city_id=city_id,
                origem=Coordenada(args.orig_lat, args.orig_lon),
                destino=Coordenada(args.dest_lat, args.dest_lon),
                usar_aleatorio=False,
                seed=args.seed,
            )
        print("\n[E4] Rota por distância concluída ✅")
        print("Mapa:", res["html_path"])
        return

    if args.cmd == "centrality":
        res = calcular_centralidades(
            city_id=_dataset_city(args),
            top_k=args.top_k,
            k_betweenness=args.k_b,
            k_edge_betweenness=args.k_e,
            seed=args.seed,
        )
        print("\n[E5] Centralidades concluídas ✅")
        print("Top nós CSV:", res["top_nodes_csv"])
        print("Top arestas CSV:", res["top_edges_csv"])
        print("Relatório:", res["report_txt"])
        print("Mapa:", res["map_html"])
        return

    if args.cmd == "communities":
        res = detectar_comunidades(
            city_id=_dataset_city(args),
            method=args.method,
            min_size_for_map=args.min_size,
            seed=args.seed,
        )
        print("\n[E6] Comunidades concluídas ✅")
        print("Nós->Comunidade CSV:", res["nodes_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Relatório:", res["report_txt"])
        print("Mapa:", res["map_html"])
        return

    if args.cmd == "resilience":
        res = testar_resiliencia(
            city_id=_dataset_city(args),
            strategy=args.strategy,
            max_fraction=args.max_fraction,
            steps=args.steps,
            k_edge=args.k_edge,
            efficiency_samples=args.eff_samples,
            seed=args.seed,
        )
        print("\n[E7] Resiliência concluída ✅")
        print("Curva CSV:", res["curve_csv"])
        print("Figura:", res["curve_plot"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "community-resilience":
        res = testar_resiliencia_comunidades(
            city_id=_dataset_city(args),
            strategy=args.strategy,
            max_fraction=args.max_fraction,
            steps=args.steps,
            min_size=args.min_size,
            seed=args.seed,
        )
        print("\n[E7C] Resiliência por comunidades concluída ✅")
        print("Curva CSV:", res["curve_csv"])
        print("Resumo comunidades:", res["summary_csv"])
        print("Top conexões:", res["top_edges_csv"])
        print("Figura:", res["curve_plot"])
        print("Relatório:", res["report_txt"])
        return
    
    if args.cmd == "report":
        res = gerar_relatorio_final(_dataset_city(args))
        print("\n[E8] Relatório consolidado gerado ✅")
        print("Report:", res["report_md"])
        print("Manifest:", res["manifest_txt"])
        return
    
    if args.cmd == "plot-graphs":
        res = plotar_grafos_png(_dataset_city(args), which=args.which)
        print("\n[PNG] Imagens geradas ✅")
        print("Entrada:", res["graph_path"])
        print("1) Ruas:", res["png_roads"])
        print("2) Ruas + nós:", res["png_roads_nodes"])
        print("3) Comunidades:", res["png_communities"])
        print("Comunidades:", res["communities_status"])
        return
    
    if args.cmd == "export-kepler":
        res = exportar_para_kepler(_dataset_city(args), which=args.which)
        print("\n[E8.5] Exportação para Kepler concluída ✅")
        print("Pasta:", res["kepler_dir"])
        print("Linhas (arestas) GeoJSON:", res["edges_geojson"])
        print("Pontos (nós) CSV:", res["nodes_csv"])
        print("Top nós (E5):", res["top_nodes_csv"] or "(não encontrado)")
        print("Nós->Comunidades (E6):", res["nodes_communities_csv"] or "(não encontrado)")
        print("Resumo comunidades (E6):", res["community_summary_csv"] or "(não encontrado)")
        print("Rota (E4):", res["route_geojson"] or "(não encontrada)")
        return

    if args.cmd == "inventory":
        res = gerar_planilha_grafo(_dataset_city(args))
        print("\n[Inventário] Planilhas geradas ✅")
        print("Resumo:", res["summary_csv"])
        print("Tipos de via:", res["highway_csv"])
        print("Superfície:", res["surface_csv"])
        print("Velocidade:", res["maxspeed_csv"])
        print("Faixas:", res["lanes_csv"])
        print("Mão única:", res["oneway_csv"])
        print("Distribuição de grau:", res["degree_csv"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "dashboard":
        res = gerar_dashboard_html(_dataset_city(args))
        print("\n[Dashboard] HTML gerado ✅")
        print("HTML:", res["dashboard_html"])
        print("Inventário usado:", res["inventory_summary_csv"])
        return

    if args.cmd == "compare":
        res = gerar_comparacao_html(args.datasets, output_path=args.output)
        print("\n[Compare] HTML comparativo gerado ✅")
        print("Datasets:", ", ".join(res["datasets"]))
        print("HTML:", res["compare_html"])
        return

if __name__ == "__main__":
    main()
