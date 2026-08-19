# Dicionário de dados e contratos científicos

Este documento descreve os artefatos primários da pipeline. O contrato executável mais detalhado
está em `src/ic/artifact_integrity.py`; divergências devem falhar na auditoria, não ser corrigidas
silenciosamente durante a análise.

## Convenções gerais

| Convenção | Significado |
|---|---|
| `dataset` / `city_id` | identificador seguro e estável do recorte, por exemplo `campinas_admin` |
| `node` | identificador do nó OSMnx/OSM; não é necessariamente persistente entre snapshots |
| `u`, `v`, `key` | origem, destino e chave da aresta no `MultiDiGraph` |
| `length`, `*_m` | comprimento em metros; deve ser finito e positivo |
| `*_fraction`, `*_rate`, `*_pct` | proporção em `[0,1]`, apesar do sufixo histórico `pct` |
| `*_retained` | valor atual dividido pelo baseline da mesma execução |
| `*_drop` | baseline menos valor atual |
| campo vazio | ausente, não aplicável ou incerteza não estimada; nunca converter automaticamente em zero |
| `seed` / `attack_seed` | controla o sorteio/ordem do ataque |
| `evaluation_seed` | controla somente a amostra usada para estimar eficiência |

## Entradas

### `data/graphs/<dataset>_<network_type>_raw.graphml`

Grafo adquirido do OSM, normalmente um `MultiDiGraph` dirigido. Preserva direção e arestas
paralelas. É a referência para medir perdas introduzidas pelo pré-processamento.

### `data/graphs/<dataset>_<network_type>_clean.graphml`

Grafo após a política de limpeza. O pipeline legado retém a maior componente fracamente conectada;
essa seleção deve ser quantificada pela auditoria de representação.

### `data/metadata/<dataset>_<network_type>_raw.json`

Campos novos obrigatórios em aquisições regeneradas:

- início/fim UTC da consulta;
- `snapshot_mode`: `historical` ou `live_unfrozen`;
- timestamp histórico explícito quando aplicável;
- `network_type`, `simplify` e versão OSMnx;
- configuração efetiva e SHA-256 do YAML;
- definição do recorte e `boundary_identity_sha256`: geometria normalizada para `place` quando
  disponível ou parâmetros canônicos para bbox/radius;
- identificador/relação OSM quando disponível, com ausência explícita;
- CRS do limite e do grafo.

`live_unfrozen` documenta uma consulta ao estado corrente, mas não comprova snapshot idêntico entre
cidades.

## Proveniência

### `outputs/experiments/cli_runs.jsonl`

Uma linha JSON por comando. O mesmo registro é anexado a
`outputs/<dataset>/logs/cli_runs.jsonl`.

Campos centrais:

- `schema_version`, `run_id`, `status`, `error`;
- `argv`, `command_line`, `command`, `parameters` já com defaults;
- timestamps e duração;
- runtime Python e versões das dependências;
- commit, branch, `dirty` e SHA-256 do diff, incluindo conteúdo de arquivos não rastreados;
- datasets inferidos;
- fingerprints das entradas;
- artefatos criados/modificados, com SHA-256, tamanho e mtime.

### `EXPERIMENT_MANIFEST_<dataset>.json`

O manifesto v2 é um snapshot consolidado. Inclui o comando real do relatório, ambiente, Git,
última execução registrada por comando e fingerprints das entradas/saídas existentes. Presença no
manifesto não substitui o gate de integridade/frescor. `logs/cli_runs.jsonl` é controle mutável e
fica fora do conjunto autoritativo de outputs para não invalidar o manifesto no fim da execução.

## Métricas estruturais e representação

### `structural_metrics.csv`

Formato chave–valor (`metric,value`). Inclui tamanho do grafo analisado, grau, clustering,
transitividade, assortatividade e aproximações de caminhos/diâmetro. O relatório deve indicar a
representação e a componente usada.

### `graph_representation_audit.csv`

Uma linha por estágio (`raw`, `clean`) e representação:

- `multidigraph_directed`;
- `multigraph_undirected`;
- `digraph_min_length`;
- `graph_min_length`.

Registra nós, arestas, componentes, LCC/SCC, loops, paralelas, reciprocidade, comprimentos inválidos,
extensão dirigida, extensão física colapsada e perdas raw→clean.

### `representation_metric_sensitivity.csv`

Compara rankings de grau e betweenness por Spearman tie-aware e sobreposição top-k. Correlação
indefinida fica vazia com `status` explicativo.

## Centralidades

### `node_centralities.csv`

Cobertura completa de nós, com coordenadas, grau, betweenness, closeness aproximada e autovetor.
`top_nodes.csv` é apenas uma visualização truncada e não pode substituir este arquivo.

### `edge_centralities.csv`

Cobertura completa de arestas do grafo simples analisado, incluindo `u`, `v`, betweenness e
atributos preservados. `top_edges.csv` contém somente o ranking top-k. Índices downstream falham se
o arquivo completo tiver duplicatas, valores não finitos, arestas ausentes ou extras.

## Curvas de robustez estrutural

Arquivos de origem mantêm `resilience` no nome por compatibilidade.

Colunas comuns:

| Coluna | Definição |
|---|---|
| `removed`, `removed_fraction` | quantidade/fração de objetos removidos |
| `lcc_size`, `lcc_fraction` | tamanho/fração da maior componente em relação ao baseline |
| `components` | componentes conectadas após a remoção |
| `efficiency_topological_retained` | eficiência topológica retida |
| `efficiency_length_retained` | eficiência ponderada por comprimento retida |
| `attack_seed` | semente do processo de remoção |
| `evaluation_seed` | semente independente da estimativa de eficiência |

Em comunidades, a resposta primária é `lcc_weighted_fraction`, ponderada pelo número de nós
originais. `lcc_communities_fraction` responde a outra pergunta e não deve substituir a ponderada.

### Agregados aleatórios

`resilience_random_aggregate.csv` e `node_resilience_random_aggregate.csv` contêm, por ponto da
curva: média, desvio amostral, erro-padrão, mediana, quantis, mínimo/máximo e IC 95% bootstrap.
O mínimo recomendado é 30 repetições.

`resilience_random_auc.csv` e `node_resilience_random_auc.csv` separam linhas de execução e
resumo. A AUC é normalizada pela fração de remoção realmente observada.

### `robustness_summary.csv` / `robustness_comparison.csv`

Uma linha por dataset × modalidade × estratégia × resposta. Contém intervalo comum, número de
repetições, AUC, incerteza, checkpoints, limiares, diferença/razão contra o baseline aleatório e
estado da incerteza. A matriz incompleta é erro por padrão.

## Inventário e extensão

`graph_inventory_summary.csv` distingue:

- `directed_routing_length_km`: soma dos arcos direcionados, útil para roteamento;
- `physical_collapsed_length_km`: menor segmento válido por par não ordenado, proxy que evita
  duplicar automaticamente ida/volta;
- versões `*_per_km2` normalizadas pela área registrada.

O proxy físico ainda pode subcontar pistas separadas ou vias paralelas reais; não é reconstrução
geométrica de ruas.

Valores de superfície “estimados” redistribuem desconhecidos conforme a proporção observada e
pressupõem ausência ao acaso. Sempre relatar também a cobertura de `surface`.

## Módulos exploratórios

- `route_redundancy_*`: alternativa após remover todos os arcos da melhor rota; cenário disjunto
  estrito.
- `spatial_robustness_*`: bloqueios por célula sem probabilidade; eficiência calculada em amostra
  aleatória simples quando o limite não cobre todas as células.
- `urban_morphology_*`: classes heurísticas dependentes de escala/limiares.
- `subcenters_*`: candidatos de alta centralidade topológica, não centros econômicos observados.
- `network_scale_profile_*`: sensibilidade descritiva à grade e ao MAUP.
- `functional_topology_*`: associações com tags OSM, sem inferência causal ou validação de tráfego.
- `od_efficiency_*`: pares uniformes entre nós, não demanda OD populacional.

## Gates

### `artifact_integrity_audit.csv`

Cada linha registra `dataset`, `stage`, `check`, `status`, `path`, esperado, observado e detalhes.
Somente `PASS` libera o dataset; `WARN` e `FAIL` fecham o gate.

Sem `--stages`, os nomes canônicos representam a auditoria completa inferida. Com escopo explícito,
os arquivos recebem sufixo, por exemplo `artifact_integrity_audit__representation_audit.csv`;
`PASS` nesse arquivo não libera etapas não auditadas. O hash não tem limite de tamanho por padrão.
Os comandos CLI encerram com código diferente de zero quando o gate fecha.

### `scientific_comparability_*.csv`

- `criteria`: evidência por critério/dataset/par;
- `datasets`: estado agregado e assinaturas;
- `pairs`: decisão par a par.

Estados possíveis: `confirmada`, `nao_comprovada`, `incomparavel`. O perfil exploratório grava
arquivos com prefixo diferente para impedir confusão com evidência científica.
