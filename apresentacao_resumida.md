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

**Fala sugerida**

"Aqui eu estou mostrando uma análise que não existia no projeto inicial: além de remover ruas,
eu passo a remover interseções. Esses dados vêm do grafo viário limpo, em que os vértices são
cruzamentos ou pontos estruturais da malha. A curva mostra quanto da rede continua conectada
conforme os vértices mais críticos são removidos. Isso serve para discutir se a cidade depende
de poucos cruzamentos estratégicos e para comparar esse comportamento com a remoção de vias.

No gráfico, o eixo X é a fração de vértices removidos, ou seja, quanto da rede foi atacada. O
eixo Y mostra frações retidas, principalmente a maior componente conectada e a eficiência
topológica. Se a curva cai rápido, significa que poucas remoções já prejudicam bastante a
conectividade. O CSV de vértices removidos mostra quais nós entraram no ataque, em qual ordem e
com quais métricas de centralidade. Então eu posso apontar não só que a rede perde robustez, mas
também quais interseções explicam essa perda."

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

**Fala sugerida**

"Aqui eu separo a cidade em comunidades detectadas pela própria estrutura do grafo. Os dados vêm
do arquivo que associa cada nó a uma comunidade e das conexões entre essas comunidades. A análise
entre comunidades mostra se as regiões dependem de poucas ligações externas. A análise interna
mostra se uma comunidade específica se fragmenta rápido quando perde ruas. Isso ajuda a mostrar
que a robustez da cidade não é uniforme: uma rede pode parecer boa no agregado, mas ter regiões
internamente frágeis.

Nos gráficos de robustez entre comunidades, o eixo X é a fração de conexões entre comunidades
removidas. O eixo Y mostra a fração ainda preservada na maior componente do grafo agregado,
tanto em número de comunidades quanto ponderada pelos nós representados. Já no gráfico de
robustez interna, cada ponto representa uma comunidade: o eixo X é o tamanho da comunidade em
nós, e o eixo Y é a AUC da curva de robustez interna. Comunidades com AUC menor são mais frágeis.
O CSV de conexões críticas mostra quais ligações entre comunidades sustentam mais a integração
da rede urbana."

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

**Fala sugerida**

"Algumas métricas, como betweenness e closeness, são muito custosas em grafos grandes. Então o
sistema usa aproximações. Este arquivo mostra de onde vem a confiança nessas aproximações: eu
pego subgrafos controlados, calculo o valor exato e comparo com o aproximado. Isso é importante
porque eu consigo dizer ao professor quais métricas são mais estáveis e quais precisam de mais
cautela na análise.

Aqui a saída principal é tabular. Cada linha do CSV representa uma combinação de métrica,
tamanho de amostra e repetição. As colunas mostram erro, correlação de ranking e parâmetros do
teste. O dado representa uma auditoria interna do método: se a correlação é alta, o ranking
aproximado preserva bem a ordem dos elementos mais importantes; se é baixa, aquela aproximação
deve ser usada apenas como indicativo. Isso é importante para eu não vender uma métrica
aproximada como se fosse exata."

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

**Fala sugerida**

"Este ranking junta vários sinais de criticidade em um único índice. Os dados vêm das
centralidades, da detecção de pontes e articulações, das comunidades, dos atributos das vias e
dos testes de robustez. O que ele representa não é uma verdade absoluta de risco urbano, mas uma
priorização topológica: quais nós e arestas concentram mais sinais de vulnerabilidade. Isso é
útil para escolher o que analisar com mais detalhe no relatório.

Nos mapas, não há eixo X e Y; a leitura é espacial. Cada ponto ou linha representa um nó ou uma
aresta, e a cor/tamanho indica maior ou menor score de vulnerabilidade. Ao clicar no popup, eu
consigo ver os componentes do score, como centralidade, se é ponte, se está em fronteira entre
comunidades e o tipo de via. Nos CSVs, cada linha é um elemento da rede e as colunas mostram os
critérios que formaram o índice. Então eu consigo explicar por que um trecho apareceu como
vulnerável, em vez de apenas mostrar um ranking sem justificativa."

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

**Fala sugerida**

"Aqui eu mostro os elementos que são gargalos estruturais no sentido matemático. Os dados vêm do
grafo limpo e de algoritmos de pontes e nós de articulação. Uma ponte é uma aresta cuja remoção
fragmenta a rede; uma articulação é um nó cuja remoção faz o mesmo. Isso é forte para o projeto
porque não depende de interpretação subjetiva: o próprio grafo mostra que certos pontos sustentam
a conectividade entre partes da cidade.

Nos mapas, os pontos representam articulações e as linhas representam pontes estruturais ou
gargalos. A leitura é espacial: eu mostro onde esses elementos estão na cidade. O popup informa
o ranking, o score e principalmente quantos nós saem da maior componente se aquele elemento for
removido. No CSV, cada linha é um gargalo, com tipo, elemento, score, componentes após remoção e
nós destacados. Isso significa que eu consigo defender tecnicamente por que um ponto é crítico:
não é porque ele parece importante no mapa, mas porque a remoção dele fragmenta o grafo."

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

**Fala sugerida**

"Nesta parte eu estou medindo redundância de rotas. Os dados vêm de pares origem-destino
amostrados no grafo. Para cada par, o sistema calcula a melhor rota, bloqueia essa rota e tenta
encontrar uma alternativa. Isso representa a capacidade estrutural da rede de oferecer caminhos
substitutos. No projeto, isso ajuda a diferenciar cidades que parecem parecidas em distância
média, mas têm níveis diferentes de alternativas viárias.

No mapa, cada linha representa uma rota analisada ou uma rota alternativa relevante. A leitura é
geográfica, não por eixo: eu mostro visualmente onde os pares OD têm maior desvio ou pior
alternativa. No CSV de pares, cada linha é um par origem-destino, com distância original,
existência de alternativa, razão entre alternativa e rota original e indicação se a alternativa
é razoável. No resumo, as métricas principais são taxa de alternativa, taxa de alternativa
razoável e taxa de desconexão após bloqueio. Isso mostra se a malha tem redundância ou se ela
depende demais de corredores únicos."

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

**Fala sugerida**

"Aqui eu divido a cidade em células espaciais, normalmente de 1 km. Os dados vêm do mesmo grafo
viário, mas agregados por região. Em cada célula eu calculo conectividade local, vulnerabilidade,
pontes, articulações e sinais de redundância. Isso representa uma leitura interna da cidade: em
vez de dizer apenas como Campinas é no total, eu consigo mostrar quais regiões são mais frágeis
ou mais conectadas.

Nos mapas, cada quadrado é uma célula espacial. A cor representa a métrica escolhida: no mapa de
vulnerabilidade, cores mais fortes indicam maior vulnerabilidade local; no de conectividade,
indicam maior grau médio local; no de redundância, indicam maior taxa de desconexão ou baixa
alternativa. O popup mostra os valores da célula, como número de nós, arestas internas,
vulnerabilidade máxima e redundância. No CSV, cada linha é uma célula. Isso é útil porque eu
consigo apontar regiões específicas da cidade e dizer quais têm pior comportamento estrutural."

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

**Fala sugerida**

"Nesta análise eu simulo bloqueios por região. Os dados vêm das células espaciais: para cada
célula, o sistema remove vias associadas àquela área e mede o impacto no grafo inteiro. Isso não
é uma previsão de enchente ou acidente, mas um experimento topológico. Ele serve para responder:
se uma região da cidade ficar comprometida, qual seria o impacto estrutural na conectividade
global?

Nos mapas, cada célula recebe uma cor de acordo com o impacto do bloqueio. No mapa de LCC, a cor
representa a queda da maior componente conectada; no mapa de eficiência, representa quanto a
eficiência topológica cai; no mapa de fragmentação, representa o aumento no número de
componentes. Portanto, quanto mais intensa a célula, maior o impacto global de bloquear aquela
região. No CSV, cada linha é uma célula simulada, com arestas removidas, queda de LCC,
eficiência retida e componentes após bloqueio. Isso ajuda a identificar regiões espacialmente
sensíveis da rede."

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

**Fala sugerida**

"Aqui eu uso o atributo `highway` do OpenStreetMap para separar as vias por hierarquia, como
primárias, secundárias, residenciais e serviços. Esses dados vêm diretamente dos atributos OSM
das arestas. A análise mede quanto cada classe contribui para extensão, centralidade e robustez.
Isso representa a dependência da rede em relação a certos tipos de via. No projeto, permite
discutir se a cidade é muito dependente de arteriais ou se a malha local também distribui bem a
conectividade.

No mapa, as arestas são coloridas por classe viária, então eu consigo mostrar espacialmente onde
estão as vias arteriais, coletoras, residenciais e de serviço. Nos CSVs, cada linha representa
uma classe `highway`. As colunas mostram quantidade de arestas, extensão total, participação na
rede, centralidade observada e impacto da remoção daquela classe. Se remover uma classe causa
grande queda na maior componente ou na eficiência, isso indica dependência estrutural daquela
hierarquia. Esse dado pode ser usado no projeto para ligar a topologia da rede à função urbana
das vias."

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

**Fala sugerida**

"Nesta parte eu tento aproximar o grafo da morfologia urbana. Os dados vêm da geometria das
arestas: orientação das vias, comprimento dos segmentos e conectividade dentro de cada célula.
Com isso, o sistema classifica regiões como gradeadas, lineares, orgânicas ou fragmentadas.
Isso não substitui uma análise urbanística humana, mas dá um indicador quantitativo para falar
do padrão espacial da malha viária.

Nos mapas, cada célula representa uma região da cidade. No mapa de classes, a cor indica a
classe morfológica atribuída: gradeada, radial/linear, orgânica, fragmentada ou mista. No mapa
de entropia angular, cores mais fortes indicam maior diversidade de orientação das vias; isso
sugere traçados mais irregulares. No mapa de conectividade, a cor representa conectividade
local. No CSV, cada linha é uma célula e as colunas trazem orientação, entropia, grau médio,
maior componente e classe final. Assim eu consigo explicar que a classificação vem de métricas
calculadas e não de uma impressão visual."

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

**Fala sugerida**

"Aqui eu saio de uma rota isolada e passo para muitos pares origem-destino. Os dados vêm de nós
amostrados no grafo, não de dados reais de viagem. Para cada par, o sistema mede distância da
rota, distância direta, desvio, eficiência e número de trechos percorridos. Isso representa a
eficiência estrutural da malha para deslocamentos hipotéticos. No projeto, serve para comparar
cidades de forma estatística, sem depender de um único exemplo de rota.

No mapa, aparecem rotas selecionadas, principalmente as de maior desvio. A leitura é espacial:
eu posso mostrar onde a malha obriga caminhos mais indiretos. No CSV de pares, cada linha é um
par OD, com distância da rota, distância direta, número de hops, circuity e eficiência. A
circuity é a razão entre distância da rota e distância direta; quanto maior, mais indireto é o
caminho. Se eu gerar ou mostrar gráficos dessa análise, normalmente o eixo X pode ser distância,
circuity ou eficiência, e o eixo Y pode ser frequência ou valor agregado. O resumo CSV mostra
médias, percentis e taxas de acessibilidade em limiares como 2 km, 5 km e 10 km."

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

**Fala sugerida**

"Nesta parte cada cidade vira um vetor de métricas. Os dados vêm do inventário consolidado de
cada dataset: tamanho, centralidades, robustez, vulnerabilidade, morfologia, barreiras e outras
métricas. O sistema padroniza tudo e calcula distância, similaridade, PCA e agrupamento. Isso
representa uma comparação multivariada entre cidades. Eu vou apresentar como exploração, porque
com quatro cidades ainda não dá para falar em padrão universal, mas já mostra como o projeto pode
comparar estruturas urbanas diferentes.

No heatmap de distância, os dois eixos são as cidades comparadas, e cada célula mostra a
distância entre os vetores de métricas: valores menores indicam cidades mais parecidas segundo
esse conjunto de indicadores. No heatmap de similaridade cosseno, os eixos também são cidades,
mas valores maiores indicam perfis mais alinhados. No PCA, o eixo X é o primeiro componente
principal e o eixo Y é o segundo; eles resumem a variação multivariada em duas dimensões para
visualizar agrupamentos. No dendrograma, o eixo mostra a distância de junção entre cidades ou
grupos. O ponto central é: isso não prova causalidade, mas organiza a comparação entre cidades
de forma quantitativa."

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

**Fala sugerida**

"Aqui eu identifico células candidatas a subcentros topológicos. Os dados vêm das centralidades
dos nós, das comunidades e da densidade local em cada célula. O score mostra regiões que
concentram importância estrutural na rede viária. Eu não vou afirmar que são subcentros urbanos
reais, porque para isso precisaria de empregos, população e atividades. Mas isso já indica onde
a própria rede concentra acessibilidade e importância topológica.

No mapa, cada célula recebe uma cor de acordo com o score de candidatura. As células destacadas
com marcadores são as que passaram do percentil definido. O popup mostra o score, ranking,
quantidade de nós, arestas, centralidade acumulada e comunidades tocadas. No CSV
`subcenters.csv`, cada linha é uma célula candidata; no `subcenters_summary.csv`, aparecem
indicadores como dispersão, dominância e participação da principal célula. Então eu posso dizer:
esta não é uma validação socioeconômica de centralidade urbana, mas uma detecção de concentração
topológica na rede viária."

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

**Fala sugerida**

"Nesta análise eu procuro sinais de barreiras urbanas pela própria estrutura do grafo. Os dados
vêm das conexões entre células vizinhas, das pontes estruturais, das comunidades e do comprimento
das travessias. O resultado representa baixa permeabilidade topológica: regiões próximas que têm
poucas ligações entre si ou dependem de poucas travessias. Eu não afirmo automaticamente que é
um rio, ferrovia ou rodovia; eu digo que o grafo sugere uma barreira que vale investigar.

No mapa de permeabilidade, cada célula é colorida conforme o score de baixa permeabilidade:
cores mais fortes indicam regiões com menos conexões para células vizinhas ou maior dependência
de travessias críticas. No mapa de conexões, as linhas ligam pares de células; linhas mais
críticas indicam pares com poucas travessias, travessias longas, pontes estruturais ou fronteiras
de comunidade. No CSV de células, cada linha é uma região; no CSV de conexões, cada linha é um
par de regiões. Esse dado pode ser usado para levantar hipóteses: onde a rede parece ser cortada
ou menos permeável?"

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

**Fala sugerida**

"Aqui eu testo a sensibilidade da análise espacial. Os dados vêm do mesmo grafo, mas agregados
em células de 500 metros, 1 km, 2 km e 3 km. O sistema mede se as métricas mudam muito quando eu
mudo a escala. Isso representa uma checagem metodológica: se uma conclusão aparece em várias
escalas, ela é mais robusta; se aparece só em uma escala, talvez dependa da escolha da grade.

No gráfico de métricas por escala, o eixo X é o tamanho da célula em metros: 500, 1000, 2000 e
3000. O eixo Y mostra o valor agregado da métrica, como grau médio local, maior componente local,
permeabilidade ou fração de baixa permeabilidade. Se a linha muda muito entre escalas, a métrica
é sensível à resolução. No gráfico de estabilidade, o eixo Y lista as métricas e o eixo X mostra
o score de estabilidade entre 0 e 1; valores mais próximos de 1 são mais estáveis. O mapa permite
alternar camadas por escala para ver se as regiões críticas permanecem parecidas."

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

**Fala sugerida**

"Essa auditoria nasceu de uma limitação importante: comparar o OSM atual com o OSM antigo pode
confundir evolução da cidade com evolução do mapeamento. Os dados vêm dos grafos históricos e
do grafo de referência atual. O sistema mede cobertura e núcleo comum para dizer se uma
comparação histórica é confiável ou apenas exploratória. Isso protege o projeto contra uma
conclusão errada sobre crescimento urbano.

A saída principal é tabular. Cada linha representa um dataset histórico comparado com a
referência. As colunas indicam cobertura, proporção de caminhos preservados, elementos ausentes
e classificação de confiabilidade. O arquivo de núcleo comum mostra quais elementos podem ser
comparados com menos viés. Então, na apresentação, eu posso dizer que a análise histórica não
foi descartada, mas passou a ter um gate metodológico: só interpreto diferenças temporais quando
a cobertura do OSM permite."

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

**Fala sugerida**

"Aqui eu mostro a parte de consolidação. Os dados vêm de todos os módulos anteriores e são
organizados em dashboard, relatório, inventário e comparação entre cidades. Isso representa a
entrega prática do sistema: eu não preciso abrir dezenas de arquivos soltos, porque o projeto
gera uma leitura organizada dos resultados. Para a IC, isso facilita a apresentação e depois a
escrita do relatório científico.

O dashboard é visual e navegável: ele reúne tabelas, mapas HTML e gráficos PNG. O relatório
Markdown organiza as principais seções em texto e tabelas, funcionando como base para escrita.
O inventário é um CSV com indicadores padronizados; cada linha é uma métrica consolidada. O
comparador HTML coloca cidades lado a lado, e o CSV comparativo permite usar os dados em outras
análises. Então essa parte não é uma métrica nova isolada, mas a infraestrutura que transforma
as análises em material apresentável e reproduzível."

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

**Fala sugerida**

"Esta parte resume numericamente as curvas de robustez. Os dados vêm das curvas de remoção já
geradas para arestas, vértices e comunidades. Em vez de comparar apenas o ponto final, eu calculo
a área sob a curva, perdas em percentuais padronizados e cruzamentos de limiares. Isso representa
uma forma mais objetiva de comparar degradação da rede. No projeto, ajuda a transformar gráficos
de robustez em indicadores comparáveis entre cidades e estratégias.

No gráfico de comparação de AUC, normalmente o eixo X separa cidades, estratégias ou modalidades
de remoção, e o eixo Y mostra a AUC normalizada. AUC maior significa que a rede preservou melhor
a resposta ao longo da curva. No gráfico de perdas, o eixo X mostra a cidade/estratégia ou uma
fração de remoção padronizada, e o eixo Y mostra a perda de conectividade ou eficiência. O CSV
traz esses valores de forma tabular: modalidade, estratégia, cidade, AUC, perdas em 1%, 5%, 10%
e 15%, além dos limiares de queda. Isso permite comparar as curvas sem depender apenas da
inspeção visual."

**Comando**

```bash
ic robustness-summary campinas_admin jundiai_admin sorocaba_admin valinhos_admin
```

## Fechamento

As principais novidades transformaram o projeto de uma pipeline básica de métricas de grafos em uma plataforma de análise urbana mais completa. Agora o sistema mede não só estrutura global, mas também vulnerabilidade, robustez por diferentes modos de falha, síntese quantitativa das curvas, comunidades, acessibilidade, morfologia urbana, subcentros, barreiras, estabilidade por escala e similaridade entre cidades.
