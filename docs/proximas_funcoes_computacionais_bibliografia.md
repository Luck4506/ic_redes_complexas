# Próximas funções computacionais orientadas pela revisão bibliográfica

Data da análise: 21 de junho de 2026.

## 1. Diagnóstico

O escopo computacional original está coberto. A revisão bibliográfica não indica que seja
necessário simplesmente adicionar mais métricas globais. A principal lacuna é transformar os
artefatos já produzidos em **experimentos científicos comparáveis**, com síntese quantitativa,
incerteza, sensibilidade e testes de estabilidade.

As recomendações abaixo estão divididas em:

- **P0 - necessária antes do texto científico final:** reduz fragilidades metodológicas centrais;
- **P1 - expansão de alto valor:** amplia o projeto sem mudar seu tema;
- **P2 - pesquisa futura:** relevante, mas aumenta bastante o escopo ou depende de novos dados.

## 2. P0 - Funções necessárias antes do texto final

### P0.1 Síntese quantitativa das curvas de robustez

**Status: implementado em 21 de junho de 2026.**

**Problema atual:** existem curvas de remoção de nós, arestas e comunidades, mas falta um resumo
numérico comum. Comparar apenas o último ponto ou olhar os gráficos pode produzir conclusões
diferentes conforme a fração escolhida.

**Comando implementado:** `ic robustness-summary <dataset_1> <dataset_2> ...`.

Funções:

- calcular área sob a curva normalizada (AUC) de:
  - fração da maior componente;
  - eficiência topológica retida;
  - eficiência ponderada retida;
- calcular perda em frações padronizadas, por exemplo 1%, 5%, 10% e 15%;
- calcular limiares de degradação, como a fração removida até LCC ou eficiência cair abaixo de
  90%, 75% e 50%, quando o intervalo simulado alcançar o limiar;
- comparar `random`, `targeted` e `targeted_adaptive` na mesma faixa de remoção;
- gerar uma tabela única por cidade e uma tabela comparativa entre cidades;
- separar rigorosamente remoção de nós, arestas e arestas entre comunidades.

Saídas sugeridas:

- `metrics/robustness_summary.csv`;
- `outputs/comparisons/robustness_comparison.csv`;
- `outputs/comparisons/robustness_comparison.html`;
- gráfico de AUC e perdas por estratégia com incerteza.

**Referências que motivam:** Albert et al. (2000), Latora e Marchiori (2001), Iyer et al. (2013),
Duan e Lu (2013) e Tian et al. (2019).

**Prioridade:** fazer primeiro. É a função que mais ajuda a responder às hipóteses do trabalho.

Implementação realizada em `src/ic/robustness_summary.py`, integrada ao CLI, inventário,
dashboard, relatório consolidado e apresentações. A comparação conjunta das quatro cidades usa a
maior fração realmente disponível em todas as curvas de cada modalidade. A integração é
trapezoidal com interpolação linear. Para ataques aleatórios por nós e arestas, as repetições já
existentes são usadas para calcular média, desvio, mínimo e máximo da AUC.

### P0.2 Incerteza estatística dos ataques aleatórios

**Estado após implementação:** `random-resilience-stats` usa 30 repetições por padrão, sementes
de ataque e avaliação separadas e intervalos bootstrap. Os artefatos legados com cinco
sementes continuam inadequados e precisam ser regenerados.

**Expandir o comando existente:**

- executar pelo menos 30 repetições por cidade e modalidade;
- permitir informar `--repetitions 30` e gerar sementes deterministicamente a partir de uma
  semente-mestra;
- calcular média, desvio-padrão, erro-padrão, mediana, quantis e intervalo de confiança de 95%;
- calcular intervalo de confiança também para AUC, não apenas ponto a ponto;
- registrar todas as sementes e parâmetros no manifesto;
- usar _bootstrap_ sobre repetições quando a distribuição não justificar aproximação normal;
- apresentar o tamanho do efeito entre ataque aleatório e dirigido, além de valores brutos.

Saídas sugeridas:

- ampliar `resilience_random_aggregate.csv` e `node_resilience_random_aggregate.csv`;
- `robustness_effect_sizes.csv`;
- curvas com faixas de confiança.

**Observação:** o ataque dirigido é determinístico apenas quando algoritmo, amostra e semente são
fixos. Como a intermediação é aproximada, também deve ser repetido quando sua amostragem variar.

**Prioridade:** fazer junto com P0.1.

### P0.3 Auditoria unificada de sensibilidade e convergência

**Problema atual:** há validação de aproximações e perfil de escala, mas não há uma função que
responda se os rankings e as conclusões permanecem estáveis quando os parâmetros experimentais
mudam.

**Implementar:** comando sugerido `ic sensitivity-audit`.

Parâmetros a variar:

- `k_edge` e `k_node` da intermediação aproximada;
- quantidade de fontes da eficiência;
- quantidade de pares OD e de redundância de rotas;
- número de repetições aleatórias;
- tamanho das células espaciais;
- fração máxima removida e número de pontos das curvas;
- pesos do índice composto de vulnerabilidade.

Indicadores de estabilidade:

- correlação de Spearman e Kendall entre rankings;
- sobreposição do top 10/top 50;
- erro relativo de métricas escalares;
- coeficiente de variação;
- estabilidade da AUC e do ranking das cidades;
- ponto de convergência da média de circuity, eficiência e redundância.

Saídas sugeridas:

- `metrics/sensitivity_results.csv`;
- `metrics/sensitivity_recommendations.csv`, com o menor parâmetro considerado estável;
- gráficos de convergência e estabilidade;
- relatório que marque resultados como `estavel`, `sensivel` ou `inconclusivo`.

**Referências que motivam:** Boeing (2019, circuity), Boeing (2020, multiescala), Crucitti et al.
(2006) e Iyer et al. (2013).

**Prioridade:** necessária para justificar os parâmetros no método, mas pode ser executada depois
de P0.1 e P0.2.

### P0.4 Estabilidade e resolução das comunidades

**Problema atual:** o projeto aceita `greedy` e `louvain`, mas as execuções principais usam uma
partição greedy. Não há comparação das partições, variação de resolução nem medida de
estabilidade. Os arquivos atuais também podem ser sobrescritos por métodos diferentes.

**Implementar:** comando sugerido `ic community-stability`.

Funções:

- executar greedy e Louvain sem sobrescrever artefatos;
- executar Louvain com várias sementes;
- variar o parâmetro de resolução em uma faixa documentada;
- calcular modularidade, número e distribuição dos tamanhos das comunidades;
- comparar partições com Adjusted Rand Index, Normalized Mutual Information ou Variation of
  Information;
- medir consenso/estabilidade de cada nó;
- repetir robustez intercomunitária nas partições estáveis;
- marcar comunidades pequenas potencialmente afetadas pelo limite de resolução;
- criar mapa de nós com atribuição instável.

Saídas sugeridas:

- `metrics/community_partitions.csv`;
- `metrics/community_stability.csv`;
- `metrics/community_method_comparison.csv`;
- `maps/community_instability.html`.

**Referências que motivam:** Newman (2006) e Duan e Lu (2013).

**Prioridade:** necessária se comunidades e resiliência comunitária forem resultados centrais do
relatório. Caso apareçam apenas como exploração, pode ser movida para P1.

### P0.5 Auditoria de representação do grafo

**Problema atual:** vários módulos usam o grafo simples não dirigido e a maior componente, mas o
grafo original é um `MultiDiGraph` dirigido e não planar. Falta quantificar o que cada transformação
remove e se ela altera conclusões.

**Implementar:** comando sugerido `ic representation-audit`.

Funções:

- comparar grafo bruto, simplificado, dirigido, não dirigido, multigrafo e grafo simples;
- registrar nós/arestas antes e depois de cada transformação;
- medir componentes descartados e sua extensão total;
- medir arestas paralelas colapsadas, pares recíprocos e vias de mão única;
- verificar cruzamentos geométricos que não são interseções topológicas;
- verificar se consolidação de interseções complexas foi aplicada;
- recalcular um conjunto pequeno de indicadores em representações alternativas;
- medir estabilidade dos rankings de nós/arestas críticos;
- produzir um fluxograma exato da representação usada por cada módulo.

Saídas sugeridas:

- `metrics/graph_representation_audit.csv`;
- `metrics/representation_metric_sensitivity.csv`;
- `logs/graph_representation_report.txt`.

**Referências que motivam:** Porta, Crucitti e Latora (2006), Boeing (2017), Boeing (2020,
planarity) e Boeing (2025).

**Prioridade:** necessária para escrever uma metodologia defensável e evitar misturar conclusões
topológicas e funcionais.

## 3. P1 - Expansões computacionais de alto valor

### P1.1 Redundância por caminhos independentes e k melhores rotas

**Problema atual:** `route_redundancy.py` remove todos os segmentos da melhor rota e procura uma
alternativa. É uma medida válida, mas severa: equivale a bloquear a rota inteira e não mede quantos
caminhos estruturalmente independentes existem.

**Expandir:** comando sugerido `ic route-alternatives` ou ampliar `route-redundancy`.

Funções:

- número de caminhos independentes por aresta e por nó entre cada par;
- conectividade local do par via `edge_connectivity`/`node_connectivity` em amostra controlada;
- k menores caminhos simples, com limite de custo e sobreposição máxima;
- razão de desvio de cada alternativa;
- percentual de arestas compartilhadas com a rota principal;
- alternativa após bloquear uma única aresta crítica da rota, além de bloquear a rota toda;
- distribuição e intervalos de confiança por cidade e por célula;
- mapas de pares com baixa redundância.

**Referências que motivam:** Ip e Wang (2011) e Boeing (2019, circuity).

**Valor científico:** aproxima a análise de uma interpretação funcional sem exigir dados de
tráfego. É a expansão mais coerente depois das tarefas P0.

### P1.2 Recuperação da rede e resiliência em sentido amplo

**Problema atual:** os comandos chamados `resilience` medem degradação/robustez, mas não modelam
recuperação. Sem recuperação, o texto deve usar “robustez estrutural”.

**Implementar:** comando sugerido `ic recovery-resilience`.

Cenários de recuperação:

- restauração na ordem inversa do ataque;
- restauração aleatória;
- restauração prioritária pelo ganho marginal de LCC;
- restauração prioritária pelo ganho marginal de eficiência;
- restauração por classe viária ou vulnerabilidade;
- orçamento fixo por etapa.

Respostas:

- curva de recuperação da LCC e das eficiências;
- tempo/passos até recuperar 90%, 95% e 100% do valor inicial;
- área de perda de desempenho durante dano e recuperação;
- comparação entre estratégias de restauração;
- lista de elementos cuja restauração produz maior ganho marginal.

**Valor científico:** permitiria usar “resiliência” de maneira mais completa e propor prioridades
de recuperação. O tempo seria abstrato em passos, a menos que existam dados reais de reparo.

**Cuidado:** deixar explícito que se trata de recuperação estrutural simulada, não de tempo real de
obras ou normalização do tráfego.

### P1.3 Ataques dirigidos por diferentes centralidades

**Problema atual:** os ataques dirigidos usam principalmente intermediação. A literatura mostra que
o critério de remoção pode mudar a conclusão.

**Expandir os comandos de robustez:**

- aceitar `--ranking degree`, `betweenness`, `closeness`, `eigenvector`, `vulnerability` e
  `impact_oracle`;
- separar ranking estático e adaptativo;
- comparar poder destrutivo por AUC;
- medir correlação entre rankings de ataque;
- registrar custo computacional de cada critério;
- para `impact_oracle`, usar apenas grafos/subgrafos controlados, pois testar o impacto real de
  cada remoção pode ser caro.

**Referências que motivam:** Crucitti et al. (2006), Iyer et al. (2013) e Tian et al. (2019).

**Valor científico:** testa se a conclusão “intermediação identifica elementos críticos” é robusta
ou depende da escolha do indicador.

### P1.4 Validação e classificação morfológica baseada em dados

**Problema atual:** `urban_morphology.py` usa classes e limiares próprios. A entropia angular tem
base bibliográfica, mas as categorias atuais não foram validadas.

**Implementar:** comando sugerido `ic morphology-validation`.

Funções:

- análise de sensibilidade dos limiares e do número de bins angulares;
- entropia ponderada e não ponderada pelo comprimento das vias;
- histograma bidirecional de orientações;
- indicadores de quatro vias, becos sem saída, circuity e comprimento típico;
- clusterização não supervisionada das células pelas métricas;
- comparação entre clusters empíricos e classes por regra;
- amostra estratificada de células para validação visual manual;
- matriz de confusão e registro das células discordantes;
- estabilidade das classes em múltiplas escalas de grade.

**Referências que motivam:** Boeing (2019, ordem espacial) e Boeing (2020, multiescala).

**Valor científico:** evita apresentar rótulos morfológicos próprios como categorias já validadas
pela literatura.

### P1.5 Sensibilidade do índice composto de vulnerabilidade

**Problema atual:** o índice combina sinais distintos, mas seus pesos podem determinar o ranking.

**Implementar:** comando sugerido `ic vulnerability-sensitivity`.

Funções:

- permitir configuração explícita de pesos;
- executar cenários de pesos iguais, orientados por especialista e amostrados;
- medir Spearman, Kendall e sobreposição do top-k entre cenários;
- calcular frequência com que cada elemento aparece no top-k;
- produzir intervalos/ranks robustos, em vez de apenas um score;
- separar componentes observados e aproximados do índice;
- verificar dominância de uma variável após normalização.

**Valor científico:** transforma o índice em uma ferramenta transparente de análise multicritério,
sem alegar que há uma combinação única correta.

### P1.6 Validação externa entre centralidade e atividades urbanas

**Problema atual:** `functional-relations.py` relaciona centralidade a atributos das próprias vias.
Isso não valida se a centralidade se relaciona a atividades ou fluxos urbanos.

**Implementar:** comando sugerido `ic external-centrality-validation`.

Possíveis dados:

- pontos de interesse do OSM, com auditoria de completude;
- estabelecimentos e empregos de fonte oficial, quando disponíveis;
- equipamentos públicos, terminais e centralidades de uso do solo;
- contagens de tráfego ou matriz OD, caso possam ser obtidas.

Funções:

- agregar atividades por nó, segmento, buffer ou célula;
- testar Spearman e modelos espaciais simples;
- controlar densidade, distância ao centro e área da unidade;
- corrigir múltiplos testes;
- mapear resíduos e associações locais;
- distinguir validação exploratória com OSM de validação com fonte independente.

**Referência que motiva:** Lima e Ribeiro (2020).

**Valor científico:** é o passo que mais aproxima estrutura topológica de fenômenos urbanos reais.

**Dependência:** exige adquirir e documentar uma base externa; não deve ser implementado apenas com
dados inventados ou inferidos.

### P1.7 Correspondência histórica por geometria e atributos

**Problema atual:** `historical_quality.py` usa a interseção de `osmid`. IDs OSM não são
identificadores permanentes de objetos reais; edições, divisões e fusões podem alterar o ID.

**Expandir `historical-audit`:**

- pareamento em CRS projetado por proximidade/overlap geométrico;
- similaridade de nome normalizado e classe `highway`;
- tratamento de uma via histórica dividida em várias vias atuais;
- score de confiança do pareamento;
- comparação entre cobertura por ID e por geometria;
- amostra de validação manual;
- cobertura e recência de tags e edições, quando o histórico completo estiver disponível;
- classificação de qualidade com intervalos/limiares documentados.

**Referências que motivam:** Barron, Neis e Zipf (2014) e Minghini e Frassinelli (2019).

**Valor científico:** necessário se a análise histórica continuar como resultado do relatório. Se
ela permanecer apenas como apêndice exploratório, pode ser adiada.

## 4. P2 - Pesquisa futura ou expansão grande de escopo

### P2.1 Comparação multimodal: rede dirigível versus caminhável

Baixar e processar grafos `drive` e `walk` com o mesmo recorte; comparar circuity, densidade,
conectividade, interseções, caminhos e robustez. Isso segue diretamente Boeing (2019), mas duplica
parte do custo experimental e muda o projeto de rede viária dirigível para redes de circulação
multimodal.

**Só fazer agora se mobilidade multimodal entrar nos objetivos formais.** O diretório
`rotas_multimodais/` não substitui uma comparação controlada dos dois grafos.

### P2.2 Ampliar a amostra de cidades para similaridade e agrupamento

Com quatro cidades, PCA, dendrograma e clustering são visualizações exploratórias. Para usar
similaridade como resultado central:

- selecionar amostra maior e critérios de inclusão antes da análise;
- automatizar download e pipeline em lote;
- restringir o vetor a indicadores teoricamente justificados;
- medir estabilidade de clusters por reamostragem;
- controlar escala, área rural, população e região;
- separar treinamento exploratório e validação.

**Referência que motiva:** Spadon et al. (2018), que analisou 645 municípios paulistas.

**Cuidado:** esta expansão aumenta muito armazenamento e tempo de execução. É preferível remover
PCA/clustering das conclusões principais a sustentá-los com somente quatro observações.

### P2.3 Modelos nulos compatíveis com redes espaciais

Criar controles para responder se modularidade, centralidade concentrada ou robustez diferem do
esperado apenas por tamanho e distribuição de graus.

Possibilidades:

- _degree-preserving edge swaps_, declarando que quebram parte da geometria/planaridade;
- grafos geométricos com mesma quantidade de nós e distribuição espacial aproximada;
- controles que preservem comprimentos ou conectividade local;
- modelos sintéticos de grade, radial, árvore e orgânico como referências didáticas.

**Valor:** fortalece inferência mecanística.

**Cuidado:** não existe um modelo nulo simples que preserve simultaneamente grau, geometria,
planaridade, comprimento e hierarquia. Esta função exige uma pergunta científica bem definida.

### P2.4 Falhas em cascata baseadas em carga e capacidade

Implementar modelo teórico no qual a carga inicial é aproximada por intermediação, a capacidade é
`C_i = (1 + alpha) L_i`, uma remoção redistribui caminhos e elementos sobrecarregados falham.

Saídas:

- tamanho final da cascata;
- LCC e eficiência após estabilização;
- limiar de tolerância `alpha`;
- elementos iniciadores mais perigosos;
- comparação entre cidades.

**Referência que motiva:** Tian et al. (2019).

**Cuidado:** sem capacidade e fluxo observados, trata-se de um experimento topológico de carga
sintética, não de previsão de congestionamento ou colapso real.

### P2.5 Straightness e information centrality

Adicionar as centralidades ausentes da avaliação múltipla de Crucitti, Latora e Porta (2006):

- straightness: relação entre distância euclidiana e distância pela rede;
- information centrality: perda de eficiência causada pela remoção do elemento.

**Valor:** completa melhor a comparação com o artigo e pode melhorar a interpretação espacial.

**Cuidado:** information centrality exata é cara em grafos municipais. Deve usar aproximação
validada ou subgrafos. Não adicionar apenas para aumentar a lista de métricas; deve existir uma
hipótese associada.

## 5. Itens que não recomendo implementar agora

1. **Mais índices globais sem pergunta associada.** O projeto já produz dezenas de métricas; isso
   aumenta seleção posterior e dificulta a narrativa.
2. **Previsão de tráfego sem tráfego observado.** OSM fornece estrutura e tags, não demanda,
   capacidade efetiva nem velocidade observada.
3. **Classificador complexo/deep learning de morfologia com quatro cidades.** Primeiro validar as
   métricas e classes simples.
4. **Inferência histórica forte apenas com snapshots OSM.** Melhorar o pareamento reduz viés, mas
   não substitui cadastro, imagem ou outra fonte histórica.
5. **Otimização de novas vias como recomendação de política.** Antes seriam necessários demanda,
   custo, restrições ambientais, desapropriação, segurança e validação funcional.
6. **Misturar todas as expansões no resultado principal.** Robustez, comunidades e comparação
   municipal já formam uma contribuição suficiente; expansões devem responder hipóteses claras.

## 6. Ordem prática recomendada

### Ciclo A - tornar os resultados atuais publicáveis

1. **Concluído:** P0.1 - síntese/AUC, perdas e limiares das curvas;
2. **Concluído no código; regeneração pendente:** P0.2 - 30 ou mais repetições e intervalos de confiança;
3. P0.3 - sensibilidade/convergência;
4. **Concluído:** P0.5 - auditoria de representação;
5. P0.4 - estabilidade de comunidades, se comunidades forem resultado central.

### Ciclo B - expansão científica mais coerente

6. P1.1 - caminhos independentes e alternativas;
7. P1.2 - recuperação e resiliência estrutural;
8. P1.3 - ataques por diferentes centralidades;
9. P1.5 - sensibilidade do índice de vulnerabilidade.

### Ciclo C - ligação com fenômenos urbanos e qualidade dos dados

10. P1.4 - validação morfológica;
11. P1.6 - validação externa, se uma base adequada for obtida;
12. P1.7 - pareamento histórico, se a análise temporal permanecer no trabalho.

### Ciclo D - somente se houver tempo e objetivo formal

13. comparação `drive` versus `walk`;
14. aumento da amostra de cidades;
15. modelos nulos espaciais;
16. cascatas de carga sintética;
17. novas centralidades.

## 7. Escopo mínimo recomendado para a próxima etapa

Se for necessário escolher pouco, implementar somente:

1. **Concluído:** `robustness-summary` com AUC, perdas, limiares e comparação das estratégias;
2. **Concluído no código; regeneração pendente:** ampliar ataques aleatórios para 30 repetições com intervalo de confiança;
3. `sensitivity-audit` para os parâmetros usados nas conclusões;
4. **Concluído:** `representation-audit`;
5. caminhos independentes/alternativos em `route-redundancy`.

Esse conjunto melhora substancialmente a força científica sem desviar o projeto para tráfego,
planejamento de obras ou aprendizado de máquina.

## 8. Critério para decidir se uma função entra no projeto

Antes de implementar qualquer item, responder:

1. qual pergunta ou hipótese a função testa?
2. qual entrada observada ela usa e qual entrada é simulada?
3. qual é a unidade de análise: nó, aresta, comunidade, célula, cidade ou par OD?
4. qual saída será citada no relatório?
5. como será medida incerteza ou sensibilidade?
6. qual limitação impede interpretar o resultado como tráfego ou causalidade?
7. o custo computacional permite executar o mesmo protocolo em todas as cidades?

Se essas respostas não estiverem definidas, a função deve permanecer como ideia futura.
