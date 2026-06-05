# Apresentação da Reunião - IC Redes Complexas

Objetivo deste arquivo: servir como roteiro para apresentar ao professor o que foi implementado no projeto, quais dados foram gerados, onde mostrar cada resultado e qual comando reproduz cada análise.

Dataset de referência usado nos exemplos: `campinas_admin`.
Para outras cidades, troque `campinas_admin` por `jundiai_admin`, `sorocaba_admin`, `valinhos_admin` ou outro dataset processado.

## 1. Ideia central do projeto

**Como apresentar**

O sistema pega o grafo viário de uma cidade, processa a rede, calcula métricas de teoria dos grafos, gera mapas, tabelas, gráficos e relatórios. A ideia não é escrever automaticamente a análise científica final, mas produzir os dados para que a interpretação seja feita depois no relatório da IC.

**O que mostrar**

- Dashboard geral: [outputs/campinas_admin/dashboard_campinas_admin.html](outputs/campinas_admin/dashboard_campinas_admin.html)
- Relatório consolidado: [outputs/campinas_admin/REPORT_campinas_admin.md](outputs/campinas_admin/REPORT_campinas_admin.md)
- Comparação entre cidades: [outputs/comparisons/compare_admin_cities.html](outputs/comparisons/compare_admin_cities.html)

**Por que isso importa**

Isso transforma o projeto em uma ferramenta reprodutível: dado o grafo de uma cidade, o sistema gera um pacote de evidências para discutir estrutura, vulnerabilidade, resiliência, comunidades, acessibilidade e diferenças entre cidades.

**Comandos**

```bash
ic dashboard --city campinas_admin
ic report --city campinas_admin
ic compare campinas_admin jundiai_admin sorocaba_admin valinhos_admin --output outputs/comparisons/compare_admin_cities.html
```

## 2. Aquisição, limpeza e caracterização básica do grafo

**O que é**

Esta é a base do projeto. O grafo viário vem do OpenStreetMap/OSMnx. Os nós representam interseções ou pontos da rede. As arestas representam segmentos viários. Depois do download, o sistema limpa o grafo, mantém a maior componente conectada e calcula métricas estruturais básicas.

**O que mostrar**

- Grafo de ruas: [outputs/campinas_admin/figures/grafo_campinas_admin_clean_ruas.png](outputs/campinas_admin/figures/grafo_campinas_admin_clean_ruas.png)
- Grafo com nós: [outputs/campinas_admin/figures/grafo_campinas_admin_clean_ruas_nos.png](outputs/campinas_admin/figures/grafo_campinas_admin_clean_ruas_nos.png)
- Métricas estruturais: [outputs/campinas_admin/metrics/structural_metrics.csv](outputs/campinas_admin/metrics/structural_metrics.csv)
- Inventário consolidado: [outputs/campinas_admin/metrics/graph_inventory_summary.csv](outputs/campinas_admin/metrics/graph_inventory_summary.csv)

**Como explicar**

As métricas iniciais incluem número de nós, número de arestas, extensão total da rede, grau médio, densidade, transitividade, assortatividade, caminho médio aproximado e diâmetro aproximado. Elas dão a primeira leitura da forma da rede: se ela é densa ou esparsa, se tem muitas conexões locais, se o deslocamento médio tende a ser curto ou longo e se há concentração em poucos eixos.

**Por que faz sentido no projeto**

O PDF da IC fala em caracterizar redes viárias urbanas com métricas de redes complexas. Essa etapa cobre o núcleo mais direto: transformar a malha viária em grafo e calcular medidas estruturais.

**Comandos**

```bash
ic preprocess --city campinas_admin
ic structural --city campinas_admin --samples 30 --seed 42
ic plot-graphs --city campinas_admin
ic inventory --city campinas_admin
```

## 3. Distribuição de grau

**O que é**

O grau de um nó é a quantidade de conexões incidentes nele. Em uma rede viária, isso aproxima a conectividade local de uma interseção. A distribuição de grau mostra quantos nós têm grau 1, 2, 3, 4 etc.

**O que mostrar**

- Gráfico log-log: [outputs/campinas_admin/figures/degree_distribution_loglog.png](outputs/campinas_admin/figures/degree_distribution_loglog.png)
- CSV da distribuição: [outputs/campinas_admin/metrics/degree_distribution.csv](outputs/campinas_admin/metrics/degree_distribution.csv)

**Como explicar**

Ruas urbanas normalmente têm muitos nós de grau 2 ou 3 e menos nós de grau alto. Interseções com grau alto podem representar cruzamentos importantes ou pontos de maior conectividade. A distribuição ajuda a comparar se uma cidade tem malha mais regular, mais fragmentada ou mais dependente de poucos cruzamentos muito conectados.

**Por que importa**

É uma das métricas mais clássicas em redes complexas e aparece diretamente no escopo do projeto.

**Comando**

```bash
ic structural --city campinas_admin
```

## 4. Centralidades e pontos críticos

**O que é**

Centralidade mede a importância de nós e arestas dentro da rede. Foram implementadas centralidade de grau, intermediação, proximidade aproximada e autovetor.

**O que mostrar**

- Mapa de pontos críticos: [outputs/campinas_admin/maps/pontos_criticos.html](outputs/campinas_admin/maps/pontos_criticos.html)
- Mapa de arestas críticas: [outputs/campinas_admin/maps/arestas_criticas.html](outputs/campinas_admin/maps/arestas_criticas.html)
- Ranking de nós críticos: [outputs/campinas_admin/metrics/top_nodes.csv](outputs/campinas_admin/metrics/top_nodes.csv)
- Ranking de arestas críticas: [outputs/campinas_admin/metrics/top_edges.csv](outputs/campinas_admin/metrics/top_edges.csv)
- Centralidades completas por nó: [outputs/campinas_admin/metrics/node_centralities.csv](outputs/campinas_admin/metrics/node_centralities.csv)
- Rankings por métrica: [outputs/campinas_admin/metrics/centrality_rankings.csv](outputs/campinas_admin/metrics/centrality_rankings.csv)

**Como explicar**

- Grau: mede conexões diretas.
- Betweenness/intermediação: mede quanto um nó ou aresta aparece em caminhos mínimos. Indica potenciais gargalos.
- Closeness/proximidade: mede o quão perto um nó está dos demais em termos topológicos.
- Autovetor/eigenvector: mede importância levando em conta se o nó se conecta a outros nós importantes.

**Por que importa**

Essas métricas permitem identificar elementos estratégicos da rede. Dentro do projeto, elas ajudam a responder quais pontos concentram acessibilidade e quais segmentos podem gerar maior impacto se forem bloqueados.

**Comando**

```bash
ic centrality --city campinas_admin --top-k 30 --k-b 120 --k-e 60 --k-c 120 --seed 42
```

## 5. Comunidades da rede

**O que é**

Comunidades são grupos de nós mais conectados internamente do que com o restante do grafo. Em rede viária, podem indicar regiões urbanas com maior coesão interna.

**O que mostrar**

- Mapa de comunidades: [outputs/campinas_admin/maps/comunidades.html](outputs/campinas_admin/maps/comunidades.html)
- Grafo colorido por comunidades: [outputs/campinas_admin/figures/grafo_campinas_admin_clean_comunidades.png](outputs/campinas_admin/figures/grafo_campinas_admin_clean_comunidades.png)
- Nós por comunidade: [outputs/campinas_admin/metrics/nodes_communities.csv](outputs/campinas_admin/metrics/nodes_communities.csv)
- Resumo das comunidades: [outputs/campinas_admin/metrics/community_summary.csv](outputs/campinas_admin/metrics/community_summary.csv)

**Como explicar**

A detecção de comunidades segmenta a cidade em blocos topológicos. Isso não é necessariamente igual a bairros oficiais, mas revela regiões que a própria estrutura viária aproxima ou separa.

**Por que importa**

Ajuda a sair da análise apenas global. O grafo inteiro pode parecer bem conectado, mas algumas comunidades podem ser frágeis ou depender de poucas conexões externas.

**Comando**

```bash
ic communities --city campinas_admin --method greedy --min-size 30 --seed 42
```

## 6. Resiliência por remoção de arestas

**O que é**

Simula a remoção progressiva de vias/arestas e mede como a rede perde conectividade. Existem estratégias aleatória, dirigida e dirigida adaptativa.

**O que mostrar**

- Curva dirigida: [outputs/campinas_admin/figures/resilience_curve_targeted.png](outputs/campinas_admin/figures/resilience_curve_targeted.png)
- Curva adaptativa: [outputs/campinas_admin/figures/resilience_curve_targeted_adaptive.png](outputs/campinas_admin/figures/resilience_curve_targeted_adaptive.png)
- Curva aleatória: [outputs/campinas_admin/figures/resilience_curve_random.png](outputs/campinas_admin/figures/resilience_curve_random.png)
- CSV dirigido: [outputs/campinas_admin/metrics/resilience_curve_targeted.csv](outputs/campinas_admin/metrics/resilience_curve_targeted.csv)
- Agregado aleatório: [outputs/campinas_admin/figures/resilience_random_aggregate.png](outputs/campinas_admin/figures/resilience_random_aggregate.png)

**Como explicar**

A principal métrica observada é a fração da maior componente conectada. Se ela cai rápido, a rede é frágil ao tipo de ataque testado. A remoção aleatória funciona como baseline. A remoção dirigida remove primeiro elementos mais centrais. A adaptativa recalcula a importância durante o processo.

**Por que importa**

Resiliência é central para discutir robustez da rede viária. Ela mostra o comportamento da rede sob falhas, bloqueios, obras ou interrupções.

**Comandos**

```bash
ic resilience --city campinas_admin --strategy targeted --max-fraction 0.15 --steps 15 --k-edge 80 --eff-samples 20 --seed 42
ic resilience --city campinas_admin --strategy targeted_adaptive --max-fraction 0.15 --steps 15 --k-edge 80 --eff-samples 20 --seed 42
ic resilience --city campinas_admin --strategy random --max-fraction 0.15 --steps 15 --k-edge 80 --eff-samples 20 --seed 42
ic random-resilience-stats --city campinas_admin --mode edge --seeds 42 43 44 45 46
```

## 7. Resiliência por remoção de vértices

**O que é**

É o mesmo princípio da resiliência, mas removendo nós/interseções em vez de arestas/vias.

**O que mostrar**

- Curva dirigida por vértices: [outputs/campinas_admin/figures/node_resilience_curve_targeted.png](outputs/campinas_admin/figures/node_resilience_curve_targeted.png)
- Curva adaptativa por vértices: [outputs/campinas_admin/figures/node_resilience_curve_targeted_adaptive.png](outputs/campinas_admin/figures/node_resilience_curve_targeted_adaptive.png)
- Curva aleatória por vértices: [outputs/campinas_admin/figures/node_resilience_curve_random.png](outputs/campinas_admin/figures/node_resilience_curve_random.png)
- Vértices removidos no ataque dirigido: [outputs/campinas_admin/metrics/node_resilience_removed_targeted.csv](outputs/campinas_admin/metrics/node_resilience_removed_targeted.csv)
- Agregado aleatório: [outputs/campinas_admin/figures/node_resilience_random_aggregate.png](outputs/campinas_admin/figures/node_resilience_random_aggregate.png)

**Como explicar**

Remover uma interseção pode desconectar várias vias ao mesmo tempo. Por isso, a resiliência por vértices mede um tipo diferente de fragilidade. Ela é útil para simular bloqueios em cruzamentos, rotatórias, entroncamentos ou nós de alta centralidade.

**Por que importa**

Duas cidades podem parecer parecidas quando removemos vias, mas reagir de forma diferente quando removemos interseções. Isso amplia a robustez da análise.

**Comandos**

```bash
ic node-resilience --city campinas_admin --strategy targeted --max-fraction 0.15 --steps 15 --k-node 80 --eff-samples 20 --seed 42
ic node-resilience --city campinas_admin --strategy targeted_adaptive --max-fraction 0.15 --steps 15 --k-node 80 --eff-samples 20 --seed 42
ic node-resilience --city campinas_admin --strategy random --max-fraction 0.15 --steps 15 --k-node 80 --eff-samples 20 --seed 42
ic random-resilience-stats --city campinas_admin --mode node --seeds 42 43 44 45 46
```

## 8. Resiliência entre comunidades

**O que é**

As comunidades são agregadas em um novo grafo: cada comunidade vira um nó, e as conexões entre comunidades viram arestas. Depois o sistema testa a resiliência desse grafo agregado.

**O que mostrar**

- Curva dirigida: [outputs/campinas_admin/figures/community_resilience_curve_targeted.png](outputs/campinas_admin/figures/community_resilience_curve_targeted.png)
- Curva adaptativa: [outputs/campinas_admin/figures/community_resilience_curve_targeted_adaptive.png](outputs/campinas_admin/figures/community_resilience_curve_targeted_adaptive.png)
- Curva aleatória: [outputs/campinas_admin/figures/community_resilience_curve_random.png](outputs/campinas_admin/figures/community_resilience_curve_random.png)
- Resumo por comunidade: [outputs/campinas_admin/metrics/community_resilience_summary.csv](outputs/campinas_admin/metrics/community_resilience_summary.csv)
- Conexões críticas entre comunidades: [outputs/campinas_admin/metrics/community_resilience_top_edges.csv](outputs/campinas_admin/metrics/community_resilience_top_edges.csv)

**Como explicar**

Essa análise mede se as regiões internas da cidade estão bem conectadas entre si ou se dependem de poucas ligações. Não olha só para ruas individuais, mas para a estrutura entre blocos urbanos.

**Por que importa**

É uma ponte entre teoria dos grafos e leitura urbana: a cidade pode ter comunidades internas bem definidas, mas ser frágil nas conexões entre elas.

**Comando**

```bash
ic community-resilience --city campinas_admin --strategy targeted --max-fraction 0.30 --steps 15 --min-size 30 --seed 42
```

## 9. Resiliência interna de cada comunidade

**O que é**

Mede separadamente a robustez de cada comunidade, removendo arestas dentro do subgrafo daquela comunidade.

**O que mostrar**

- Gráfico dirigido: [outputs/campinas_admin/figures/intra_community_resilience_targeted.png](outputs/campinas_admin/figures/intra_community_resilience_targeted.png)
- Gráfico adaptativo: [outputs/campinas_admin/figures/intra_community_resilience_targeted_adaptive.png](outputs/campinas_admin/figures/intra_community_resilience_targeted_adaptive.png)
- Gráfico aleatório: [outputs/campinas_admin/figures/intra_community_resilience_random.png](outputs/campinas_admin/figures/intra_community_resilience_random.png)
- Resumo dirigido: [outputs/campinas_admin/metrics/intra_community_resilience_summary_targeted.csv](outputs/campinas_admin/metrics/intra_community_resilience_summary_targeted.csv)

**Como explicar**

Essa análise responde: quais comunidades são internamente mais frágeis? O indicador principal é a área sob a curva da maior componente. Quanto menor essa área, mais rápido a comunidade se fragmenta quando sofre remoções.

**Por que importa**

O grafo inteiro pode esconder desigualdades. Algumas partes da cidade podem ser muito resilientes, enquanto outras quebram com poucas remoções.

**Comando**

```bash
ic intra-community-resilience --city campinas_admin --strategy targeted --max-fraction 0.15 --steps 10 --min-size 2 --k-edge 40 --eff-samples 20 --seed 42
```

## 10. Validação das aproximações

**O que é**

Algumas métricas são caras para grafos grandes, então usamos aproximações por amostragem. Esta etapa compara aproximações com valores exatos em subgrafos controlados.

**O que mostrar**

- Validação: [outputs/campinas_admin/metrics/approximation_validation.csv](outputs/campinas_admin/metrics/approximation_validation.csv)

**Como explicar**

O sistema mede, por exemplo, se o ranking aproximado de betweenness ou closeness preserva bem o ranking exato. Isso é importante porque evita apresentar aproximações como se fossem verdades absolutas.

**Por que importa**

É uma parte metodológica forte: demonstra cuidado com erro, estabilidade e confiabilidade dos resultados.

**Comando**

```bash
ic validate-approximations --city campinas_admin --subgraph-size 400 --samples 10 30 60 120 --repeats 3 --seed 42
```

## 11. Relação entre topologia e atributos viários

**O que é**

Compara atributos OSM, como `highway`, `maxspeed`, `lanes`, `surface`, com métricas topológicas.

**O que mostrar**

- Grupos funcionais: [outputs/campinas_admin/metrics/functional_topology_groups.csv](outputs/campinas_admin/metrics/functional_topology_groups.csv)
- Correlações: [outputs/campinas_admin/metrics/functional_topology_correlations.csv](outputs/campinas_admin/metrics/functional_topology_correlations.csv)
- Inventário de tipos de via: [outputs/campinas_admin/metrics/graph_inventory_highway.csv](outputs/campinas_admin/metrics/graph_inventory_highway.csv)
- Inventário de superfície: [outputs/campinas_admin/metrics/graph_inventory_surface.csv](outputs/campinas_admin/metrics/graph_inventory_surface.csv)

**Como explicar**

Essa análise verifica associações descritivas: por exemplo, se vias com mais faixas ou maior velocidade tendem a aparecer mais em posições centrais. Não é causalidade, mas ajuda a aproximar a topologia da função urbana da via.

**Por que importa**

O PDF menciona características funcionais da rede. Essa etapa conecta a rede abstrata com atributos reais do OSM.

**Comando**

```bash
ic functional-relations --city campinas_admin
```

## 12. Índice composto de vulnerabilidade viária

**O que é**

Cria rankings compostos de vulnerabilidade para nós e arestas, combinando múltiplos sinais: centralidade, articulações, pontes, comunidades, tipo de via, comprimento e participação em ataques.

**O que mostrar**

- Mapa de vulnerabilidade dos nós: [outputs/campinas_admin/maps/vulnerability_nodes.html](outputs/campinas_admin/maps/vulnerability_nodes.html)
- Mapa de vulnerabilidade das arestas: [outputs/campinas_admin/maps/vulnerability_edges.html](outputs/campinas_admin/maps/vulnerability_edges.html)
- CSV de nós vulneráveis: [outputs/campinas_admin/metrics/vulnerability_nodes.csv](outputs/campinas_admin/metrics/vulnerability_nodes.csv)
- CSV de arestas vulneráveis: [outputs/campinas_admin/metrics/vulnerability_edges.csv](outputs/campinas_admin/metrics/vulnerability_edges.csv)

**Como explicar**

O score não depende de uma única métrica. Um elemento é considerado mais vulnerável quando aparece como importante em vários critérios ao mesmo tempo. Por exemplo: alta centralidade, ponte estrutural, fronteira entre comunidades e via de classe importante.

**Por que importa**

É útil para priorizar análise: em vez de olhar dezenas de tabelas separadas, temos um ranking sintético de elementos críticos.

**Comando**

```bash
ic vulnerability-index --city campinas_admin --top-k 100
```

## 13. Pontes, articulações e gargalos estruturais

**O que é**

Identifica elementos cuja remoção fragmenta diretamente a rede. Ponte estrutural é uma aresta cuja remoção aumenta o número de componentes. Nó de articulação é um vértice cuja remoção aumenta o número de componentes.

**O que mostrar**

- Mapa de gargalos combinados: [outputs/campinas_admin/maps/structural_bottlenecks.html](outputs/campinas_admin/maps/structural_bottlenecks.html)
- Mapa de pontes: [outputs/campinas_admin/maps/structural_bridges.html](outputs/campinas_admin/maps/structural_bridges.html)
- Mapa de articulações: [outputs/campinas_admin/maps/structural_articulations.html](outputs/campinas_admin/maps/structural_articulations.html)
- CSV de gargalos: [outputs/campinas_admin/metrics/structural_bottlenecks.csv](outputs/campinas_admin/metrics/structural_bottlenecks.csv)
- CSV de pontes: [outputs/campinas_admin/metrics/structural_bridges.csv](outputs/campinas_admin/metrics/structural_bridges.csv)
- CSV de articulações: [outputs/campinas_admin/metrics/structural_articulations.csv](outputs/campinas_admin/metrics/structural_articulations.csv)

**Como explicar**

Essa análise mede impacto direto: quantos nós ficam fora da maior componente se aquele elemento for removido. É mais estrutural e menos estatística do que centralidade.

**Por que importa**

Mostra pontos onde a rede depende de conexões únicas. Isso é essencial para discutir fragilidade física/topológica da malha.

**Comando**

```bash
ic structural-bottlenecks --city campinas_admin --top-k 100
```

## 14. Perfil de redundância de rotas

**O que é**

Amostra pares origem-destino, calcula a melhor rota, bloqueia essa rota e verifica se existe alternativa razoável.

**O que mostrar**

- Mapa de redundância: [outputs/campinas_admin/maps/route_redundancy.html](outputs/campinas_admin/maps/route_redundancy.html)
- Resumo: [outputs/campinas_admin/metrics/route_redundancy_summary.csv](outputs/campinas_admin/metrics/route_redundancy_summary.csv)
- Pares analisados: [outputs/campinas_admin/metrics/route_redundancy_pairs.csv](outputs/campinas_admin/metrics/route_redundancy_pairs.csv)

**Como explicar**

Para cada par OD, o sistema pergunta: se a melhor rota estiver indisponível, ainda existe outra? E essa outra rota é aceitável ou muito longa? O limiar padrão é 1,5 vez a rota original.

**Por que importa**

Duas cidades podem ter caminho médio parecido, mas uma pode oferecer muito mais alternativas. Isso mede robustez funcional, não apenas conectividade abstrata.

**Comando**

```bash
ic route-redundancy --city campinas_admin --pairs 100 --threshold 1.50 --seed 42 --map-limit 20
```

## 15. Análise multiescala por células espaciais

**O que é**

Divide a cidade em células espaciais e calcula métricas locais de conectividade, vulnerabilidade e redundância.

**O que mostrar**

- Mapa de vulnerabilidade local: [outputs/campinas_admin/maps/spatial_multiscale_vulnerability.html](outputs/campinas_admin/maps/spatial_multiscale_vulnerability.html)
- Mapa de conectividade local: [outputs/campinas_admin/maps/spatial_multiscale_connectivity.html](outputs/campinas_admin/maps/spatial_multiscale_connectivity.html)
- Mapa de baixa redundância: [outputs/campinas_admin/maps/spatial_multiscale_redundancy.html](outputs/campinas_admin/maps/spatial_multiscale_redundancy.html)
- Células: [outputs/campinas_admin/metrics/spatial_multiscale_cells.csv](outputs/campinas_admin/metrics/spatial_multiscale_cells.csv)
- Resumo: [outputs/campinas_admin/metrics/spatial_multiscale_summary.csv](outputs/campinas_admin/metrics/spatial_multiscale_summary.csv)

**Como explicar**

Cada célula é tratada como uma região local. O sistema calcula grau médio, densidade, componentes, pontes, articulações, vulnerabilidade média e sinais de redundância de rotas.

**Por que importa**

O grafo inteiro esconde desigualdades internas. Essa análise mostra onde a rede é mais conectada, mais vulnerável ou menos redundante.

**Comando**

```bash
ic spatial-multiscale --city campinas_admin --cell-size-m 1000
```

## 16. Robustez espacial por bloqueios regionais

**O que é**

Simula falhas concentradas em uma região: remove vias associadas a uma célula e mede o impacto no grafo inteiro.

**O que mostrar**

- Mapa de queda da maior componente: [outputs/campinas_admin/maps/spatial_robustness_lcc_drop.html](outputs/campinas_admin/maps/spatial_robustness_lcc_drop.html)
- Mapa de queda de eficiência: [outputs/campinas_admin/maps/spatial_robustness_efficiency_drop.html](outputs/campinas_admin/maps/spatial_robustness_efficiency_drop.html)
- Mapa de fragmentação: [outputs/campinas_admin/maps/spatial_robustness_fragmentation.html](outputs/campinas_admin/maps/spatial_robustness_fragmentation.html)
- Células testadas: [outputs/campinas_admin/metrics/spatial_robustness_cells.csv](outputs/campinas_admin/metrics/spatial_robustness_cells.csv)
- Resumo: [outputs/campinas_admin/metrics/spatial_robustness_summary.csv](outputs/campinas_admin/metrics/spatial_robustness_summary.csv)

**Como explicar**

Eventos reais raramente removem vias aleatórias espalhadas pela cidade. Enchentes, obras, acidentes e bloqueios costumam afetar áreas locais. Essa análise aproxima o teste de resiliência de cenários urbanos mais realistas.

**Por que importa**

Mostra quais regiões, se bloqueadas, causam maior dano global à rede.

**Comando**

```bash
ic spatial-robustness --city campinas_admin --cell-size-m 1000 --mode incident --eff-samples 10 --max-eff-cells 100 --seed 42
```

## 17. Análise de hierarquia viária

**O que é**

Agrupa as arestas pelo atributo OSM `highway`: primary, secondary, residential, service etc. Depois mede como cada classe contribui para extensão, centralidade, vulnerabilidade e resiliência.

**O que mostrar**

- Mapa de hierarquia: [outputs/campinas_admin/maps/road_hierarchy_impact.html](outputs/campinas_admin/maps/road_hierarchy_impact.html)
- Resumo: [outputs/campinas_admin/metrics/road_hierarchy_summary.csv](outputs/campinas_admin/metrics/road_hierarchy_summary.csv)
- Métricas por classe: [outputs/campinas_admin/metrics/road_hierarchy_by_class.csv](outputs/campinas_admin/metrics/road_hierarchy_by_class.csv)

**Como explicar**

A análise mede se a cidade depende muito de vias arteriais ou se a conectividade é distribuída pela malha local. Também testa o impacto de remover classes inteiras de vias.

**Por que importa**

Conecta a teoria de grafos à função urbana das vias, usando uma informação que já existe no OSM.

**Comando**

```bash
ic road-hierarchy --city campinas_admin --eff-samples 20 --seed 42 --map-edges-per-class 1200
```

## 18. Morfologia urbana: planejamento urbano x estrutura da rede

**O que é**

Classifica células como gradeadas, radiais/lineares, orgânicas, fragmentadas, mistas ou insuficientes, usando orientação das vias, entropia angular e conectividade local.

**O que mostrar**

- Mapa de classes morfológicas: [outputs/campinas_admin/maps/urban_morphology_classes.html](outputs/campinas_admin/maps/urban_morphology_classes.html)
- Mapa de entropia angular: [outputs/campinas_admin/maps/urban_morphology_orientation_entropy.html](outputs/campinas_admin/maps/urban_morphology_orientation_entropy.html)
- Mapa de conectividade morfológica: [outputs/campinas_admin/maps/urban_morphology_connectivity.html](outputs/campinas_admin/maps/urban_morphology_connectivity.html)
- Células classificadas: [outputs/campinas_admin/metrics/urban_morphology_cells.csv](outputs/campinas_admin/metrics/urban_morphology_cells.csv)
- Resumo: [outputs/campinas_admin/metrics/urban_morphology_summary.csv](outputs/campinas_admin/metrics/urban_morphology_summary.csv)

**Como explicar**

Traçados gradeados tendem a ter orientação mais ordenada e conectividade local maior. Traçados orgânicos tendem a ter maior diversidade angular. Áreas fragmentadas têm baixa conectividade ou componentes locais pequenas.

**Por que importa**

Conecta redes complexas com morfologia urbana. Ajuda a discutir padrões locais da cidade e não apenas métricas abstratas.

**Comando**

```bash
ic urban-morphology --city campinas_admin --cell-size-m 1000
```

## 19. Eficiência de rotas em múltiplos pares OD

**O que é**

Amostra muitos pares origem-destino e calcula estatísticas das rotas: distância, hops, circuity, eficiência e acessibilidade por limiares.

**O que mostrar**

- Mapa de rotas com maior desvio: [outputs/campinas_admin/maps/od_efficiency_routes.html](outputs/campinas_admin/maps/od_efficiency_routes.html)
- Resumo estatístico: [outputs/campinas_admin/metrics/od_efficiency_summary.csv](outputs/campinas_admin/metrics/od_efficiency_summary.csv)
- Pares OD: [outputs/campinas_admin/metrics/od_efficiency_pairs.csv](outputs/campinas_admin/metrics/od_efficiency_pairs.csv)

**Como explicar**

Circuity é a razão entre a distância da rota e a distância direta geográfica. Valores maiores indicam rotas mais indiretas. Eficiência relativa é o inverso: distância direta dividida pela distância da rota.

**Por que importa**

Transforma a análise de rota pontual em uma distribuição estatística, mais útil para comparar cidades.

**Comando**

```bash
ic od-efficiency --city campinas_admin --pairs 1000 --seed 42 --map-limit 80
```

## 20. Similaridade entre cidades

**O que é**

Cria vetores de métricas por cidade e mede distância, similaridade cosseno, PCA e clustering.

**O que mostrar**

- Dashboard de similaridade: [outputs/comparisons/city_similarity_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.html](outputs/comparisons/city_similarity_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.html)
- Heatmap de distância: [outputs/comparisons/city_similarity_distance_heatmap_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png](outputs/comparisons/city_similarity_distance_heatmap_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png)
- Heatmap de similaridade cosseno: [outputs/comparisons/city_similarity_cosine_heatmap_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png](outputs/comparisons/city_similarity_cosine_heatmap_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png)
- PCA: [outputs/comparisons/city_similarity_pca_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png](outputs/comparisons/city_similarity_pca_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png)
- Dendrograma: [outputs/comparisons/city_similarity_dendrogram_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png](outputs/comparisons/city_similarity_dendrogram_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.png)
- Vetores: [outputs/comparisons/city_similarity_vectors_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.csv](outputs/comparisons/city_similarity_vectors_campinas_admin_vs_jundiai_admin_vs_sorocaba_admin_vs_valinhos_admin.csv)

**Como explicar**

Cada cidade vira um vetor numérico com métricas consolidadas. O sistema padroniza as métricas por z-score e calcula proximidade entre cidades. Isso permite perguntar: quais cidades são estruturalmente parecidas?

**Por que importa**

Fortalece a parte do projeto sobre padrões universais e especificidades locais. Em vez de comparar métrica por métrica, compara o perfil estrutural completo.

**Comando**

```bash
ic city-similarity campinas_admin jundiai_admin sorocaba_admin valinhos_admin --output-dir outputs/comparisons --min-coverage 1.0
```

## 21. Detecção de subcentros e centralidade policêntrica

**O que é**

Mede se a cidade depende de um centro topológico dominante ou se distribui sua importância entre vários subcentros.

**O que mostrar**

- Mapa de subcentros: [outputs/campinas_admin/maps/subcenters.html](outputs/campinas_admin/maps/subcenters.html)
- Subcentros detectados: [outputs/campinas_admin/metrics/subcenters.csv](outputs/campinas_admin/metrics/subcenters.csv)
- Células e ranking: [outputs/campinas_admin/metrics/subcenters_cells.csv](outputs/campinas_admin/metrics/subcenters_cells.csv)
- Resumo: [outputs/campinas_admin/metrics/subcenters_summary.csv](outputs/campinas_admin/metrics/subcenters_summary.csv)

**Como explicar tecnicamente**

A cidade é dividida em células espaciais. Para cada célula, o sistema calcula um score de subcentro combinando:

- soma e máximo de betweenness dos nós;
- closeness média;
- eigenvector médio;
- densidade local;
- grau médio local;
- quantidade de nós;
- diversidade de comunidades tocadas.

As células elegíveis acima do percentil configurado são classificadas como subcentros. Depois, a distribuição dos scores gera:

- índice de policentralidade: alto quando vários subcentros dividem a importância;
- índice de monocentralidade: alto quando um subcentro domina;
- entropia dos scores: mede dispersão da importância entre subcentros.

**Por que importa**

Duas cidades podem ter métricas globais parecidas, mas uma ser monocêntrica e outra policêntrica. Isso conecta grafos, acessibilidade e planejamento urbano.

**Comando**

```bash
ic subcenters --city campinas_admin --cell-size-m 1000 --percentile 0.90 --min-nodes 20
```

## 22. Exposição da rede a barreiras urbanas

**O que é**

Identifica evidências topológicas de barreiras urbanas prováveis: regiões próximas com poucas conexões, travessias longas, fronteiras entre comunidades, pontes estruturais ou conexões adjacentes ausentes.

**O que mostrar**

- Mapa de permeabilidade: [outputs/campinas_admin/maps/urban_barriers_permeability.html](outputs/campinas_admin/maps/urban_barriers_permeability.html)
- Mapa de conexões/barreiras prováveis: [outputs/campinas_admin/maps/urban_barriers_connections.html](outputs/campinas_admin/maps/urban_barriers_connections.html)
- Células com baixa permeabilidade: [outputs/campinas_admin/metrics/urban_barriers_cells.csv](outputs/campinas_admin/metrics/urban_barriers_cells.csv)
- Conexões entre regiões: [outputs/campinas_admin/metrics/urban_barriers_connections.csv](outputs/campinas_admin/metrics/urban_barriers_connections.csv)
- Resumo: [outputs/campinas_admin/metrics/urban_barriers_summary.csv](outputs/campinas_admin/metrics/urban_barriers_summary.csv)

**Como explicar tecnicamente**

O sistema divide a cidade em células e mede:

- quantas células vizinhas poderiam estar conectadas;
- quantas estão efetivamente conectadas;
- quantas conexões vizinhas estão ausentes;
- quantas travessias existem entre regiões;
- se essas travessias são pontes estruturais;
- se cruzam fronteiras de comunidades;
- se são travessias longas.

Com isso, calcula o índice de permeabilidade espacial e o índice de exposição a barreiras.

**Cuidado metodológico**

Sem camada externa, o sistema não afirma que a barreira é necessariamente rio, ferrovia, rodovia ou vazio urbano. Ele indica evidência topológica de baixa permeabilidade, que depois pode ser conferida visualmente ou cruzada com dados externos.

**Por que importa**

Muitas fragilidades viárias não aparecem só por grau médio. Barreiras físicas e urbanísticas podem reduzir muito as alternativas de travessia.

**Comando**

```bash
ic urban-barriers --city campinas_admin --cell-size-m 1000 --map-limit 250
```

## 23. Perfil de escala da rede viária

**O que é**

Mede se as conclusões espaciais são estáveis em diferentes escalas de grade: 500 m, 1 km, 2 km e 3 km.

**O que mostrar**

- Gráfico de métricas por escala: [outputs/campinas_admin/figures/network_scale_profile_metrics.png](outputs/campinas_admin/figures/network_scale_profile_metrics.png)
- Gráfico de estabilidade: [outputs/campinas_admin/figures/network_scale_profile_stability.png](outputs/campinas_admin/figures/network_scale_profile_stability.png)
- Mapa multiescala de baixa permeabilidade: [outputs/campinas_admin/maps/network_scale_profile_low_permeability.html](outputs/campinas_admin/maps/network_scale_profile_low_permeability.html)
- Métricas por escala: [outputs/campinas_admin/metrics/network_scale_profile_scales.csv](outputs/campinas_admin/metrics/network_scale_profile_scales.csv)
- Estabilidade das métricas: [outputs/campinas_admin/metrics/network_scale_profile_stability.csv](outputs/campinas_admin/metrics/network_scale_profile_stability.csv)
- Resumo: [outputs/campinas_admin/metrics/network_scale_profile_summary.csv](outputs/campinas_admin/metrics/network_scale_profile_summary.csv)

**Como explicar tecnicamente**

O sistema recalcula as métricas locais em várias escalas. Depois mede a variação de cada métrica entre escalas usando coeficiente de variação. O score de estabilidade é maior quando a métrica muda pouco com a escala.

Indicadores importantes:

- índice de robustez multiescalar;
- métrica mais estável;
- métrica menos estável;
- coeficiente de variação por métrica;
- células de maior baixa permeabilidade em cada escala.

**Por que importa**

É uma defesa metodológica. Se uma conclusão só aparece em 1 km, pode ser artefato da grade. Se aparece em várias escalas, a conclusão é mais forte.

**Comando**

```bash
ic network-scale-profile --city campinas_admin --scales 500 1000 2000 3000
```

## 24. Comparação entre cidades

**O que é**

Gera uma tabela e um HTML comparativo com as métricas dos datasets administrativos.

**O que mostrar**

- Comparação HTML: [outputs/comparisons/compare_admin_cities.html](outputs/comparisons/compare_admin_cities.html)
- CSV comparativo: [outputs/comparisons/compare_admin_cities.csv](outputs/comparisons/compare_admin_cities.csv)
- Auditoria de comparabilidade: [outputs/comparisons/comparability_audit_admin.csv](outputs/comparisons/comparability_audit_admin.csv)

**Como explicar**

A comparação coloca lado a lado métricas estruturais, funcionais, espaciais, resiliência, vulnerabilidade, subcentros, barreiras e escala. A auditoria ajuda a verificar se os datasets são comparáveis em recorte e qualidade.

**Por que importa**

O escopo da IC envolve comparar diferentes cidades e buscar padrões recorrentes e especificidades locais. Essa é a saída principal para esse objetivo.

**Comandos**

```bash
ic comparison-audit campinas_admin jundiai_admin sorocaba_admin valinhos_admin --output outputs/comparisons/comparability_audit_admin.csv
ic compare campinas_admin jundiai_admin sorocaba_admin valinhos_admin --output outputs/comparisons/compare_admin_cities.html
```

## 25. Auditoria da análise histórica OSM

**O que é**

Foi criada porque comparações históricas com OSM podem ser enganosas. Um grafo de 10 anos atrás pode parecer menor ou pior conectado não porque a cidade mudou, mas porque o OSM era menos completo.

**O que mostrar**

- Qualidade histórica: [outputs/comparisons/historical_quality_campinas_historical_17_datasets.csv](outputs/comparisons/historical_quality_campinas_historical_17_datasets.csv)
- Relatório histórico: [outputs/comparisons/historical_quality_campinas_historical_17_datasets.txt](outputs/comparisons/historical_quality_campinas_historical_17_datasets.txt)
- Núcleo comum: [outputs/comparisons/historical_common_core_campinas_historical_17_datasets.csv](outputs/comparisons/historical_common_core_campinas_historical_17_datasets.csv)

**Como explicar**

A auditoria mede cobertura histórica em relação ao dataset atual e classifica comparações como `nao_confiavel`, `exploratorio` ou `comparavel_com_cautela`. Isso evita confundir evolução do mapeamento com evolução urbana.

**Por que importa**

É uma proteção metodológica importante. Sem essa auditoria, a análise histórica poderia produzir conclusões erradas.

**Comando**

```bash
ic historical-audit --reference campinas campinas_2010 campinas_2011 campinas_2012 --output-dir outputs/comparisons
```

## 26. Relatório final automático e manifesto experimental

**O que é**

O relatório consolida os principais resultados de uma cidade. O manifesto lista os arquivos gerados e metadados do experimento.

**O que mostrar**

- Relatório: [outputs/campinas_admin/REPORT_campinas_admin.md](outputs/campinas_admin/REPORT_campinas_admin.md)
- Manifesto: [outputs/campinas_admin/MANIFEST_campinas_admin.txt](outputs/campinas_admin/MANIFEST_campinas_admin.txt)
- Manifesto JSON: [outputs/campinas_admin/EXPERIMENT_MANIFEST_campinas_admin.json](outputs/campinas_admin/EXPERIMENT_MANIFEST_campinas_admin.json)

**Como explicar**

O relatório automático não substitui o relatório científico da IC. Ele é o pacote técnico de dados, tabelas, mapas e evidências que sustenta a escrita acadêmica posterior.

**Por que importa**

Ajuda na reprodutibilidade e evita perda de contexto. Cada execução fica registrada com seus artefatos.

**Comando**

```bash
ic report --city campinas_admin
```

## 27. Ordem recomendada para apresentar na reunião

1. Mostrar o dashboard geral para dar visão do sistema.
2. Mostrar grafo de ruas e distribuição de grau para explicar a base.
3. Mostrar centralidades e comunidades.
4. Mostrar resiliência por arestas, vértices e comunidades.
5. Mostrar vulnerabilidade, pontes, articulações e gargalos.
6. Mostrar redundância de rotas, eficiência OD e robustez espacial.
7. Mostrar hierarquia viária, morfologia urbana, subcentros e barreiras.
8. Mostrar perfil de escala para defender a metodologia.
9. Mostrar comparação entre cidades e similaridade.
10. Fechar com auditoria histórica e relatório consolidado.

## 28. Comando completo recomendado para regenerar os principais dados de uma cidade

```bash
ic structural --city campinas_admin
ic centrality --city campinas_admin
ic functional-relations --city campinas_admin
ic validate-approximations --city campinas_admin
ic communities --city campinas_admin
ic resilience --city campinas_admin --strategy targeted
ic node-resilience --city campinas_admin --strategy targeted
ic random-resilience-stats --city campinas_admin --mode both
ic community-resilience --city campinas_admin --strategy targeted
ic intra-community-resilience --city campinas_admin --strategy targeted
ic vulnerability-index --city campinas_admin
ic structural-bottlenecks --city campinas_admin
ic route-redundancy --city campinas_admin
ic spatial-multiscale --city campinas_admin
ic spatial-robustness --city campinas_admin
ic road-hierarchy --city campinas_admin
ic urban-morphology --city campinas_admin
ic od-efficiency --city campinas_admin
ic subcenters --city campinas_admin
ic urban-barriers --city campinas_admin
ic network-scale-profile --city campinas_admin
ic inventory --city campinas_admin
ic report --city campinas_admin
ic dashboard --city campinas_admin
```

## 29. Frase de fechamento para a reunião

O projeto já possui uma base computacional capaz de transformar o grafo viário de uma cidade em um conjunto amplo de evidências: métricas estruturais, centralidades, comunidades, resiliência, vulnerabilidade, acessibilidade, morfologia urbana, barreiras, subcentros, perfil de escala e comparação entre cidades. A próxima etapa natural é usar esses dados para escrever a análise científica: formular hipóteses, comparar os resultados entre cidades, discutir limitações e relacionar os padrões encontrados com a literatura de redes complexas e planejamento urbano.
