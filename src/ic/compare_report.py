from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

from .graph_inventory import gerar_planilha_grafo
from .html_report import _as_float, _e, _format_value, _read_csv_dicts
from .comparison_protocol import auditar_comparabilidade
from .io_utils import dataset_graph_path


COMPARISON_METRICS = [
    ("tamanho", "nodes", "Nos", "Quantidade de intersecoes/pontos do grafo."),
    ("tamanho", "edges", "Arestas", "Quantidade de segmentos direcionados."),
    ("tamanho", "directed_routing_length_km", "Extensão dirigida de roteamento", "Soma dos arcos dirigidos; pares recíprocos podem contar o mesmo trecho duas vezes."),
    ("tamanho", "physical_collapsed_length_km", "Extensão física colapsada", "Proxy com um segmento por par não ordenado; preferível para comparar extensão física da malha."),
    ("tamanho", "named_streets_unique", "Vias nomeadas", "Nomes distintos de vias no OSM."),
    ("normalizacao", "clip_area_km2", "Area do recorte", "Area do limite administrativo em km2."),
    ("normalizacao", "nodes_per_km2", "Nos por km2", "Quantidade de nos normalizada pela area do recorte."),
    ("normalizacao", "edges_per_km2", "Arestas por km2", "Quantidade de arestas direcionadas normalizada pela area do recorte."),
    ("normalizacao", "directed_routing_length_km_per_km2", "Extensão dirigida por km²", "Extensão de roteamento dirigida normalizada pela área do recorte."),
    ("normalizacao", "physical_collapsed_length_km_per_km2", "Densidade viária física", "Proxy de extensão física colapsada normalizada pela área do recorte."),
    ("topologia", "degree_mean", "Grau medio", "Media do grau dos nos na maior componente."),
    ("topologia", "degree_max", "Grau maximo", "Maior grau observado."),
    ("topologia", "density", "Densidade", "Densidade do grafo nao direcionado."),
    ("topologia", "transitivity", "Transitividade", "Coeficiente global de transitividade."),
    ("superficie", "paved_edges_pct", "Pavimentado informado", "Percentual das arestas totais com surface pavimentado no OSM."),
    ("superficie_estimativa", "estimated_paved_edges_pct", "Pavimentado estimado", "Estimativa: aplica aos trechos sem surface a proporcao observada nos trechos com surface conhecido."),
    ("superficie_estimativa", "estimated_paved_length_pct", "Extensao pavimentada estimada", "Estimativa por extensao; nao e dado observado direto."),
    ("superficie", "unpaved_edges_pct", "Terra informado", "Percentual das arestas totais com surface de terra/sem pavimento no OSM."),
    ("superficie_estimativa", "estimated_unpaved_edges_pct", "Terra estimada", "Estimativa de terra/sem pavimento usando a proporcao observada nos trechos conhecidos."),
    ("superficie", "unknown_surface_edges_pct", "Surface desconhecido", "Percentual das arestas sem surface no OSM."),
    ("superficie", "surface_known_edges_pct", "Surface conhecido", "Cobertura do atributo surface no OSM por arestas."),
    ("velocidade", "maxspeed_mean", "Velocidade media informada", "Media dos valores numericos de maxspeed conhecidos."),
    ("velocidade", "maxspeed_known_edges_pct", "Maxspeed conhecido", "Percentual das arestas com maxspeed informado."),
    ("faixas", "lanes_mean", "Faixas medias informadas", "Media dos valores numericos de lanes conhecidos."),
    ("faixas", "lanes_known_edges_pct", "Lanes conhecido", "Percentual das arestas com lanes informado."),
    ("comunidades", "communities_count", "Comunidades", "Quantidade de comunidades detectadas."),
    ("comunidades", "communities_largest_size", "Maior comunidade", "Tamanho da maior comunidade."),
    ("comunidades", "communities_largest_pct", "Maior comunidade (%)", "Participacao da maior comunidade no total classificado."),
    ("centralidade", "centrality_top_node_betweenness", "Maior betweenness de no", "Betweenness do no mais critico salvo em top_nodes.csv."),
    ("centralidade", "centrality_top_edge_betweenness", "Maior edge betweenness", "Edge betweenness da aresta mais critica."),
    ("centralidade", "centrality_top_closeness_approx_value", "Maior proximidade aproximada", "Maior centralidade de proximidade aproximada."),
    ("centralidade", "centrality_top_eigenvector_value", "Maior centralidade de autovetor", "Maior centralidade de autovetor."),
    ("topologia_funcao", "functional_maxspeed_betweenness_spearman", "Velocidade x intermediação", "Correlação de Spearman entre maxspeed e posição por intermediação."),
    ("topologia_funcao", "functional_lanes_betweenness_spearman", "Faixas x intermediação", "Correlação de Spearman entre lanes e posição por intermediação."),
    ("validacao", "validation_betweenness_rank_spearman_mean_at_120", "Validação da intermediação", "Correlação média do ranking aproximado de betweenness com o exato."),
    ("validacao", "validation_closeness_rank_spearman_mean_at_120", "Validação da proximidade", "Correlação média do ranking aproximado de closeness com o exato."),
    ("resiliencia", "resilience_targeted_final_lcc_fraction", "LCC final dirigida", "Fracao da maior componente no fim da remocao dirigida."),
    ("resiliencia", "resilience_targeted_lcc_fraction_drop", "Queda LCC dirigida", "Queda da fracao da maior componente na remocao dirigida."),
    ("resiliencia", "resilience_targeted_final_efficiency_topological_retained", "Eficiencia topologica retida dirigida", "Fracao da eficiencia topologica preservada no fim da remocao dirigida."),
    ("resiliencia", "resilience_targeted_final_efficiency_length_retained", "Eficiencia por distancia retida dirigida", "Fracao da eficiencia ponderada por distancia preservada no fim da remocao dirigida."),
    ("resiliencia", "resilience_targeted_adaptive_final_lcc_fraction", "LCC final dirigida adaptativa", "Fracao da maior componente no fim da remocao dirigida adaptativa."),
    ("resiliencia", "resilience_targeted_adaptive_lcc_fraction_drop", "Queda LCC dirigida adaptativa", "Queda da fracao da maior componente na remocao dirigida adaptativa."),
    ("resiliencia", "resilience_targeted_adaptive_final_efficiency_topological_retained", "Eficiencia topologica retida adaptativa", "Fracao da eficiencia topologica preservada no fim da remocao dirigida adaptativa."),
    ("resiliencia", "resilience_targeted_adaptive_final_efficiency_length_retained", "Eficiencia por distancia retida adaptativa", "Fracao da eficiencia ponderada por distancia preservada no fim da remocao dirigida adaptativa."),
    ("resiliencia", "resilience_random_final_lcc_fraction", "LCC final aleatoria", "Fracao da maior componente no fim da remocao aleatoria."),
    ("resiliencia", "resilience_random_lcc_fraction_drop", "Queda LCC aleatoria", "Queda da fracao da maior componente na remocao aleatoria."),
    ("resiliencia", "resilience_random_final_efficiency_topological_retained", "Eficiencia topologica retida aleatoria", "Fracao da eficiencia topologica preservada no fim da remocao aleatoria."),
    ("resiliencia", "resilience_random_final_efficiency_length_retained", "Eficiencia por distancia retida aleatoria", "Fracao da eficiencia ponderada por distancia preservada no fim da remocao aleatoria."),
    ("resiliencia_aleatoria_agregada", "resilience_random_aggregate_runs", "Repeticoes aleatorias arestas", "Quantidade de execucoes aleatorias agregadas por arestas."),
    ("resiliencia_aleatoria_agregada", "resilience_random_final_lcc_fraction_mean", "LCC media aleatoria arestas", "Media final da LCC nas repeticoes aleatorias por arestas."),
    ("resiliencia_aleatoria_agregada", "resilience_random_final_lcc_fraction_std", "Desvio LCC aleatoria arestas", "Desvio-padrao final da LCC nas repeticoes aleatorias por arestas."),
    ("resiliencia_aleatoria_agregada", "resilience_random_final_efficiency_topological_retained_mean", "Eficiencia media aleatoria arestas", "Media final da eficiencia topologica retida nas repeticoes aleatorias por arestas."),
    ("resiliencia_vertices", "node_resilience_targeted_final_lcc_fraction", "LCC final vértices dirigida", "Fração da maior componente após remoção dirigida de vértices."),
    ("resiliencia_vertices", "node_resilience_targeted_lcc_fraction_drop", "Queda LCC vértices dirigida", "Queda da maior componente após remoção dirigida de vértices."),
    ("resiliencia_vertices", "node_resilience_targeted_final_efficiency_topological_retained", "Eficiência vértices dirigida", "Eficiência topológica retida após remoção dirigida de vértices."),
    ("resiliencia_vertices", "node_resilience_targeted_final_efficiency_length_retained", "Eficiência distância vértices dirigida", "Eficiência por distância retida após remoção dirigida de vértices."),
    ("resiliencia_vertices", "node_resilience_targeted_adaptive_final_lcc_fraction", "LCC final vértices adaptativa", "Fração da maior componente após remoção adaptativa de vértices."),
    ("resiliencia_vertices", "node_resilience_targeted_adaptive_lcc_fraction_drop", "Queda LCC vértices adaptativa", "Queda da maior componente após remoção adaptativa de vértices."),
    ("resiliencia_vertices", "node_resilience_targeted_adaptive_final_efficiency_topological_retained", "Eficiência vértices adaptativa", "Eficiência topológica retida após remoção adaptativa de vértices."),
    ("resiliencia_vertices", "node_resilience_random_final_lcc_fraction", "LCC final vértices aleatória", "Fração da maior componente após remoção aleatória de vértices."),
    ("resiliencia_vertices", "node_resilience_random_lcc_fraction_drop", "Queda LCC vértices aleatória", "Queda da maior componente após remoção aleatória de vértices."),
    ("resiliencia_vertices", "node_resilience_random_final_efficiency_topological_retained", "Eficiência vértices aleatória", "Eficiência topológica retida após remoção aleatória de vértices."),
    ("resiliencia_vertices_aleatoria_agregada", "node_resilience_random_aggregate_runs", "Repeticoes aleatorias vértices", "Quantidade de execucoes aleatorias agregadas por vértices."),
    ("resiliencia_vertices_aleatoria_agregada", "node_resilience_random_final_lcc_fraction_mean", "LCC media aleatoria vértices", "Media final da LCC nas repeticoes aleatorias por vértices."),
    ("resiliencia_vertices_aleatoria_agregada", "node_resilience_random_final_lcc_fraction_std", "Desvio LCC aleatoria vértices", "Desvio-padrao final da LCC nas repeticoes aleatorias por vértices."),
    ("resiliencia_vertices_aleatoria_agregada", "node_resilience_random_final_efficiency_topological_retained_mean", "Eficiencia media aleatoria vértices", "Media final da eficiencia topologica retida nas repeticoes aleatorias por vértices."),
    ("resiliencia_comunidades", "community_resilience_targeted_final_lcc_nodes_fraction", "LCC final comunidades dirigida", "Fracao ponderada por nos na maior componente do grafo de comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_lcc_nodes_fraction_drop", "Queda LCC comunidades dirigida", "Queda da fracao ponderada por nos no grafo de comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_final_efficiency_topological_retained", "Eficiencia comunidades dirigida", "Fracao da eficiencia topologica retida no grafo de comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_adaptive_final_lcc_nodes_fraction", "LCC final comunidades adaptativa", "Fracao ponderada por nos na maior componente apos remocao adaptativa."),
    ("resiliencia_comunidades", "community_resilience_targeted_adaptive_lcc_nodes_fraction_drop", "Queda LCC comunidades adaptativa", "Queda da fracao ponderada por nos no ataque adaptativo entre comunidades."),
    ("resiliencia_comunidades", "community_resilience_targeted_adaptive_final_efficiency_topological_retained", "Eficiencia comunidades adaptativa", "Fracao da eficiencia topologica retida no ataque adaptativo entre comunidades."),
    ("resiliencia_comunidades", "community_resilience_random_final_lcc_nodes_fraction", "LCC final comunidades aleatoria", "Fracao ponderada por nos na maior componente com remocao aleatoria."),
    ("resiliencia_comunidades", "community_resilience_random_lcc_nodes_fraction_drop", "Queda LCC comunidades aleatoria", "Queda da fracao ponderada por nos no grafo de comunidades."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_auc_lcc_mean", "AUC media interna dirigida", "Media da resiliencia interna das comunidades sob remocao dirigida."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_auc_lcc_min", "Menor AUC interna dirigida", "Comunidade mais fragil sob remocao dirigida."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_final_lcc_mean", "LCC final interna media dirigida", "Media da fracao final da maior componente dentro de cada comunidade."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_targeted_adaptive_auc_lcc_mean", "AUC media interna adaptativa", "Media da resiliencia interna das comunidades sob remocao adaptativa."),
    ("resiliencia_interna_comunidades", "intra_community_resilience_random_auc_lcc_mean", "AUC media interna aleatoria", "Baseline aleatorio medio da resiliencia interna das comunidades."),
    ("vulnerabilidade", "vulnerability_top_node_score", "Maior vulnerabilidade de nó", "Maior score composto de vulnerabilidade entre nós."),
    ("vulnerabilidade", "vulnerability_articulation_nodes", "Nós de articulação", "Quantidade de nós cuja remoção aumenta a fragmentação da rede."),
    ("vulnerabilidade", "vulnerability_top_edge_score", "Maior vulnerabilidade de aresta", "Maior score composto de vulnerabilidade entre arestas."),
    ("vulnerabilidade", "vulnerability_bridge_edges", "Pontes estruturais", "Quantidade de arestas cuja remoção aumenta a fragmentação da rede."),
    ("gargalos_estruturais", "structural_articulation_nodes", "Nós de articulação estruturais", "Quantidade de nós cuja remoção fragmenta a rede."),
    ("gargalos_estruturais", "structural_bridge_edges", "Pontes estruturais diretas", "Quantidade de arestas cuja remoção fragmenta a rede."),
    ("gargalos_estruturais", "structural_top_articulation_detached_nodes", "Maior impacto por articulação", "Nós destacados pela remoção do principal nó de articulação."),
    ("gargalos_estruturais", "structural_top_bridge_detached_nodes", "Maior impacto por ponte", "Nós destacados pela remoção da principal ponte estrutural."),
    ("gargalos_estruturais", "structural_top_bottleneck_score", "Maior score de gargalo", "Score composto do principal gargalo estrutural."),
    ("gargalos_estruturais", "structural_top_bottleneck_detached_nodes", "Maior impacto de gargalo", "Nós destacados pelo principal gargalo estrutural."),
    ("redundancia_rotas", "route_redundancy_sampled_pairs", "Pares OD amostrados", "Quantidade de pares origem-destino usados no perfil de redundância."),
    ("redundancia_rotas", "route_redundancy_alternative_rate", "Taxa com alternativa", "Fração dos pares com alguma rota alternativa após bloqueio da melhor rota."),
    ("redundancia_rotas", "route_redundancy_reasonable_rate", "Taxa com alternativa razoável", "Fração dos pares com alternativa dentro do limiar configurado."),
    ("redundancia_rotas", "route_redundancy_disconnected_rate", "Taxa sem rota após bloqueio", "Fração dos pares que ficam desconectados após bloqueio da melhor rota."),
    ("redundancia_rotas", "route_redundancy_alternative_ratio_mean", "Razão média alternativa/melhor", "Distância média da alternativa em relação à melhor rota."),
    ("redundancia_rotas", "route_redundancy_detour_distance_m_mean", "Desvio médio da alternativa", "Acréscimo médio de distância em metros quando há alternativa."),
    ("multiescala_espacial", "spatial_populated_cells", "Células povoadas", "Quantidade de células espaciais com pelo menos um nó."),
    ("multiescala_espacial", "spatial_mean_nodes_per_cell", "Nós médios por célula", "Média de nós por célula povoada."),
    ("multiescala_espacial", "spatial_mean_degree_by_cell", "Grau médio local", "Média do grau médio local entre células."),
    ("multiescala_espacial", "spatial_mean_vulnerability_by_cell", "Vulnerabilidade média local", "Média da vulnerabilidade média local entre células."),
    ("multiescala_espacial", "spatial_mean_route_redundancy_reasonable_rate", "Redundância razoável local", "Média da taxa local de alternativas razoáveis nas células com pares OD."),
    ("multiescala_espacial", "spatial_mean_route_redundancy_disconnected_rate", "Desconexão local", "Média da taxa local de desconexão após bloqueio nas células com pares OD."),
    ("multiescala_espacial", "spatial_top_vulnerability_value", "Maior vulnerabilidade local", "Maior vulnerabilidade observada em uma célula espacial."),
    ("robustez_espacial", "spatial_robustness_tested_cells", "Células testadas", "Quantidade de células com bloqueio espacial simulado."),
    ("robustez_espacial", "spatial_robustness_mean_removed_edges", "Arestas removidas médias", "Média de arestas removidas por bloqueio regional."),
    ("robustez_espacial", "spatial_robustness_mean_lcc_fraction_drop", "Queda LCC média espacial", "Queda média da maior componente após bloqueios regionais."),
    ("robustez_espacial", "spatial_robustness_max_lcc_fraction_drop", "Maior queda LCC espacial", "Maior queda da maior componente causada por uma célula."),
    ("robustez_espacial", "spatial_robustness_mean_efficiency_retained", "Eficiência média retida espacial", "Eficiência topológica média retida após bloqueios regionais."),
    ("robustez_espacial", "spatial_robustness_min_efficiency_retained", "Menor eficiência retida espacial", "Menor eficiência topológica retida após um bloqueio regional."),
    ("robustez_espacial", "spatial_robustness_max_components_increase", "Maior fragmentação espacial", "Maior aumento no número de componentes após um bloqueio regional."),
    ("hierarquia_viaria", "road_hierarchy_arterial_edge_fraction", "Arestas arteriais", "Fração de arestas nas classes motorway, trunk, primary e secondary."),
    ("hierarquia_viaria", "road_hierarchy_arterial_length_fraction", "Extensão arterial", "Fração da extensão viária nas classes arteriais."),
    ("hierarquia_viaria", "road_hierarchy_local_edge_fraction", "Arestas locais", "Fração de arestas nas classes residencial, living_street e service."),
    ("hierarquia_viaria", "road_hierarchy_top_lcc_dependency_drop", "Dependência LCC por classe", "Maior queda da maior componente causada pela remoção de uma classe highway."),
    ("hierarquia_viaria", "road_hierarchy_top_efficiency_retained", "Eficiência retida por classe crítica", "Eficiência topológica retida após remoção da classe mais crítica por eficiência."),
    ("hierarquia_viaria", "road_hierarchy_top_centrality_class", "Classe mais central", "Classe highway com maior edge betweenness observado no ranking de arestas críticas."),
    ("morfologia_urbana", "urban_morphology_dominant_class", "Classe morfológica dominante", "Padrão morfológico mais frequente nas células espaciais."),
    ("morfologia_urbana", "urban_morphology_insufficient_fraction", "Fração insuficiente", "Fração de células povoadas com poucos elementos para classificação morfológica."),
    ("morfologia_urbana", "urban_morphology_grid_fraction", "Fração gradeada", "Fração das células classificadas como gradeadas."),
    ("morfologia_urbana", "urban_morphology_radial_linear_fraction", "Fração radial/linear", "Fração das células classificadas como radiais ou lineares."),
    ("morfologia_urbana", "urban_morphology_organic_fraction", "Fração orgânica", "Fração das células classificadas como orgânicas."),
    ("morfologia_urbana", "urban_morphology_fragmented_fraction", "Fração fragmentada", "Fração das células classificadas como fragmentadas."),
    ("morfologia_urbana", "urban_morphology_mean_orientation_entropy", "Entropia angular média", "Diversidade média das orientações viárias locais."),
    ("morfologia_urbana", "urban_morphology_mean_orthogonal_share", "Ortogonalidade média", "Participação média dos dois eixos ortogonais dominantes."),
    ("morfologia_urbana", "urban_morphology_mean_segment_length_m", "Segmento médio", "Comprimento médio dos segmentos viários nas células classificadas."),
    ("eficiencia_od", "od_efficiency_sampled_pairs", "Pares OD eficiência", "Quantidade de pares origem-destino amostrados para eficiência estatística."),
    ("eficiencia_od", "od_efficiency_route_distance_m_mean", "Distância média OD", "Distância média das rotas mínimas entre pares OD."),
    ("eficiencia_od", "od_efficiency_route_distance_m_p90", "Distância OD P90", "Percentil 90 da distância das rotas mínimas."),
    ("eficiencia_od", "od_efficiency_hops_mean", "Hops médios OD", "Quantidade média de segmentos por rota OD."),
    ("eficiencia_od", "od_efficiency_circuity_ratio_mean", "Circuity média OD", "Distância da rota dividida pela distância direta geográfica."),
    ("eficiencia_od", "od_efficiency_circuity_ratio_p90", "Circuity P90 OD", "Percentil 90 do desvio das rotas."),
    ("eficiencia_od", "od_efficiency_route_efficiency_mean", "Eficiência média OD", "Distância direta dividida pela distância da rota."),
    ("eficiencia_od", "od_efficiency_accessibility_within_5km_rate", "Acessibilidade até 5 km", "Fração dos pares OD com rota até 5 km."),
    ("eficiencia_od", "od_efficiency_accessibility_within_10km_rate", "Acessibilidade até 10 km", "Fração dos pares OD com rota até 10 km."),
    ("eficiencia_od", "od_efficiency_high_detour_rate", "Taxa de alto desvio OD", "Fração dos pares com circuity acima de 1,75."),
    ("subcentros", "subcenters_count", "Células candidatas", "Quantidade de células candidatas de alta centralidade topológica."),
    ("subcentros", "subcenters_fraction", "Fração de candidatas", "Fração de células povoadas selecionadas como candidatas topológicas."),
    ("subcentros", "subcenters_polycentricity_index", "Dispersão exploratória", "Distribuição da importância estrutural entre células candidatas."),
    ("subcentros", "subcenters_monocentricity_index", "Dominância exploratória", "Participação da principal célula candidata no score total."),
    ("subcentros", "subcenters_score_entropy", "Entropia das candidatas", "Entropia normalizada dos scores das células candidatas."),
    ("subcentros", "subcenters_top_score", "Maior score candidato", "Maior score de candidatura topológica."),
    ("barreiras_urbanas", "urban_barriers_spatial_permeability_index", "Permeabilidade espacial", "Permeabilidade média entre células espaciais vizinhas."),
    ("barreiras_urbanas", "urban_barriers_exposure_index", "Exposição a barreiras", "Índice composto de exposição da rede a barreiras topológicas."),
    ("barreiras_urbanas", "urban_barriers_low_permeability_cells", "Células pouco permeáveis", "Quantidade de células com permeabilidade inferior a 0,50."),
    ("barreiras_urbanas", "urban_barriers_missing_adjacent_connections", "Conexões vizinhas ausentes", "Pares de células vizinhas sem conexão viária direta."),
    ("barreiras_urbanas", "urban_barriers_critical_structural_connections", "Travessias críticas", "Conexões entre regiões que passam por pontes estruturais."),
    ("barreiras_urbanas", "urban_barriers_top_barrier_score", "Maior score de barreira", "Maior score de barreira provável observado entre regiões."),
    ("perfil_escala", "network_scale_multiscale_robustness_index", "Robustez multiescalar", "Estabilidade média das principais métricas locais entre escalas."),
    ("perfil_escala", "network_scale_least_stable_score", "Menor estabilidade por escala", "Score de estabilidade da métrica mais sensível à escala."),
    ("perfil_escala", "network_scale_least_stable_cv", "Maior CV por escala", "Coeficiente de variação da métrica mais sensível à escala."),
    ("perfil_escala", "network_scale_most_stable_score", "Maior estabilidade por escala", "Score de estabilidade da métrica mais estável entre escalas."),
]

for _modality, _modality_label in [
    ("edge", "arestas"),
    ("node", "vértices"),
    ("community", "comunidades"),
]:
    for _strategy, _strategy_label in [
        ("random", "aleatória"),
        ("targeted", "dirigida"),
        ("targeted_adaptive", "dirigida adaptativa"),
    ]:
        for _metric, _metric_label in [
            ("lcc", "LCC"),
            ("efficiency_topological", "eficiência topológica"),
            ("efficiency_length", "eficiência por distância"),
        ]:
            COMPARISON_METRICS.append(
                (
                    "sintese_robustez",
                    f"robustness_{_modality}_{_strategy}_{_metric}_auc_normalized_mean",
                    f"AUC {_metric_label} - {_modality_label} - {_strategy_label}",
                    "AUC normalizada da resposta retida no intervalo comum; valores maiores indicam maior robustez estrutural.",
                )
            )


def _safe_name(value: str) -> str:
    return "".join(ch if ch.isalnum() or ch in {"_", "-"} else "_" for ch in value)


def _summary_for_dataset(dataset: str) -> dict[str, dict[str, str]]:
    graph_path = dataset_graph_path(dataset, "clean")
    if not graph_path.exists():
        raise FileNotFoundError(f"Grafo limpo nao encontrado para '{dataset}': {graph_path}")

    gerar_planilha_grafo(dataset)
    rows = _read_csv_dicts(f"outputs/{dataset}/metrics/graph_inventory_summary.csv")
    return {row.get("indicador", ""): row for row in rows if row.get("indicador")}


def _value(summary: dict[str, dict[str, str]], metric: str) -> str:
    row = summary.get(metric)
    if not row:
        return ""
    return row.get("valor", "")


def _unit(summary: dict[str, dict[str, str]], metric: str) -> str:
    row = summary.get(metric)
    if not row:
        return ""
    return row.get("unidade", "")


def _delta(first: str, second: str, unit: str, metric: str) -> str:
    a = _as_float(first)
    b = _as_float(second)
    if a is None or b is None:
        return "-"

    diff = b - a
    formatted = _format_value(diff, unit, metric)
    if diff > 0:
        return f"+{formatted}"
    return formatted


def _comparison_table(datasets: list[str], summaries: dict[str, dict[str, dict[str, str]]]) -> str:
    include_delta = len(datasets) == 2
    headers = ["Grupo", "Indicador", *datasets]
    if include_delta:
        headers.append(f"Delta {datasets[1]} - {datasets[0]}")
    headers.append("Descricao")

    rows = []
    for group, metric, label, description in COMPARISON_METRICS:
        cells = [f"<td>{_e(group)}</td>", f"<td><strong>{_e(label)}</strong><br><code>{_e(metric)}</code></td>"]
        raw_values = []
        unit = ""
        for dataset in datasets:
            summary = summaries[dataset]
            raw = _value(summary, metric)
            unit = _unit(summary, metric) or unit
            raw_values.append(raw)
            cells.append(f"<td class=\"numeric\">{_format_value(raw, unit, metric) if raw != '' else '<span class=\"missing\">nao encontrado</span>'}</td>")
        if include_delta:
            cells.append(f"<td class=\"numeric delta\">{_e(_delta(raw_values[0], raw_values[1], unit, metric))}</td>")
        cells.append(f"<td>{_e(description)}</td>")
        rows.append("<tr>" + "".join(cells) + "</tr>")

    header_html = "".join(f"<th>{_e(header)}</th>" for header in headers)
    return f"""
    <section class="panel wide">
      <h2>Comparacao Consolidada</h2>
      <div class="table-wrap">
        <table>
          <thead><tr>{header_html}</tr></thead>
          <tbody>{''.join(rows)}</tbody>
        </table>
      </div>
    </section>
    """


def _write_comparison_csv(
    datasets: list[str],
    summaries: dict[str, dict[str, dict[str, str]]],
    output_path: str,
) -> str:
    csv_path = str(Path(output_path).with_suffix(".csv"))
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=[
                "dataset",
                "grupo",
                "indicador",
                "rotulo",
                "valor",
                "unidade",
                "descricao",
            ],
        )
        writer.writeheader()
        for group, metric, label, description in COMPARISON_METRICS:
            for dataset in datasets:
                summary = summaries[dataset]
                writer.writerow(
                    {
                        "dataset": dataset,
                        "grupo": group,
                        "indicador": metric,
                        "rotulo": label,
                        "valor": _value(summary, metric),
                        "unidade": _unit(summary, metric),
                        "descricao": description,
                    }
                )
    return csv_path


def _dataset_cards(datasets: list[str], summaries: dict[str, dict[str, dict[str, str]]]) -> str:
    cards = []
    for dataset in datasets:
        summary = summaries[dataset]
        nodes = _format_value(_value(summary, "nodes"), _unit(summary, "nodes"), "nodes")
        edges = _format_value(_value(summary, "edges"), _unit(summary, "edges"), "edges")
        length = _format_value(
            _value(summary, "physical_collapsed_length_km"),
            _unit(summary, "physical_collapsed_length_km"),
            "physical_collapsed_length_km",
        )
        lcc_drop = _format_value(
            _value(summary, "resilience_targeted_lcc_fraction_drop"),
            _unit(summary, "resilience_targeted_lcc_fraction_drop"),
            "resilience_targeted_lcc_fraction_drop",
        )
        paved_est = _format_value(
            _value(summary, "estimated_paved_edges_pct"),
            _unit(summary, "estimated_paved_edges_pct"),
            "estimated_paved_edges_pct",
        )
        surface_known = _format_value(
            _value(summary, "surface_known_edges_pct"),
            _unit(summary, "surface_known_edges_pct"),
            "surface_known_edges_pct",
        )
        cards.append(
            f"""
            <article class="card">
              <div class="card-title">{_e(dataset)}</div>
              <div class="mini-grid">
                <div><strong>{nodes}</strong><span>Nos</span></div>
                <div><strong>{edges}</strong><span>Arestas</span></div>
                <div><strong>{length} km</strong><span>Extensão física (proxy)</span></div>
                <div><strong>{paved_est}</strong><span>Asfalto estimado</span></div>
                <div><strong>{surface_known}</strong><span>Surface conhecido</span></div>
                <div><strong>{lcc_drop}</strong><span>Queda LCC dirigida</span></div>
              </div>
            </article>
            """
        )
    return f"<section class=\"cards\">{''.join(cards)}</section>"


def _link_grid(datasets: list[str]) -> str:
    items = []
    for dataset in datasets:
        dashboard = Path(f"outputs/{dataset}/dashboard_{dataset}.html")
        inventory = Path(f"outputs/{dataset}/metrics/graph_inventory_summary.csv")
        report = Path(f"outputs/{dataset}/REPORT_{dataset}.md")
        links = []
        if dashboard.exists():
            links.append(f"<a href=\"../{_e(dataset)}/dashboard_{_e(dataset)}.html\">Dashboard</a>")
        if inventory.exists():
            links.append(f"<a href=\"../{_e(dataset)}/metrics/graph_inventory_summary.csv\">Inventario CSV</a>")
        if report.exists():
            links.append(f"<a href=\"../{_e(dataset)}/REPORT_{_e(dataset)}.md\">Relatorio MD</a>")
        items.append(
            f"""
            <div class="link-box">
              <strong>{_e(dataset)}</strong>
              <span>{' · '.join(links) if links else 'Sem links auxiliares encontrados'}</span>
            </div>
            """
        )
    return f"""
    <section class="panel wide">
      <h2>Arquivos de Origem</h2>
      <div class="link-grid">{''.join(items)}</div>
    </section>
    """


def _artifact_path(dataset: str, kind: str) -> Path:
    if kind == "roads":
        return Path(f"outputs/{dataset}/figures/grafo_{dataset}_clean_ruas.png")
    if kind == "roads_nodes":
        return Path(f"outputs/{dataset}/figures/grafo_{dataset}_clean_ruas_nos.png")
    if kind == "communities_graph":
        return Path(f"outputs/{dataset}/figures/grafo_{dataset}_clean_comunidades.png")
    if kind == "degree":
        return Path(f"outputs/{dataset}/figures/degree_distribution_loglog.png")
    if kind == "resilience_targeted":
        return Path(f"outputs/{dataset}/figures/resilience_curve_targeted.png")
    if kind == "resilience_targeted_adaptive":
        return Path(f"outputs/{dataset}/figures/resilience_curve_targeted_adaptive.png")
    if kind == "resilience_random":
        return Path(f"outputs/{dataset}/figures/resilience_curve_random.png")
    if kind == "resilience_random_aggregate":
        return Path(f"outputs/{dataset}/figures/resilience_random_aggregate.png")
    if kind == "node_resilience_targeted":
        return Path(f"outputs/{dataset}/figures/node_resilience_curve_targeted.png")
    if kind == "node_resilience_targeted_adaptive":
        return Path(f"outputs/{dataset}/figures/node_resilience_curve_targeted_adaptive.png")
    if kind == "node_resilience_random":
        return Path(f"outputs/{dataset}/figures/node_resilience_curve_random.png")
    if kind == "node_resilience_random_aggregate":
        return Path(f"outputs/{dataset}/figures/node_resilience_random_aggregate.png")
    if kind == "community_resilience_targeted":
        return Path(f"outputs/{dataset}/figures/community_resilience_curve_targeted.png")
    if kind == "community_resilience_targeted_adaptive":
        return Path(f"outputs/{dataset}/figures/community_resilience_curve_targeted_adaptive.png")
    if kind == "community_resilience_random":
        return Path(f"outputs/{dataset}/figures/community_resilience_curve_random.png")
    if kind == "intra_community_resilience_targeted":
        return Path(f"outputs/{dataset}/figures/intra_community_resilience_targeted.png")
    if kind == "intra_community_resilience_targeted_adaptive":
        return Path(f"outputs/{dataset}/figures/intra_community_resilience_targeted_adaptive.png")
    if kind == "intra_community_resilience_random":
        return Path(f"outputs/{dataset}/figures/intra_community_resilience_random.png")
    if kind == "route_map":
        return Path(f"outputs/{dataset}/maps/rota_distancia.html")
    if kind == "critical_map":
        return Path(f"outputs/{dataset}/maps/pontos_criticos.html")
    if kind == "critical_edges_map":
        return Path(f"outputs/{dataset}/maps/arestas_criticas.html")
    if kind == "vulnerability_nodes_map":
        return Path(f"outputs/{dataset}/maps/vulnerability_nodes.html")
    if kind == "vulnerability_edges_map":
        return Path(f"outputs/{dataset}/maps/vulnerability_edges.html")
    if kind == "structural_articulations_map":
        return Path(f"outputs/{dataset}/maps/structural_articulations.html")
    if kind == "structural_bridges_map":
        return Path(f"outputs/{dataset}/maps/structural_bridges.html")
    if kind == "structural_bottlenecks_map":
        return Path(f"outputs/{dataset}/maps/structural_bottlenecks.html")
    if kind == "route_redundancy_map":
        return Path(f"outputs/{dataset}/maps/route_redundancy.html")
    if kind == "spatial_multiscale_vulnerability_map":
        return Path(f"outputs/{dataset}/maps/spatial_multiscale_vulnerability.html")
    if kind == "spatial_multiscale_connectivity_map":
        return Path(f"outputs/{dataset}/maps/spatial_multiscale_connectivity.html")
    if kind == "spatial_multiscale_redundancy_map":
        return Path(f"outputs/{dataset}/maps/spatial_multiscale_redundancy.html")
    if kind == "spatial_robustness_lcc_map":
        return Path(f"outputs/{dataset}/maps/spatial_robustness_lcc_drop.html")
    if kind == "spatial_robustness_efficiency_map":
        return Path(f"outputs/{dataset}/maps/spatial_robustness_efficiency_drop.html")
    if kind == "spatial_robustness_fragmentation_map":
        return Path(f"outputs/{dataset}/maps/spatial_robustness_fragmentation.html")
    if kind == "road_hierarchy_map":
        return Path(f"outputs/{dataset}/maps/road_hierarchy_impact.html")
    if kind == "urban_morphology_class_map":
        return Path(f"outputs/{dataset}/maps/urban_morphology_classes.html")
    if kind == "urban_morphology_entropy_map":
        return Path(f"outputs/{dataset}/maps/urban_morphology_orientation_entropy.html")
    if kind == "urban_morphology_connectivity_map":
        return Path(f"outputs/{dataset}/maps/urban_morphology_connectivity.html")
    if kind == "od_efficiency_map":
        return Path(f"outputs/{dataset}/maps/od_efficiency_routes.html")
    if kind == "subcenters_map":
        return Path(f"outputs/{dataset}/maps/subcenters.html")
    if kind == "urban_barriers_permeability_map":
        return Path(f"outputs/{dataset}/maps/urban_barriers_permeability.html")
    if kind == "urban_barriers_connections_map":
        return Path(f"outputs/{dataset}/maps/urban_barriers_connections.html")
    if kind == "network_scale_metrics":
        return Path(f"outputs/{dataset}/figures/network_scale_profile_metrics.png")
    if kind == "network_scale_stability":
        return Path(f"outputs/{dataset}/figures/network_scale_profile_stability.png")
    if kind == "network_scale_map":
        return Path(f"outputs/{dataset}/maps/network_scale_profile_low_permeability.html")
    if kind == "communities_map":
        return Path(f"outputs/{dataset}/maps/comunidades.html")
    raise ValueError(f"Tipo de artefato desconhecido: {kind}")


def _artifact_src(path: Path, output_path: str) -> str:
    try:
        return path.relative_to(Path(output_path).parent).as_posix()
    except ValueError:
        try:
            return Path("../") / path.relative_to("outputs")
        except ValueError:
            return path.as_posix()


def _visual_compare_block(title: str, datasets: list[str], kind: str, media_type: str, output_path: str) -> str:
    cells = []
    found_any = False
    for dataset in datasets:
        path = _artifact_path(dataset, kind)
        if path.exists():
            found_any = True
            if media_type == "iframe":
                media = f'<iframe src="{_e(_artifact_src(path, output_path))}" loading="lazy"></iframe>'
            else:
                media = f'<img class="visual-img" src="{_e(_artifact_src(path, output_path))}" alt="{_e(title)} - {_e(dataset)}">'
        else:
            media = '<div class="missing-visual">Artefato nao encontrado</div>'

        cells.append(
            f"""
            <article class="visual-card">
              <h3>{_e(dataset)}</h3>
              {media}
            </article>
            """
        )

    if not found_any:
        return ""

    return f"""
    <section class="panel wide">
      <h2>{_e(title)}</h2>
      <div class="visual-grid" style="--cols: {len(datasets)}">
        {''.join(cells)}
      </div>
    </section>
    """


def _side_by_side_dashboard(datasets: list[str], output_path: str) -> str:
    blocks = [
        _visual_compare_block("Grafo de Ruas", datasets, "roads", "image", output_path),
        _visual_compare_block("Grafo de Ruas + Nos", datasets, "roads_nodes", "image", output_path),
        _visual_compare_block("Grafo por Comunidades", datasets, "communities_graph", "image", output_path),
        _visual_compare_block("Distribuicao de Grau", datasets, "degree", "image", output_path),
        _visual_compare_block("Robustez estrutural - Remocao Dirigida", datasets, "resilience_targeted", "image", output_path),
        _visual_compare_block("Robustez estrutural - Remocao Dirigida Adaptativa", datasets, "resilience_targeted_adaptive", "image", output_path),
        _visual_compare_block("Robustez estrutural - Remocao Aleatoria", datasets, "resilience_random", "image", output_path),
        _visual_compare_block("Robustez estrutural - Aleatoria Agregada", datasets, "resilience_random_aggregate", "image", output_path),
        _visual_compare_block("Robustez por Vertices - Dirigida", datasets, "node_resilience_targeted", "image", output_path),
        _visual_compare_block("Robustez por Vertices - Dirigida Adaptativa", datasets, "node_resilience_targeted_adaptive", "image", output_path),
        _visual_compare_block("Robustez por Vertices - Aleatoria", datasets, "node_resilience_random", "image", output_path),
        _visual_compare_block("Robustez por Vertices - Aleatoria Agregada", datasets, "node_resilience_random_aggregate", "image", output_path),
        _visual_compare_block("Robustez por Comunidades - Dirigida", datasets, "community_resilience_targeted", "image", output_path),
        _visual_compare_block("Robustez por Comunidades - Dirigida Adaptativa", datasets, "community_resilience_targeted_adaptive", "image", output_path),
        _visual_compare_block("Robustez por Comunidades - Aleatoria", datasets, "community_resilience_random", "image", output_path),
        _visual_compare_block("Robustez Interna por Comunidade - Dirigida", datasets, "intra_community_resilience_targeted", "image", output_path),
        _visual_compare_block("Robustez Interna por Comunidade - Dirigida Adaptativa", datasets, "intra_community_resilience_targeted_adaptive", "image", output_path),
        _visual_compare_block("Robustez Interna por Comunidade - Aleatoria", datasets, "intra_community_resilience_random", "image", output_path),
        _visual_compare_block("Mapa de Rota", datasets, "route_map", "iframe", output_path),
        _visual_compare_block("Mapa de Pontos Criticos", datasets, "critical_map", "iframe", output_path),
        _visual_compare_block("Mapa de Arestas Criticas", datasets, "critical_edges_map", "iframe", output_path),
        _visual_compare_block("Mapa de Vulnerabilidade - Nos", datasets, "vulnerability_nodes_map", "iframe", output_path),
        _visual_compare_block("Mapa de Vulnerabilidade - Arestas", datasets, "vulnerability_edges_map", "iframe", output_path),
        _visual_compare_block("Mapa de Gargalos - Articulacoes", datasets, "structural_articulations_map", "iframe", output_path),
        _visual_compare_block("Mapa de Gargalos - Pontes", datasets, "structural_bridges_map", "iframe", output_path),
        _visual_compare_block("Mapa de Gargalos - Ranking Combinado", datasets, "structural_bottlenecks_map", "iframe", output_path),
        _visual_compare_block("Mapa de Redundancia de Rotas", datasets, "route_redundancy_map", "iframe", output_path),
        _visual_compare_block("Mapa Multiescala - Vulnerabilidade", datasets, "spatial_multiscale_vulnerability_map", "iframe", output_path),
        _visual_compare_block("Mapa Multiescala - Conectividade", datasets, "spatial_multiscale_connectivity_map", "iframe", output_path),
        _visual_compare_block("Mapa Multiescala - Baixa Redundancia", datasets, "spatial_multiscale_redundancy_map", "iframe", output_path),
        _visual_compare_block("Mapa Robustez Espacial - Queda LCC", datasets, "spatial_robustness_lcc_map", "iframe", output_path),
        _visual_compare_block("Mapa Robustez Espacial - Queda Eficiencia", datasets, "spatial_robustness_efficiency_map", "iframe", output_path),
        _visual_compare_block("Mapa Robustez Espacial - Fragmentacao", datasets, "spatial_robustness_fragmentation_map", "iframe", output_path),
        _visual_compare_block("Mapa de Hierarquia Viaria", datasets, "road_hierarchy_map", "iframe", output_path),
        _visual_compare_block("Mapa Morfologico - Classes Urbanas", datasets, "urban_morphology_class_map", "iframe", output_path),
        _visual_compare_block("Mapa Morfologico - Entropia Angular", datasets, "urban_morphology_entropy_map", "iframe", output_path),
        _visual_compare_block("Mapa Morfologico - Conectividade", datasets, "urban_morphology_connectivity_map", "iframe", output_path),
        _visual_compare_block("Mapa Eficiencia OD - Rotas com Maior Desvio", datasets, "od_efficiency_map", "iframe", output_path),
        _visual_compare_block("Mapa de Células Candidatas de Alta Centralidade", datasets, "subcenters_map", "iframe", output_path),
        _visual_compare_block("Mapa de Barreiras Urbanas - Permeabilidade", datasets, "urban_barriers_permeability_map", "iframe", output_path),
        _visual_compare_block("Mapa de Barreiras Urbanas - Conexoes", datasets, "urban_barriers_connections_map", "iframe", output_path),
        _visual_compare_block("Perfil de Escala - Metricas", datasets, "network_scale_metrics", "image", output_path),
        _visual_compare_block("Perfil de Escala - Estabilidade", datasets, "network_scale_stability", "image", output_path),
        _visual_compare_block("Mapa Perfil de Escala - Baixa Permeabilidade", datasets, "network_scale_map", "iframe", output_path),
        _visual_compare_block("Mapa de Comunidades", datasets, "communities_map", "iframe", output_path),
    ]
    return "".join(blocks)


def gerar_comparacao_html(datasets: list[str], output_path: str | None = None) -> dict:
    if len(datasets) < 2:
        raise ValueError("Passe pelo menos dois datasets para comparar.")

    datasets = [_safe_name(dataset) for dataset in datasets]
    audit = auditar_comparabilidade(datasets)
    summaries = {dataset: _summary_for_dataset(dataset) for dataset in datasets}

    compare_dir = Path("outputs/comparisons")
    compare_dir.mkdir(parents=True, exist_ok=True)
    if output_path is None:
        output_path = str(compare_dir / f"compare_{'_vs_'.join(datasets)}.html")
    comparison_csv = _write_comparison_csv(datasets, summaries, output_path)

    css = """
    :root {
      --bg: #f6f7f9;
      --panel: #ffffff;
      --text: #1f2933;
      --muted: #687385;
      --line: #d9dee7;
      --accent: #1769aa;
      --accent-soft: #e8f2fb;
    }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
      line-height: 1.45;
    }
    header {
      padding: 32px 40px 20px;
      background: #fff;
      border-bottom: 1px solid var(--line);
    }
    header h1 { margin: 0 0 8px; font-size: 32px; letter-spacing: 0; }
    header p { margin: 0; color: var(--muted); }
    main {
      padding: 24px 40px 48px;
      display: grid;
      grid-template-columns: repeat(12, 1fr);
      gap: 18px;
    }
    .cards {
      grid-column: 1 / -1;
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 14px;
    }
    .card, .panel {
      background: var(--panel);
      border: 1px solid var(--line);
      border-radius: 8px;
      box-shadow: 0 1px 2px rgba(20, 30, 45, 0.04);
    }
    .card { padding: 16px; }
    .card-title {
      color: var(--muted);
      font-size: 13px;
      text-transform: uppercase;
      letter-spacing: .04em;
      margin-bottom: 12px;
    }
    .mini-grid {
      display: grid;
      grid-template-columns: repeat(2, minmax(0, 1fr));
      gap: 12px;
    }
    .mini-grid strong { display: block; font-size: 22px; }
    .mini-grid span { display: block; color: var(--muted); font-size: 13px; }
    .panel {
      grid-column: span 6;
      padding: 18px;
      min-width: 0;
    }
    .panel.wide { grid-column: 1 / -1; }
    h2 { margin: 0 0 14px; font-size: 19px; letter-spacing: 0; }
    .table-wrap {
      overflow: auto;
      border: 1px solid var(--line);
      border-radius: 6px;
    }
    table {
      width: 100%;
      border-collapse: collapse;
      font-size: 13px;
      background: #fff;
    }
    th, td {
      padding: 9px 10px;
      border-bottom: 1px solid var(--line);
      text-align: left;
      vertical-align: top;
      white-space: nowrap;
    }
    th {
      background: var(--accent-soft);
      color: #123a5b;
      font-weight: 650;
    }
    td.numeric {
      text-align: right;
      font-variant-numeric: tabular-nums;
    }
    td.delta {
      font-weight: 700;
      color: #0f5c37;
    }
    code {
      background: #eef1f5;
      padding: 2px 5px;
      border-radius: 4px;
      color: #314255;
    }
    .missing { color: var(--muted); }
    .link-grid {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(260px, 1fr));
      gap: 12px;
    }
    .link-box {
      border: 1px solid var(--line);
      border-radius: 6px;
      padding: 12px;
      background: #f9fafb;
    }
    .link-box strong, .link-box span { display: block; }
    .link-box span { color: var(--muted); margin-top: 4px; }
    .visual-grid {
      display: grid;
      grid-template-columns: repeat(var(--cols), minmax(360px, 1fr));
      gap: 14px;
      overflow-x: auto;
      padding-bottom: 4px;
    }
    .visual-card {
      min-width: 360px;
      border: 1px solid var(--line);
      border-radius: 8px;
      background: #f9fafb;
      padding: 12px;
    }
    .visual-card h3 {
      margin: 0 0 10px;
      font-size: 16px;
    }
    .visual-img {
      display: block;
      width: 100%;
      height: 420px;
      object-fit: contain;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    iframe {
      width: 100%;
      height: 460px;
      border: 1px solid var(--line);
      border-radius: 6px;
      background: #fff;
    }
    .missing-visual {
      display: grid;
      place-items: center;
      min-height: 180px;
      color: var(--muted);
      border: 1px dashed var(--line);
      border-radius: 6px;
      background: #fff;
    }
    a { color: var(--accent); text-decoration: none; font-weight: 600; }
    a:hover { text-decoration: underline; }
    @media (max-width: 900px) {
      header, main { padding-left: 18px; padding-right: 18px; }
      .panel { grid-column: 1 / -1; }
      header h1 { font-size: 26px; }
    }
    """

    audit_notice = (
        "<section class=\"panel wide\"><h2>Status de Comparabilidade</h2>"
        f"<p><strong>{_e(audit['status'].upper())}</strong>: "
        "a auditoria científica é fechada à falta de evidência. "
        "Somente o estado CONFIRMADA autoriza a comparação; NAO_COMPROVADA e "
        "INCOMPARAVEL permitem apenas inspeção descritiva, sem inferência entre cidades.</p></section>"
    )
    html_doc = f"""<!doctype html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Comparacao de Grafos - {_e(' vs '.join(datasets))}</title>
  <style>{css}</style>
</head>
<body>
  <header>
    <h1>Comparacao de Grafos</h1>
    <p>{_e(' vs '.join(datasets))}</p>
  </header>
  <main>
    {_dataset_cards(datasets, summaries)}
    {_side_by_side_dashboard(datasets, output_path)}
    {audit_notice}
    {_comparison_table(datasets, summaries)}
    {_link_grid(datasets)}
  </main>
</body>
</html>
"""

    Path(output_path).write_text(html_doc, encoding="utf-8")
    return {
        "compare_html": output_path,
        "compare_csv": comparison_csv,
        "datasets": datasets,
    }
