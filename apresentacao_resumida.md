# Apresentação Resumida - Novidades Implementadas no Projeto

> **Revisão metodológica — 18/08/2026:** os termos atuais são robustez estrutural, bloqueios
> regionais estilizados, pares OD uniformes entre nós e células candidatas de alta centralidade
> topológica. Outputs legados devem ser regenerados/auditados antes de apoiar conclusões.

Este arquivo resume apenas o que foi acrescentado ao projeto durante a evolução recente. A ideia é servir como versão curta para reunião: explicar o que cada nova análise faz, o que mostrar ao professor, por que ela faz sentido dentro da IC e qual comando reproduz o dado.

Dataset usado nos exemplos: `campinas_admin`.

Estado revisto em 18 de agosto de 2026: há ampla cobertura funcional, mas a liberação científica
depende das novas auditorias de integridade, proveniência, representação e comparabilidade.

## 1. Robustez estrutural por remoção de vértices

**O que é**

Antes a robustez estrutural era medida removendo arestas, ou seja, trechos de vias. Foi adicionada uma análise separada para remover vértices, que representam interseções ou pontos estruturais da rede.

**Como é medida**

O sistema remove progressivamente nós do grafo e mede:

- fração da maior componente conectada;
- número de componentes;
- eficiência topológica retida;
- eficiência ponderada por distância retida;
- lista dos vértices removidos em cada etapa.

As estratégias são aleatória, dirigida e dirigida adaptativa. A adaptativa recalcula a importância dos nós durante a simulação.

**O que mostrar**

- [outputs/campinas_admin/figures/node_resilience_curve_targeted.png](outputs/campinas_admin/figures/node_resilience_curve_targeted.png)
- [outputs/campinas_admin/metrics/node_resilience_removed_targeted.csv](outputs/campinas_admin/metrics/node_resilience_removed_targeted.csv)

**Por que importa**

Bloquear uma interseção pode afetar várias vias ao mesmo tempo. Isso representa um tipo de falha diferente da remoção de uma rua isolada e fortalece a discussão sobre robustez da rede.

**Comando**

```bash
ic node-resilience --city campinas_admin --strategy targeted --max-fraction 0.15 --steps 15 --k-node 80 --eff-samples 20 --seed 42
```

## 2. Robustez estrutural entre comunidades e dentro das comunidades

**O que é**

Foi adicionada a robustez estrutural no nível das comunidades. Existem duas leituras:

- entre comunidades: cada comunidade vira um nó em um grafo agregado;
- dentro das comunidades: cada comunidade é analisada separadamente como subgrafo.

**Como é medida**

Na robustez entre comunidades, o sistema mede se as regiões topológicas da cidade dependem de poucas conexões entre si. Na robustez interna, mede quais comunidades se fragmentam mais rápido quando suas arestas internas são removidas.

**O que mostrar**

- [outputs/campinas_admin/figures/community_resilience_curve_targeted.png](outputs/campinas_admin/figures/community_resilience_curve_targeted.png)
- [outputs/campinas_admin/metrics/community_resilience_top_edges.csv](outputs/campinas_admin/metrics/community_resilience_top_edges.csv)
- [outputs/campinas_admin/figures/intra_community_resilience_targeted.png](outputs/campinas_admin/figures/intra_community_resilience_targeted.png)
- [outputs/campinas_admin/metrics/intra_community_resilience_summary_targeted.csv](outputs/campinas_admin/metrics/intra_community_resilience_summary_targeted.csv)

**Por que importa**

O grafo inteiro pode parecer estruturalmente robusto no cenário de remoção, mas algumas regiões
podem ser frágeis. Essa análise mostra a fragilidade interna e a dependência entre regiões da
cidade; não mede recuperação temporal.

**Comandos**

```bash
ic community-resilience --city campinas_admin --strategy targeted --max-fraction 0.30 --steps 15 --min-size 30 --seed 42
ic intra-community-resilience --city campinas_admin --strategy targeted --max-fraction 0.15 --steps 10 --min-size 2 --k-edge 40 --eff-samples 20 --seed 42
```

## 3. Validação das aproximações

**O que é**

Foi adicionada uma etapa para verificar se métricas aproximadas são confiáveis. Isso é importante porque centralidades e caminhos podem ser caros em grafos grandes.

**Como é medida**

O sistema pega subgrafos menores, calcula métricas exatas e compara com aproximações usando diferentes tamanhos de amostra. A saída mostra erro e correlação de ranking.

**O que mostrar**

- [outputs/campinas_admin/metrics/approximation_validation.csv](outputs/campinas_admin/metrics/approximation_validation.csv)

**Por que importa**

É uma defesa metodológica. Em vez de apenas usar aproximações, o projeto mede a qualidade delas e mostra quando a interpretação deve ser cautelosa.

**Comando**

```bash
ic validate-approximations --city campinas_admin --subgraph-size 400 --samples 10 30 60 120 --repeats 3 --seed 42
```

## 4. Índice composto de vulnerabilidade viária

**O que é**

Foi criado um ranking composto de vulnerabilidade para nós e arestas. Ele combina vários sinais de criticidade em um único score.

**Como é medido**

O score usa centralidade, participação em ataques de robustez, pontes, articulações, fronteiras entre comunidades, tipo de via, comprimento e importância topológica.

**O que mostrar**

- [outputs/campinas_admin/maps/vulnerability_nodes.html](outputs/campinas_admin/maps/vulnerability_nodes.html)
- [outputs/campinas_admin/maps/vulnerability_edges.html](outputs/campinas_admin/maps/vulnerability_edges.html)
- [outputs/campinas_admin/metrics/vulnerability_nodes.csv](outputs/campinas_admin/metrics/vulnerability_nodes.csv)
- [outputs/campinas_admin/metrics/vulnerability_edges.csv](outputs/campinas_admin/metrics/vulnerability_edges.csv)

**Por que importa**

Ajuda a priorizar elementos críticos sem depender de uma única métrica. Isso deixa a análise mais robusta e mais fácil de interpretar.

**Comando**

```bash
ic vulnerability-index --city campinas_admin --top-k 100
```

## 5. Pontes, articulações e gargalos estruturais

**O que é**

Foi adicionada uma análise estrutural direta de elementos que fragmentam a rede.

**Como é medida**

O sistema identifica:

- pontes: arestas cuja remoção aumenta o número de componentes;
- articulações: nós cuja remoção aumenta o número de componentes;
- gargalos: ranking combinado por impacto de fragmentação.

O impacto principal é a quantidade de nós que saem da maior componente após a remoção.

**O que mostrar**

- [outputs/campinas_admin/maps/structural_bottlenecks.html](outputs/campinas_admin/maps/structural_bottlenecks.html)
- [outputs/campinas_admin/maps/structural_bridges.html](outputs/campinas_admin/maps/structural_bridges.html)
- [outputs/campinas_admin/maps/structural_articulations.html](outputs/campinas_admin/maps/structural_articulations.html)
- [outputs/campinas_admin/metrics/structural_bottlenecks.csv](outputs/campinas_admin/metrics/structural_bottlenecks.csv)

**Por que importa**

Mostra dependências estruturais reais da rede: pontos ou trechos que, se removidos, causam fragmentação direta.

**Comando**

```bash
ic structural-bottlenecks --city campinas_admin --top-k 100
```

## 6. Perfil de redundância de rotas

**O que é**

Foi criada uma análise para medir se há rotas alternativas razoáveis quando a melhor rota entre origem e destino é bloqueada.

**Como é medida**

Para cada par origem-destino, o sistema:

1. calcula a menor rota por distância;
2. remove os segmentos dessa rota;
3. verifica se ainda existe alternativa;
4. mede se a alternativa é razoável, usando um limiar de distância.

O padrão usado foi alternativa até 1,5 vez a rota original.

**O que mostrar**

- [outputs/campinas_admin/maps/route_redundancy.html](outputs/campinas_admin/maps/route_redundancy.html)
- [outputs/campinas_admin/metrics/route_redundancy_summary.csv](outputs/campinas_admin/metrics/route_redundancy_summary.csv)
- [outputs/campinas_admin/metrics/route_redundancy_pairs.csv](outputs/campinas_admin/metrics/route_redundancy_pairs.csv)

**Por que importa**

Duas redes podem ter distância média parecida, mas uma pode oferecer mais alternativas. Isso
mede redundância estrutural sob um bloqueio estilizado, não robustez funcional observada.

**Comando**

```bash
ic route-redundancy --city campinas_admin --pairs 100 --threshold 1.50 --seed 42 --map-limit 20
```

## 7. Análise multiescala por células espaciais

**O que é**

Foi adicionada uma análise local por grade espacial. Em vez de olhar apenas o grafo inteiro, a cidade é dividida em células.

**Como é medida**

Para cada célula, o sistema calcula conectividade local, vulnerabilidade, pontes, articulações, componentes e sinais de redundância.

**O que mostrar**

- [outputs/campinas_admin/maps/spatial_multiscale_vulnerability.html](outputs/campinas_admin/maps/spatial_multiscale_vulnerability.html)
- [outputs/campinas_admin/maps/spatial_multiscale_connectivity.html](outputs/campinas_admin/maps/spatial_multiscale_connectivity.html)
- [outputs/campinas_admin/maps/spatial_multiscale_redundancy.html](outputs/campinas_admin/maps/spatial_multiscale_redundancy.html)
- [outputs/campinas_admin/metrics/spatial_multiscale_cells.csv](outputs/campinas_admin/metrics/spatial_multiscale_cells.csv)

**Por que importa**

O grafo inteiro pode esconder desigualdades internas. Essa análise mostra onde a cidade é mais conectada, mais vulnerável ou menos redundante.

**Comando**

```bash
ic spatial-multiscale --city campinas_admin --cell-size-m 1000
```

## 8. Robustez espacial por bloqueios regionais

**O que é**

Foi adicionada uma simulação de falhas concentradas no espaço, em vez de remoções aleatórias espalhadas.

**Como é medida**

Para cada célula, o sistema remove vias incidentes ou internas e mede o impacto no grafo inteiro:

- queda da maior componente;
- queda de eficiência;
- aumento da fragmentação.

**O que mostrar**

- [outputs/campinas_admin/maps/spatial_robustness_lcc_drop.html](outputs/campinas_admin/maps/spatial_robustness_lcc_drop.html)
- [outputs/campinas_admin/maps/spatial_robustness_efficiency_drop.html](outputs/campinas_admin/maps/spatial_robustness_efficiency_drop.html)
- [outputs/campinas_admin/maps/spatial_robustness_fragmentation.html](outputs/campinas_admin/maps/spatial_robustness_fragmentation.html)
- [outputs/campinas_admin/metrics/spatial_robustness_cells.csv](outputs/campinas_admin/metrics/spatial_robustness_cells.csv)

**Por que importa**

Eventos reais podem afetar áreas locais, mas este módulo não modela hazard, probabilidade ou
intensidade observada. Ele testa cenários regionais estilizados.

**Comando**

```bash
ic spatial-robustness --city campinas_admin --cell-size-m 1000 --mode incident --eff-samples 10 --max-eff-cells 100 --seed 42
```

## 9. Análise de hierarquia viária

**O que é**

Foi adicionada uma análise por classes `highway` do OpenStreetMap: primary, secondary, residential, service etc.

**Como é medida**

Para cada classe, o sistema calcula participação em arestas, extensão, centralidade, vulnerabilidade e impacto na robustez estrutural quando a classe é removida.

**O que mostrar**

- [outputs/campinas_admin/maps/road_hierarchy_impact.html](outputs/campinas_admin/maps/road_hierarchy_impact.html)
- [outputs/campinas_admin/metrics/road_hierarchy_summary.csv](outputs/campinas_admin/metrics/road_hierarchy_summary.csv)
- [outputs/campinas_admin/metrics/road_hierarchy_by_class.csv](outputs/campinas_admin/metrics/road_hierarchy_by_class.csv)

**Por que importa**

Mostra se a rede depende demais de vias arteriais ou se a conectividade é distribuída pela malha local.

**Comando**

```bash
ic road-hierarchy --city campinas_admin --eff-samples 20 --seed 42 --map-edges-per-class 1200
```

## 10. Morfologia urbana: planejamento urbano x estrutura da rede

**O que é**

Foi adicionada uma classificação morfológica das regiões da cidade.

**Como é medida**

Cada célula é classificada como gradeada, radial/linear, orgânica, fragmentada, mista ou insuficiente. O sistema usa orientação das vias, entropia angular, conectividade local, maior componente e comprimento médio dos segmentos.

**O que mostrar**

- [outputs/campinas_admin/maps/urban_morphology_classes.html](outputs/campinas_admin/maps/urban_morphology_classes.html)
- [outputs/campinas_admin/maps/urban_morphology_orientation_entropy.html](outputs/campinas_admin/maps/urban_morphology_orientation_entropy.html)
- [outputs/campinas_admin/maps/urban_morphology_connectivity.html](outputs/campinas_admin/maps/urban_morphology_connectivity.html)
- [outputs/campinas_admin/metrics/urban_morphology_cells.csv](outputs/campinas_admin/metrics/urban_morphology_cells.csv)

**Por que importa**

Conecta teoria dos grafos com morfologia urbana. Permite discutir se partes da cidade são mais gradeadas, orgânicas ou fragmentadas.

**Comando**

```bash
ic urban-morphology --city campinas_admin --cell-size-m 1000
```

## 11. Eficiência de rotas em múltiplos pares origem-destino

**O que é**

Foi adicionada uma análise estatística de rotas, usando muitos pares origem-destino em vez de uma rota pontual.

**Como é medida**

Para cada par OD uniforme entre nós, o sistema calcula distância da rota, distância direta, hops,
circuity, eficiência relativa e fração abaixo de limiares de distância.

**O que mostrar**

- [outputs/campinas_admin/maps/od_efficiency_routes.html](outputs/campinas_admin/maps/od_efficiency_routes.html)
- [outputs/campinas_admin/metrics/od_efficiency_summary.csv](outputs/campinas_admin/metrics/od_efficiency_summary.csv)
- [outputs/campinas_admin/metrics/od_efficiency_pairs.csv](outputs/campinas_admin/metrics/od_efficiency_pairs.csv)

**Por que importa**

Produz uma distribuição estatística sob esse desenho amostral; não estima demanda OD nem
acessibilidade observada da população.

**Comando**

```bash
ic od-efficiency --city campinas_admin --pairs 1000 --seed 42 --map-limit 80
```

## 12. Similaridade entre cidades

**O que é**

Foi adicionada uma análise que transforma cada cidade em um vetor de métricas e calcula similaridade estrutural.

**Como é medida**

O sistema usa métricas consolidadas do inventário, padroniza por z-score e calcula distância euclidiana, similaridade cosseno, PCA e clustering hierárquico.

**O que mostrar**

- [outputs/comparisons/city_similarity_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.html](outputs/comparisons/city_similarity_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.html)
- [outputs/comparisons/city_similarity_distance_heatmap_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png](outputs/comparisons/city_similarity_distance_heatmap_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png)
- [outputs/comparisons/city_similarity_pca_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png](outputs/comparisons/city_similarity_pca_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png)
- [outputs/comparisons/city_similarity_dendrogram_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png](outputs/comparisons/city_similarity_dendrogram_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png)

**Por que importa**

Com amostra suficiente, ajuda a comparar perfis estruturais. Com apenas quatro cidades, PCA,
clustering e “cidade mais próxima” são visualizações exploratórias sensíveis às métricas e ao
escalonamento; não estabelecem semelhança estrutural geral.

**Comando**

```bash
ic city-similarity campinas_admin jundiai_admin sorocaba_admin valinhos_admin \
  --output-dir outputs/comparisons --min-coverage 1.0 --allow-small-sample-exploration
```

## 13. Células candidatas de alta centralidade topológica

**O que é**

Foi adicionada uma análise para localizar células candidatas com alta centralidade topológica e
medir a concentração do score entre elas.

**Como é medida**

Cada célula recebe um score de candidatura combinando centralidade acumulada, centralidade
máxima, closeness, eigenvector, densidade, grau médio, quantidade de nós e diversidade de
comunidades. As células acima do percentil configurado são selecionadas como candidatas
topológicas, não como subcentros urbanos validados.

Também são calculados:

- índice exploratório de dispersão dos candidatos;
- índice de dominância topológica;
- entropia dos scores;
- participação da principal célula candidata.

**O que mostrar**

- [outputs/campinas_admin/maps/subcenters.html](outputs/campinas_admin/maps/subcenters.html)
- [outputs/campinas_admin/metrics/subcenters.csv](outputs/campinas_admin/metrics/subcenters.csv)
- [outputs/campinas_admin/metrics/subcenters_summary.csv](outputs/campinas_admin/metrics/subcenters_summary.csv)

**Por que importa**

Sem dados de empregos, população, atividades ou fluxos, o módulo não classifica cidades como
mono ou policêntricas; ele compara apenas a concentração da centralidade topológica.

**Comando**

```bash
ic subcenters --city campinas_admin --cell-size-m 1000 --percentile 0.90 --min-nodes 20
```

## 14. Exposição da rede a barreiras urbanas

**O que é**

Foi adicionada uma análise para detectar evidências topológicas de barreiras urbanas prováveis.

**Como é medida**

O sistema mede baixa conectividade entre células vizinhas, conexões adjacentes ausentes, travessias longas, pontes estruturais e fronteiras entre comunidades.

Importante: sem dados externos, a análise não afirma que a barreira é necessariamente rio, ferrovia ou rodovia. Ela indica baixa permeabilidade topológica.

**O que mostrar**

- [outputs/campinas_admin/maps/urban_barriers_permeability.html](outputs/campinas_admin/maps/urban_barriers_permeability.html)
- [outputs/campinas_admin/maps/urban_barriers_connections.html](outputs/campinas_admin/maps/urban_barriers_connections.html)
- [outputs/campinas_admin/metrics/urban_barriers_cells.csv](outputs/campinas_admin/metrics/urban_barriers_cells.csv)
- [outputs/campinas_admin/metrics/urban_barriers_summary.csv](outputs/campinas_admin/metrics/urban_barriers_summary.csv)

**Por que importa**

Muitas fragilidades urbanas aparecem como baixa permeabilidade entre regiões, e não apenas como baixo grau médio ou alta centralidade.

**Comando**

```bash
ic urban-barriers --city campinas_admin --cell-size-m 1000 --map-limit 250
```

## 15. Perfil de escala da rede viária

**O que é**

Foi adicionada uma análise para testar se as conclusões espaciais dependem do tamanho da grade.

**Como é medida**

O sistema recalcula métricas em células de 500 m, 1 km, 2 km e 3 km. Depois calcula a estabilidade de cada métrica usando coeficiente de variação e um score de estabilidade.

O resumo inclui:

- índice de robustez multiescalar;
- métrica mais estável;
- métrica menos estável;
- estabilidade por indicador.

**O que mostrar**

- [outputs/campinas_admin/figures/network_scale_profile_metrics.png](outputs/campinas_admin/figures/network_scale_profile_metrics.png)
- [outputs/campinas_admin/figures/network_scale_profile_stability.png](outputs/campinas_admin/figures/network_scale_profile_stability.png)
- [outputs/campinas_admin/maps/network_scale_profile_low_permeability.html](outputs/campinas_admin/maps/network_scale_profile_low_permeability.html)
- [outputs/campinas_admin/metrics/network_scale_profile_summary.csv](outputs/campinas_admin/metrics/network_scale_profile_summary.csv)

**Por que importa**

Se uma conclusão aparece em várias escalas, ela é mais defensável. Se aparece só em uma escala, pode ser artefato da grade.

**Comando**

```bash
ic network-scale-profile --city campinas_admin --scales 500 1000 2000 3000
```

## 16. Auditoria da análise histórica OSM

**O que é**

Foi adicionada uma auditoria para evitar interpretações erradas em comparações históricas com OpenStreetMap.

**Como é medida**

O sistema compara datasets antigos com uma referência atual e mede cobertura, caminhos preservados e qualidade do núcleo comum. Depois classifica a comparação como confiável, exploratória ou não confiável.

**O que mostrar**

- [outputs/comparisons/historical_quality_campinas_historical_17_datasets.csv](outputs/comparisons/historical_quality_campinas_historical_17_datasets.csv)
- [outputs/comparisons/historical_quality_campinas_historical_17_datasets.txt](outputs/comparisons/historical_quality_campinas_historical_17_datasets.txt)
- [outputs/comparisons/historical_common_core_campinas_historical_17_datasets.csv](outputs/comparisons/historical_common_core_campinas_historical_17_datasets.csv)

**Por que importa**

Sem essa auditoria, uma rede antiga pode parecer menos conectada apenas porque o OSM era menos completo, e não porque a cidade realmente mudou.

**Comando**

```bash
ic historical-audit --reference campinas campinas_2010 campinas_2011 campinas_2012 --output-dir outputs/comparisons
```

## 17. Dashboards, relatórios e comparação consolidada

**O que é**

Foram ampliados os artefatos finais para reunir todas as análises em formatos apresentáveis.

**O que mostrar**

- [outputs/campinas_admin/dashboard_campinas_admin.html](outputs/campinas_admin/dashboard_campinas_admin.html)
- [outputs/campinas_admin/REPORT_campinas_admin.md](outputs/campinas_admin/REPORT_campinas_admin.md)
- [outputs/comparisons/compare_admin_cities.html](outputs/comparisons/compare_admin_cities.html)
- [outputs/comparisons/compare_admin_cities.csv](outputs/comparisons/compare_admin_cities.csv)

**Por que importa**

Esses arquivos são o pacote principal para reunião e escrita do relatório. Eles juntam mapas, gráficos, tabelas e métricas em formato comum; a comparação só é liberada depois dos gates.

**Comandos**

```bash
ic inventory --city campinas_admin
ic dashboard --city campinas_admin
ic report --city campinas_admin
ic compare campinas_admin jundiai_admin sorocaba_admin valinhos_admin --output outputs/comparisons/compare_admin_cities.html
```

## 18. Síntese quantitativa das curvas de robustez

**O que é**

As curvas de remoção agora também são resumidas numericamente. O sistema calcula a área sob a
curva normalizada (AUC), perdas em frações padronizadas e o ponto em que conectividade ou
eficiência caem abaixo de limiares definidos.

**Como é medida**

- integra por trapézios as curvas da maior componente, eficiência topológica e eficiência por
  distância;
- usa a maior fração de remoção comum entre todas as cidades e estratégias da mesma modalidade;
- interpola resultados em 1%, 5%, 10% e 15%;
- procura os primeiros cruzamentos abaixo de 90%, 75% e 50%;
- mantém separadas remoções de nós, arestas e conexões entre comunidades;
- usa as repetições aleatórias existentes para mostrar a dispersão da AUC.

AUC maior significa que a rede preservou, em média, uma parcela maior da resposta durante o
intervalo analisado. Ela não deve ser comparada diretamente entre modalidades diferentes sem
explicar que nós, arestas e comunidades representam perturbações distintas.

**O que mostrar**

- [outputs/comparisons/robustness_comparison.html](outputs/comparisons/robustness_comparison.html)
- [outputs/comparisons/robustness_comparison.png](outputs/comparisons/robustness_comparison.png)
- [outputs/comparisons/robustness_losses.png](outputs/comparisons/robustness_losses.png)
- [outputs/comparisons/robustness_comparison.csv](outputs/comparisons/robustness_comparison.csv)
- [outputs/campinas_admin/figures/robustness_summary_auc.png](outputs/campinas_admin/figures/robustness_summary_auc.png)
- [outputs/campinas_admin/figures/robustness_summary_losses.png](outputs/campinas_admin/figures/robustness_summary_losses.png)
- [outputs/campinas_admin/metrics/robustness_summary.csv](outputs/campinas_admin/metrics/robustness_summary.csv)

**Por que importa**

Antes, a comparação podia depender do último ponto ou da inspeção visual. A AUC usa a curva
inteira no intervalo comum e permite responder com mais rigor qual estratégia degrada mais cada
rede e qual cidade retém melhor conectividade ou eficiência.

**Comando**

```bash
ic robustness-summary campinas_admin jundiai_admin sorocaba_admin valinhos_admin
```

## Fechamento

As principais novidades transformaram o projeto de uma pipeline básica de métricas de grafos em uma plataforma de análise urbana mais completa. Agora o sistema mede não só estrutura global, mas também vulnerabilidade, robustez por diferentes modos de falha, síntese quantitativa das curvas, comunidades, acessibilidade, morfologia urbana, subcentros, barreiras, estabilidade por escala e similaridade entre cidades.
