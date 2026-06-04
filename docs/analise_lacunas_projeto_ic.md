# Auditoria de aderência ao Plano de Trabalho da IC

Data da auditoria: 4 de junho de 2026.

Documento de referência: `_Projeto_2026__Lucas_Soares.pdf`, plano **Análise Estrutural da Rede
Viária Urbana Brasileira Utilizando Métricas de Redes Complexas**.

Período formal informado no PDF: **1º de setembro de 2026 a 31 de agosto de 2027**.

## Conclusão executiva

O repositório já possui uma base computacional forte e cobre grande parte da aquisição,
processamento, cálculo de métricas e visualização. Entretanto, o escopo original ainda não
está concluído.

As principais lacunas obrigatórias são:

1. centralidades de proximidade e autovetor;
2. resiliência por remoção de vértices;
3. protocolo comparativo padronizado entre cidades;
4. análise científica dos padrões, além da geração de tabelas;
5. relação entre propriedades topológicas e características funcionais;
6. avaliação quantitativa e qualitativa formal;
7. documentação metodológica e reprodutibilidade experimental;
8. produtos acadêmicos previstos nas atividades A1 a A8.

A análise histórica é uma expansão válida, mas não deve receber prioridade até que esses itens
do escopo original estejam completos.

## Matriz dos objetivos específicos

| Requisito explícito do PDF | Estado | Evidência atual | O que falta para concluir |
|---|---|---|---|
| Distribuição de graus | Implementado | CSV e gráfico log-log | Interpretar e comparar os padrões entre cidades |
| Coeficiente de aglomeração | Implementado parcialmente | Transitividade e clustering aproximado | Validar a aproximação e justificar qual indicador será usado |
| Comprimento médio de caminhos | Implementado parcialmente | Estimativa por amostragem, em hops e metros | Estudo de sensibilidade, incerteza e padronização entre cidades |
| Diâmetro da rede | Implementado parcialmente | Estimativa por amostragem | Validar erro/estabilidade e documentar que não é diâmetro exato |
| Assortatividade | Implementado | Assortatividade por grau | Interpretar e comparar resultados |
| Centralidade de grau | Implementado | Calculada para nós selecionados | Salvar ranking completo ou resumo comparável |
| Centralidade de intermediação | Implementado parcialmente | Betweenness aproximada de nós e arestas | Validar amostragem e mapear também vias críticas com atributos viários |
| Centralidade de proximidade | Ausente | Não calculada | Implementar, documentar e integrar aos relatórios/mapas |
| Centralidade de autovetor | Ausente | Não calculada | Implementar, documentar e integrar aos relatórios/mapas |
| Resiliência por remoção de arestas | Implementado parcialmente | Estratégias aleatória, dirigida e adaptativa | Repetir ataques aleatórios e quantificar incerteza |
| Resiliência por remoção de vértices | Ausente | Não há remoção de nós | Implementar ataques aleatórios e dirigidos, curvas e mapas |
| Comparação entre diferentes cidades | Implementado parcialmente | Comparador HTML para Campinas, Jundiaí, Sorocaba e Valinhos | Padronizar recortes, completar experimentos e interpretar padrões |
| Identificar padrões universais e especificidades locais | Ausente como resultado científico | Existem tabelas comparativas | Formular hipóteses, normalizar métricas e produzir análise/conclusões |
| Visualizações interativas | Implementado | Dashboards e mapas Folium | Melhorar consistência e garantir cobertura completa em todas as cidades |
| Relação entre topologia e características funcionais | Ausente/parcial | Inventário possui `highway`, `maxspeed`, `lanes`, `oneway` e `surface` | Executar análises relacionando esses atributos às métricas topológicas |

## Matriz das atividades A1 a A8

| Atividade | Estado atual | Observação |
|---|---|---|
| A1 - Estado da arte e estudo do OSMnx | Sem evidência organizada no repositório | Criar revisão estruturada, protocolo de busca e síntese dos trabalhos |
| A2 - Participação no encontro de IC | Ainda não aplicável | É atividade acadêmica futura, não uma funcionalidade de software |
| A3 - Estudo dos conceitos de Teoria dos Grafos | Parcial | Os conceitos aparecem no código, mas falta documentação teórica e justificativa metodológica |
| A4 - Relatório parcial | Ainda não aplicável | O gerador atual produz inventário técnico, não um relatório parcial acadêmico |
| A5 - Aplicação das métricas | Parcial avançado | Faltam proximidade, autovetor, remoção de vértices e fechamento comparativo |
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

Já há mapa de nós críticos por betweenness e rankings de arestas. Falta:

- mapear visualmente as arestas/vias críticas;
- incluir nome, tipo e atributos das vias;
- incorporar criticidade por remoção de vértices;
- comparar criticidade entre diferentes centralidades;
- explicar por que cada elemento é crítico e qual impacto sua remoção produz.

### Códigos reprodutíveis e dashboards

**Estado: implementado parcialmente.**

Os dashboards existem, mas a cobertura experimental é desigual. Campinas possui análises mais
completas; Jundiaí, Sorocaba e Valinhos não possuem, por exemplo, resiliência adaptativa nem
resiliência interna por comunidade. Antes da comparação final, todas as cidades devem passar
pelo mesmo pipeline e pelos mesmos parâmetros.

## Problemas metodológicos que precisam ser resolvidos

### 1. Recortes geográficos não padronizados

As quatro cidades usam caixas delimitadoras com dimensões diferentes. Isso pode incluir áreas
fora do município e tornar diferenças de tamanho, densidade e caminhos consequência do
recorte, não da estrutura urbana.

É necessário escolher e justificar um protocolo:

- limites administrativos oficiais/OSM; ou
- recortes de mesma área; ou
- análise em múltiplas escalas.

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

### 3. Aproximações sem validação

Betweenness, clustering, caminhos, diâmetro e eficiência usam amostragens. Falta executar um
estudo de sensibilidade, variando o número de amostras e medindo estabilidade dos rankings,
valores e tempo de execução.

### 4. Ataque aleatório sem distribuição estatística

Uma execução com uma semente não representa adequadamente um ataque aleatório. O resultado
deve usar múltiplas repetições, média, desvio-padrão e intervalo de confiança.

### 5. Comparação incompleta entre cidades

Campinas possui resultados que ainda não existem para as demais cidades. Uma comparação
final só é válida quando todos os datasets usam:

- mesma versão dos dados ou datas explicitamente controladas;
- mesmos parâmetros;
- mesmas estratégias;
- mesmo protocolo de recorte;
- mesmas métricas e formatos de saída.

### 6. Cálculo não equivale a análise

Os relatórios atuais consolidam valores e artefatos, mas quase não apresentam interpretação,
discussão, hipóteses, limitações ou conclusões. O plano exige **calcular e analisar**, avaliar
quantitativa e qualitativamente e identificar padrões.

## Expansões já implementadas fora do núcleo obrigatório

Estas expansões são úteis e devem ser preservadas, mas não devem bloquear o fechamento do
escopo original:

- análise histórica de Campinas;
- resiliência entre comunidades;
- resiliência interna de cada comunidade;
- inventário de superfície, faixas, velocidade e mão única;
- exportação para Kepler.gl;
- rotas multimodais;
- comparadores visuais extensos.

Algumas dessas expansões podem ajudar a cumprir o escopo. Por exemplo, os atributos viários
do inventário podem ser usados para estabelecer relações entre topologia e características
funcionais.

## Ordem recomendada para concluir o escopo original

### Fase 1 - Completar os requisitos explícitos

1. Implementar centralidades de proximidade e autovetor.
2. Implementar resiliência por remoção de vértices.
3. Integrar as novas métricas ao inventário, mapas, relatório e dashboard.
4. Criar testes unitários e de integração para essas etapas.

### Fase 2 - Tornar os experimentos cientificamente válidos

1. Definir protocolo padronizado de recorte das cidades.
2. Criar manifesto completo de cada experimento.
3. Implementar repetições estatísticas dos ataques aleatórios.
4. Executar estudo de sensibilidade das métricas aproximadas.
5. Reprocessar todas as cidades com o mesmo pipeline e parâmetros.

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
