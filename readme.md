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
ic communities --city campinas
ic resilience --city campinas --strategy targeted
ic community-resilience --city campinas --strategy targeted
ic intra-community-resilience --city campinas --strategy targeted
ic inventory --city campinas
ic report --city campinas
ic dashboard --city campinas
```

Os mesmos comandos aceitam `--year ANO` para datasets históricos. A lista detalhada de
parâmetros e exemplos está em [config/comandos.md](config/comandos.md).

## Três escalas de resiliência

- `resilience`: mede a resiliência do grafo viário inteiro.
- `community-resilience`: agrega cada comunidade como um nó e mede a resiliência das
  conexões **entre** comunidades.
- `intra-community-resilience`: mede separadamente a resiliência **interna de cada
  comunidade**, removendo arestas de seu subgrafo induzido.

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

## Aderência ao plano da IC

A análise de cobertura atual, lacunas metodológicas e prioridades está em
[docs/analise_lacunas_projeto_ic.md](docs/analise_lacunas_projeto_ic.md).
