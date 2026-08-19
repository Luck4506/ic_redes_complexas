## Resumo Para Apresentar ao Professor

> **Nota de auditoria — 18/08/2026:** este arquivo preserva a memória cronológica do trabalho,
> mas algumas formulações antigas eram mais fortes que a evidência. Para a interpretação atual,
> “resiliência” significa apenas **robustez estrutural sob remoção**, os quatro municípios são
> estudos de caso paulistas e a comparabilidade científica permanece `nao_comprovada` até que
> snapshot OSM, hashes, parâmetros e integridade sejam verificados pelo protocolo atual.

O projeto foi revisado com base no plano original da iniciação científica. Foram identificadas lacunas metodológicas e implementadas melhorias para aproximar o repositório do escopo previsto.

### Atualização consolidada — 21 de junho de 2026

**Situação computacional em 21/06/2026:** havia ampla cobertura funcional. A auditoria posterior
identificou bugs de contrato, proveniência insuficiente e outputs misturados; portanto os artefatos
legados precisam ser validados/regenerados antes da análise final. As expansões de vulnerabilidade,
gargalos, rotas, análises espaciais, hierarquia, morfologia, similaridade, subcentros, barreiras e
escala existem, mas várias são proxies exploratórias.

**Situação científica:** ainda em andamento. As próximas entregas são formular perguntas e
hipóteses, interpretar os resultados comparativos, documentar as escolhas metodológicas,
organizar o estado da arte e produzir os textos acadêmicos.

**Melhorias de engenharia auditadas em 18/08/2026:** proveniência estruturada, dicionário de
dados, detecção de saídas desatualizadas e testes de contrato passaram a ser requisitos de
liberação, não detalhes não bloqueantes. Um orquestrador único de toda a pipeline continua como
evolução futura.

As listas antigas de pendências neste arquivo são mantidas como histórico. Quando uma seção
posterior informa que uma pendência foi tratada, vale o estado consolidado acima.

### 1. Robustez estrutural das comunidades

Além da robustez do grafo completo, foram implementadas duas análises:

- **Robustez entre comunidades:** avalia o impacto da remoção das conexões que ligam diferentes comunidades.
- **Robustez interna das comunidades:** avalia individualmente quanto cada comunidade resiste à remoção de suas próprias vias.

Essas análises permitem identificar comunidades frágeis e conexões críticas para a integração da rede.

### 1.1 Robustez estrutural por remoção de vértices

Foi implementada uma nova análise que remove exclusivamente vértices da rede, sem substituir
ou combinar a análise existente por remoção de arestas.

Foram incluídas três estratégias:

- **aleatória:** representa falhas sem seleção intencional;
- **dirigida estática:** remove primeiro os vértices com maior centralidade de intermediação
  calculada na rede original;
- **dirigida adaptativa:** recalcula a centralidade após cada etapa de remoção.

Cada execução gera curvas da maior componente conectada, quantidade de componentes,
eficiência topológica, eficiência ponderada por distância e uma lista dos vértices removidos.
Os vértices removidos são considerados desconectados no denominador das métricas, e as mesmas
fontes amostradas são mantidas em toda a curva para reduzir ruído experimental.

As curvas por vértices e por arestas aparecem separadamente nos dashboards e comparadores.

As duas modalidades foram executadas de forma padronizada nos oito datasets disponíveis:
Campinas, Jundiaí, Sorocaba e Valinhos, tanto nos recortes antigos quanto nos recortes
administrativos. Foram usados 15 pontos até 15% de remoção, `k=80`, 20 fontes para eficiência
e semente 42. Não foi criada nenhuma estratégia que misture remoção de vértices e arestas.

### 2. Novas centralidades

Foram adicionadas:

- centralidade de proximidade;
- centralidade de autovetor;
- rankings completos de grau, intermediação, proximidade e autovetor;
- centralidades calculadas para todos os nós.

Isso permite identificar diferentes formas de importância topológica na rede viária.

### 3. Comparação padronizada entre cidades

Os recortes antigos utilizavam caixas geográficas de tamanhos muito diferentes, tornando a comparação apenas exploratória.

Foram criados novos datasets usando os limites administrativos de:

- Campinas;
- Jundiaí;
- Sorocaba;
- Valinhos.

Também foram adicionadas métricas normalizadas por área, como:

- nós por km²;
- arestas por km²;
- extensão viária por km².

Uma auditoria automática legada verificou apenas condições superficiais. A revisão de
18/08/2026 mostrou que ela não confirma comparabilidade científica; o estado correto é
`nao_comprovada` até que snapshot OSM, geometria do limite, hashes, parâmetros, sementes e
frescor sejam auditados.

### 4. Validação das aproximações

Foi implementado um estudo de sensibilidade que compara métricas aproximadas com cálculos exatos em subgrafos controlados.

Principais resultados:

- betweenness e closeness apresentaram rankings muito estáveis;
- caminho médio apresentou erros geralmente baixos;
- diâmetro foi corretamente estimado nos principais testes;
- clustering aproximado apresentou instabilidade e deve ser utilizado com cautela.

Essa validação fornece evidências quantitativas sobre a confiabilidade das métricas utilizadas.

### 5. Relação entre topologia e características viárias

Foi criada uma análise relacionando a posição topológica das vias com atributos do OpenStreetMap:

- tipo de via;
- superfície;
- mão única;
- velocidade máxima;
- quantidade de faixas.

Os resultados são apresentados como associações descritivas, sem afirmar causalidade.

### 6. Dashboards e relatórios

Os dashboards foram atualizados com:

- guia metodológico de leitura;
- rankings de centralidade;
- resultados da validação das aproximações;
- relações entre topologia e características viárias;
- avisos sobre limitações e comparabilidade.

Também foram atualizados os relatórios consolidados, inventários e a documentação metodológica.

### 7. Auditoria da análise histórica

Foi identificado um problema metodológico importante: comparar Campinas atual com Campinas de
10 anos atrás usando OSM histórico pode refletir principalmente a evolução da cobertura do
OpenStreetMap, não a mudança real da cidade.

Para resolver isso de forma defensável, foi implementado o comando:

```bash
ic historical-audit --reference campinas campinas_2010 ... campinas_2026
```

Ele mede a cobertura histórica usando os identificadores de vias do OSM e classifica cada ano
como:

- `nao_confiavel`;
- `exploratorio`;
- `comparavel_com_cautela`.

Resultado em Campinas:

- 2010 a 2014: não confiável;
- 2015 a 2020: exploratório;
- 2021 a 2026: comparável com cautela.

Também foi criado um núcleo comum de vias presentes no ano histórico e no grafo atual. Esse
núcleo ajuda a comparar apenas o que foi mapeado nos dois períodos, mas não substitui uma
fonte histórica independente.

### Situação Atual

O projeto agora possui uma base computacional mais completa e cientificamente defensável para caracterizar e comparar redes viárias.

Após uma nova leitura do PDF separando software de escrita acadêmica, a parte computacional
pendente foi organizada em `docs/lacunas_computacionais_escopo_ic.md`. A ideia central ficou
definida assim: dado o grafo de uma cidade, o sistema deve gerar tabelas, rankings, curvas,
mapas e dashboards para análise posterior no relatório.

As pendências computacionais identificadas naquele momento eram:

- executar comunidades, resiliência entre comunidades e resiliência interna nos quatro datasets administrativos;
- atualizar dashboards e relatórios desses datasets após essas execuções;
- gerar uma tabela comparativa consolidada em CSV, além do HTML comparativo;
- repetir ataques aleatórios com múltiplas sementes e gerar média, desvio, mínimo e máximo;
- melhorar o manifesto experimental com versões, comando, parâmetros, semente, data e commit;
- criar um mapa próprio de arestas/vias críticas.

Essas pendências foram tratadas no item 8.

As principais etapas acadêmicas ainda pendentes são:

- interpretar e comparar cientificamente os resultados de resiliência por vértices e arestas;
- usar a auditoria histórica antes de interpretar qualquer comparação temporal;
- aprofundar a interpretação científica dos resultados;
- formular hipóteses e identificar padrões recorrentes ou especificidades locais;
- produzir a avaliação quantitativa e qualitativa final;
- preparar relatório acadêmico e artigo científico.

### 8. Fechamento das lacunas computacionais do escopo original

Depois de separar o que é software do que é escrita acadêmica, as lacunas computacionais
identificadas foram fechadas.

Foram executadas as análises de comunidades nos quatro datasets administrativos avaliados; a
comparabilidade científica atual permanece não comprovada:

- Campinas administrativa;
- Jundiaí administrativa;
- Sorocaba administrativa;
- Valinhos administrativa.

Para cada cidade foram gerados:

- detecção de comunidades;
- mapa interativo de comunidades;
- resiliência entre comunidades nas estratégias aleatória, dirigida e adaptativa;
- resiliência interna de cada comunidade nas estratégias aleatória, dirigida e adaptativa;
- imagens estáticas do grafo, do grafo com nós e do grafo por comunidades;
- dashboard e relatório atualizados.

Quantidade de comunidades analisadas na resiliência interna dirigida:

- Campinas: 103 comunidades;
- Jundiaí: 73 comunidades;
- Sorocaba: 71 comunidades;
- Valinhos: 43 comunidades.

Também foi implementada a tabela comparativa consolidada em CSV. Antes o comparador gerava
principalmente HTML; agora também gera:

```bash
outputs/comparisons/compare_admin_cities.csv
```

Esse CSV organiza as métricas em formato longo, com dataset, grupo, indicador, rótulo, valor,
unidade e descrição. Isso facilita usar os dados no relatório, em planilhas ou em análises
posteriores.

Foi criado o comando:

```bash
ic random-resilience-stats --city <dataset> --mode both --seeds 42 43 44 45 46
```

Ele repete ataques aleatórios por arestas e por vértices com múltiplas sementes e gera média,
desvio-padrão, mínimo e máximo. Isso evita tirar conclusão com base em um único sorteio.

Arquivos principais gerados por cidade:

- `metrics/resilience_random_aggregate.csv`;
- `metrics/node_resilience_random_aggregate.csv`;
- `figures/resilience_random_aggregate.png`;
- `figures/node_resilience_random_aggregate.png`.

Também foi criado um mapa próprio de vias críticas:

```bash
outputs/<dataset>/maps/arestas_criticas.html
```

Esse mapa usa as arestas com maior centralidade de intermediação e mostra ranking, score,
comprimento, nome da via quando disponível e tipo de via OSM. Isso complementa o mapa de
pontos críticos, que mostra os nós.

Por fim, os relatórios passaram a gerar um manifesto experimental em JSON:

```bash
outputs/<dataset>/EXPERIMENT_MANIFEST_<dataset>.json
```

Esse manifesto registra ambiente, versões das bibliotecas, data/hora, estado do Git, entradas
e artefatos gerados. Isso melhora a reprodutibilidade da base computacional.

Com essas mudanças, a parte computacional do escopo original pode ser considerada concluída:
o sistema recebe o grafo de uma cidade e gera dados estruturais, centralidades, comunidades,
resiliência por arestas, vértices e comunidades, estatísticas aleatórias agregadas, mapas,
dashboards, relatórios, manifestos e comparação consolidada entre cidades.

### 9. Auditoria de sanidade antes de ampliar o escopo

Antes de iniciar um novo escopo, foi feita uma checagem geral da base computacional já
implementada.

Foram validados:

- testes unitários;
- compilação dos módulos Python;
- checagem de whitespace com `git diff --check`;
- existência dos principais CSVs, mapas, dashboards, relatórios e manifestos dos quatro
  datasets administrativos;
- presença dos artefatos de comparação HTML e CSV;
- leitura dos manifestos experimentais JSON;
- presença das métricas agregadas de resiliência aleatória;
- exposição do novo comando `random-resilience-stats` no CLI.

Durante essa auditoria, foi encontrada uma lacuna pequena: as rotas aleatórias ainda não
tinham sido geradas para os datasets administrativos, então os dashboards e relatórios
indicavam ausência da etapa `paths`. Isso foi corrigido executando a geração de rotas para:

- `campinas_admin`;
- `jundiai_admin`;
- `sorocaba_admin`;
- `valinhos_admin`.

Depois disso, inventários, dashboards, relatórios e comparação foram regenerados. A busca por
avisos de arquivo ausente nos dashboards, relatórios e inventários não retornou problemas.

Registro da validação daquela etapa — **não representa o gate atual**:

- 14 testes passaram;
- compilação concluída sem erro;
- `git diff --check` sem problemas;
- naquela verificação, os artefatos esperados existiam e não estavam vazios.

Existência e tamanho não provam integridade, frescor ou comparabilidade. A auditoria completa de
18/08/2026 bloqueia os quatro datasets legados; consulte
`docs/registro_aprimoramentos_2026-08-18.md` para o estado vigente.

### 10. Expansão: Índice Composto de Vulnerabilidade Viária

Como primeira expansão após o fechamento do escopo computacional original, foi implementado um
índice composto de vulnerabilidade para nós e arestas da rede viária.

Motivação:

- o projeto já calculava várias métricas separadas de criticidade;
- para a análise posterior, é útil ter um ranking único que combine diferentes sinais;
- isso é coerente com os objetivos confirmados no PDF de centralidade, robustez estrutural e
  identificação de pontos críticos; a matriz literal está em
  `docs/matriz_aderencia_plano_trabalho.md`.

Foi criado o comando:

```bash
ic vulnerability-index --city <dataset> --top-k 100
```

O índice de nós combina:

- centralidade de intermediação;
- centralidade de grau;
- centralidade de proximidade;
- centralidade de autovetor;
- presença nos ataques dirigidos por remoção de vértices;
- presença nos ataques adaptativos por remoção de vértices;
- identificação de pontos de articulação.

O índice de arestas combina:

- edge betweenness;
- identificação de pontes estruturais;
- importância do tipo de via OSM;
- comprimento da aresta;
- indicação se a aresta conecta comunidades diferentes.

Arquivos gerados por dataset:

- `metrics/vulnerability_nodes.csv`;
- `metrics/vulnerability_edges.csv`;
- `maps/vulnerability_nodes.html`;
- `maps/vulnerability_edges.html`;
- `logs/vulnerability_index_report.txt`.

Os dashboards passaram a exibir:

- tabela de nós mais vulneráveis;
- tabela de arestas mais vulneráveis;
- mapa de vulnerabilidade dos nós;
- mapa de vulnerabilidade das arestas.

O relatório consolidado também passou a incluir uma seção específica para o índice de
vulnerabilidade. O comparador entre cidades passou a incluir métricas como:

- maior vulnerabilidade de nó;
- quantidade de nós de articulação;
- maior vulnerabilidade de aresta;
- quantidade de pontes estruturais.

A expansão foi executada nos quatro datasets administrativos:

- `campinas_admin`;
- `jundiai_admin`;
- `sorocaba_admin`;
- `valinhos_admin`.

Depois da execução, inventários, dashboards, relatórios e comparação foram regenerados.

### 11. Expansão: Pontes, Articulações e Gargalos Estruturais

Foi implementada uma análise específica para identificar elementos que fragmentam diretamente
a rede viária.

Motivação:

- o índice de vulnerabilidade combina vários sinais, mas nem sempre mostra isoladamente o
  efeito mecânico de fragmentação;
- pontes estruturais e nós de articulação têm uma interpretação topológica direta;
- essa análise ajuda a responder quais trechos ou interseções separam partes da cidade quando
  são removidos da rede.

Foi criado o comando:

```bash
ic structural-bottlenecks --city <dataset> --top-k 100
```

A análise gera três conjuntos de dados:

- nós de articulação;
- pontes estruturais;
- ranking combinado de gargalos estruturais.

Para cada nó de articulação, o sistema mede:

- quantos componentes aparecem após remover o nó;
- tamanho da maior componente restante;
- tamanho da segunda maior componente;
- quantos nós ficam fora da maior componente;
- fração de nós destacados;
- comunidade associada;
- métricas de centralidade disponíveis.

Para cada ponte estrutural, o sistema mede:

- quantos componentes aparecem após remover a aresta;
- quantos nós ficam fora da maior componente;
- fração de nós destacados;
- tipo de via OSM;
- comprimento;
- comunidades conectadas pela aresta;
- se a aresta cruza fronteira entre comunidades.

Arquivos gerados por dataset:

- `metrics/structural_articulations.csv`;
- `metrics/structural_bridges.csv`;
- `metrics/structural_bottlenecks.csv`;
- `maps/structural_articulations.html`;
- `maps/structural_bridges.html`;
- `maps/structural_bottlenecks.html`;
- `logs/structural_bottlenecks_report.txt`.

Os dashboards passaram a exibir:

- tabela de nós de articulação;
- tabela de pontes estruturais;
- tabela do ranking combinado de gargalos;
- mapa de articulações;
- mapa de pontes;
- mapa combinado de gargalos.

O relatório consolidado passou a ter uma seção própria para pontes, articulações e gargalos
estruturais. O comparador entre cidades também passou a incluir indicadores como quantidade de
articulações, quantidade de pontes e maior impacto de fragmentação observado.

### 12. Expansão: Perfil de Redundância de Rotas

Foi implementada uma análise para medir se a rede viária oferece alternativas razoáveis de
deslocamento quando a melhor rota entre dois pontos é bloqueada.

Motivação:

- duas cidades podem ter caminho médio parecido, mas níveis muito diferentes de redundância;
- uma malha com mais alternativas tende a ser funcionalmente mais robusta;
- essa análise complementa as métricas topológicas, porque trabalha com pares origem-destino
  e rotas por distância.

Foi criado o comando:

```bash
ic route-redundancy --city <dataset> --pairs 100 --threshold 1.50 --seed 42 --map-limit 20
```

Como a análise funciona:

1. o sistema amostra pares origem-destino alcançáveis no grafo dirigido;
2. calcula a menor rota por distância;
3. bloqueia todos os segmentos direcionados dessa melhor rota;
4. tenta calcular uma nova rota entre a mesma origem e o mesmo destino;
5. classifica a alternativa como razoável quando ela existe e não ultrapassa o limiar
   configurado em relação à melhor rota original.

Com `--threshold 1.50`, por exemplo, uma rota alternativa é considerada razoável se tiver no
máximo 150% da distância da rota original.

Arquivos gerados por dataset:

- `metrics/route_redundancy_pairs.csv`;
- `metrics/route_redundancy_summary.csv`;
- `maps/route_redundancy.html`;
- `logs/route_redundancy_report.txt`.

O CSV detalhado por par registra:

- origem e destino;
- distância da melhor rota;
- quantidade de segmentos bloqueados;
- existência ou não de alternativa;
- distância da alternativa;
- razão entre alternativa e rota original;
- acréscimo de distância;
- classificação da alternativa como razoável ou não.

O resumo agregado registra:

- quantidade de pares analisados;
- taxa de pares com alguma alternativa;
- taxa de pares com alternativa razoável;
- taxa de pares que ficam sem rota após bloqueio;
- razão média entre rota alternativa e melhor rota;
- desvio médio de distância quando há alternativa.

Os dashboards passaram a exibir tabela de resumo, tabela dos pares origem-destino e mapa das
rotas avaliadas. O relatório consolidado passou a ter uma seção específica para o perfil de
redundância de rotas. O comparador entre cidades passou a incluir os indicadores agregados de
redundância.

### 13. Expansão: Análise Multiescala por Células Espaciais

Foi implementada uma análise para dividir a cidade em regiões menores e calcular métricas
locais da rede viária.

Motivação:

- métricas do grafo inteiro podem esconder desigualdades internas;
- uma cidade pode ter boa conectividade média, mas possuir regiões locais frágeis;
- a análise espacial permite identificar onde há maior conectividade, maior vulnerabilidade
  ou menor redundância.

Como não havia no repositório uma base oficial de bairros, foi adotada uma grade espacial
regular. Essa escolha mantém a análise reprodutível e permite aplicar o mesmo critério para
todas as cidades.

Foi criado o comando:

```bash
ic spatial-multiscale --city <dataset> --cell-size-m 1000
```

Com `--cell-size-m 1000`, cada célula representa aproximadamente uma região de 1 km por 1 km.

Para cada célula, o sistema calcula:

- quantidade de nós;
- quantidade de arestas internas;
- extensão viária interna;
- grau médio local;
- densidade local;
- quantidade de componentes;
- fração da maior componente local;
- nós de articulação dentro da célula;
- pontes estruturais dentro da célula;
- vulnerabilidade média e máxima dos nós da célula;
- quantidade de pares origem-destino amostrados que começam na célula;
- taxa local de alternativas razoáveis;
- taxa local de desconexão após bloqueio da melhor rota.

Arquivos gerados por dataset:

- `metrics/spatial_multiscale_cells.csv`;
- `metrics/spatial_multiscale_summary.csv`;
- `maps/spatial_multiscale_vulnerability.html`;
- `maps/spatial_multiscale_connectivity.html`;
- `maps/spatial_multiscale_redundancy.html`;
- `logs/spatial_multiscale_report.txt`.

Os mapas gerados mostram:

- regiões com maior vulnerabilidade local;
- regiões com maior conectividade média;
- regiões com maior taxa local de desconexão, ou seja, menor redundância observada.

Os dashboards passaram a exibir tabela de resumo, tabela das células e os três mapas
temáticos. O relatório consolidado passou a ter uma seção própria de análise multiescala. O
comparador entre cidades passou a incluir indicadores agregados de desigualdade espacial, como
número de células povoadas, média de nós por célula, vulnerabilidade média local e redundância
local.

### 14. Expansão: Robustez Espacial por Bloqueios Regionais

Foi implementada uma análise para simular falhas espacialmente concentradas na rede viária.

Motivação:

- eventos reais raramente removem vias espalhadas aleatoriamente;
- enchentes, obras, acidentes e bloqueios costumam afetar uma região específica;
- a análise cria cenários regionais estilizados; sem hazard, probabilidade ou observações
  externas, eles não devem ser chamados de mais realistas.

Foi criado o comando:

```bash
ic spatial-robustness --city <dataset> --cell-size-m 1000 --mode incident --eff-samples 10 --max-eff-cells 100 --seed 42
```

Como a análise funciona:

1. a cidade é dividida na mesma grade espacial usada na análise multiescala;
2. para cada célula, o sistema identifica as vias associadas à região;
3. essas vias são removidas do grafo;
4. o impacto é medido no grafo inteiro;
5. as células são ranqueadas pelo dano causado.

O modo padrão `incident` remove arestas que tocam nós da célula. Isso representa um bloqueio
regional estilizado, porque uma ocorrência local pode afetar vias internas e acessos à
região. Também existe o modo `internal`, que remove apenas arestas totalmente internas à
célula.

Para cada célula, o sistema mede:

- quantidade de nós da célula;
- quantidade de arestas removidas;
- fração de arestas removidas;
- tamanho da maior componente após o bloqueio;
- queda da maior componente;
- número de componentes após o bloqueio;
- aumento no número de componentes;
- eficiência topológica retida;
- eficiência ponderada por distância retida.

Para manter a execução viável em cidades grandes, a queda da maior componente e a
fragmentação são calculadas para todas as células. A eficiência, que é mais custosa, é
calculada nas células de maior impacto preliminar, controladas por `--max-eff-cells`.

Arquivos gerados por dataset:

- `metrics/spatial_robustness_cells.csv`;
- `metrics/spatial_robustness_summary.csv`;
- `maps/spatial_robustness_lcc_drop.html`;
- `maps/spatial_robustness_efficiency_drop.html`;
- `maps/spatial_robustness_fragmentation.html`;
- `logs/spatial_robustness_report.txt`.

Os mapas gerados mostram:

- células cujo bloqueio mais reduz a maior componente;
- células cujo bloqueio mais reduz a eficiência topológica;
- células cujo bloqueio mais aumenta a fragmentação.

Os dashboards passaram a exibir tabela de resumo, tabela dos bloqueios por célula e os três
mapas de robustez espacial. O relatório consolidado passou a ter uma seção própria para
robustez espacial. O comparador entre cidades passou a incluir indicadores como queda média da
maior componente, maior queda observada, eficiência média retida e maior aumento de
componentes após bloqueios regionais.

### 15. Expansão: Análise de Hierarquia Viária

Foi implementada uma análise para medir como diferentes classes de vias contribuem para a
estrutura da rede.

Motivação:

- o OSM já classifica as vias pelo atributo `highway`;
- vias arteriais podem concentrar conectividade e fluxo potencial;
- uma cidade pode depender muito de poucas classes, como `motorway`, `primary` ou
  `secondary`;
- a análise ajuda a discutir se a malha distribui bem a conectividade ou se depende demais de
  eixos específicos.

Foi criado o comando:

```bash
ic road-hierarchy --city <dataset> --eff-samples 20 --seed 42 --map-edges-per-class 1200
```

A análise agrupa as vias por classe `highway`. Classes do tipo link são agregadas à classe
principal. Por exemplo:

- `primary_link` entra como `primary`;
- `secondary_link` entra como `secondary`;
- `motorway_link` entra como `motorway`.

Para cada classe viária, o sistema calcula:

- quantidade de arestas;
- fração de arestas da rede;
- extensão total em metros e quilômetros;
- fração da extensão total;
- quantidade de nós tocados pela classe;
- pontes estruturais dentro da classe;
- centralidade de arestas observada a partir do ranking `top_edges.csv`;
- vulnerabilidade média e máxima das arestas da classe;
- queda da maior componente ao remover toda a classe;
- aumento no número de componentes;
- eficiência topológica retida;
- eficiência ponderada por distância retida.

Arquivos gerados por dataset:

- `metrics/road_hierarchy_by_class.csv`;
- `metrics/road_hierarchy_summary.csv`;
- `maps/road_hierarchy_impact.html`;
- `logs/road_hierarchy_report.txt`.

O resumo agregado registra:

- fração de arestas arteriais;
- fração de extensão arterial;
- fração de arestas locais;
- classe cuja remoção mais reduz a maior componente;
- classe cuja remoção mais reduz a eficiência;
- classe com maior centralidade observada entre as arestas críticas.

Os dashboards passaram a exibir tabela de resumo, tabela por classe `highway` e mapa de
hierarquia viária. O relatório consolidado passou a ter uma seção própria para hierarquia
viária. O comparador entre cidades passou a incluir indicadores como dependência de classes
arteriais, extensão arterial, dependência de LCC por classe e eficiência retida após remoção
da classe mais crítica.

### 16. Expansão: Comparação Planejamento Urbano x Estrutura da Rede

Foi implementado um perfil heurístico de orientação e conectividade a partir da estrutura
local do grafo viário. Ele não identifica regimes de planejamento sem validação externa.

Motivação:

- conectar teoria de grafos com morfologia urbana;
- identificar regiões mais gradeadas, radiais/lineares, orgânicas, fragmentadas ou mistas;
- revelar diferenças internas da cidade que métricas globais não mostram;
- gerar hipóteses sobre diferenças locais da malha viária, sem alegar universalidade.

Foi criado o comando:

```bash
ic urban-morphology --city <dataset> --cell-size-m 1000
```

A análise divide a cidade em células espaciais e, para cada célula, calcula:

- quantidade de nós e arestas internas;
- extensão total da malha na célula;
- comprimento médio dos segmentos viários;
- grau médio local;
- densidade local;
- número de componentes;
- fração da maior componente;
- entropia angular das vias;
- dominância da orientação principal;
- participação de eixos ortogonais dominantes;
- classe morfológica atribuída;
- justificativa textual da classificação.

As classes usadas foram:

- `gradeada`: orientações ortogonais dominantes e boa conectividade local;
- `radial_linear`: forte concentração em poucos eixos de orientação;
- `organica`: alta diversidade angular, sugerindo traçado menos regular;
- `fragmentada`: baixa conectividade local ou maior componente pequena;
- `mista`: combinação de sinais sem predomínio claro;
- `insuficiente`: poucos elementos viários para inferir padrão.

Arquivos gerados por dataset:

- `metrics/urban_morphology_cells.csv`;
- `metrics/urban_morphology_summary.csv`;
- `maps/urban_morphology_classes.html`;
- `maps/urban_morphology_orientation_entropy.html`;
- `maps/urban_morphology_connectivity.html`;
- `logs/urban_morphology_report.txt`.

Os dashboards passaram a exibir tabela de resumo, tabela por célula e três mapas
morfológicos: classes urbanas, entropia angular e conectividade local. O relatório
consolidado ganhou uma seção própria chamada **Planejamento urbano x estrutura da rede**. O
comparador entre cidades passou a incluir indicadores como fração gradeada, fração
radial/linear, fração orgânica, fração fragmentada, entropia angular média, ortogonalidade
média e comprimento médio dos segmentos.

Essa análise é importante porque permite transformar o grafo viário em evidência sobre forma
urbana. Em vez de dizer apenas que uma cidade tem certo grau médio ou certa centralidade, o
sistema passa a indicar se diferentes partes da cidade se aproximam de uma malha planejada em
grade, de eixos radiais/lineares, de traçados orgânicos ou de áreas fragmentadas.

### 17. Expansão: Eficiência de Rotas em Múltiplos Pares Origem-Destino

Foi implementada uma análise estatística de rotas para substituir a leitura baseada em apenas
uma rota pontual.

Motivação:

- a rota única ajuda a demonstrar o funcionamento do sistema, mas não representa a cidade;
- centenas ou milhares de pares origem-destino uniformemente amostrados entre nós estimam a
  distribuição induzida por esse desenho amostral, não a distribuição real de acessibilidade;
- a comparação entre cidades fica mais robusta quando usa médias, medianas, percentis e
  taxas, não apenas um exemplo;
- a análise conversa diretamente com eficiência, acessibilidade e estrutura da rede viária.

Foi criado o comando:

```bash
ic od-efficiency --city <dataset> --pairs 1000 --seed 42 --map-limit 80
```

Para cada par origem-destino amostrado, o sistema calcula:

- origem e destino;
- distância da menor rota por `length`;
- distância direta geográfica entre origem e destino;
- desvio absoluto em metros;
- `circuity_ratio`, isto é, distância da rota dividida pela distância direta;
- `route_efficiency`, isto é, distância direta dividida pela distância da rota;
- quantidade de hops ou segmentos da rota;
- comprimento médio dos segmentos da rota;
- tempo aproximado assumindo 30 km/h;
- velocidade efetiva aproximada em linha reta;
- coordenadas de origem e destino.

O resumo estatístico registra:

- quantidade de pares solicitados e amostrados;
- média, mediana e percentil 90 da distância das rotas;
- média e mediana de hops;
- média, mediana e percentil 90 do `circuity_ratio`;
- média e mediana da eficiência de rota;
- acessibilidade até 2 km, 5 km e 10 km;
- taxa de baixo desvio, com `circuity <= 1.25`;
- taxa de alto desvio, com `circuity > 1.75`.

Arquivos gerados por dataset:

- `metrics/od_efficiency_pairs.csv`;
- `metrics/od_efficiency_summary.csv`;
- `maps/od_efficiency_routes.html`;
- `logs/od_efficiency_report.txt`.

Os dashboards passaram a exibir o resumo estatístico, a tabela dos pares com maior desvio e o
mapa das rotas mais desviadas. O relatório consolidado ganhou a seção **Eficiência de rotas
em múltiplos pares OD**. O comparador entre cidades passou a incluir distância média OD,
distância P90, hops médios, circuity média, circuity P90, eficiência média, acessibilidade até
5 km e 10 km e taxa de alto desvio.

Essa análise é importante porque transforma acessibilidade em uma medida estatística. Assim,
em vez de depender de uma rota escolhida manualmente, o projeto passa a descrever como a rede
se comporta em muitos deslocamentos possíveis.

### 18. Expansão: Similaridade Entre Cidades

Foi implementada uma análise exploratória para transformar um conjunto teórico reduzido de
métricas de cada cidade em vetores numéricos.

Motivação:

- gerar hipóteses sobre recorrências e especificidades locais;
- explorar quais cidades parecem próximas sob escolhas explícitas de métricas e escala;
- reduzir dezenas de métricas a uma leitura comparativa mais sintética;
- criar uma base quantitativa para agrupamento, PCA e interpretação multivariada.

Foi criado o comando:

```bash
ic city-similarity <dataset_1> <dataset_2> <dataset_3> --output-dir outputs/comparisons \
  --min-coverage 1.0 --allow-small-sample-exploration
```

A análise faz o seguinte:

- lê o `graph_inventory_summary.csv` de cada dataset;
- seleciona métricas numéricas da lista usada no comparador entre cidades;
- remove métricas sem variação entre as cidades;
- preenche ausências com a média da própria métrica;
- padroniza cada métrica por z-score;
- calcula distância euclidiana entre cidades;
- calcula similaridade cosseno;
- calcula PCA por decomposição SVD;
- calcula agrupamento hierárquico por ligação média;
- identifica, para cada cidade, a cidade mais parecida.

Arquivos gerados:

- `outputs/comparisons/city_similarity_vectors_<datasets>.csv`;
- `outputs/comparisons/city_similarity_distances_<datasets>.csv`;
- `outputs/comparisons/city_similarity_cosine_<datasets>.csv`;
- `outputs/comparisons/city_similarity_pca_<datasets>.csv`;
- `outputs/comparisons/city_similarity_clusters_<datasets>.csv`;
- `outputs/comparisons/city_similarity_nearest_<datasets>.csv`;
- `outputs/comparisons/city_similarity_<datasets>.html`;
- `outputs/comparisons/city_similarity_distance_heatmap_<datasets>.png`;
- `outputs/comparisons/city_similarity_cosine_heatmap_<datasets>.png`;
- `outputs/comparisons/city_similarity_pca_<datasets>.png`;
- `outputs/comparisons/city_similarity_dendrogram_<datasets>.png`;
- `outputs/comparisons/city_similarity_report_<datasets>.txt`.

O HTML gerado reúne:

- metodologia resumida;
- matriz de distância;
- matriz de similaridade cosseno;
- gráfico PCA;
- dendrograma do clustering;
- tabela da cidade mais parecida para cada dataset;
- coordenadas PCA.

Essa análise é uma visualização multivariada exploratória. Em amostra suficiente, pode ajudar a
comparar perfis sob escolhas explícitas de métricas e escala. Com poucos casos, PCA, clustering e
“cidade mais próxima” são instáveis e não estabelecem uma proximidade estrutural geral; por isso,
o comando exige oito datasets por padrão e uma liberação explícita abaixo desse limite.

### 19. Expansão: Células Candidatas de Alta Centralidade Topológica

Foi implementada uma análise exploratória para medir se a importância topológica se concentra em
uma única célula ou se fica distribuída entre várias células candidatas.

Motivação:

- duas cidades podem ter métricas globais parecidas, mas estruturas internas diferentes;
- redes podem concentrar ou dispersar centralidade entre regiões;
- a análise gera hipóteses para estudos de morfologia e padrões locais da rede;
- sem empregos, população, atividades ou fluxos, ela não identifica centros urbanos nem
  comprova policentricidade.

Foi criado o comando:

```bash
ic subcenters --city <dataset> --cell-size-m 1000 --percentile 0.90 --min-nodes 20
```

A análise divide a cidade em células espaciais e calcula, para cada célula:

- quantidade de nós;
- quantidade de arestas internas;
- extensão viária interna;
- densidade local;
- grau médio local;
- soma da centralidade de intermediação dos nós;
- média e máximo de betweenness;
- média de centralidade de grau;
- média de closeness aproximada;
- média de autovetor;
- quantidade de comunidades tocadas;
- comunidade dominante;
- participação da comunidade dominante;
- score de candidatura topológica;
- ranking regional de centralidade;
- indicação se a célula foi selecionada como candidata.

O score de candidatura combina:

- centralidade acumulada na região;
- presença de nós muito centrais;
- proximidade topológica;
- autovetor;
- densidade;
- grau médio local;
- tamanho da região em nós;
- diversidade de comunidades tocadas.

As células elegíveis com score acima do percentil configurado são selecionadas como candidatas
topológicas. Com `--percentile 0.90`, o sistema seleciona aproximadamente o topo de 10% das
regiões elegíveis, sem validá-las como subcentros urbanos.

O resumo agregado registra:

- quantidade de células candidatas;
- fração de células povoadas selecionadas;
- índice exploratório de dispersão;
- índice exploratório de dominância;
- entropia dos scores das candidatas;
- participação da principal candidata;
- célula candidata principal;
- maior score de candidatura.

Arquivos gerados por dataset:

- `metrics/subcenters_cells.csv`;
- `metrics/subcenters.csv`;
- `metrics/subcenters_summary.csv`;
- `maps/subcenters.html`;
- `logs/subcenters_report.txt`.

Os dashboards passaram a exibir resumo, ranking de células candidatas, ranking de centralidade
por região e mapa topológico. O relatório e o comparador preservam os nomes técnicos legados dos
campos, mas os apresentam como medidas exploratórias de concentração e dispersão.

Essa análise é importante porque transforma centralidade, comunidades e densidade local em uma
hipótese espacial testável. Qualquer interpretação como centro urbano exige validação externa.

### 20. Expansão: Exposição da Rede a Barreiras Urbanas

Foi implementada uma análise para identificar evidências topológicas de barreiras urbanas
prováveis na rede viária.

Motivação:

- muitas fragilidades urbanas não aparecem apenas por grau médio, caminho médio ou
  centralidade global;
- rios, rodovias, ferrovias, grandes vazios e descontinuidades urbanas tendem a aparecer no
  grafo como poucas conexões entre regiões próximas;
- mesmo sem camadas externas, é possível detectar sinais de baixa permeabilidade espacial;
- isso aproxima a análise de grafos da cidade real e melhora a discussão sobre travessias,
  fragmentação e dependência de poucos pontos de passagem.

Foi criado o comando:

```bash
ic urban-barriers --city <dataset> --cell-size-m 1000 --map-limit 250
```

A análise divide a cidade em células espaciais e calcula:

- quantidade de células vizinhas possíveis;
- quantidade de células vizinhas efetivamente conectadas por vias;
- conexões adjacentes ausentes;
- índice de permeabilidade por célula;
- arestas de travessia incidentes;
- pontes estruturais incidentes;
- nós de articulação por célula;
- travessias longas;
- score médio de barreira nas vizinhanças;
- score composto de baixa permeabilidade;
- ranking de células com menor permeabilidade.

Também foi criado um ranking de conexões entre regiões, com:

- par de células analisado;
- quantidade de arestas de travessia;
- extensão total das travessias;
- maior travessia observada;
- travessias longas;
- pontes estruturais na conexão;
- proporção de fronteira entre comunidades;
- indicação de conexão adjacente ausente;
- score composto de barreira provável.

O resumo agregado registra:

- índice de permeabilidade espacial;
- índice de exposição a barreiras;
- quantidade de células com permeabilidade inferior a 0,50;
- quantidade de conexões adjacentes ausentes;
- quantidade de conexões críticas estruturais;
- célula de menor permeabilidade;
- par de células com maior score de barreira provável.

Arquivos gerados por dataset:

- `metrics/urban_barriers_cells.csv`;
- `metrics/urban_barriers_connections.csv`;
- `metrics/urban_barriers_summary.csv`;
- `maps/urban_barriers_permeability.html`;
- `maps/urban_barriers_connections.html`;
- `logs/urban_barriers_report.txt`.

Os dashboards passaram a exibir as tabelas de resumo, células com baixa permeabilidade e
conexões entre regiões. Também foram adicionados dois mapas: um mapa de baixa permeabilidade
por célula e outro mapa com as conexões/barreiras prováveis entre regiões.

O relatório consolidado passou a ter uma seção própria chamada **Exposição da rede a
barreiras urbanas**. O inventário consolidado e o comparador entre cidades passaram a incluir
os principais indicadores de permeabilidade e exposição a barreiras.

Observação metodológica importante: sem dados externos, o sistema não afirma que uma barreira
é necessariamente rio, ferrovia, rodovia ou vazio urbano. A análise identifica evidências
topológicas de baixa permeabilidade, que depois podem ser interpretadas visualmente ou
cruzadas com dados urbanos externos.

### 21. Expansão: Perfil de Escala da Rede Viária

Foi implementada uma análise para medir a sensibilidade das métricas espaciais ao tamanho da
grade usada na agregação.

Motivação:

- a análise espacial anterior usava uma grade fixa, normalmente de 1 km;
- uma conclusão que aparece apenas em uma escala pode ser artefato da escolha da célula;
- uma conclusão que se mantém em 500 m, 1 km, 2 km e 3 km é metodologicamente mais defensável;
- isso fortalece a comparação entre cidades e a discussão sobre padrões recorrentes e
  especificidades locais.

Foi criado o comando:

```bash
ic network-scale-profile --city <dataset> --scales 500 1000 2000 3000
```

A análise recalcula, para cada escala:

- quantidade de células povoadas;
- quantidade de conexões entre células;
- nós médios por célula;
- coeficiente de variação dos nós por célula;
- grau médio local;
- coeficiente de variação do grau local;
- densidade média local;
- coeficiente de variação da densidade local;
- fração média da maior componente local;
- média de nós de articulação por célula;
- média de pontes internas por célula;
- permeabilidade espacial média;
- quantidade e fração de células com baixa permeabilidade;
- conexões adjacentes ausentes;
- score médio de baixa permeabilidade;
- célula de maior baixa permeabilidade em cada escala.

Depois, o sistema calcula a estabilidade das métricas entre escalas:

- média entre escalas;
- desvio-padrão;
- coeficiente de variação;
- valor mínimo;
- valor máximo;
- score de estabilidade;
- métrica mais estável;
- métrica menos estável;
- índice de robustez multiescalar.

Arquivos gerados por dataset:

- `metrics/network_scale_profile_scales.csv`;
- `metrics/network_scale_profile_cells.csv`;
- `metrics/network_scale_profile_stability.csv`;
- `metrics/network_scale_profile_summary.csv`;
- `figures/network_scale_profile_metrics.png`;
- `figures/network_scale_profile_stability.png`;
- `maps/network_scale_profile_low_permeability.html`;
- `logs/network_scale_profile_report.txt`.

Os dashboards passaram a exibir o resumo multiescalar, as métricas por escala, a estabilidade
das métricas, as células por escala, dois gráficos e um mapa com camadas para comparar baixa
permeabilidade em diferentes resoluções.

O relatório consolidado passou a ter uma seção própria chamada **Perfil de escala da rede
viária**. O inventário consolidado, o comparador entre cidades e a análise de similaridade
passaram a incluir o índice de robustez multiescalar e os principais indicadores de
estabilidade.

Essa análise é importante porque aumenta a rigorosidade metodológica: ela permite dizer se uma
interpretação espacial é robusta em diferentes escalas ou se depende demais da escolha de uma
grade específica.

### 22. Documento de apoio para apresentação ao professor

Foi criado o arquivo `apresentação reunião.md`.

O objetivo desse arquivo é servir como roteiro de reunião. Ele organiza tudo o que foi
implementado no projeto em formato de notas de apresentação, com:

- o que cada análise mede;
- quais arquivos mostrar ao professor;
- preferência por mapas, gráficos e dashboards quando disponíveis;
- CSVs correspondentes quando a saída principal é tabular;
- explicação técnica de cada dado;
- importância de cada análise dentro do escopo da IC;
- comandos necessários para reproduzir os artefatos.
- caixa de controle para marcar o que já foi mostrado ao professor.

O documento cobre desde a base do grafo, métricas estruturais, centralidades, comunidades,
resiliência, validação, vulnerabilidade, gargalos, redundância de rotas, análise espacial,
hierarquia viária, morfologia urbana, eficiência OD, similaridade entre cidades, subcentros,
barreiras urbanas e perfil de escala, até auditoria histórica e relatório consolidado.
Também inclui a rota mínima entre origem e destino e a exportação para Kepler.gl.

Esse arquivo foi pensado para ser usado diretamente na conversa com o professor: a cada tema,
há um artefato indicado para abrir e uma explicação pronta do que o dado significa.

### 23. Síntese quantitativa das curvas de robustez

Com base na revisão bibliográfica, foi implementada a primeira etapa de fortalecimento científico
dos experimentos de robustez. Antes, as estratégias eram comparadas principalmente pelas curvas e
pelo último ponto. Agora o sistema resume toda a trajetória de degradação em um intervalo comum.

Foi criado o comando:

```bash
ic robustness-summary campinas_admin jundiai_admin sorocaba_admin valinhos_admin
```

O comando processa separadamente:

- remoção de arestas do grafo viário;
- remoção de vértices;
- remoção de conexões entre comunidades.

Para cada modalidade, estratégia e resposta, calcula:

- área sob a curva normalizada (AUC);
- valor e perda em 1%, 5%, 10% e 15% de remoção;
- primeira fração que reduz a resposta abaixo de 90%, 75% e 50%;
- média, desvio-padrão, mínimo e máximo da AUC quando existem repetições aleatórias;
- maior fração de remoção realmente comum entre todas as cidades e estratégias comparadas.

As respostas sintetizadas são:

- fração da maior componente conectada;
- eficiência topológica retida;
- eficiência ponderada por distância retida;
- no grafo de comunidades, também a maior componente em número de comunidades e ponderada pelos
  nós urbanos representados.

Arquivos gerados por dataset:

- `metrics/robustness_summary.csv`;
- `figures/robustness_summary_auc.png`;
- `figures/robustness_summary_losses.png`;
- `logs/robustness_summary_report.txt`.

Arquivos comparativos:

- `outputs/comparisons/robustness_comparison.csv`;
- `outputs/comparisons/robustness_comparison.html`;
- `outputs/comparisons/robustness_comparison.png`.
- `outputs/comparisons/robustness_losses.png`.

A AUC é integrada pelo método dos trapézios com interpolação linear. Uma AUC maior indica que a
rede reteve, em média, uma parcela maior da resposta durante o intervalo. O sistema não mistura as
modalidades: robustez a remoção de nós, arestas e conexões entre comunidades continua sendo
interpretada separadamente.

A síntese foi integrada ao inventário, ao dashboard, ao relatório consolidado, ao README, à lista
de comandos e aos dois documentos de apresentação ao professor. Essa etapa permite comparar as
cidades e estratégias por toda a curva, e não apenas por inspeção visual ou por um ponto final.
