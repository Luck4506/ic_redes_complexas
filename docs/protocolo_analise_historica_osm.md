# Protocolo para análise histórica com OpenStreetMap

## Problema

Comparar diretamente um grafo OSM antigo com um grafo atual pode medir a evolução do
mapeamento, não a evolução real da cidade. Em anos antigos, muitas vias podem existir na
cidade, mas ainda não terem sido mapeadas no OSM.

Portanto, a análise histórica só deve ser usada depois de uma auditoria de cobertura.

## Solução implementada

Foi criado o comando:

```bash
ic historical-audit --reference campinas campinas_2010 campinas_2011 ... campinas_2026
```

Ele compara cada dataset histórico com uma referência atual e gera:

- `historical_quality_*.csv`: cobertura e classificação metodológica por ano;
- `historical_common_core_*.csv`: métricas do núcleo comum de vias que aparecem no ano
  histórico e na referência atual;
- `historical_quality_*.txt`: relatório interpretativo.

## Indicadores usados

A auditoria usa os identificadores de vias do OSM (`osmid`) para estimar:

- quantas vias únicas existem em cada ano;
- qual fração das vias atuais já aparece no ano histórico;
- qual fração das vias históricas também aparece na referência atual;
- cobertura de atributos como `surface` e `maxspeed`;
- quantidade de ways históricas descartadas por estarem incompletas.

## Classificação

- `nao_confiavel`: cobertura muito baixa. A comparação bruta provavelmente mede evolução do
  OSM, não evolução urbana.
- `exploratorio`: há cobertura parcial, mas não suficiente para conclusão forte.
- `comparavel_com_cautela`: cobertura suficiente para análise histórica descritiva, sem
  afirmar causalidade.

## Resultado para Campinas

Com referência no dataset atual `campinas`, a auditoria indicou:

- 2010 a 2014: **não confiável**;
- 2015 a 2020: **exploratório**;
- 2021 a 2026: **comparável com cautela**.

Isso confirma que uma comparação bruta entre Campinas atual e Campinas de 10 anos atrás é
dominada pela evolução da cobertura OSM.

## Como usar cientificamente

1. Não apresentar crescimento bruto de nós, arestas ou extensão como crescimento urbano sem
   passar pela auditoria.
2. Usar o núcleo comum para perguntas do tipo: “como mudou a representação topológica das
   vias que aparecem nos dois anos?”.
3. Tratar anos `nao_confiavel` apenas como evidência de incompletude do OSM histórico.
4. Tratar anos `exploratorio` como material auxiliar, não como resultado central.
5. Para inferir expansão urbana real, combinar OSM com outra fonte externa, como imagens de
   satélite, cadastro municipal, MapBiomas, IBGE ou bases viárias oficiais.

## Limitação importante

O núcleo comum reduz o viés de cobertura, mas não recupera vias que existiam no passado e não
foram mapeadas. Portanto, ele melhora a honestidade metodológica, mas não substitui uma fonte
histórica independente.
