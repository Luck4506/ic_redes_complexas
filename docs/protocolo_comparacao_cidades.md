# Protocolo de comparação entre cidades

## Regra principal

Uma comparação só pode sustentar interpretações sobre padrões urbanos quando os datasets
usarem o mesmo protocolo de recorte, data controlada, parâmetros e cobertura experimental.
Caso contrário, a comparação deve ser identificada como **exploratória**.

## Protocolo mínimo

1. Usar limites administrativos equivalentes ou recortes com áreas que diferem no máximo 10%.
2. Usar dados OSM da mesma data, ou declarar explicitamente a diferença temporal.
3. Executar as mesmas métricas com os mesmos parâmetros e sementes.
4. Normalizar métricas dependentes do tamanho da rede.
5. Registrar área aproximada, quantidade de nós, arestas e extensão viária.
6. Não chamar padrões de universais com apenas quatro cidades.

## Situação atual

Há dois conjuntos de comparação:

- os datasets originais por BBOX continuam classificados como **exploratórios**, pois usam
  caixas delimitadoras com áreas muito diferentes;
- os datasets `campinas_admin`, `jundiai_admin`, `sorocaba_admin` e `valinhos_admin` usam
  limites administrativos municipais, a mesma data OSM atual e os mesmos parâmetros. A
  auditoria em `outputs/comparisons/comparability_audit_admin.csv` os classifica como
  **comparáveis**.

As configurações reprodutíveis estão em `config/comparable/` e o relatório comparativo
padronizado está em `outputs/comparisons/compare_admin_cities.html`. Os datasets por BBOX
foram preservados para não invalidar resultados anteriores.

Ser comparável não torna as cidades equivalentes: métricas dependentes do tamanho ainda devem
ser normalizadas e as diferenças precisam ser discutidas no contexto de cada município.
