# Auditoria de aderência ao Plano de Trabalho da IC

Data da auditoria original: 4 de junho de 2026.

Última atualização: 18 de agosto de 2026.

Documento de referência: [`_Projeto_2026__Lucas_Soares.pdf`](../_Projeto_2026__Lucas_Soares.pdf),
plano **Análise Estrutural da Rede Viária Urbana Brasileira Utilizando Métricas de Redes
Complexas**. O arquivo foi anexado e conferido integral e visualmente em 18 de agosto de 2026.
Objetivos, atividades A1–A8 e resultados esperados foram reconciliados com o original na
[`matriz_aderencia_plano_trabalho.md`](matriz_aderencia_plano_trabalho.md).

Período formal informado no PDF: **1º de setembro de 2026 a 31 de agosto de 2027**.

Observação: a etapa computacional, que exclui escrita acadêmica e avaliação humana e considera
somente o sistema que gera dados para análise posterior, foi fechada em
[`docs/lacunas_computacionais_escopo_ic.md`](lacunas_computacionais_escopo_ic.md).

> **Estado revalidado em 18 de agosto de 2026.** O software tem cobertura computacional ampla,
> mas os resultados legados das quatro cidades não passaram os novos gates científicos. A
> comparabilidade ficou `nao_comprovada` por falta de snapshot OSM congelado, identidade/hash
> dos limites e proveniência integral dos artefatos antigos. Declarações anteriores de conjunto
> “comparável”, “reprocessado” ou “concluído” ficam supersedidas por este estado.

## Conclusão executiva

O núcleo computacional previsto para esta etapa tem cobertura ampla: o repositório cobre
aquisição, processamento, métricas, validação, visualização, robustez estrutural sob remoção e
comparação entre cidades. As comparações científicas dependem de uma nova execução integral
com dados e proveniência compatíveis.
O projeto de IC como trabalho científico ainda não está concluído, porque geração de artefatos
não substitui interpretação, discussão e produção acadêmica.

Após a conferência de 21 de junho de 2026, as principais lacunas restantes estão no plano
acadêmico/metodológico, não na geração computacional dos dados:

1. manter a matriz literal requisito-evidência sincronizada com o PDF e a implementação;
2. regenerar dados e produtos com snapshot, limites e proveniência documentados;
3. realizar análise científica dos padrões, além da geração de tabelas;
4. concluir avaliação quantitativa/qualitativa e os produtos acadêmicos A1 a A8.

Já foram implementados: centralidades de proximidade e autovetor, protocolo/auditoria de
comparabilidade, datasets municipais padronizados, análise descritiva topologia-função,
validação quantitativa das aproximações, comunidades nos datasets administrativos,
robustez por comunidades, estatísticas agregadas de ataques aleatórios, mapa de arestas
críticas, manifesto experimental, CSV comparativo consolidado e índice composto de
vulnerabilidade viária, além da análise de pontes, articulações, gargalos estruturais e
redundância de rotas, com análise multiescala por células espaciais, robustez espacial por
bloqueios regionais, análise de hierarquia viária por classes OSM `highway` e morfologia
urbana por padrões espaciais da rede, além de eficiência estatística de rotas em múltiplos
pares origem-destino e similaridade estrutural entre cidades.
Também foram adicionados candidatos de alta centralidade topológica (não subcentros urbanos
validados),
exposição da rede a barreiras urbanas prováveis por baixa permeabilidade espacial e perfil de
escala da rede viária.

A análise histórica é uma expansão válida, mas deve ser usada somente após auditoria de
cobertura OSM, pois anos antigos podem refletir evolução do mapeamento, não evolução urbana.

## Quadro consolidado em 21 de junho de 2026

### Concluído

- [x] aquisição, limpeza e caracterização dos grafos;
- [x] métricas estruturais e centralidades previstas;
- [x] comunidades e robustez estrutural por arestas, vértices e comunidades;
- [x] validação das aproximações e repetição dos ataques aleatórios;
- [x] recortes administrativos homogêneos em formato, ainda sem comparabilidade científica comprovada;
- [x] mapas, dashboards, relatórios técnicos e manifestos experimentais;
- [x] comparação descritiva consolidada; similaridade confirmatória exige amostra maior;
- [x] expansões computacionais descritas neste documento.

### Pendente

- [ ] transformar as perguntas e hipóteses H1–H4 propostas na revisão em protocolo operacional;
- [ ] produzir interpretação comparativa quantitativa e qualitativa;
- [ ] documentar fundamentos teóricos e escolhas metodológicas;
- [x] organizar uma primeira revisão do estado da arte e bibliografia ampliada;
- [ ] preparar relatório parcial, artigo e relatório final acadêmico;
- [ ] concluir as melhorias de engenharia listadas na seção de reprodutibilidade;
- [ ] corrigir as datas inconsistentes do cronograma na próxima versão do plano.

## Matriz dos objetivos específicos

| Requisito explícito do PDF | Estado | Evidência atual | O que falta para concluir |
|---|---|---|---|
| Distribuição de graus | Implementado | CSV e gráfico log-log | Interpretar e comparar os padrões entre cidades |
| Coeficiente de aglomeração | Implementado parcialmente | Transitividade, clustering aproximado e estudo de sensibilidade | A validação mostrou instabilidade do clustering aproximado; justificar o indicador ou ampliar amostras |
| Comprimento médio de caminhos | Implementado | Estimativa por amostragem, em hops e metros, com validação | Interpretar resultados e limitações |
| Diâmetro da rede | Implementado | Estimativa por amostragem com validação | Interpretar resultados e documentar que não é diâmetro exato no grafo completo |
| Assortatividade | Implementado | Assortatividade por grau | Interpretar e comparar resultados |
| Centralidade de grau | Implementado | Ranking completo e resumo padronizado | Interpretar após os gates |
| Centralidade de intermediação | Implementado | Betweenness aproximada validada de nós e arestas; mapa de arestas críticas | Interpretar resultados |
| Centralidade de proximidade | Implementado | Closeness aproximada, ranking completo e validação | Interpretar resultados e manter parâmetros padronizados |
| Centralidade de autovetor | Implementado | Cálculo espectral, ranking completo e integração | Interpretar resultados |
| Robustez por remoção de arestas | Implementado | Estratégias aleatória, dirigida e adaptativa; padrão de 30 repetições e IC bootstrap | Regenerar e interpretar; não chamar de recuperação/resiliência temporal |
| Robustez por remoção de vértices | Implementado | Ataques aleatório, dirigido estático e adaptativo, curvas e rankings de remoção | Regenerar e interpretar; o eixo não é diretamente equivalente ao de arestas |
| Comparação entre diferentes cidades | Implementado como gate e visualização | Auditoria científica fail-closed, comparador HTML e CSV | Obter snapshot/limites/proveniência e alcançar estado `confirmada` antes de inferir |
| Identificar padrões recorrentes e especificidades locais | Ausente como resultado científico | Existem tabelas, métricas normalizadas por área, similaridade, PCA e agrupamento | Formular hipóteses, interpretar os resultados, ampliar ou justificar a amostra e produzir conclusões |
| Visualizações interativas | Implementado | Dashboards, mapas Folium, comunidades e arestas críticas | Interpretar resultados |
| Relação entre topologia e características funcionais | Implementado descritivamente | Grupos e correlações de Spearman para atributos OSM | Interpretar com cautela e incorporar outras fontes funcionais futuramente |

## Matriz das atividades A1 a A8

| Atividade | Estado atual | Observação |
|---|---|---|
| A1 - Estado da arte e estudo do OSMnx | Parcial avançado | A revisão e o BibTeX estão organizados; falta explicitar protocolo de busca, critérios de inclusão e síntese no formato acadêmico |
| A2 - Participação no encontro de IC | Ainda não aplicável | É atividade acadêmica futura, não uma funcionalidade de software |
| A3 - Estudo dos conceitos de Teoria dos Grafos | Parcial | Os conceitos aparecem no código, mas falta documentação teórica e justificativa metodológica |
| A4 - Relatório parcial | Ainda não aplicável | O gerador atual produz inventário técnico, não um relatório parcial acadêmico |
| A5 - Aplicação das métricas | Parcial avançado | Falta o fechamento analítico comparativo |
| A6 - Avaliação quantitativa e qualitativa | Parcial | Estatística, validação e gates foram implementados; falta operacionalizar H1–H4, interpretar efeitos e realizar a discussão qualitativa |
| A7 - Artigo científico | Ainda não iniciado | Deve ser produzido após consolidar método e resultados |
| A8 - Relatório final | Ainda não aplicável | O Markdown atual é um relatório automático de artefatos, não o relatório científico final |

## Matriz dos resultados esperados

### Base estruturada, metadados e documentação

**Estado: implementado com melhorias de engenharia pendentes.**

Já existem GraphML, metadados JSON, configurações YAML, saídas organizadas e manifestos
experimentais. Novas execuções registram argumentos resolvidos, versões, timestamps, Git,
sementes e fingerprints de entradas/saídas. Os artefatos legados não recebem essa evidência
retroativamente e, portanto, precisam ser regenerados.

Melhorias ainda pendentes:

- estender os contratos de proveniência quando novos módulos forem adicionados;
- manter o dicionário de dados central sincronizado com atributos e métricas;
- revisar e padronizar metadados também nos datasets legados e históricos;
- criar um comando único para executar a pipeline completa;
- executar o gate de integridade para impedir o uso de saídas desatualizadas;
- ampliar os testes de integração da pipeline.

### Caracterização estrutural em tabelas e gráficos

**Estado: parcial avançado.**

Os cálculos e artefatos existem, mas falta transformar os resultados em análise científica:
explicar significado, comparar cidades, discutir limitações e responder perguntas de pesquisa.

### Padrões recorrentes, regularidades e especificidades locais

**Estado: ausente como conclusão científica.**

O comparador atual coloca métricas lado a lado, mas não identifica formalmente padrões
universais. Para isso, é necessário:

- usar novos recortes administrativos ou de mancha urbanizada com proveniência comprovada;
- priorizar os indicadores já normalizados por área e justificar o uso de valores absolutos;
- ampliar ou justificar a amostra de cidades;
- analisar dispersão, correlações e agrupamentos;
- discutir contexto urbano e limitações;
- evitar chamar um padrão de universal sem evidência suficiente.

### Mapeamento de elementos críticos

**Estado: parcial.**

Já há mapa de nós críticos por betweenness, ranking completo de centralidade de arestas e mapa
próprio com nome, tipo, comprimento e ranking quando os atributos existem no OSM. Scores
compostos pertencem aos módulos de vulnerabilidade e não devem ser confundidos com
betweenness. Falta a interpretação científica desses elementos.

### Códigos reprodutíveis e dashboards

**Estado: implementado para a etapa computacional atual.**

O sistema consegue gerar dashboards para os quatro datasets administrativos, incluindo
comunidades, robustez por arestas, vértices e comunidades, estatísticas agregadas, mapas e
manifestos. Os dashboards legados devem ser tratados como demonstração até a regeneração
integral passar pelos gates de integridade e comparabilidade.

## Problemas metodológicos que precisam ser resolvidos

### 1. Recortes geográficos padronizados, com conjunto legado preservado

Os datasets originais usam caixas delimitadoras com dimensões diferentes e permanecem
exploratórios. O conjunto principal agora usa limites administrativos OSM para as quatro
cidades e tem homogeneidade protocolar exploratória; a auditoria científica atual o classifica
como `nao_comprovada`.

Já existem indicadores por área (`nodes_per_km2`, `edges_per_km2` e
`total_length_km_per_km2`). Ainda é necessário justificar formalmente o recorte no texto
científico, priorizar esses indicadores na interpretação e explicar quando valores absolutos
forem usados.

### 2. Representação do grafo

Grande parte das métricas usa grafo simples, não direcionado e maior componente conectada.
Essa escolha é válida para certas análises estruturais, mas remove:

- sentidos das vias;
- arestas paralelas;
- diferenças entre componentes menores;
- parte do comportamento funcional da circulação.

O trabalho precisa justificar essa transformação e separar claramente:

- métricas topológicas no grafo simples não direcionado;
- métricas funcionais no grafo direcionado e ponderado.

### 3. Aproximações validadas em subgrafo controlado

O estudo de sensibilidade agora compara valores aproximados e exatos em subgrafo conectado,
variando amostras, repetições e sementes. Betweenness e closeness apresentaram rankings
estáveis; o clustering aproximado apresentou variação relevante e exige cautela. A validação
não prova que o erro seja idêntico no grafo municipal completo.

### 4. Ataque aleatório com incerteza explícita

A etapa computacional agora usa 30 repetições por padrão, separa a semente de ataque da semente
de avaliação e gera média, erro-padrão, quantis e intervalos bootstrap. Resultados antigos com
cinco sementes precisam ser regenerados; estratégias dirigidas aproximadas também requerem
repetição para que `n=1` não seja confundido com incerteza nula.

### 5. Comparação padronizada disponível, interpretação ainda incompleta

As configurações declaradas são semelhantes, mas a equivalência temporal, geométrica e
experimental permanece não comprovada. Os resultados comparativos atuais são exploratórios,
mesmo quando há indicadores normalizados por área.

### 6. Cálculo não equivale a análise

Os relatórios atuais consolidam valores e artefatos, mas quase não apresentam interpretação,
discussão, hipóteses, limitações ou conclusões. O plano exige **calcular e analisar**, avaliar
quantitativa e qualitativamente e identificar padrões.

## Expansões já implementadas fora do núcleo obrigatório

Estas expansões são úteis e devem ser preservadas, mas não devem bloquear o fechamento do
escopo original:

- análise histórica de Campinas;
- auditoria de qualidade da análise histórica OSM;
- resiliência entre comunidades;
- resiliência interna de cada comunidade;
- inventário de superfície, faixas, velocidade e mão única;
- exportação para Kepler.gl;
- rotas multimodais;
- comparadores visuais extensos;
- índice composto de vulnerabilidade de nós e arestas;
- pontes, articulações e gargalos estruturais;
- perfil de redundância de rotas;
- análise multiescala por grade espacial;
- robustez espacial por bloqueios regionais;
- análise de hierarquia viária;
- comparação planejamento urbano x estrutura da rede por morfologia urbana;
- eficiência de rotas em múltiplos pares origem-destino;
- similaridade estrutural entre cidades por vetores de métricas;
- seleção exploratória de células candidatas de alta centralidade topológica;
- exposição da rede a barreiras urbanas prováveis;
- perfil de escala da rede viária.

Algumas dessas expansões podem ajudar a cumprir o escopo. Por exemplo, os atributos viários
do inventário podem ser usados para estabelecer relações entre topologia e características
funcionais.

## Observação sobre análise histórica OSM

Foi implementado o comando `ic historical-audit` para evitar interpretar a incompletude do OSM
antigo como mudança urbana. Para Campinas, a auditoria classificou 2010 a 2014 como
**não confiável**, 2015 a 2020 como **exploratório** e 2021 a 2026 como **comparável com
cautela**. Comparações históricas brutas anteriores a 2021 não devem ser usadas como evidência
central de evolução urbana.

## Ordem recomendada para concluir o escopo original

### Fase 1 - Completar os requisitos explícitos

1. **Concluída:** requisitos computacionais explícitos implementados; manter testes adicionais
   de integração como melhoria de engenharia.

### Fase 2 - Tornar os experimentos cientificamente válidos

1. **Implementada no software, mas ainda não regenerada integralmente:** identidade do recorte,
   manifesto v2, proveniência, repetições estatísticas e auditorias foram incorporados. Os
   datasets administrativos legados continuam bloqueados pelos novos gates.
2. **Implementada após a revisão bibliográfica:** síntese quantitativa das curvas de robustez com
   AUC normalizada, perdas em frações padronizadas, limiares de degradação e faixa comum entre
   cidades/estratégias.
3. **Parcialmente concluída:** parâmetros e artefatos agora são registrados e outputs stale são
   detectados; permanece pendente um comando único para orquestrar toda a pipeline.

### Fase 3 - Responder ao objetivo científico

1. Operacionalizar as perguntas e hipóteses H1–H4 propostas na revisão bibliográfica.
2. Relacionar métricas topológicas a características funcionais disponíveis.
3. Produzir análise comparativa quantitativa e qualitativa.
4. Identificar padrões recorrentes e especificidades locais com cautela estatística.
5. Escrever discussão, limitações e conclusões.

### Fase 4 - Produtos acadêmicos

1. Organizar revisão do estado da arte.
2. Criar documentação teórica e metodológica.
3. Preparar relatório parcial.
4. Estruturar artigo científico.
5. Preparar relatório final.

## Critério de conclusão do escopo original

O escopo original pode ser considerado tecnicamente e cientificamente contemplado quando:

- todas as métricas e experimentos explicitamente prometidos estiverem implementados;
- todas as cidades forem processadas com protocolo comparável;
- aproximações e aleatoriedade tiverem validação;
- houver análise das relações topológicas e funcionais;
- houver discussão quantitativa e qualitativa dos resultados;
- os experimentos forem reproduzíveis;
- os produtos acadêmicos previstos estiverem preparados conforme o cronograma.

## Observação sobre o PDF

O período textual informa **1º de setembro de 2026 a 31 de agosto de 2027**, mas o cabeçalho
da tabela do cronograma mostra **2025** e **2026**. As datas da tabela devem ser corrigidas
para **2026** e **2027** em uma próxima versão do plano.
