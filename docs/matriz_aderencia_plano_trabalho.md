# Matriz de aderência ao Plano de Trabalho da Iniciação Científica

**Fonte primária:** [`_Projeto_2026__Lucas_Soares.pdf`](../_Projeto_2026__Lucas_Soares.pdf),
conferido integral e visualmente em 18 de agosto de 2026. As páginas abaixo correspondem à
numeração impressa no documento, não à posição física no arquivo.

## Legenda

| Estado | Significado |
|---|---|
| **Atendido computacionalmente** | O repositório já implementa e testa a capacidade solicitada |
| **Atendido com ressalva** | A capacidade existe, mas depende de regeneração, interpretação, validação externa ou delimitação conceitual |
| **Pendente empírico** | Falta dado, desenho amostral, execução homogênea ou evidência para sustentar a conclusão |
| **Pendente acadêmico** | É uma atividade de pesquisa, escrita ou participação institucional, não uma funcionalidade de software |
| **Expansão exploratória** | Vai além do requisito literal e deve ser apresentada como hipótese ou complemento |

## Objetivo geral e resumo do plano

| Fonte no PDF | Exigência | Implementação/evidência | Estado | Lacuna remanescente |
|---|---|---|---|---|
| Resumo, p. 1; Objetivos, p. 3 | Caracterizar a estrutura topológica de redes viárias urbanas brasileiras | [`metrics_structural.py`](../src/ic/metrics_structural.py), [`centrality.py`](../src/ic/centrality.py), [`communities.py`](../src/ic/communities.py), inventários e relatórios | Atendido com ressalva | A implementação é aplicável a novas cidades, mas a evidência atual cobre somente quatro municípios paulistas |
| Resumo, p. 1; Objetivos, p. 3 | Relacionar propriedades topológicas a características funcionais | [`functional_relations.py`](../src/ic/functional_relations.py), hierarquia e atributos OSM | Atendido com ressalva | São associações com tags OSM; não há tráfego, demanda OD, empregos ou tempos observados |
| Resumo, p. 1; Resultado Esperado, p. 5 | Identificar padrões universais e especificidades locais | Comparador, similaridade, métricas normalizadas e gates de comparabilidade | Pendente empírico | Quatro casos regionais não sustentam generalização nacional ou universal |
| Justificativa, p. 2 | Detectar nós/arestas cuja falha reduz conectividade e eficiência | Centralidades, ataques, gargalos, vulnerabilidade e mapas | Atendido com ressalva | Falta interpretar resultados regenerados e distinguir criticidade topológica de impacto real no tráfego |
| Justificativa, p. 2 | Subsidiar planejamento e priorização de recursos | Rankings, mapas e dashboards exploratórios | Pendente empírico | Uso decisório exige validação externa, análise de sensibilidade e contexto urbano |

## Objetivos específicos — Seção 3, página 3

| Nº | Requisito literal do plano | Implementação/evidência | Aprimoramento realizado | Estado | Próximo passo |
|---:|---|---|---|---|---|
| 1.1 | Distribuição de graus | `degree_distribution.csv`, figura log-log e [`metrics_structural.py`](../src/ic/metrics_structural.py) | Contratos de representação e testes numéricos | Atendido computacionalmente | Regenerar e interpretar entre cidades |
| 1.2 | Coeficiente de aglomeração | Clustering/transitividade em [`metrics_structural.py`](../src/ic/metrics_structural.py) | Validação de aproximações e limitação documentada | Atendido com ressalva | Aumentar amostras ou justificar o indicador; aproximação mostrou maior instabilidade |
| 1.3 | Comprimento médio de caminhos | [`paths_accessibility.py`](../src/ic/paths_accessibility.py) e métricas estruturais | Separação entre hops e metros; amostragem validada | Atendido com ressalva | Declarar que é estimativa e relatar incerteza/limites |
| 1.4 | Diâmetro da rede | Estimativa de diâmetro na pipeline estrutural | Testes e linguagem corrigida para “estimado” | Atendido com ressalva | Não apresentar como diâmetro exato do grafo completo |
| 1.5 | Assortatividade | Assortatividade por grau | Contrato e saída padronizados | Atendido computacionalmente | Interpretar após os gates |
| 2.1 | Centralidade de grau | `node_centralities.csv` e `centrality_rankings.csv` | Ranking completo e schema padronizado | Atendido computacionalmente | Interpretar os pontos críticos |
| 2.2 | Centralidade de intermediação | Nós e arestas em [`centrality.py`](../src/ic/centrality.py) | `edge_centralities.csv` completo; consumidores rejeitam cobertura parcial | Atendido computacionalmente | Regenerar outputs legados e módulos dependentes |
| 2.3 | Centralidade de proximidade | `closeness_approx` | Correção do viés nos landmarks e testes de amostra parcial | Atendido com ressalva | Manter parâmetros comuns e relatar erro aproximado |
| 2.4 | Centralidade de autovetor | Ranking espectral | Integração ao ranking completo e testes | Atendido computacionalmente | Interpretar com cautela em representação não dirigida |
| 2.5 | Identificar vias e interseções críticas | Mapas, rankings, vulnerabilidade e gargalos | Separação entre centralidade pura e score composto | Atendido com ressalva | Validar criticidade funcional com dados externos se houver alegação operacional |
| 3.1 | Remoção de arestas | [`resilience.py`](../src/ic/resilience.py) | Ataques aleatório, dirigido e adaptativo; estatística agregada | Atendido com ressalva | Regenerar e interpretar; chamar de robustez estrutural |
| 3.2 | Remoção de vértices | [`node_resilience.py`](../src/ic/node_resilience.py) | Ataques aleatório, dirigido e adaptativo; estatística agregada | Atendido com ressalva | Não comparar AUC de nós e arestas sem explicar populações distintas |
| 3.3 | “Resiliência” da rede | Curvas de LCC e eficiência | Constructo delimitado como degradação/robustez sob remoção | Atendido com ressalva | Modelar recuperação temporal para usar resiliência em sentido forte |
| 4.1 | Comparar propriedades entre cidades | [`compare_report.py`](../src/ic/compare_report.py) e auditoria científica | Verificação *fail-closed* de snapshot, recorte, código, sementes e produtos | Atendido com ressalva | Regenerar os quatro casos e alcançar `confirmada` |
| 4.2 | Identificar padrões universais | Similaridade exploratória e métricas comuns | Modo principal exige ao menos oito datasets e perfil reduzido | Pendente empírico | Ampliar amostra, regiões e desenho antes de generalizar |
| 4.3 | Identificar características específicas | Tabelas comparativas, mapas e descritores | Separação explícita entre comparação exploratória e científica | Pendente empírico | Integrar contexto urbano e interpretar resultados liberados |
| 5.1 | Visualizações interativas das redes | Dashboards, Folium e Kepler.gl | Padronização, mapas temáticos e textos de limitação | Atendido computacionalmente | Atualizar com a nova execução homogênea |
| 5.2 | Facilitar interpretação dos resultados | Relatórios Markdown/HTML, figuras e dicionário | Síntese de robustez e documentação explicativa | Atendido com ressalva | Produzir narrativa científica, não apenas apresentação automática |

## Atividades — Seção 4, páginas 4–5

| Atividade | Exigência no PDF | Evidência atual | Estado | O que falta |
|---|---|---|---|---|
| A1 | Estado da arte, desafios de grafos viários, trabalhos em Cidades Inteligentes e estudo do OSMnx | [`revisao_bibliografica_projeto_ic.md`](revisao_bibliografica_projeto_ic.md), [`referencias_ic.bib`](referencias_ic.bib), protocolos e código de download | Atendido com ressalva | Consolidar método de busca, critérios de seleção e síntese no texto acadêmico |
| A2 | Participação no Encontro de IC/Desenvolvimento Tecnológico | Não é um artefato de software | Pendente acadêmico | Participar e registrar a atividade no período institucional |
| A3 | Estudo de grau, caminhos, centralidade, conectividade, clustering e modularidade | Módulos estruturais, centralidades, comunidades, testes e documentação | Atendido com ressalva | Transformar conhecimento implementado em fundamentação teórica concisa no relatório |
| A4 | Entrega do relatório parcial | Relatórios técnicos automáticos e esta documentação fornecem insumos | Pendente acadêmico | Redigir o relatório parcial no formato institucional, com resultados válidos do período |
| A5 | Aplicar e analisar grau, centralidades, caminhos, clustering, densidade e modularidade | Pipeline computacional ampla e 104 testes | Atendido com ressalva | Regenerar, analisar e discutir; cálculo sozinho não encerra A5 |
| A6 | Avaliação quantitativa e qualitativa da solução | Estatística de robustez, validação de aproximações, integridade e comparabilidade | Atendido com ressalva | Definir hipóteses, resultados primários, critérios qualitativos e discussão contextual |
| A7 | Escrita e divulgação de artigo científico | Bibliografia, pipeline e futuros resultados são insumos | Pendente acadêmico | Escrever após a liberação e interpretação dos resultados |
| A8 | Entrega do relatório final | Relatório técnico automático não equivale ao relatório de IC | Pendente acadêmico | Integrar método, resultados, discussão, limitações e conclusão no formato institucional |

## Resultados esperados — Seção 5, página 5

| Resultado esperado | Evidência no repositório | Estado | Lacuna remanescente |
|---|---|---|---|
| Base estruturada de grafos de cidades | GraphML bruto/limpo, YAML, metadados e diretórios por dataset | Atendido com ressalva | Ampliar/diversificar a amostra e regenerar o conjunto principal |
| Metadados padronizados | [`download.py`](../src/ic/download.py), manifesto v2 e dicionário | Atendido para novas execuções | Outputs legados não recebem proveniência retroativamente |
| Documentação de extração, modelagem e processamento | README, comandos, protocolos, dicionário e registro de aprimoramentos | Atendido com ressalva | Manter sincronização e incorporar versão final ao relatório acadêmico |
| Reprodutibilidade dos experimentos | [`provenance.py`](../src/ic/provenance.py), lock e CI | Atendido com ressalva | Regenerar; lock ainda não possui hashes e ambientes virtuais continuam versionados |
| Caracterização estrutural em tabelas e figuras | Métricas, inventários, imagens e dashboards | Atendido computacionalmente | Interpretar os resultados validados |
| Comparação quantitativa entre cidades | Comparador e auditoria científica | Atendido com ressalva | Estado atual é `nao_comprovada`; nova execução obrigatória |
| Conectividade, centralidade, eficiência e modularidade | Módulos estruturais, centralidade, caminhos e comunidades | Atendido computacionalmente | Consolidar perguntas e estimandos primários |
| Padrões recorrentes e regularidades brasileiras | Similaridade e comparações exploratórias | Pendente empírico | Amostra nacional/diversa, hipóteses, incerteza e modelos nulos |
| Especificidades regionais e históricas | Comparação, auditoria histórica e mapas | Pendente empírico | Integrar contexto externo e validar qualidade histórica do OSM |
| Mapeamento de vias/interseções críticas | Mapas de centralidade, vulnerabilidade e gargalos | Atendido com ressalva | Explicar a definição de criticidade e evitar inferência de tráfego real |
| Apoio a vulnerabilidade e planejamento | Cenários de remoção, rankings e visualizações | Pendente empírico | Validar externamente antes de recomendação operacional |
| Código reprodutível | Pacote Python, CLI, testes, CI e lock | Atendido com ressalva | Executar o experimento final e versionar somente fontes/artefatos necessários |
| Painéis interativos para públicos técnicos e não técnicos | Dashboards e mapas HTML | Atendido computacionalmente | Regenerar com dados liberados e adaptar a narrativa ao público |

## Expansões não exigidas literalmente, mas coerentes

| Módulo | Vínculo com o plano | Classificação |
|---|---|---|
| Robustez entre/dentro de comunidades | Aprofunda modularidade e remoção de elementos | Expansão exploratória |
| Índice de vulnerabilidade | Combina sinais de criticidade previstos na justificativa | Expansão exploratória |
| Pontes, articulações e gargalos | Identifica falhas estruturais críticas | Expansão exploratória |
| Redundância de rotas | Explora eficiência e alternativas após interrupção | Expansão exploratória |
| Robustez espacial | Examina remoções regionalizadas | Expansão exploratória |
| Hierarquia viária | Relaciona topologia a classes OSM | Expansão exploratória |
| Morfologia e orientação | Descreve padrões espaciais da rede | Expansão exploratória |
| Pares OD amostrados | Resume eficiência entre pares de nós | Expansão exploratória |
| Candidatos a subcentros | Localiza concentração topológica | Expansão exploratória |
| Barreiras prováveis | Examina permeabilidade espacial | Expansão exploratória |
| Perfil multiescalar | Avalia sensibilidade agregada à grade | Expansão exploratória |
| Auditoria histórica | Controla viés de mapeamento do OSM | Expansão exploratória |

## Controles científicos acrescentados ao plano

Esses itens não são objetivos separados no PDF, mas tornam os objetivos executáveis com rigor.

| Controle | Por que foi necessário | Evidência |
|---|---|---|
| Proveniência por comando | Saber exatamente como cada artefato foi produzido | [`provenance.py`](../src/ic/provenance.py) |
| Manifesto experimental v2 | Registrar entradas, saídas e hashes sem auto-invalidação | [`final_report.py`](../src/ic/final_report.py) |
| Gate de integridade | Impedir uso de arquivo faltante, antigo, misturado ou adulterado | [`artifact_integrity.py`](../src/ic/artifact_integrity.py) |
| Gate de comparabilidade | Impedir comparação sem equivalência temporal, geométrica e experimental | [`scientific_comparability.py`](../src/ic/scientific_comparability.py) |
| Auditoria da representação | Quantificar o efeito de direção, multiplicidade e colapso | [`representation_audit.py`](../src/ic/representation_audit.py) |
| Incerteza dos ataques | Separar resultado médio da variação aleatória | [`random_resilience_stats.py`](../src/ic/random_resilience_stats.py) |
| Contrato de centralidade completa | Impedir ranking truncado em cálculos downstream | [`centrality.py`](../src/ic/centrality.py) |
| Salvaguarda de amostra pequena | Evitar PCA/clustering apresentados como conclusão com n=4 | [`city_similarity.py`](../src/ic/city_similarity.py) |
| Testes e CI | Detectar regressões e contratos quebrados | [`tests`](../tests), [workflow](../.github/workflows/quality.yml) |

## Inconsistências e decisões que devem ser levadas ao orientador

1. **Cronograma:** capa e texto indicam 01/09/2026–31/08/2027, mas a Tabela 6.1 está rotulada
   2025–2026. A correção provável é 2026–2027.
2. **Resiliência:** o experimento atual mede robustez estrutural sob remoção; recuperação temporal
   não está modelada.
3. **Alcance nacional:** quatro municípios paulistas não sustentam, sozinhos, conclusão sobre a
   rede viária urbana brasileira.
4. **Função do transporte:** tags OSM descrevem a infraestrutura cadastrada; não medem tráfego,
   demanda ou desempenho observado.
5. **Recorte:** limites administrativos são reproduzíveis, mas podem incluir área rural e não são
   equivalentes à mancha urbanizada.
6. **Outputs antigos:** sua existência não comprova compatibilidade com o protocolo atual; o estado
   formal dos quatro datasets é `nao_comprovada`.

## Sequência objetiva para fechar a próxima etapa

1. aprovar com o orientador o enquadramento, as hipóteses, a amostra e o recorte;
2. corrigir o ano do cronograma no plano;
3. congelar o snapshot OSM e a configuração comum;
4. regenerar todos os datasets com a mesma versão do código;
5. executar integridade e comparabilidade até obter liberação;
6. realizar a análise quantitativa/qualitativa e documentar limitações;
7. ampliar a amostra antes de qualquer alegação nacional;
8. produzir relatório parcial, artigo, apresentação e relatório final no calendário previsto.
