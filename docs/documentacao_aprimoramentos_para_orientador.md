# Documentação formal dos aprimoramentos do projeto de Iniciação Científica

**Projeto-base:** *Análise Estrutural da Rede Viária Urbana Brasileira Utilizando Métricas de Redes Complexas*  
**Documento conferido:** [`_Projeto_2026__Lucas_Soares.pdf`](../_Projeto_2026__Lucas_Soares.pdf)  
**Pesquisador:** Lucas Soares Gonçalves  
**Orientador:** Prof. Dr. Ademar Takeo Akabane  
**Período previsto:** 1º de setembro de 2026 a 31 de agosto de 2027  
**Data desta documentação:** 18 de agosto de 2026

## Finalidade deste documento

Este documento registra, em linguagem acadêmica, os aprimoramentos realizados no projeto,
explica a relação de cada frente de trabalho com o plano de Iniciação Científica e separa três
estados que não devem ser confundidos:

1. **capacidade computacional implementada**: o programa já consegue executar a tarefa;
2. **resultado científico validado**: os dados foram produzidos em condições comparáveis,
   passaram pelos controles de qualidade e podem sustentar uma conclusão;
3. **entrega acadêmica concluída**: os resultados foram interpretados e incorporados a relatório,
   artigo ou apresentação.

O avanço realizado concentra-se sobretudo no primeiro estado e na criação de controles rigorosos
para alcançar o segundo. Ele não substitui a análise científica nem as entregas acadêmicas futuras.

## Síntese executiva

O projeto deixou de ser apenas uma coleção extensa de cálculos e arquivos e passou a funcionar
como uma pipeline científica auditável. Foram reforçados os cinco objetivos específicos do plano:
métricas estruturais, centralidades, robustez sob remoção de vértices e arestas, comparação entre
cidades e visualizações. Além disso, foram adicionados mecanismos de proveniência, validação,
integridade, comparabilidade e controle estatístico que não estavam explicitados no plano, mas são
necessários para que seus resultados sejam reprodutíveis e defensáveis.

Os principais avanços foram:

- ampliação da suíte automatizada de 29 para **104 testes**, cobrindo precisão, regressões,
  contratos de arquivos, falhas esperadas, proveniência, download, representação e robustez;
- separação conceitual entre **robustez estrutural** e resiliência em sentido forte;
- ataques aleatórios com 30 repetições, sementes independentes e intervalo de confiança;
- arquivo completo de centralidade de arestas e validação dos módulos que o consomem;
- registro detalhado de cada execução, incluindo parâmetros, versões, estado do código e hashes;
- auditorias *fail-closed*: evidência ausente ou inconsistente impede a liberação científica;
- auditoria de representação do grafo e separação entre extensão dirigida e extensão física;
- proteção contra comparações frágeis com apenas quatro cidades e muitas variáveis;
- revisão da terminologia, das limitações e das alegações presentes na documentação.

O resultado mais importante é metodológico: o sistema agora diferencia **“arquivo existente”** de
**“evidência científica pronta para uso”**. Os outputs antigos continuam preservados, mas foram
corretamente classificados como legados e ainda não liberados para comparação científica.

## Relação direta com os objetivos do PDF

### Objetivo 1 — métricas estruturais fundamentais

O plano exige distribuição de graus, coeficiente de aglomeração, comprimento médio de caminhos,
diâmetro e assortatividade. Esses cálculos já existiam em diferentes níveis; o trabalho de
aprimoramento fortaleceu a sua validade e a sua interpretação.

Foram adicionados ou aprimorados:

- contratos explícitos para a representação usada em cada métrica;
- validação das aproximações em subgrafos controlados;
- tratamento explícito de comprimentos ausentes ou inválidos;
- separação entre distância topológica, distância métrica e extensão viária;
- inventário padronizado de nós, arestas, componentes, densidade e atributos OSM;
- testes numéricos de regressão em redes pequenas com resposta conhecida.

**Relação com o projeto:** atende diretamente ao primeiro objetivo específico e à atividade A5.
Também fornece a base quantitativa necessária para A6.

**Evidências principais:**
[`metrics_structural.py`](../src/ic/metrics_structural.py),
[`paths_accessibility.py`](../src/ic/paths_accessibility.py),
[`graph_inventory.py`](../src/ic/graph_inventory.py),
[`approximation_validation.py`](../src/ic/approximation_validation.py) e
[`test_metric_precision.py`](../tests/test_metric_precision.py).

### Objetivo 2 — centralidades e identificação de elementos críticos

O plano solicita centralidades de grau, intermediação, proximidade e autovetor para identificar
vias e interseções críticas.

Foram adicionados ou aprimorados:

- ranking completo e padronizado das centralidades de nós;
- centralidade completa de arestas em `edge_centralities.csv`;
- manutenção de `top_edges.csv` apenas como recorte visual, sem utilizá-lo como base incompleta;
- correção do estimador aproximado de proximidade para não mudar sua definição nos landmarks;
- validação de cobertura: arestas ausentes, extras, duplicadas ou não finitas causam falha;
- propagação da centralidade completa para vulnerabilidade, gargalos e relações funcionais;
- mapas próprios de nós e arestas críticas.

**Relação com o projeto:** atende diretamente ao segundo objetivo, à atividade A5 e ao resultado
esperado de mapear elementos cuja remoção cause impacto relevante.

**Evidências principais:**
[`centrality.py`](../src/ic/centrality.py),
[`vulnerability_index.py`](../src/ic/vulnerability_index.py),
[`structural_bottlenecks.py`](../src/ic/structural_bottlenecks.py),
[`functional_relations.py`](../src/ic/functional_relations.py),
[`test_edge_centrality_contract.py`](../tests/test_edge_centrality_contract.py) e
[`test_closeness_regressions.py`](../tests/test_closeness_regressions.py).

### Objetivo 3 — remoção de vértices e arestas

O PDF utiliza o termo “resiliência”. O software, entretanto, observa a degradação da conectividade
e da eficiência durante remoções; ele não modela reparo, adaptação ou recuperação no tempo.
Portanto, o constructo foi formalizado como **robustez estrutural sob remoção**. Essa formulação
atende ao experimento descrito no objetivo sem atribuir ao cálculo um significado mais amplo do
que ele possui.

Foram adicionados ou aprimorados:

- estratégias aleatória, dirigida e adaptativa para arestas e vértices;
- 30 repetições por padrão nos ataques aleatórios;
- separação entre a semente que define a ordem do ataque e a semente que estima a eficiência;
- média, desvio amostral, erro-padrão, mediana, quantis, mínimo, máximo e IC 95% por bootstrap;
- AUC das curvas, checkpoints e limiares em uma síntese comum;
- incerteza `NA` quando existe apenas uma execução, em vez de desvio zero artificial;
- validação de baseline, domínio, finitude, monotonicidade e cobertura das curvas;
- exigência da matriz completa de modalidades e estratégias para sínteses confirmatórias;
- correções em checkpoints fracionários e em comunidades que já começam desconectadas.

**Relação com o projeto:** atende diretamente ao terceiro objetivo e reforça A5 e A6, porque a
avaliação deixa de depender de uma única ordem aleatória.

**Evidências principais:**
[`resilience.py`](../src/ic/resilience.py),
[`node_resilience.py`](../src/ic/node_resilience.py),
[`random_resilience_stats.py`](../src/ic/random_resilience_stats.py),
[`robustness_summary.py`](../src/ic/robustness_summary.py),
[`test_random_resilience_statistics.py`](../tests/test_random_resilience_statistics.py) e
[`test_robustness_summary_contract.py`](../tests/test_robustness_summary_contract.py).

### Objetivo 4 — comparação entre cidades

Comparar cidades exige mais do que colocar valores lado a lado. Os datasets precisam ter recortes,
datas do OSM, tipos de rede, parâmetros, sementes e versões compatíveis. Por isso, foi criada uma
auditoria científica que falha de forma conservadora quando a evidência não é suficiente.

Foram adicionados ou aprimorados:

- três estados inequívocos: `confirmada`, `nao_comprovada` e `incomparavel`;
- perfis científico e exploratório separados;
- verificação de snapshot OSM, identidade do limite, configuração, sementes e estado do código;
- fingerprints dos grafos e dos artefatos obrigatórios;
- matriz de completude dos produtos por dataset e por par de cidades;
- proteção contra similaridade multivariada instável: o modo principal exige ao menos oito
  datasets e usa um conjunto teórico reduzido de variáveis;
- classificação explícita das quatro cidades atuais como estudo de caso exploratório.

**Relação com o projeto:** implementa a infraestrutura do quarto objetivo. A conclusão sobre
“padrões universais” ainda não está atendida, pois quatro municípios próximos no interior paulista
não representam a diversidade urbana brasileira.

**Evidências principais:**
[`scientific_comparability.py`](../src/ic/scientific_comparability.py),
[`comparison_protocol.py`](../src/ic/comparison_protocol.py),
[`compare_report.py`](../src/ic/compare_report.py),
[`city_similarity.py`](../src/ic/city_similarity.py),
[`test_scientific_comparability.py`](../tests/test_scientific_comparability.py) e
[`test_city_similarity_safeguards.py`](../tests/test_city_similarity_safeguards.py).

### Objetivo 5 — visualizações interativas

O projeto já gerava mapas e painéis. O aprimoramento integrou essas visualizações aos contratos de
dados e deixou mais claro o que cada mapa representa.

Foram consolidados:

- dashboards HTML por dataset;
- mapas de centralidade, comunidades, vulnerabilidade, barreiras, rotas e criticidade;
- figuras de estrutura, robustez, incerteza e sensibilidade à representação;
- exportação para Kepler.gl;
- relatórios Markdown e síntese HTML com referências somente a artefatos efetivamente produzidos;
- textos de limitação nos módulos exploratórios.

**Relação com o projeto:** atende diretamente ao quinto objetivo e ao produto computacional de
painéis destinados a públicos técnicos e não técnicos.

**Evidências principais:**
[`html_report.py`](../src/ic/html_report.py),
[`plot_graph.py`](../src/ic/plot_graph.py),
[`kepler_export.py`](../src/ic/kepler_export.py) e os módulos de mapas associados às análises.

## Aprimoramentos transversais necessários à validade científica

### Aquisição de dados e metadados do OpenStreetMap

O download passou a registrar início e fim da consulta em UTC, modo histórico ou ao vivo,
timestamp do snapshot quando existente, configuração efetiva, hash do YAML, versão do OSMnx,
CRS, tipo de rede e identidade canônica do recorte. Recortes por `place` usam relação e geometria;
`bbox` e `radius` recebem fingerprints dos parâmetros que os definem.

Isso atende ao resultado esperado de uma base estruturada com metadados padronizados e permite
demonstrar que duas redes foram obtidas sob condições compatíveis.

**Evidências:** [`download.py`](../src/ic/download.py) e
[`test_download_metadata.py`](../tests/test_download_metadata.py).

### Proveniência por execução

Cada comando novo registra em JSONL:

- argumentos reais e parâmetros resolvidos, inclusive valores padrão;
- subcomando, horário, duração e diretório de trabalho;
- versão do Python e das principais dependências;
- commit, branch, estado limpo/sujo e hash do conteúdo alterado, inclusive arquivos não rastreados;
- fingerprints SHA-256 das entradas e dos produtos criados ou modificados;
- status de sucesso ou falha e erro correspondente;
- datasets efetivamente envolvidos, inclusive referência em auditoria histórica.

A escrita é idempotente por identificador de execução e preserva o erro original caso o próprio
log de proveniência falhe. O manifesto final exclui o log mutável de seu conjunto autoritativo,
evitando que o registro da execução invalide o manifesto recém-criado.

**Relação com o projeto:** fortalece o resultado esperado de códigos reprodutíveis, metadados e
documentação técnica.

**Evidências:** [`provenance.py`](../src/ic/provenance.py),
[`final_report.py`](../src/ic/final_report.py),
[`test_provenance.py`](../tests/test_provenance.py) e
[`test_final_manifest.py`](../tests/test_final_manifest.py).

### Integridade dos artefatos

Foi criada uma auditoria que verifica existência, tamanho, schema, número mínimo de linhas,
frescor, dependências, hashes, manifesto, outputs extras e mistura de datasets. O comportamento é
*fail-closed*: somente `PASS` libera o uso; `WARN` e `FAIL` bloqueiam. Auditorias parciais recebem
nomes por escopo para não sobrescreverem a auditoria completa.

**Relação com o projeto:** impede que tabelas ou figuras antigas sejam utilizadas como se tivessem
sido produzidas pela versão atual do método.

**Evidências:** [`artifact_integrity.py`](../src/ic/artifact_integrity.py),
[`test_artifact_integrity.py`](../tests/test_artifact_integrity.py) e
[`test_cli_gates.py`](../tests/test_cli_gates.py).

### Representação do grafo e extensão física

A rede OSM é originalmente um `MultiDiGraph`: dirigida e com múltiplas arestas. Muitas métricas
topológicas usam uma projeção simples e não dirigida. Essa transformação pode alterar número de
arestas, comprimento, componentes e rankings.

Foi criada uma auditoria que compara `MultiDiGraph`, `MultiGraph`, `DiGraph` e `Graph`, tanto no
grafo bruto quanto no limpo. Ela registra perdas, componentes, reciprocidade, loops, paralelas,
mão única, comprimento e estabilidade de rankings.

Também foram separados:

- **comprimento dirigido**, apropriado ao roteamento e que conta arcos em cada sentido;
- **proxy de comprimento físico**, que colapsa sentidos recíprocos e evita duplicar uma rua de
  mão dupla na densidade viária.

Esse refinamento é diretamente relevante ao primeiro objetivo, porque mostra que a representação
não é um detalhe neutro do cálculo.

**Evidências:** [`representation_audit.py`](../src/ic/representation_audit.py),
[`metric_graphs.py`](../src/ic/metric_graphs.py),
[`graph_inventory.py`](../src/ic/graph_inventory.py) e
[`test_representation_audit.py`](../tests/test_representation_audit.py).

## Expansões computacionais e sua relação com o plano

Os módulos a seguir ampliam o projeto, mas não devem ser apresentados como novos objetivos
obrigatórios do PDF. Eles são desdobramentos coerentes das ideias de conectividade, criticidade,
vulnerabilidade, comparação e visualização.

| Expansão | Relação com o plano | Limite de interpretação |
|---|---|---|
| Comunidades e modularidade | A3 e A5 citam modularidade; ajuda a descrever organização interna | Comunidade topológica não equivale a bairro ou região funcional |
| Robustez entre e dentro de comunidades | Aprofunda a remoção de elementos críticos | Continua sendo robustez estrutural, sem recuperação temporal |
| Índice de vulnerabilidade | Combina sinais de criticidade para priorização exploratória | Pesos exigem análise de sensibilidade e validação antes de uso decisório |
| Pontes, articulações e gargalos | Identifica ligações cuja remoção fragmenta a rede | Não mede tráfego ou capacidade real |
| Redundância de rotas | Examina disponibilidade de alternativa estrutural | Pares de nós não representam demanda OD observada |
| Bloqueios espaciais | Cria cenários regionais estilizados | Não contém risco, probabilidade ou hazard real |
| Hierarquia viária | Relaciona topologia a classes `highway` do OSM | Tags OSM não substituem uma validação funcional externa |
| Morfologia urbana | Gera perfis heurísticos de orientação e conectividade | Classes e limiares ainda não foram validados empiricamente |
| Eficiência em pares OD | Resume a distribuição induzida pela amostragem de nós | Não representa deslocamentos observados da população |
| Candidatos a subcentros | Localiza células de alta centralidade topológica | Não comprova subcentros sem empregos, POIs, população e fluxos |
| Barreiras urbanas prováveis | Examina baixa permeabilidade espacial | É proxy estrutural, não inventário validado de barreiras |
| Perfil de escala | Mede sensibilidade agregada à grade | Não demonstra estabilidade espacial de hotspots e sofre MAUP |
| Auditoria histórica | Controla viés de cobertura antes de comparar anos do OSM | Mudança de ID ou mapeamento não é automaticamente mudança urbana |

## Evidências quantitativas do avanço

### Qualidade de software

| Indicador | Estado inicial | Estado após a revisão | Interpretação correta |
|---|---:|---:|---|
| Testes automatizados | 29 | 104 | Cobertura ampliada em 75 casos; não substitui validação científica |
| Tipos de teste | Predominantemente precisão unitária | Unidade, regressão, propriedades, integração, CLI, contratos e gates | Menor risco de regressões silenciosas |
| Piso de Python | Declarado 3.10, incompatível com o lock | 3.11+, CI em 3.12 | Ambiente declarado alinhado ao executável |
| Dependências | Faixas de versão | Lock de versões | Melhora repetibilidade; hashes de pacotes ainda faltam |

### Sensibilidade à representação nos quatro datasets existentes

| Dataset | Nós raw | Arestas raw | Perda de nós no clean | Perda de arestas no clean | Extensão dirigida | Proxy física | Redução da proxy física |
|---|---:|---:|---:|---:|---:|---:|---:|
| Campinas | 32.801 | 81.277 | 1,33% | 1,13% | 9.058,2 km | 5.316,5 km | 41,31% |
| Jundiaí | 11.785 | 25.146 | 0,83% | 0,58% | 3.419,7 km | 2.030,6 km | 40,62% |
| Sorocaba | 17.184 | 39.690 | 5,16% | 3,56% | 4.361,5 km | 2.618,0 km | 39,98% |
| Valinhos | 4.040 | 9.465 | 4,50% | 4,17% | 1.305,8 km | 749,3 km | 42,62% |

A proxy de extensão física é aproximadamente 40%–43% menor que a soma dirigida. Isso demonstra
que a escolha da representação afeta diretamente densidade e interpretação. A auditoria também
mostrou que a sobreposição dos 20 nós com maior grau entre `MultiDiGraph` e `Graph` pode ser muito
baixa, chegando a zero em Campinas e Sorocaba.

### Estado dos resultados legados

| Dataset | Critérios científicos confirmados | Pendentes | Artefatos obrigatórios válidos | Artefatos cobertos por proveniência | Estado |
|---|---:|---:|---:|---:|---|
| Campinas | 28/39 | 11 | 10/10 | 2/10 | `nao_comprovada` |
| Jundiaí | 28/39 | 11 | 10/10 | 2/10 | `nao_comprovada` |
| Sorocaba | 28/39 | 11 | 10/10 | 2/10 | `nao_comprovada` |
| Valinhos | 28/39 | 11 | 10/10 | 2/10 | `nao_comprovada` |

Os seis pares de cidades também estão `nao_comprovada`. Isso não significa que os algoritmos
falharam; significa que os arquivos antigos não possuem toda a evidência que o novo protocolo
exige. O bloqueio é uma melhoria: evita conclusões comparativas produzidas com datas, limites ou
versões não demonstravelmente equivalentes.

## Avaliação de aderência ao plano

| Parte do plano | Situação após o aprimoramento | Observação |
|---|---|---|
| Cinco objetivos específicos | Cobertura computacional ampla | Objetivo comparativo exige nova execução e amostra mais abrangente para alegações nacionais |
| A1 — estado da arte e OSMnx | Atendido em documentação, ainda evolutivo | Há revisão e bibliografia ampliadas; protocolo sistemático pode ser refinado |
| A2 — encontro de IC | Pendente acadêmico | Não é tarefa de software e depende do calendário institucional |
| A3 — teoria dos grafos | Atendido na implementação e parcialmente na documentação | A fundamentação deverá ser condensada no texto científico final |
| A4 — relatório parcial | Pendente acadêmico | Os relatórios técnicos gerados servem de insumo, mas não substituem o relatório parcial |
| A5 — aplicação das métricas | Parcial avançado | Cálculo implementado; falta regenerar, interpretar e comparar os resultados validados |
| A6 — avaliação quantitativa e qualitativa | Parcial | Estatística e gates foram implementados; faltam hipóteses, análise contextual e discussão |
| A7 — artigo científico | Pendente acadêmico | Deve usar somente resultados liberados pelos gates |
| A8 — relatório final | Pendente acadêmico | O gerador técnico não equivale ao relatório científico final |
| Base estruturada e metadados | Implementado para novas execuções | Datasets legados precisam ser regenerados |
| Tabelas, figuras e dashboards | Implementado | Resultados comparativos legados permanecem exploratórios |
| Padrões universais e especificidades | Pendente como conclusão | Exige amostra, desenho e análise adequados |
| Mapeamento de elementos críticos | Implementado computacionalmente | Requer interpretação e, para função real, validação externa |

A matriz detalhada requisito por requisito está em
[`matriz_aderencia_plano_trabalho.md`](matriz_aderencia_plano_trabalho.md).

## O que ainda falta

### Prioridade 1 — antes de usar resultados comparativos

1. Definir uma data/snapshot OSM congelado e documentado.
2. Fixar e justificar o recorte de cada cidade, incluindo uma análise de sensibilidade entre
   limite administrativo e mancha urbanizada quando possível.
3. Regenerar as quatro cidades do download ao relatório com o código atual e parâmetros comuns.
4. Produzir `edge_centralities.csv` e regenerar todos os módulos dependentes.
5. Gerar os manifestos v2 somente ao final da execução homogênea.
6. Obter `PASS` na auditoria completa de integridade.
7. Obter `confirmada` na auditoria científica dos pares que serão comparados.
8. Só depois atualizar tabelas, figuras e conclusões do trabalho.

### Prioridade 2 — para sustentar a contribuição científica

1. Formular perguntas de pesquisa, hipóteses e poucos resultados primários antes da análise.
2. Relatar tamanho de efeito, incerteza, análise de sensibilidade e, quando aplicável, controle de
   multiplicidade e modelos nulos espaciais.
3. Ampliar e diversificar a amostra para sustentar o título nacional e qualquer afirmação de
   padrão universal; com quatro municípios paulistas, a formulação correta é “estudo de caso”.
4. Validar as aproximações em várias subamostras espaciais, não somente em um subgrafo.
5. Incorporar fontes externas — tráfego, empregos, população, POIs ou uso do solo — antes de
   afirmar relação funcional ou policentricidade urbana.
6. Validar ou rebaixar a importância dos módulos heurísticos de morfologia, subcentros, barreiras,
   multiescala e qualidade histórica.
7. Se o termo “resiliência” for mantido em sentido forte, modelar recuperação/adaptação ao longo
   do tempo; caso contrário, usar “robustez estrutural”.

### Prioridade 3 — entregas acadêmicas e manutenção

1. Transformar a revisão bibliográfica em seção do relatório e manter um protocolo de busca.
2. Produzir relatório parcial, artigo, apresentação e relatório final nos períodos A4, A7 e A8.
3. Remover ambientes virtuais do versionamento em uma alteração controlada; eles somam milhares
   de arquivos e não devem compor o produto científico.
4. Acrescentar hashes ao lock de dependências se for necessária reprodução mais próxima de
   bit a bit e verificação de cadeia de fornecimento.
5. Corrigir no PDF a tabela do cronograma: o texto informa 2026–2027, mas o cabeçalho da Tabela
   6.1 está rotulado como 2025–2026.
6. Corrigir o final da atividade A5 no PDF, onde aparece a pontuação duplicada `viária.;`.
7. Preservar em [`referencias_ic.bib`](referencias_ic.bib) as referências originais do plano que
   ainda não foram incorporadas, além da bibliografia ampliada.
8. Adicionar licença do código, `CITATION.cff` e instruções de distribuição/atribuição dos dados.
9. Definir como os resultados serão entregues: `data/` e `outputs/` estão ignorados pelo Git e
   somam aproximadamente 4,1 GB; um clone limpo não contém os arquivos demonstrados.
10. Criar um comando único de orquestração da pipeline para reduzir erro manual na regeneração.

Em 18 de agosto de 2026, o período formal da IC ainda não havia começado. Assim, A2, A4, A7 e A8
devem ser descritas como atividades futuras previstas, não como atrasos ou falhas desta etapa
preparatória.

## Formulação formal recomendada para apresentar o avanço

> O aprimoramento realizado não se limitou à inclusão de novas métricas. O foco principal foi
> transformar a implementação em uma pipeline científica auditável. Os cinco objetivos
> computacionais do plano foram cobertos, mas cada resultado passou a depender de contratos de
> dados, proveniência, controle estatístico, integridade e comparabilidade. Essa mudança permite
> distinguir a existência de um artefato da sua aptidão para sustentar uma conclusão científica.
> A reauditoria mostrou que os outputs legados ainda não possuem evidência suficiente para uma
> comparação confirmatória; por isso, eles foram preservados como exploratórios e deverão ser
> regenerados sob um snapshot OSM e um protocolo homogêneo. O próximo ciclo de trabalho é menos
> sobre acrescentar funcionalidades e mais sobre executar o desenho experimental, interpretar os
> resultados e produzir as entregas acadêmicas previstas no plano.

## Conclusão

O projeto apresenta hoje uma base computacional substancialmente mais rigorosa, abrangente e
reprodutível. A contribuição do aprimoramento está tanto nas novas capacidades quanto na criação
de limites objetivos para o uso dos resultados. A implementação já cobre amplamente o núcleo do
plano; o trabalho remanescente é essencialmente a regeneração homogênea dos experimentos, a
ampliação ou delimitação da amostra, a interpretação científica e a produção acadêmica.

Esse estado é mais defensável do que declarar o projeto “concluído”: há um avanço concreto e
verificável, acompanhado de uma lista explícita do que precisa ocorrer antes das conclusões finais.
