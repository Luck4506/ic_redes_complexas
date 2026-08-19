from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .download import download_from_config
from .io_utils import dataset_id_for_year
from .preprocess import preprocess_city
from .metrics_structural import structural_metrics
from .communities import detectar_comunidades
from .resilience import testar_resiliencia
from .node_resilience import testar_resiliencia_vertices
from .community_resilience import testar_resiliencia_comunidades
from .intra_community_resilience import testar_resiliencia_interna_comunidades
from .final_report import gerar_relatorio_final
from .plot_graph import plotar_grafos_png
from .paths_accessibility import gerar_rota_distancia, Coordenada
from .centrality import calcular_centralidades
from .kepler_export import exportar_para_kepler
from .graph_inventory import gerar_planilha_grafo
from .html_report import gerar_dashboard_html
from .compare_report import gerar_comparacao_html
from .functional_relations import analisar_relacoes_funcionais
from .approximation_validation import validar_aproximacoes
from .scientific_comparability import CONFIRMED, auditar_comparabilidade_cientifica
from .comparison_protocol import write_legacy_comparison_csv
from .historical_quality import auditar_qualidade_historica
from .random_resilience_stats import gerar_estatisticas_resiliencia_aleatoria
from .vulnerability_index import calcular_indice_vulnerabilidade
from .structural_bottlenecks import analisar_gargalos_estruturais
from .route_redundancy import analisar_redundancia_rotas
from .spatial_multiscale import analisar_multiescala_espacial
from .spatial_robustness import simular_robustez_espacial
from .road_hierarchy import analisar_hierarquia_viaria
from .urban_morphology import analisar_morfologia_urbana
from .od_efficiency import analisar_eficiencia_od
from .city_similarity import analisar_similaridade_cidades
from .subcenters import detectar_subcentros
from .urban_barriers import analisar_barreiras_urbanas
from .network_scale_profile import analisar_perfil_escala_rede
from .robustness_summary import gerar_sintese_robustez
from .representation_audit import analisar_representacoes
from .provenance import CliRunRecorder, begin_cli_run
from .artifact_integrity import (
    DEFAULT_HASH_SIZE_LIMIT_BYTES,
    STAGE_CONTRACTS,
    auditar_integridade_artefatos,
)


class _ProvenanceArgumentParser(argparse.ArgumentParser):
    """Preserve argparse's user-facing diagnostic on its original SystemExit."""

    def error(self, message: str) -> None:
        self.print_usage(sys.stderr)
        self._print_message(f"{self.prog}: error: {message}\n", sys.stderr)
        error = SystemExit(2)
        error._ic_argparse_message = message  # type: ignore[attr-defined]
        raise error


def _add_year_argument(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--year", type=int, help="Ano histórico. Ex.: 2021. Se omitido, usa o OSM atual.")


def _dataset_city(args: argparse.Namespace) -> str:
    return dataset_id_for_year(args.city, getattr(args, "year", None))


def _main(recorder: CliRunRecorder) -> None:
    parser = _ProvenanceArgumentParser(prog="ic", description="IC — Redes Complexas (CLI)")
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
    p_cent.add_argument("--k-c", type=int, default=120, help="Landmarks para closeness aproximada.")
    p_cent.add_argument("--seed", type=int, default=42)

    # --- Detecção de comunidades ---
    p_comm = sub.add_parser("communities", help="E6: detecção de comunidades + mapa.")
    p_comm.add_argument("--city", required=True)
    _add_year_argument(p_comm)
    p_comm.add_argument("--method", choices=["greedy", "louvain"], default="greedy")
    p_comm.add_argument("--min-size", type=int, default=30)
    p_comm.add_argument("--seed", type=int, default=42)

    # --- Teste de robustez estrutural (nome do comando preservado) ---
    p_res = sub.add_parser("resilience", help="E7: robustez estrutural sob remoção de arestas.")
    p_res.add_argument("--city", required=True)
    _add_year_argument(p_res)
    p_res.add_argument("--strategy", choices=["random", "targeted", "targeted_adaptive"], default="targeted")
    p_res.add_argument("--max-fraction", type=float, default=0.15)
    p_res.add_argument("--steps", type=int, default=15)
    p_res.add_argument("--k-edge", type=int, default=80)
    p_res.add_argument("--eff-samples", type=int, default=20)
    p_res.add_argument("--seed", type=int, default=42)
    p_res.add_argument(
        "--evaluation-seed",
        type=int,
        default=104729,
        help="Semente independente usada apenas para estimar a eficiência.",
    )

    # --- Teste de robustez estrutural por remoção exclusiva de vértices ---
    p_node_res = sub.add_parser("node-resilience", help="E7V: robustez estrutural sob remoção de vértices.")
    p_node_res.add_argument("--city", required=True)
    _add_year_argument(p_node_res)
    p_node_res.add_argument("--strategy", choices=["random", "targeted", "targeted_adaptive"], default="targeted")
    p_node_res.add_argument("--max-fraction", type=float, default=0.15)
    p_node_res.add_argument("--steps", type=int, default=15)
    p_node_res.add_argument("--k-node", type=int, default=80)
    p_node_res.add_argument("--eff-samples", type=int, default=20)
    p_node_res.add_argument("--seed", type=int, default=42)
    p_node_res.add_argument(
        "--evaluation-seed",
        type=int,
        default=104729,
        help="Semente independente usada apenas para estimar a eficiência.",
    )

    # --- Teste de robustez estrutural no grafo agregado de comunidades ---
    p_res_comm = sub.add_parser("community-resilience", help="E7C: robustez estrutural entre comunidades detectadas.")
    p_res_comm.add_argument("--city", required=True)
    _add_year_argument(p_res_comm)
    p_res_comm.add_argument("--strategy", choices=["random", "targeted", "targeted_adaptive"], default="targeted")
    p_res_comm.add_argument("--max-fraction", type=float, default=0.30)
    p_res_comm.add_argument("--steps", type=int, default=15)
    p_res_comm.add_argument("--min-size", type=int, default=30)
    p_res_comm.add_argument("--seed", type=int, default=42)

    # --- Teste de robustez estrutural dentro de cada comunidade ---
    p_res_intra = sub.add_parser(
        "intra-community-resilience",
        help="E7I: robustez estrutural interna de cada comunidade detectada.",
    )
    p_res_intra.add_argument("--city", required=True)
    _add_year_argument(p_res_intra)
    p_res_intra.add_argument("--strategy", choices=["random", "targeted", "targeted_adaptive"], default="targeted")
    p_res_intra.add_argument("--max-fraction", type=float, default=0.15)
    p_res_intra.add_argument("--steps", type=int, default=10)
    p_res_intra.add_argument("--min-size", type=int, default=2)
    p_res_intra.add_argument("--k-edge", type=int, default=40)
    p_res_intra.add_argument("--eff-samples", type=int, default=20)
    p_res_intra.add_argument("--seed", type=int, default=42)

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

    p_similarity = sub.add_parser(
        "city-similarity",
        help="Explora distâncias entre perfis urbanos com trava de amostra e conjunto teórico reduzido.",
    )
    p_similarity.add_argument("datasets", nargs="+", help="Ex.: campinas_admin jundiai_admin sorocaba_admin")
    p_similarity.add_argument("--output-dir", default="outputs/comparisons")
    p_similarity.add_argument("--min-coverage", type=float, default=1.0)
    p_similarity.add_argument("--metric-profile", choices=["theory_core", "all"], default="theory_core")
    p_similarity.add_argument("--minimum-datasets", type=int, default=8)
    p_similarity.add_argument(
        "--allow-small-sample-exploration",
        action="store_true",
        help="Libera explicitamente análises descritivas abaixo da amostra mínima.",
    )

    p_functional = sub.add_parser("functional-relations", help="Relaciona atributos OSM e posição topológica.")
    p_functional.add_argument("--city", required=True)
    _add_year_argument(p_functional)

    p_validate = sub.add_parser("validate-approximations", help="Valida métricas aproximadas em subgrafo controlado.")
    p_validate.add_argument("--city", required=True)
    _add_year_argument(p_validate)
    p_validate.add_argument("--subgraph-size", type=int, default=400)
    p_validate.add_argument("--samples", type=int, nargs="+", default=[10, 30, 60, 120])
    p_validate.add_argument("--repeats", type=int, default=3)
    p_validate.add_argument("--seed", type=int, default=42)

    p_audit = sub.add_parser(
        "comparison-audit",
        help="Auditoria fail-closed de comparabilidade e proveniência.",
    )
    p_audit.add_argument("datasets", nargs="+")
    p_audit.add_argument("--output-dir", default="outputs/comparisons")
    p_audit.add_argument(
        "--output",
        help="Alias legado: grava uma cópia do resumo por dataset neste CSV exato.",
    )
    p_audit.add_argument("--profile", choices=["cientifico", "exploratorio"], default="cientifico")
    p_audit.add_argument("--snapshot-policy", choices=["same", "documented"], default="same")

    p_hist_audit = sub.add_parser("historical-audit", help="Audita viés de cobertura OSM em comparações temporais.")
    p_hist_audit.add_argument("--reference", required=True, help="Dataset de referência atual. Ex.: campinas")
    p_hist_audit.add_argument("datasets", nargs="+", help="Datasets históricos. Ex.: campinas_2014 campinas_2024")
    p_hist_audit.add_argument("--output-dir", default="outputs/comparisons")

    p_random_stats = sub.add_parser(
        "random-resilience-stats",
        help="Repete ataques aleatórios com múltiplas sementes e agrega estatísticas.",
    )
    p_random_stats.add_argument("--city", required=True)
    _add_year_argument(p_random_stats)
    p_random_stats.add_argument("--mode", choices=["edge", "node", "both"], default="both")
    p_random_stats.add_argument(
        "--seeds",
        type=int,
        nargs="+",
        help="Sementes explícitas de ataque. Se omitidas, são geradas 30 repetições.",
    )
    p_random_stats.add_argument("--repetitions", type=int)
    p_random_stats.add_argument("--master-seed", type=int, default=42)
    p_random_stats.add_argument("--evaluation-seed", type=int, default=104729)
    p_random_stats.add_argument("--bootstrap-resamples", type=int, default=2000)
    p_random_stats.add_argument("--max-fraction", type=float, default=0.15)
    p_random_stats.add_argument("--steps", type=int, default=15)
    p_random_stats.add_argument("--k-edge", type=int, default=80)
    p_random_stats.add_argument("--k-node", type=int, default=80)
    p_random_stats.add_argument("--eff-samples", type=int, default=20)

    p_vulnerability = sub.add_parser(
        "vulnerability-index",
        help="Gera índice composto de vulnerabilidade de nós e arestas.",
    )
    p_vulnerability.add_argument("--city", required=True)
    _add_year_argument(p_vulnerability)
    p_vulnerability.add_argument("--top-k", type=int, default=100)

    p_bottlenecks = sub.add_parser(
        "structural-bottlenecks",
        help="Identifica pontes, articulações e gargalos estruturais.",
    )
    p_bottlenecks.add_argument("--city", required=True)
    _add_year_argument(p_bottlenecks)
    p_bottlenecks.add_argument("--top-k", type=int, default=100)

    p_route_redundancy = sub.add_parser(
        "route-redundancy",
        help="Avalia alternativas de rota quando a melhor rota é bloqueada.",
    )
    p_route_redundancy.add_argument("--city", required=True)
    _add_year_argument(p_route_redundancy)
    p_route_redundancy.add_argument("--pairs", type=int, default=100)
    p_route_redundancy.add_argument("--threshold", type=float, default=1.50)
    p_route_redundancy.add_argument("--seed", type=int, default=42)
    p_route_redundancy.add_argument("--map-limit", type=int, default=20)

    p_spatial = sub.add_parser(
        "spatial-multiscale",
        help="Calcula métricas locais por grade espacial.",
    )
    p_spatial.add_argument("--city", required=True)
    _add_year_argument(p_spatial)
    p_spatial.add_argument("--cell-size-m", type=float, default=1000.0)

    p_spatial_robustness = sub.add_parser(
        "spatial-robustness",
        help="Simula bloqueios regionais por célula espacial e mede impacto global.",
    )
    p_spatial_robustness.add_argument("--city", required=True)
    _add_year_argument(p_spatial_robustness)
    p_spatial_robustness.add_argument("--cell-size-m", type=float, default=1000.0)
    p_spatial_robustness.add_argument("--mode", choices=["incident", "internal"], default="incident")
    p_spatial_robustness.add_argument("--eff-samples", type=int, default=10)
    p_spatial_robustness.add_argument("--max-eff-cells", type=int, default=100)
    p_spatial_robustness.add_argument("--seed", type=int, default=42)

    p_road_hierarchy = sub.add_parser(
        "road-hierarchy",
        help="Analisa contribuição de classes highway para conectividade, centralidade e robustez estrutural.",
    )
    p_road_hierarchy.add_argument("--city", required=True)
    _add_year_argument(p_road_hierarchy)
    p_road_hierarchy.add_argument("--eff-samples", type=int, default=20)
    p_road_hierarchy.add_argument("--seed", type=int, default=42)
    p_road_hierarchy.add_argument("--map-edges-per-class", type=int, default=1200)

    p_urban_morphology = sub.add_parser(
        "urban-morphology",
        help="Classifica padrões urbanos locais por orientação, entropia angular e conectividade.",
    )
    p_urban_morphology.add_argument("--city", required=True)
    _add_year_argument(p_urban_morphology)
    p_urban_morphology.add_argument("--cell-size-m", type=float, default=1000.0)

    p_od_efficiency = sub.add_parser(
        "od-efficiency",
        help="Amostra múltiplos pares origem-destino e mede eficiência estatística de rotas.",
    )
    p_od_efficiency.add_argument("--city", required=True)
    _add_year_argument(p_od_efficiency)
    p_od_efficiency.add_argument("--pairs", type=int, default=1000)
    p_od_efficiency.add_argument("--seed", type=int, default=42)
    p_od_efficiency.add_argument("--map-limit", type=int, default=80)

    p_subcenters = sub.add_parser(
        "subcenters",
        help="Seleciona células candidatas de alta centralidade topológica.",
    )
    p_subcenters.add_argument("--city", required=True)
    _add_year_argument(p_subcenters)
    p_subcenters.add_argument("--cell-size-m", type=float, default=1000.0)
    p_subcenters.add_argument("--percentile", type=float, default=0.90)
    p_subcenters.add_argument("--min-nodes", type=int, default=20)

    p_urban_barriers = sub.add_parser(
        "urban-barriers",
        help="Infere barreiras urbanas prováveis por baixa permeabilidade espacial da rede.",
    )
    p_urban_barriers.add_argument("--city", required=True)
    _add_year_argument(p_urban_barriers)
    p_urban_barriers.add_argument("--cell-size-m", type=float, default=1000.0)
    p_urban_barriers.add_argument("--map-limit", type=int, default=250)

    p_scale_profile = sub.add_parser(
        "network-scale-profile",
        help="Mede sensibilidade das métricas espaciais a diferentes tamanhos de célula.",
    )
    p_scale_profile.add_argument("--city", required=True)
    _add_year_argument(p_scale_profile)
    p_scale_profile.add_argument("--scales", type=float, nargs="+", default=[500.0, 1000.0, 2000.0, 3000.0])

    p_robustness_summary = sub.add_parser(
        "robustness-summary",
        help="Sintetiza curvas de robustez por AUC, perdas e limiares em intervalo comparável.",
    )
    p_robustness_summary.add_argument(
        "datasets",
        nargs="+",
        help="Datasets processados. Ex.: campinas_admin jundiai_admin sorocaba_admin valinhos_admin",
    )
    p_robustness_summary.add_argument("--output-dir", default="outputs/comparisons")
    p_robustness_summary.add_argument(
        "--max-fraction",
        type=float,
        help="Limite opcional; cada modalidade usa o menor valor entre este limite e a cobertura comum real.",
    )
    p_robustness_summary.add_argument(
        "--checkpoints",
        type=float,
        nargs="+",
        default=[0.01, 0.05, 0.10, 0.15],
        help="Frações para interpolar valores e perdas.",
    )
    p_robustness_summary.add_argument(
        "--thresholds",
        type=float,
        nargs="+",
        default=[0.90, 0.75, 0.50],
        help="Níveis retidos cujos primeiros cruzamentos serão estimados.",
    )
    p_robustness_summary.add_argument(
        "--allow-incomplete",
        action="store_true",
        help="Aceita conscientemente uma matriz incompleta de curvas; o padrão é falhar.",
    )
    p_robustness_summary.add_argument(
        "--city-output-root",
        help="Raiz explícita dos resumos por dataset; útil para execuções isoladas.",
    )

    p_representation = sub.add_parser(
        "representation-audit",
        help="Compara representações dirigidas/múltiplas e mede a sensibilidade dos rankings.",
    )
    p_representation.add_argument("--city", required=True)
    _add_year_argument(p_representation)
    p_representation.add_argument("--top-k", type=int, default=20)
    p_representation.add_argument("--seed", type=int, default=42)

    p_integrity = sub.add_parser(
        "artifact-integrity",
        help="Gate fail-closed de completude, hashes, esquema e frescor dos artefatos.",
    )
    p_integrity.add_argument(
        "--city",
        help="Dataset; pode ser omitido quando --manifest identifica exatamente um dataset.",
    )
    _add_year_argument(p_integrity)
    p_integrity.add_argument("--manifest")
    p_integrity.add_argument("--output-root", default="outputs")
    p_integrity.add_argument("--stages", nargs="+", choices=sorted(STAGE_CONTRACTS))
    p_integrity.add_argument(
        "--hash-size-limit-bytes",
        type=int,
        default=DEFAULT_HASH_SIZE_LIMIT_BYTES,
        help="Limite opcional para hashing; por padrão todos os arquivos declarados são verificados.",
    )

    args = parser.parse_args()
    recorder.set_parsed_args(args)

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
            k_closeness=args.k_c,
            seed=args.seed,
        )
        print("\n[E5] Centralidades concluídas ✅")
        print("Top nós CSV:", res["top_nodes_csv"])
        print("Centralidades completas:", res["all_nodes_csv"])
        print("Centralidades completas de arestas:", res["edge_centralities_csv"])
        print("Rankings:", res["rankings_csv"])
        print("Top arestas CSV:", res["top_edges_csv"])
        print("Relatório:", res["report_txt"])
        print("Mapa:", res["map_html"])
        print("Mapa de arestas:", res["edge_map_html"])
        return

    if args.cmd == "functional-relations":
        res = analisar_relacoes_funcionais(_dataset_city(args))
        print("\n[Relações funcionais] Análise concluída ✅")
        print("Grupos:", res["grouped_csv"])
        print("Correlações:", res["correlations_csv"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "validate-approximations":
        res = validar_aproximacoes(
            _dataset_city(args),
            subgraph_size=args.subgraph_size,
            sample_sizes=args.samples,
            repeats=args.repeats,
            seed=args.seed,
        )
        print("\n[Validação] Aproximações avaliadas ✅")
        print("Resultados:", res["validation_csv"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "comparison-audit":
        comparison_output_dir = (
            str(Path(args.output).parent) if args.output else args.output_dir
        )
        res = auditar_comparabilidade_cientifica(
            args.datasets,
            output_dir=comparison_output_dir,
            perfil=args.profile,
            snapshot_policy=args.snapshot_policy,
        )
        if args.output:
            write_legacy_comparison_csv(args.datasets, res, args.output)
        print("\n[Comparabilidade] Auditoria concluída")
        print("Estado:", res["state"])
        print("Critérios:", res["criteria_csv"])
        print("Datasets:", res["datasets_csv"])
        print("Pares:", res["pairs_csv"])
        print("Relatório:", res["report_txt"])
        if args.output:
            print("CSV legado solicitado:", args.output)
        if res["state"] != CONFIRMED:
            raise SystemExit(1)
        return

    if args.cmd == "historical-audit":
        res = auditar_qualidade_historica(args.reference, args.datasets, output_dir=args.output_dir)
        print("\n[Histórico] Auditoria de qualidade OSM concluída")
        print("Auditoria:", res["audit_csv"])
        print("Núcleo comum:", res["common_core_csv"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "random-resilience-stats":
        res = gerar_estatisticas_resiliencia_aleatoria(
            city_id=_dataset_city(args),
            mode=args.mode,
            seeds=args.seeds,
            repetitions=args.repetitions,
            master_seed=args.master_seed,
            evaluation_seed=args.evaluation_seed,
            max_fraction=args.max_fraction,
            steps=args.steps,
            k_edge=args.k_edge,
            k_node=args.k_node,
            efficiency_samples=args.eff_samples,
            bootstrap_resamples=args.bootstrap_resamples,
        )
        print("\n[ESTATÍSTICA] Robustez aleatória agregada concluída ✅")
        print("Repetições independentes:", res["repetitions"])
        print("Semente fixa de avaliação:", res["evaluation_seed"])
        if "edge" in res:
            print("Arestas CSV agregado:", res["edge"]["aggregate_csv"])
            print("Arestas AUC:", res["edge"]["auc_csv"])
        if "node" in res:
            print("Vértices CSV agregado:", res["node"]["aggregate_csv"])
            print("Vértices AUC:", res["node"]["auc_csv"])
        return

    if args.cmd == "vulnerability-index":
        res = calcular_indice_vulnerabilidade(_dataset_city(args), top_k=args.top_k)
        print("\n[Vulnerabilidade] Índice composto gerado ✅")
        print("Nós CSV:", res["node_csv"])
        print("Arestas CSV:", res["edge_csv"])
        print("Mapa nós:", res["node_map"])
        print("Mapa arestas:", res["edge_map"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "structural-bottlenecks":
        res = analisar_gargalos_estruturais(_dataset_city(args), top_k=args.top_k)
        print("\n[Gargalos] Pontes, articulações e gargalos estruturais gerados ✅")
        print("Articulações CSV:", res["articulations_csv"])
        print("Pontes CSV:", res["bridges_csv"])
        print("Gargalos CSV:", res["bottlenecks_csv"])
        print("Mapa articulações:", res["articulations_map"])
        print("Mapa pontes:", res["bridges_map"])
        print("Mapa gargalos:", res["bottlenecks_map"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "route-redundancy":
        res = analisar_redundancia_rotas(
            _dataset_city(args),
            pairs=args.pairs,
            threshold=args.threshold,
            seed=args.seed,
            map_limit=args.map_limit,
        )
        print("\n[Rotas] Perfil de redundância gerado ✅")
        print("Pares CSV:", res["pairs_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa:", res["map_html"])
        print("Relatório:", res["report_txt"])
        print("Alternativas razoáveis:", f"{res['reasonable_alternative_rate']:.4f}")
        return

    if args.cmd == "spatial-multiscale":
        res = analisar_multiescala_espacial(_dataset_city(args), cell_size_m=args.cell_size_m)
        print("\n[Espacial] Análise multiescala por grade gerada ✅")
        print("Células CSV:", res["cells_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa vulnerabilidade:", res["vulnerability_map"])
        print("Mapa conectividade:", res["connectivity_map"])
        print("Mapa redundância:", res["redundancy_map"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "spatial-robustness":
        res = simular_robustez_espacial(
            _dataset_city(args),
            cell_size_m=args.cell_size_m,
            mode=args.mode,
            efficiency_samples=args.eff_samples,
            max_efficiency_cells=args.max_eff_cells,
            seed=args.seed,
        )
        print("\n[Espacial] Robustez por bloqueios regionais gerada ✅")
        print("Células CSV:", res["cells_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa LCC:", res["lcc_map"])
        print("Mapa eficiência:", res["efficiency_map"])
        print("Mapa fragmentação:", res["fragmentation_map"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "road-hierarchy":
        res = analisar_hierarquia_viaria(
            _dataset_city(args),
            efficiency_samples=args.eff_samples,
            seed=args.seed,
            map_edges_per_class=args.map_edges_per_class,
        )
        print("\n[Hierarquia] Análise de hierarquia viária gerada ✅")
        print("Por classe CSV:", res["by_class_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa:", res["map_html"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "urban-morphology":
        res = analisar_morfologia_urbana(_dataset_city(args), cell_size_m=args.cell_size_m)
        print("\n[Morfologia] Comparação planejamento urbano x estrutura da rede gerada ✅")
        print("Células CSV:", res["cells_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa classes:", res["class_map"])
        print("Mapa entropia:", res["entropy_map"])
        print("Mapa conectividade:", res["connectivity_map"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "od-efficiency":
        res = analisar_eficiencia_od(
            _dataset_city(args),
            pairs=args.pairs,
            seed=args.seed,
            map_limit=args.map_limit,
        )
        print("\n[OD] Eficiência de rotas em múltiplos pares gerada ✅")
        print("Pares CSV:", res["pairs_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa:", res["map_html"])
        print("Relatório:", res["report_txt"])
        print("Pares amostrados:", res["sampled_pairs"])
        return

    if args.cmd == "subcenters":
        res = detectar_subcentros(
            _dataset_city(args),
            cell_size_m=args.cell_size_m,
            percentile=args.percentile,
            min_nodes=args.min_nodes,
        )
        print("\n[Candidatos topológicos] Análise exploratória gerada ✅")
        print("Células CSV:", res["cells_csv"])
        print("Candidatos CSV:", res["subcenters_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa:", res["map_html"])
        print("Relatório:", res["report_txt"])
        print("Candidatos selecionados:", res["subcenters_count"])
        return

    if args.cmd == "urban-barriers":
        res = analisar_barreiras_urbanas(
            _dataset_city(args),
            cell_size_m=args.cell_size_m,
            map_limit=args.map_limit,
        )
        print("\n[Barreiras] Exposição da rede a barreiras urbanas gerada ✅")
        print("Células CSV:", res["cells_csv"])
        print("Conexões CSV:", res["connections_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Mapa permeabilidade:", res["permeability_map"])
        print("Mapa conexões:", res["connections_map"])
        print("Relatório:", res["report_txt"])
        print("Índice de permeabilidade:", res["spatial_permeability_index"])
        return

    if args.cmd == "network-scale-profile":
        res = analisar_perfil_escala_rede(_dataset_city(args), scales_m=args.scales)
        print("\n[Escala] Perfil de escala da rede viária gerado ✅")
        print("CSV por escala:", res["scales_csv"])
        print("CSV células:", res["cells_csv"])
        print("CSV estabilidade:", res["stability_csv"])
        print("CSV resumo:", res["summary_csv"])
        print("Gráfico métricas:", res["metrics_plot"])
        print("Gráfico estabilidade:", res["stability_plot"])
        print("Mapa:", res["scale_map"])
        print("Relatório:", res["report_txt"])
        print("Índice multiescalar:", res["multiscale_robustness_index"])
        return

    if args.cmd == "robustness-summary":
        res = gerar_sintese_robustez(
            args.datasets,
            output_dir=args.output_dir,
            max_fraction=args.max_fraction,
            checkpoints=args.checkpoints,
            thresholds=args.thresholds,
            allow_incomplete=args.allow_incomplete,
            city_output_root=args.city_output_root,
        )
        print("\n[Robustez] Síntese quantitativa concluída ✅")
        print("Datasets:", ", ".join(res["datasets"]))
        print("Frações comuns:", res["common_fractions"])
        print("CSV comparativo:", res["comparison_csv"])
        print("HTML comparativo:", res["comparison_html"])
        print("Gráfico comparativo:", res["comparison_plot"])
        print("Gráfico de perdas:", res["comparison_losses_plot"])
        for dataset, paths in res["city_outputs"].items():
            print(f"Resumo {dataset}:", paths["summary_csv"])
        return

    if args.cmd == "representation-audit":
        res = analisar_representacoes(
            _dataset_city(args),
            top_k=args.top_k,
            seed=args.seed,
        )
        print("\n[Representação] Auditoria concluída ✅")
        print("Inventário:", res["audit_csv"])
        print("Sensibilidade dos rankings:", res["sensitivity_csv"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "artifact-integrity":
        if args.city is None and args.year is not None:
            raise SystemExit("--year exige --city; sem cidade, o dataset deve vir de --manifest.")
        res = auditar_integridade_artefatos(
            dataset=_dataset_city(args) if args.city is not None else None,
            manifest=args.manifest,
            output_root=args.output_root,
            stages=args.stages,
            hash_size_limit_bytes=args.hash_size_limit_bytes,
        )
        print("\n[Integridade] Auditoria concluída")
        print("Escopo:", res["scope"])
        print("Status do escopo:", res["overall_status"])
        print("Seguro dentro do escopo auditado:", "SIM" if res["safe_to_use"] else "NÃO")
        print("CSV:", res["audit_csv"])
        print("Relatório:", res["report_txt"])
        if not res["safe_to_use"]:
            raise SystemExit(1)
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
            evaluation_seed=args.evaluation_seed,
        )
        print("\n[E7] Robustez estrutural concluída ✅")
        print("Curva CSV:", res["curve_csv"])
        print("Figura:", res["curve_plot"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "node-resilience":
        res = testar_resiliencia_vertices(
            city_id=_dataset_city(args),
            strategy=args.strategy,
            max_fraction=args.max_fraction,
            steps=args.steps,
            k_node=args.k_node,
            efficiency_samples=args.eff_samples,
            seed=args.seed,
            evaluation_seed=args.evaluation_seed,
        )
        print("\n[E7V] Robustez estrutural por remoção de vértices concluída ✅")
        print("Curva CSV:", res["curve_csv"])
        print("Vértices removidos:", res["removed_nodes_csv"])
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
        print("\n[E7C] Robustez estrutural por comunidades concluída ✅")
        print("Curva CSV:", res["curve_csv"])
        print("Resumo comunidades:", res["summary_csv"])
        print("Top conexões:", res["top_edges_csv"])
        print("Figura:", res["curve_plot"])
        print("Relatório:", res["report_txt"])
        return

    if args.cmd == "intra-community-resilience":
        res = testar_resiliencia_interna_comunidades(
            city_id=_dataset_city(args),
            strategy=args.strategy,
            max_fraction=args.max_fraction,
            steps=args.steps,
            min_size=args.min_size,
            k_edge=args.k_edge,
            efficiency_samples=args.eff_samples,
            seed=args.seed,
        )
        print("\n[E7I] Robustez estrutural interna das comunidades concluída ✅")
        print("Comunidades analisadas:", res["communities_analyzed"])
        print("Curvas CSV:", res["curve_csv"])
        print("Resumo CSV:", res["summary_csv"])
        print("Figura:", res["curve_plot"])
        print("Relatório:", res["report_txt"])
        return
    
    if args.cmd == "report":
        res = gerar_relatorio_final(_dataset_city(args))
        print("\n[E8] Relatório consolidado gerado ✅")
        print("Report:", res["report_md"])
        print("Manifest:", res["manifest_txt"])
        print("Manifest JSON:", res["manifest_json"])
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
        print("CSV:", res["compare_csv"])
        return

    if args.cmd == "city-similarity":
        res = analisar_similaridade_cidades(
            args.datasets,
            output_dir=args.output_dir,
            min_coverage=args.min_coverage,
            metric_profile=args.metric_profile,
            minimum_datasets=args.minimum_datasets,
            allow_small_sample_exploration=args.allow_small_sample_exploration,
        )
        print("\n[Similaridade] Análise entre cidades gerada ✅")
        print("Métricas usadas:", res["metrics_used"])
        print("HTML:", res["html"])
        print("Vetores:", res["vectors_csv"])
        print("Distâncias:", res["distances_csv"])
        print("Similaridade cosseno:", res["similarities_csv"])
        print("PCA:", res["pca_csv"])
        print("Clusters:", res["clusters_csv"])
        print("Relatório:", res["report_txt"])
        print("Status de inferência:", res["inference_status"])
        return

def main() -> None:
    recorder = begin_cli_run()
    try:
        _main(recorder)
    except SystemExit as exc:
        try:
            recorder.finish(
                "success" if exc.code in (None, 0) else "failure",
                exc if exc.code else None,
            )
        except BaseException as provenance_error:
            exc.add_note(
                "Falha adicional ao persistir a proveniência: "
                f"{type(provenance_error).__name__}: {provenance_error}"
            )
            raise exc from provenance_error
        raise
    except BaseException as exc:
        try:
            recorder.finish("failure", exc)
        except BaseException as provenance_error:
            exc.add_note(
                "Falha adicional ao persistir a proveniência: "
                f"{type(provenance_error).__name__}: {provenance_error}"
            )
            raise exc from provenance_error
        raise
    else:
        recorder.finish("success")


if __name__ == "__main__":
    main()
