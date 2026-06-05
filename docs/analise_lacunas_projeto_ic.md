# Auditoria de aderência ao Plano de Trabalho da IC

Data da auditoria: 4 de junho de 2026.

Documento de referência: `_Projeto_2026__Lucas_Soares.pdf`, plano **Análise Estrutural da Rede
Viária Urbana Brasileira Utilizando Métricas de Redes Complexas**.

Período formal informado no PDF: **1º de setembro de 2026 a 31 de agosto de 2027**.

Observação: a etapa computacional, que exclui escrita acadêmica e avaliação humana e considera
somente o sistema que gera dados para análise posterior, foi fechada em
[`docs/lacunas_computacionais_escopo_ic.md`](lacunas_computacionais_escopo_ic.md).

## Conclusão executiva

O repositório já possui uma base computacional forte e cobre grande parte da aquisição,
processamento, cálculo de métricas e visualização. Entretanto, o escopo original ainda não
está concluído.

Após as melhorias de 4 de junho de 2026, as principais lacunas restantes estão no plano
acadêmico/metodológico, não na geração computacional dos dados:

1. análise científica dos padrões, além da geração de tabelas;
2. avaliação quantitativa e qualitativa formal;
3. documentação metodológica e reprodutibilidade experimental;
4. produtos acadêmicos previstos nas atividades A1 a A8.

Já foram implementados: centralidades de proximidade e autovetor, protocolo/auditoria de
comparabilidade, datasets municipais padronizados, análise descritiva topologia-função,
validação quantitativa das aproximações, comunidades nos datasets administrativos,
resiliência por comunidades, estatísticas agregadas de ataques aleatórios, mapa de arestas
críticas, manifesto experimental, CSV comparativo consolidado e índice composto de
vulnerabilidade viária, além da análise de pontes, articulações, gargalos estruturais e
redundância de rotas, com análise multiescala por células espaciais, robustez espacial por
bloqueios regionais, análise de hierarquia viária por classes OSM `highway` e morfologia
urbana por padrões espaciais da rede, além de eficiência estatística de rotas em múltiplos
pares origem-destino e similaridade estrutural entre cidades.
Também foram adicionadas detecção de subcentros topológicos, centralidade policêntrica,
exposição da rede a barreiras urbanas prováveis por baixa permeabilidade espacial e perfil de
escala da rede viária.

A análise histórica é uma expansão válida, mas deve ser usada somente após auditoria de
cobertura OSM, pois anos antigos podem refletir evolução do mapeamento, não evolução urbana.

## Matriz dos objetivos específicos

| Requisito explícito do PDF | Estado | Evidência atual | O que falta para concluir |
|---|---|---|---|
| Distribuição de graus | Implementado | CSV e gráfico log-log | Interpretar e comparar os padrões entre cidades |
| Coeficiente de aglomeração | Implementado parcialmente | Transitividade, clustering aproximado e estudo de sensibilidade | A validação mostrou instabilidade do clustering aproximado; justificar o indicador ou ampliar amostras |
| Comprimento médio de caminhos | Implementado | Estimativa por amostragem, em hops e metros, com validação | Interpretar resultados e limitações |
| Diâmetro da rede | Implementado | Estimativa por amostragem com validação | Interpretar resultados e documentar que não é diâmetro exato no grafo completo |
| Assortatividade | Implementado | Assortatividade por grau | Interpretar e comparar resultados |
| Centralidade de grau | Implementado | Ranking completo e resumo comparável | Interpretar resultados |
| Centralidade de intermediação | Implementado | Betweenness aproximada validada de nós e arestas; mapa de arestas críticas | Interpretar resultados |
| Centralidade de proximidade | Implementado | Closeness aproximada, ranking completo e validação | Interpretar resultados e manter parâmetros padronizados |
| Centralidade de autovetor | Implementado | Cálculo espectral, ranking completo e integração | Interpretar resultados |
| Resiliência por remoção de arestas | Implementado | Estratégias aleatória, dirigida e adaptativa; repetição aleatória com 5 sementes | Interpretar resultados |
| Resiliência por remoção de vértices | Implementado | Ataques aleatório, dirigido estático e adaptativo, curvas e rankings de remoção | Interpretar e comparar com a remoção de arestas |
| Comparação entre diferentes cidades | Implementado | Datasets administrativos padronizados, auditoria, comparador HTML e CSV consolidado | Interpretar padrões |
| Identificar padrões universais e especificidades locais | Ausente como resultado científico | Existem tabelas comparativas | Formular hipóteses, normalizar métricas e produzir análise/conclusões |
| Visualizações interativas | Implementado | Dashboards, mapas Folium, comunidades e arestas críticas | Interpretar resultados |
| Relação entre topologia e características funcionais | Implementado descritivamente | Grupos e correlações de Spearman para atributos OSM | Interpretar com cautela e incorporar outras fontes funcionais futuramente |

## Matriz das atividades A1 a A8

| Atividade | Estado atual | Observação |
|---|---|---|
| A1 - Estado da arte e estudo do OSMnx | Sem evidência organizada no repositório | Criar revisão estruturada, protocolo de busca e síntese dos trabalhos |
| A2 - Participação no encontro de IC | Ainda não aplicável | É atividade acadêmica futura, não uma funcionalidade de software |
| A3 - Estudo dos conceitos de Teoria dos Grafos | Parcial | Os conceitos aparecem no código, mas falta documentação teórica e justificativa metodológica |
| A4 - Relatório parcial | Ainda não aplicável | O gerador atual produz inventário técnico, não um relatório parcial acadêmico |
| A5 - Aplicação das métricas | Parcial avançado | Falta o fechamento analítico comparativo |
| A6 - Avaliação quantitativa e qualitativa | Ausente | Falta protocolo, perguntas de pesquisa, hipóteses, critérios e discussão |
| A7 - Artigo científico | Ainda não iniciado | Deve ser produzido após consolidar método e resultados |
| A8 - Relatório final | Ainda não aplicável | O Markdown atual é um relatório automático de artefatos, não o relatório científico final |

## Matriz dos resultados esperados

### Base estruturada, metadados e documentação

**Estado: parcial avançado.**

Já existem GraphML, metadados JSON, configurações YAML e saídas organizadas. Para completar:

- registrar versões de Python, OSMnx, NetworkX e demais dependências;
- registrar comando, parâmetros, semente, data e commit Git de cada experimento;
- criar dicionário de dados para atributos e métricas;
- padronizar metadados de todos os datasets;
- criar uma execução única e reproduzível do pipeline completo;
- detectar saídas desatualizadas em relação ao código.

Foi encontrado um exemplo concreto de inconsistência: o código estrutural atual grava métricas
ponderadas em metros e dados do grafo direcionado, mas os CSVs existentes das quatro cidades
estão em um formato anterior e não contêm esses campos.

### Caracterização estrutural em tabelas e gráficos

**Estado: parcial avançado.**

Os cálculos e artefatos existem, mas falta transformar os resultados em análise científica:
explicar significado, comparar cidades, discutir limitações e responder perguntas de pesquisa.

### Padrões recorrentes, regularidades e especificidades locais

**Estado: ausente como conclusão científica.**

O comparador atual coloca métricas lado a lado, mas não identifica formalmente padrões
universais. Para isso, é necessário:

- usar recortes comparáveis;
- normalizar métricas dependentes do tamanho;
- ampliar ou justificar a amostra de cidades;
- analisar dispersão, correlações e agrupamentos;
- discutir contexto urbano e limitações;
- evitar chamar um padrão de universal sem evidência suficiente.

### Mapeamento de elementos críticos

**Estado: parcial.**

Já há mapa de nós críticos por betweenness, ranking de arestas e mapa próprio de
arestas/vias críticas com nome, tipo, comprimento, ranking e score quando os atributos existem
no OSM. A parte computacional está coberta; falta a interpretação científica desses elementos.

### Códigos reprodutíveis e dashboards

**Estado: implementado parcialmente.**

Os dashboards foram regenerados para os quatro datasets administrativos com cobertura
experimental padronizada, incluindo comunidades, resiliência por arestas, vértices e
comunidades, estatísticas aleatórias agregadas, mapas e manifestos.

## Problemas metodológicos que precisam ser resolvidos

### 1. Recortes geográficos padronizados, com conjunto legado preservado

Os datasets originais usam caixas delimitadoras com dimensões diferentes e permanecem
exploratórios. O conjunto principal agora usa limites administrativos OSM para as quatro
cidades e foi classificado como comparável pela auditoria automática.

Ainda é necessário justificar formalmente essa escolha no texto científico e normalizar
métricas dependentes do tamanho do município.

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

### 4. Ataque aleatório com distribuição estatística básica

A etapa computacional agora repete ataques aleatórios com cinco sementes e gera média,
desvio-padrão, mínimo, máximo e curvas agregadas. Isso reduz o risco de interpretar um único
sorteio como característica estrutural da cidade. Intervalos de confiança formais podem ser
adicionados futuramente se a análise estatística exigir mais repetições.

### 5. Comparação padronizada disponível, interpretação ainda incompleta

Os quatro datasets administrativos usam a mesma data, parâmetros, protocolo de recorte,
métricas e formatos de saída. A comparação computacional está pronta e inclui indicadores
normalizados por área; ainda falta produzir a interpretação científica.

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
- detecção de subcentros e centralidade policêntrica;
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

1. Requisitos computacionais explícitos concluídos; manter testes adicionais de integração como melhoria de engenharia.

### Fase 2 - Tornar os experimentos cientificamente válidos

1. Protocolo padronizado de recorte das cidades implementado para os datasets administrativos.
2. Manifesto experimental JSON implementado.
3. Repetições estatísticas dos ataques aleatórios implementadas.
4. Estudo de sensibilidade das métricas aproximadas implementado.
5. Cidades administrativas reprocessadas com pipeline e parâmetros padronizados.

### Fase 3 - Responder ao objetivo científico

1. Formular perguntas de pesquisa e hipóteses.
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
