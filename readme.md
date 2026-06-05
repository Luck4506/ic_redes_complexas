# IC - Redes Complexas na Rede Viária

Pipeline reprodutível para caracterização topológica, centralidade, comunidades, resiliência e
comparação de redes viárias urbanas brasileiras obtidas do OpenStreetMap.

## Configuração

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e .
```

## Pipeline principal

```bash
ic download --city campinas
ic preprocess --city campinas
ic structural --city campinas
ic centrality --city campinas
ic functional-relations --city campinas
ic validate-approximations --city campinas
ic communities --city campinas
ic resilience --city campinas --strategy targeted
ic node-resilience --city campinas --strategy targeted
ic random-resilience-stats --city campinas --mode both
ic community-resilience --city campinas --strategy targeted
ic intra-community-resilience --city campinas --strategy targeted
ic vulnerability-index --city campinas
ic structural-bottlenecks --city campinas
ic route-redundancy --city campinas
ic spatial-multiscale --city campinas
ic spatial-robustness --city campinas
ic road-hierarchy --city campinas
ic urban-morphology --city campinas
ic od-efficiency --city campinas
ic subcenters --city campinas
ic urban-barriers --city campinas
ic network-scale-profile --city campinas
ic inventory --city campinas
ic report --city campinas
ic dashboard --city campinas
ic comparison-audit campinas jundiai sorocaba valinhos
ic city-similarity campinas_admin jundiai_admin sorocaba_admin valinhos_admin
ic historical-audit --reference campinas campinas_2021 campinas_2024
```

Os mesmos comandos aceitam `--year ANO` para datasets históricos. A lista detalhada de
parâmetros e exemplos está em [config/comandos.md](config/comandos.md).

Comparações temporais com OSM histórico devem ser auditadas antes da interpretação. O comando
`historical-audit` mede o viés de cobertura do OSM e classifica cada ano como
`nao_confiavel`, `exploratorio` ou `comparavel_com_cautela`.

## Análises de resiliência

- `resilience`: mede a resiliência do grafo viário inteiro removendo exclusivamente arestas.
- `node-resilience`: mede a resiliência do grafo viário inteiro removendo exclusivamente
  vértices. Não combina remoção de vértices e arestas.
- `community-resilience`: agrega cada comunidade como um nó e mede a resiliência das
  conexões **entre** comunidades.
- `intra-community-resilience`: mede separadamente a resiliência **interna de cada
  comunidade**, removendo arestas de seu subgrafo induzido.
- `random-resilience-stats`: repete ataques aleatórios com múltiplas sementes e gera curvas
  agregadas com média, desvio, mínimo e máximo.
- `vulnerability-index`: combina centralidades, ataques por vértices, articulações, pontes,
  tipo de via, comprimento e fronteiras entre comunidades em rankings compostos de
  vulnerabilidade para nós e arestas.
- `structural-bottlenecks`: identifica pontes, nós de articulação e gargalos estruturais,
  medindo quantos nós saem da maior componente quando cada elemento crítico é removido.
- `route-redundancy`: amostra pares origem-destino, bloqueia a melhor rota e mede se ainda
  existe alternativa razoável de deslocamento.
- `spatial-multiscale`: divide a área do grafo em células regulares e calcula métricas locais
  de conectividade, vulnerabilidade e redundância.
- `spatial-robustness`: simula bloqueios regionais por célula espacial e mede o impacto no
  grafo inteiro.
- `road-hierarchy`: mede como classes `highway` contribuem para conectividade, centralidade,
  vulnerabilidade e resiliência.
- `urban-morphology`: classifica células como gradeadas, radiais/lineares, orgânicas,
  fragmentadas ou mistas a partir de orientação das vias, entropia angular e conectividade.
- `od-efficiency`: amostra múltiplos pares origem-destino e mede distância, hops,
  circuity, eficiência e acessibilidade como distribuição estatística.
- `city-similarity`: transforma métricas consolidadas em vetores por cidade e calcula
  distância, similaridade cosseno, PCA e agrupamento hierárquico.
- `subcenters`: detecta subcentros topológicos por células espaciais e calcula índice de
  policentralidade.
- `urban-barriers`: infere barreiras urbanas prováveis a partir de baixa permeabilidade
  espacial, conexões vizinhas ausentes, travessias longas, pontes estruturais e fronteiras
  de comunidades.
- `network-scale-profile`: recalcula métricas espaciais em múltiplas escalas de grade e mede
  a estabilidade das conclusões locais.

As estratégias disponíveis são `random`, `targeted` e `targeted_adaptive`. Para comparações
científicas, mantenha os mesmos parâmetros entre datasets e trate a estratégia aleatória como
um baseline que deve futuramente ser repetido com múltiplas sementes.

## Saídas

Cada dataset gera artefatos em `outputs/<dataset>/`:

- `metrics/`: CSVs com métricas, curvas e resumos;
- `figures/`: gráficos estáticos;
- `maps/`: mapas interativos;
- `logs/`: relatórios metodológicos;
- `dashboard_<dataset>.html`: painel consolidado;
- `REPORT_<dataset>.md`: relatório consolidado.
- `EXPERIMENT_MANIFEST_<dataset>.json`: manifesto de reprodutibilidade com ambiente,
  versões, Git e artefatos.

## Aderência ao plano da IC

A análise de cobertura atual, lacunas metodológicas e prioridades está em
[docs/analise_lacunas_projeto_ic.md](docs/analise_lacunas_projeto_ic.md).

Para a etapa atual, focada somente no sistema que gera dados para análise posterior, use a
revisão computacional em
[docs/lacunas_computacionais_escopo_ic.md](docs/lacunas_computacionais_escopo_ic.md).

O protocolo para comparações científicas e as configurações por limites administrativos estão
em [docs/protocolo_comparacao_cidades.md](docs/protocolo_comparacao_cidades.md) e
`config/comparable/`.

O protocolo específico para análise histórica com OSM está em
[docs/protocolo_analise_historica_osm.md](docs/protocolo_analise_historica_osm.md).
