# Fechamento das lacunas computacionais do escopo da IC

Data da revisão: 4 de junho de 2026.

Status após implementação: **concluído para o escopo computacional atual**.

Referência: `_Projeto_2026__Lucas_Soares.pdf`, plano **Análise Estrutural da Rede Viária Urbana Brasileira Utilizando Métricas de Redes Complexas**.

## Recorte desta revisão

Esta revisão considera apenas a primeira parte computacional do projeto: dado um grafo de uma
cidade, o sistema deve gerar dados, tabelas, rankings, curvas, mapas e dashboards para análise
posterior no relatório.

Não entram aqui como lacunas de software:

- escrita do relatório parcial ou final;
- revisão bibliográfica;
- interpretação científica final;
- avaliação qualitativa feita por humano;
- participação em eventos ou escrita de artigo.

## Estado computacional atual

O repositório já cobre a maior parte do escopo computacional prometido no PDF.

| Item do PDF | Estado computacional | Evidência no projeto |
|---|---|---|
| Base de grafos de cidades brasileiras | Implementado | `ic download`, `ic preprocess`, metadados em `data/metadata/` e grafos em `data/graphs/` |
| Métricas estruturais fundamentais | Implementado | `ic structural` gera grau, densidade, transitividade, clustering aproximado, assortatividade, caminho médio e diâmetro aproximados |
| Distribuição de graus | Implementado | `degree_distribution.csv` e `degree_distribution_loglog.png` |
| Centralidade de grau | Implementado | `top_nodes.csv`, `node_centralities.csv`, `centrality_rankings.csv` |
| Centralidade de intermediação | Implementado | rankings de nós e arestas críticas |
| Centralidade de proximidade | Implementado | `closeness_approx` e validação por subgrafo |
| Centralidade de autovetor | Implementado | `eigenvector` nos rankings |
| Resiliência por arestas | Implementado | `ic resilience` com estratégias aleatória, dirigida e adaptativa |
| Resiliência por vértices | Implementado | `ic node-resilience` com estratégias aleatória, dirigida e adaptativa |
| Comparação entre cidades | Implementado parcialmente | `ic comparison-audit` e `ic compare` |
| Visualizações interativas | Implementado | dashboards HTML, mapas de pontos críticos e mapas de rotas |
| Relação topologia-função | Implementado como expansão útil | `ic functional-relations` usa atributos OSM como tipo de via, superfície, velocidade, faixas e mão única |
| Análise histórica | Implementado como expansão controlada | `ic historical-audit` mede viés de cobertura OSM antes de interpretar anos antigos |
| Vulnerabilidade composta | Implementado como expansão útil | `ic vulnerability-index` gera rankings e mapas compostos de nós e arestas críticas |

## Itens que foram fechados

### 1. Comunidades nos datasets principais comparáveis

Os quatro datasets administrativos (`campinas_admin`, `jundiai_admin`, `sorocaba_admin` e
`valinhos_admin`) agora têm os artefatos de comunidades gerados:

- `community_summary.csv`;
- `nodes_communities.csv`;
- `maps/comunidades.html`;
- curvas de resiliência entre comunidades;
- resiliência interna por comunidade.

Comunidades analisadas na resiliência interna dirigida:

- Campinas administrativa: 103 comunidades;
- Jundiaí administrativa: 73 comunidades;
- Sorocaba administrativa: 71 comunidades;
- Valinhos administrativa: 43 comunidades.

### 2. Tabela comparativa consolidada em CSV

O comparador agora gera, além do HTML, uma tabela CSV em formato longo:

- `outputs/comparisons/compare_admin_cities.html`;
- `outputs/comparisons/compare_admin_cities.csv`.

O CSV contém:

- dataset;
- grupo da métrica;
- nome técnico da métrica;
- rótulo humano;
- valor;
- unidade;
- descrição.

Isso permite importar os resultados diretamente em planilha, Python, R ou no texto do
relatório.

### 3. Estatísticas agregadas dos ataques aleatórios

Foi implementado o comando:

```bash
ic random-resilience-stats --city <dataset> --mode both --seeds 42 43 44 45 46
```

Ele roda ataques aleatórios por arestas e por vértices com múltiplas sementes e gera:

- média;
- desvio-padrão;
- mínimo e máximo;
- curva agregada da maior componente e da eficiência.

Arquivos principais por dataset:

- `metrics/resilience_random_aggregate.csv`;
- `metrics/node_resilience_random_aggregate.csv`;
- `figures/resilience_random_aggregate.png`;
- `figures/node_resilience_random_aggregate.png`.

### 4. Manifesto experimental mais completo

Cada relatório consolidado agora gera também:

- `EXPERIMENT_MANIFEST_<dataset>.json`.

Esse manifesto registra:

- comando executado;
- comando recomendado para regeneração do relatório;
- versão do Python;
- versões de OSMnx, NetworkX, pandas, numpy e scipy;
- data/hora da execução;
- commit Git, quando disponível;
- caminhos dos arquivos gerados.

Isso atende diretamente ao resultado esperado do PDF: base estruturada, metadados
padronizados e documentação técnica dos procedimentos.

### 5. Mapa visual das arestas críticas

O comando `ic centrality` agora gera um mapa próprio de vias/arestas críticas:

- `maps/arestas_criticas.html`.

O ranking `top_edges.csv` também foi enriquecido com:

- arestas de maior edge betweenness;
- nome da via, quando disponível;
- tipo OSM da via;
- comprimento;
- ranking;
- score de criticidade.

Isso melhora a ligação entre métrica topológica e interpretação urbana posterior.

## Artefatos finais atualizados

Foram regenerados para os quatro datasets administrativos:

- inventários;
- dashboards;
- relatórios Markdown;
- manifestos TXT;
- manifestos JSON;
- imagens do grafo;
- comparação HTML;
- comparação CSV;
- auditoria de comparabilidade.

## Expansão implementada após o fechamento

Foi adicionada uma primeira expansão ainda alinhada ao PDF: o **Índice Composto de
Vulnerabilidade Viária**.

O comando:

```bash
ic vulnerability-index --city <dataset> --top-k 100
```

gera:

- `metrics/vulnerability_nodes.csv`;
- `metrics/vulnerability_edges.csv`;
- `maps/vulnerability_nodes.html`;
- `maps/vulnerability_edges.html`;
- `logs/vulnerability_index_report.txt`.

O índice de nós combina centralidade, participação em ataques por vértices e pontos de
articulação. O índice de arestas combina edge betweenness, pontes estruturais, importância do
tipo de via, comprimento e fronteiras entre comunidades. O objetivo é produzir um ranking
único para priorizar elementos que concentram múltiplos sinais de criticidade.

Também foi adicionada a expansão **Pontes, Articulações e Gargalos Estruturais**.

O comando:

```bash
ic structural-bottlenecks --city <dataset> --top-k 100
```

gera:

- `metrics/structural_articulations.csv`;
- `metrics/structural_bridges.csv`;
- `metrics/structural_bottlenecks.csv`;
- `maps/structural_articulations.html`;
- `maps/structural_bridges.html`;
- `maps/structural_bottlenecks.html`;
- `logs/structural_bottlenecks_report.txt`.

Essa etapa separa explicitamente gargalos topológicos de rankings compostos. Ela mede, para
cada ponte ou nó de articulação, quantos nós deixam de pertencer à maior componente caso o
elemento seja removido. Isso gera evidências diretas para discutir fragmentação viária.

Foi adicionada ainda a expansão **Perfil de Redundância de Rotas**.

O comando:

```bash
ic route-redundancy --city <dataset> --pairs 100 --threshold 1.50 --seed 42
```

gera:

- `metrics/route_redundancy_pairs.csv`;
- `metrics/route_redundancy_summary.csv`;
- `maps/route_redundancy.html`;
- `logs/route_redundancy_report.txt`.

A análise amostra pares origem-destino, calcula a menor rota por distância, bloqueia todos os
segmentos dessa rota e verifica se ainda existe caminho alternativo. A alternativa é
classificada como razoável quando sua distância não ultrapassa o limiar configurado em relação
à rota original. Isso permite discutir robustez funcional da malha, não apenas conectividade
topológica.

Foi adicionada também a expansão **Análise Multiescala por Células Espaciais**.

O comando:

```bash
ic spatial-multiscale --city <dataset> --cell-size-m 1000
```

gera:

- `metrics/spatial_multiscale_cells.csv`;
- `metrics/spatial_multiscale_summary.csv`;
- `maps/spatial_multiscale_vulnerability.html`;
- `maps/spatial_multiscale_connectivity.html`;
- `maps/spatial_multiscale_redundancy.html`;
- `logs/spatial_multiscale_report.txt`.

A cidade é dividida em uma grade espacial regular e cada célula recebe métricas locais do
subgrafo induzido pelos seus nós. Quando os módulos anteriores já foram executados, a análise
também agrega vulnerabilidade e redundância de rotas por célula. Isso permite observar
desigualdades internas da rede viária que o indicador global do grafo inteiro pode esconder.

Foi adicionada ainda a expansão **Robustez Espacial: Impacto de Bloqueios por Região**.

O comando:

```bash
ic spatial-robustness --city <dataset> --cell-size-m 1000 --mode incident --eff-samples 10 --max-eff-cells 100
```

gera:

- `metrics/spatial_robustness_cells.csv`;
- `metrics/spatial_robustness_summary.csv`;
- `maps/spatial_robustness_lcc_drop.html`;
- `maps/spatial_robustness_efficiency_drop.html`;
- `maps/spatial_robustness_fragmentation.html`;
- `logs/spatial_robustness_report.txt`.

Essa etapa simula falhas concentradas no espaço: para cada célula da grade, remove vias
associadas à região e mede o impacto no grafo inteiro. Isso aproxima o experimento de
cenários urbanos reais, como enchentes, obras, acidentes e bloqueios localizados.

Foi adicionada também a expansão **Análise de Hierarquia Viária**.

O comando:

```bash
ic road-hierarchy --city <dataset> --eff-samples 20 --seed 42 --map-edges-per-class 1200
```

gera:

- `metrics/road_hierarchy_by_class.csv`;
- `metrics/road_hierarchy_summary.csv`;
- `maps/road_hierarchy_impact.html`;
- `logs/road_hierarchy_report.txt`.

A análise agrupa as vias pelo atributo OSM `highway`, agregando links à classe principal
quando aplicável, por exemplo `primary_link` em `primary`. Para cada classe, calcula
participação em arestas e extensão, presença em pontes estruturais, vulnerabilidade média,
centralidade observada nas arestas críticas e impacto de remover toda a classe do grafo. Isso
permite discutir se a cidade depende excessivamente de vias arteriais ou se a conectividade é
mais distribuída na malha local.

Foi adicionada também a expansão **Comparação Planejamento Urbano x Estrutura da Rede**.

O comando:

```bash
ic urban-morphology --city <dataset> --cell-size-m 1000
```

gera:

- `metrics/urban_morphology_cells.csv`;
- `metrics/urban_morphology_summary.csv`;
- `maps/urban_morphology_classes.html`;
- `maps/urban_morphology_orientation_entropy.html`;
- `maps/urban_morphology_connectivity.html`;
- `logs/urban_morphology_report.txt`.

A análise divide a cidade em células espaciais e classifica cada região como gradeada,
radial/linear, orgânica, fragmentada, mista ou insuficiente. A classificação usa orientação
das vias, entropia angular, participação de eixos ortogonais dominantes, conectividade local,
maior componente e comprimento médio dos segmentos. Isso conecta métricas de grafos com
morfologia urbana e permite discutir padrões universais e especificidades locais da malha.

Foi adicionada também a expansão **Eficiência de Rotas em Múltiplos Pares Origem-Destino**.

O comando:

```bash
ic od-efficiency --city <dataset> --pairs 1000 --seed 42 --map-limit 80
```

gera:

- `metrics/od_efficiency_pairs.csv`;
- `metrics/od_efficiency_summary.csv`;
- `maps/od_efficiency_routes.html`;
- `logs/od_efficiency_report.txt`.

A análise amostra centenas ou milhares de pares origem-destino no grafo dirigido, calcula a
menor rota por distância e registra distância da rota, hops, distância direta geográfica,
desvio, circuity, eficiência relativa e acessibilidade por limiares de 2 km, 5 km e 10 km.
Isso transforma a rota pontual em uma distribuição estatística útil para comparar cidades.

Foi adicionada também a expansão **Similaridade Entre Cidades**.

O comando:

```bash
ic city-similarity <dataset_1> <dataset_2> <dataset_3> --output-dir outputs/comparisons
```

gera:

- `city_similarity_vectors_<datasets>.csv`;
- `city_similarity_distances_<datasets>.csv`;
- `city_similarity_cosine_<datasets>.csv`;
- `city_similarity_pca_<datasets>.csv`;
- `city_similarity_clusters_<datasets>.csv`;
- `city_similarity_nearest_<datasets>.csv`;
- `city_similarity_<datasets>.html`;
- mapas estáticos de distância, similaridade, PCA e dendrograma.

A análise usa métricas numéricas do inventário consolidado de cada cidade, preenche ausências
com a média da métrica, padroniza os indicadores por z-score e calcula distância euclidiana,
similaridade cosseno, PCA e clustering hierárquico. Isso permite responder quais cidades são
estruturalmente mais parecidas e quais se afastam do padrão do conjunto.

Foi adicionada também a expansão **Detecção de Subcentros e Centralidade Policêntrica**.

O comando:

```bash
ic subcenters --city <dataset> --cell-size-m 1000 --percentile 0.90 --min-nodes 20
```

gera:

- `metrics/subcenters_cells.csv`;
- `metrics/subcenters.csv`;
- `metrics/subcenters_summary.csv`;
- `maps/subcenters.html`;
- `logs/subcenters_report.txt`.

A análise divide a cidade em células espaciais e calcula um score de subcentro com base em
centralidade acumulada, centralidade máxima, densidade local, conectividade, centralidade de
proximidade, autovetor e diversidade de comunidades tocadas. As regiões acima do percentil
configurado são classificadas como subcentros. A distribuição dos scores gera índices de
policentralidade e monocentralidade, permitindo discutir se a cidade depende de um centro
dominante ou se distribui sua importância estrutural entre vários núcleos.

Foi adicionada também a expansão **Exposição da Rede a Barreiras Urbanas**.

O comando:

```bash
ic urban-barriers --city <dataset> --cell-size-m 1000 --map-limit 250
```

gera:

- `metrics/urban_barriers_cells.csv`;
- `metrics/urban_barriers_connections.csv`;
- `metrics/urban_barriers_summary.csv`;
- `maps/urban_barriers_permeability.html`;
- `maps/urban_barriers_connections.html`;
- `logs/urban_barriers_report.txt`.

A análise infere barreiras prováveis usando apenas a topologia da rede viária. Ela divide a
cidade em células espaciais e mede a permeabilidade entre células vizinhas, conexões
adjacentes ausentes, travessias longas, pontes estruturais incidentes e fronteiras entre
comunidades. Com isso, gera um ranking de células com baixa permeabilidade e um ranking de
conexões entre regiões com maior score de barreira provável.

O resultado não afirma a existência física de rios, ferrovias ou rodovias sem uma camada
externa. Ele identifica evidências topológicas de baixa permeabilidade, úteis para orientar a
análise posterior e aproximar o grafo da morfologia urbana real.

Foi adicionada também a expansão **Perfil de Escala da Rede Viária**.

O comando:

```bash
ic network-scale-profile --city <dataset> --scales 500 1000 2000 3000
```

gera:

- `metrics/network_scale_profile_scales.csv`;
- `metrics/network_scale_profile_cells.csv`;
- `metrics/network_scale_profile_stability.csv`;
- `metrics/network_scale_profile_summary.csv`;
- `figures/network_scale_profile_metrics.png`;
- `figures/network_scale_profile_stability.png`;
- `maps/network_scale_profile_low_permeability.html`;
- `logs/network_scale_profile_report.txt`.

A análise recalcula métricas espaciais em diferentes tamanhos de célula e mede como os
resultados mudam conforme a escala. Para cada escala, são avaliados número de células,
quantidade média de nós, grau médio local, densidade, fração da maior componente local,
permeabilidade espacial, fração de células pouco permeáveis e score médio de baixa
permeabilidade.

Em seguida, o sistema calcula a estabilidade de cada métrica entre escalas usando coeficiente
de variação e um score de estabilidade. O índice de robustez multiescalar resume a estabilidade
das principais métricas locais. Isso ajuda a separar conclusões robustas de efeitos que podem
ser artefatos da escolha de uma grade específica.

## Conclusão

O núcleo computacional prometido para esta etapa pode ser considerado fechado: dado o grafo de
uma cidade, o sistema gera métricas estruturais, centralidades, comunidades, resiliência por
arestas, vértices e comunidades, estatísticas agregadas de ataques aleatórios, mapas,
dashboards, relatórios, manifestos e comparação consolidada entre cidades.
