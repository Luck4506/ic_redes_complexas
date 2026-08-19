# Registro consolidado de aprimoramentos — 18 de agosto de 2026

## Resultado executivo

Esta revisão transformou o projeto de uma coleção ampla de análises em uma pipeline com contratos
explícitos, rastreabilidade por execução e bloqueios científicos *fail-closed*. A suíte automatizada
passou de 29 para **104 testes**, todos aprovados. As quatro redes administrativas receberam uma
auditoria real de representação, e os outputs existentes foram submetidos a gates de integridade e
comparabilidade.

O principal resultado não é uma nova conclusão urbana: é tornar impossível confundir arquivo
existente com evidência válida. Os outputs legados continuam disponíveis, mas os gates atuais os
classificam corretamente como **não liberados para comparação científica** até uma regeneração
completa e homogênea.

## Conferência com o projeto-base

O arquivo [`_Projeto_2026__Lucas_Soares.pdf`](../_Projeto_2026__Lucas_Soares.pdf) foi anexado ao
repositório e conferido integral e visualmente em 18 de agosto de 2026. A revisão que antecedeu
esse anexo foi inicialmente orientada pela documentação local; depois, objetivos, atividades A1–A8
e resultados esperados foram confrontados literalmente com o plano na
[`matriz_aderencia_plano_trabalho.md`](matriz_aderencia_plano_trabalho.md).

O escopo confirmado é a análise da estrutura topológica de redes viárias, com métricas de grau,
clustering, caminhos, diâmetro, assortatividade, centralidades, remoção de arestas/vértices,
comparação entre cidades e visualizações. Comunidades e modularidade aparecem também na atividade
A3/A5. O estudo não observa, por si só, tráfego, demanda OD, recuperação temporal ou desempenho
socioeconômico.

A conferência identificou uma inconsistência editorial no próprio plano: capa e texto informam o
período 2026–2027, enquanto o cabeçalho da Tabela 6.1 mostra 2025–2026.

## Diagnóstico inicial registrado

- 29 testes automatizados aprovados no início da revisão.
- 820 CSVs inspecionados: 2.883.357 linhas e 16.736.682 células, sem erro de parsing, cabeçalho
  duplicado, linha irregular ou duplicata exata detectada.
- 731.895 valores ausentes, concentrados principalmente em atributos OSM opcionais; ausência não
  foi convertida automaticamente em zero.
- Quatro municípios vizinhos do interior paulista; alcance adequado a estudo de caso, não a uma
  afirmação sobre toda a rede viária urbana brasileira.
- Outputs e manifestos produzidos em datas diferentes, sem proveniência suficiente por etapa.
- Ambientes virtuais versionados somam 19.839 arquivos no índice Git, um passivo de manutenção que
  foi documentado, mas não removido de forma destrutiva nesta revisão.
- O lock fixa versões, mas ainda não traz hashes dos pacotes; isso melhora repetibilidade de
  runtime, sem prometer reprodução bit a bit ou proteção completa da cadeia de fornecimento.

## Melhorias implementadas

### 1. Enquadramento científico e linguagem

- O constructo principal passou a ser chamado de **robustez estrutural sob remoção**. “Resiliência”
  foi mantida apenas em nomes legados de comandos/arquivos ou com qualificação explícita.
- Subcentros, morfologia, multiescala, bloqueios espaciais e relações funcionais foram reclassificados
  como proxies ou cenários exploratórios, com limites escritos nos relatórios.
- A amostra foi enquadrada como estudo de caso de quatro municípios paulistas.
- Afirmações de comparação confirmada, padrões universais, demanda OD “real” e validação funcional
  foram removidas ou qualificadas.

### 2. Estatística de robustez

- Ataques aleatórios usam 30 repetições por padrão.
- Sementes de ataque e de avaliação foram separadas para não misturar duas fontes de erro.
- Foram adicionados média, desvio amostral, erro-padrão, mediana, quantis, mínimo/máximo e IC 95%
  por bootstrap, além de resumos de AUC.
- Uma execução única agora recebe incerteza `NA`; desvio zero não é mais usado como falsa precisão.
- Curvas são validadas quanto a baseline, domínio, finitude, monotonicidade e coorte comum.
- A síntese exige a matriz completa de modalidades e estratégias; incompletude só é aceita por
  liberação exploratória explícita.
- Checkpoints pequenos, inclusive 1%, agora produzem figuras válidas em vez de referências HTML
  quebradas.
- Checkpoints fracionários preservam precisão nos nomes (`1p1pct`, `1p4pct`) e o HTML deriva suas
  colunas da lista solicitada, sem colisões nem cabeçalhos fixos em 5%/10%/15%.
- LCCs comunitárias absolutas aceitam baseline em `(0,1]` quando o metagrafo filtrado já começa
  desconexo; métricas retidas e LCCs de arestas/vértices continuam exigindo baseline unitário.

### 3. Centralidades e contratos downstream

- Foi criado `edge_centralities.csv` com cobertura completa; `top_edges.csv` permanece apenas como
  ranking de apresentação.
- Vulnerabilidade, gargalos e relações funcionais passaram a exigir cobertura integral e falhar
  quando há arestas ausentes, extras, duplicadas ou não finitas.
- O estimador aproximado de closeness foi corrigido para não mudar a definição nos próprios
  landmarks; foram incluídos testes de amostra parcial.
- A maior componente ponderada por nós foi corrigida na robustez de comunidades.

### 4. Representação e extensão viária

- Nova auditoria compara `MultiDiGraph`, `MultiGraph`, `DiGraph` e `Graph`, em raw e clean.
- São quantificadas perdas de nós/arestas, componentes, reciprocidade, loops, paralelas, mão única,
  comprimento inválido e estabilidade de rankings.
- Comprimento dirigido de roteamento foi separado de comprimento físico colapsado. A densidade
  urbana usa a proxy física, evitando duplicar automaticamente os dois sentidos de uma rua.
- Comprimentos inválidos passaram a falhar explicitamente em vez de contaminar somas.
- Caminhos e artefatos agora inferem `network_type` do metadado; o pipeline deixa de pressupor
  silenciosamente `drive` para redes `walk`, `bike` ou `all`.

### 5. Proveniência e aquisição OSM

- Cada comando registra JSONL com argv real, parâmetros resolvidos, timestamps, duração, versões,
  commit/branch, estado sujo, hash do diff, entradas e artefatos criados/modificados.
- O hash do estado Git incorpora conteúdo de arquivos não rastreados, não apenas seus nomes.
- A gravação é idempotente por `run_id`, usa append com lock e preserva o erro original caso o log
  de proveniência também falhe.
- Uma retomada após falha parcial entre o log global e o do dataset reutiliza exatamente o mesmo
  registro, inclusive timestamps; erros de parsing guardam a mensagem útil e o código de saída.
- A resolução de dataset histórico foi unificada entre download e proveniência.
- `historical-audit` inclui a referência e os históricos nos fingerprints; `artifact-integrity`
  iniciado apenas por manifesto infere o dataset e fingerprinta o manifesto auditado.
- Metadados de download incluem início/fim UTC, modo `historical` ou `live_unfrozen`, timestamp,
  configuração efetiva, hash do YAML, OSMnx, CRS e identidade canônica do limite.
- Recortes `place` usam relação/geometria quando disponíveis; bbox/radius recebem fingerprint
  canônico de seus parâmetros, permitindo auditoria sem exigir uma relação OSM inexistente.
- O manifesto v2 exclui o log mutável de proveniência do conjunto autoritativo, impedindo que se
  invalide no próprio encerramento do comando.

### 6. Gates de qualidade

- Nova auditoria de integridade verifica existência, schema, linhas mínimas, frescor, dependências,
  hashes, manifesto, outputs extras e mistura de dataset.
- `WARN` e `FAIL` bloqueiam uso downstream; a CLI retorna código de falha, adequado a automação/CI.
- Auditorias parciais recebem nomes por escopo e não sobrescrevem a auditoria completa. Um `PASS`
  parcial certifica apenas as etapas listadas.
- Hash SHA-256 não tem limite por padrão; um limite opcional produz `WARN`, nunca liberação tácita.
- Nova auditoria científica separa perfil científico e exploratório e usa apenas três estados:
  `confirmada`, `nao_comprovada` e `incomparavel`.
- A comparação exige snapshot OSM, identidade do limite, parâmetros, sementes, código, hashes e
  matriz de produtos. Evidência ausente permanece não comprovada.

### 7. Similaridade, espaço e amostragem

- Similaridade entre cidades passou a usar um perfil teórico reduzido; por padrão exige ao menos
  oito datasets. Quatro casos só rodam com liberação exploratória explícita.
- Redundâncias e complementos artificiais de features foram retirados do perfil principal.
- A amostra espacial usada para eficiência foi desacoplada do ranking de impacto na LCC.
- Os módulos de subcentros, morfologia e escala agora expõem sua natureza heurística e o risco de
  MAUP, em vez de produzir uma validação urbana implícita.

### 8. Engenharia, testes e documentação

- O piso de Python foi alinhado ao ambiente realmente suportado: Python 3.11+, com CI em 3.12.
- Foi adicionado lock de dependências e workflow de integração contínua.
- Suíte ampliada para 104 testes: unidade, regressão, propriedades, contratos CSV, gates CLI,
  proveniência, download, representação, robustez, manifesto e tipos de rede.
- README, comandos, protocolo comparativo, dicionário de dados, apresentações, matriz de lacunas,
  revisão bibliográfica e bibliografia foram revisados em conjunto.

## Mapa de implementação por arquivo

| Frente | Arquivos principais |
|---|---|
| Aquisição, identidade e caminhos | `src/ic/download.py`, `src/ic/io_utils.py`, `src/ic/preprocess.py` |
| Proveniência e manifesto | `src/ic/provenance.py`, `src/ic/final_report.py`, `src/ic/cli.py` |
| Gates | `src/ic/artifact_integrity.py`, `src/ic/scientific_comparability.py`, `src/ic/comparison_protocol.py` |
| Representação | `src/ic/representation_audit.py`, `src/ic/metric_graphs.py`, `src/ic/graph_inventory.py` |
| Centralidades e consumidores | `src/ic/centrality.py`, `src/ic/vulnerability_index.py`, `src/ic/structural_bottlenecks.py`, `src/ic/functional_relations.py` |
| Robustez estatística | `src/ic/resilience.py`, `src/ic/node_resilience.py`, `src/ic/random_resilience_stats.py`, `src/ic/robustness_summary.py` |
| Comunidades | `src/ic/communities.py`, `src/ic/community_resilience.py`, `src/ic/intra_community_resilience.py` |
| Espaço e proxies urbanos | `src/ic/spatial_robustness.py`, `src/ic/spatial_multiscale.py`, `src/ic/urban_morphology.py`, `src/ic/subcenters.py`, `src/ic/network_scale_profile.py` |
| Comparação e apresentação | `src/ic/city_similarity.py`, `src/ic/compare_report.py`, `src/ic/html_report.py`, `src/ic/kepler_export.py`, `src/ic/plot_graph.py` |
| Outros módulos propagados | `src/ic/approximation_validation.py`, `src/ic/historical_quality.py`, `src/ic/od_efficiency.py`, `src/ic/paths_accessibility.py`, `src/ic/road_hierarchy.py`, `src/ic/route_redundancy.py`, `src/ic/urban_barriers.py` |
| Testes | `tests/test_*` para precisão, regressões, proveniência, gates, download, representação, robustez, manifesto, CLI e tipos de rede |
| Ambiente e CI | `pyproject.toml`, `requirements.txt`, `requirements-lock.txt`, `.github/workflows/quality.yml`, `.gitignore` |
| Documentação | `readme.md`, `config/comandos.md`, `docs/*.md`, `docs/referencias_ic.bib`, apresentações e resumo de atividades |

## Evidência empírica nova: sensibilidade à representação

Resultados dos grafos raw; “físico menor” compara a extensão colapsada com a dirigida. As duas
últimas colunas comparam `MultiDiGraph` e `Graph` no grafo clean.

| Dataset | Nós raw | Arestas raw | Perda de nós clean | Perda de arestas clean | Extensão dirigida (km) | Proxy física (km) | Físico menor | Spearman grau / top-20 | Spearman betweenness / top-20 |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| Campinas | 32.801 | 81.277 | 1,33% | 1,13% | 9.058,2 | 5.316,5 | 41,31% | 0,601 / 0,00 | 0,828 / 0,70 |
| Jundiaí | 11.785 | 25.146 | 0,83% | 0,58% | 3.419,7 | 2.030,6 | 40,62% | 0,672 / 0,25 | 0,870 / 0,15 |
| Sorocaba | 17.184 | 39.690 | 5,16% | 3,56% | 4.361,5 | 2.618,0 | 39,98% | 0,618 / 0,00 | 0,839 / 0,25 |
| Valinhos | 4.040 | 9.465 | 4,50% | 4,17% | 1.305,8 | 749,3 | 42,62% | 0,620 / 0,10 | 0,891 / 0,40 |

Interpretação: a representação não é um detalhe neutro. O colapso reduz a extensão em cerca de
40%–43%, e a sobreposição top-20 de grau chega a zero em Campinas e Sorocaba. Conclusões sobre
densidade e nós “mais importantes” precisam declarar a representação usada.

## Estado dos outputs existentes após os novos gates

### Comparabilidade científica

| Dataset | Estado | Critérios confirmados | Pendentes | Artefatos válidos | Com proveniência |
|---|---|---:|---:|---:|---:|
| Campinas | `nao_comprovada` | 28/39 | 11 | 10/10 | 2/10 |
| Jundiaí | `nao_comprovada` | 28/39 | 11 | 10/10 | 2/10 |
| Sorocaba | `nao_comprovada` | 28/39 | 11 | 10/10 | 2/10 |
| Valinhos | `nao_comprovada` | 28/39 | 11 | 10/10 | 2/10 |

Todos os seis pares ficaram `nao_comprovada`: 7/11 critérios pareados foram confirmados e quatro
permaneceram pendentes — elegibilidade de cada dataset, equivalência do snapshot OSM e identidade
do limite. Esses resultados estão em `outputs/comparisons/scientific_comparability_report.txt`.

### Integridade completa

| Dataset | PASS | WARN | FAIL | Estado |
|---|---:|---:|---:|---|
| Campinas | 2.213 | 0 | 34 | bloqueado |
| Jundiaí | 2.208 | 0 | 34 | bloqueado |
| Sorocaba | 2.208 | 0 | 34 | bloqueado |
| Valinhos | 2.209 | 0 | 33 | bloqueado |

As falhas principais são: `edge_centralities.csv` ainda ausente nos outputs legados, dependentes
antigos, artefatos anteriores às entradas, arquivos alterados depois do manifesto e produtos novos
fora do manifesto antigo. A auditoria isolada de representação passou nos quatro datasets; isso
certifica somente essa etapa. Em cada total de `FAIL`, uma linha registra o estado agregado do
gate; as falhas operacionais são 33, 33, 33 e 32, respectivamente.

## O que falta para liberar uma comparação científica

1. **Concluído:** anexar/conferir o PDF-base e fechar a matriz requisito → implementação → evidência.
2. Definir um snapshot OSM congelado e um recorte verificável para cada cidade.
3. Regenerar download e todas as etapas com o código atual, sem misturar outputs antigos.
4. Produzir centralidade completa de arestas e regenerar seus consumidores.
5. Gerar relatórios e manifestos v2 no fim de cada execução homogênea.
6. Obter `PASS` na integridade completa das quatro cidades.
7. Obter `confirmada` na auditoria científica para os pares pretendidos.
8. Só então atualizar resultados, figuras e conclusões comparativas.

## Validação final da revisão

- 104/104 testes aprovados.
- Compilação de fontes e testes: aprovada.
- Dependências instaladas: consistentes.
- Contratos CLI principais: aprovados, inclusive códigos de saída fail-closed.
- Auditoria de representação: aprovada nas quatro cidades.
- Auditoria científica dos outputs legados: corretamente bloqueada.
- Auditoria completa de integridade dos outputs legados: corretamente bloqueada.

Este registro documenta trabalho verificável e limitações remanescentes; não atribui uma duração
fictícia ao processo nem transforma artefatos legados em resultados validados.
