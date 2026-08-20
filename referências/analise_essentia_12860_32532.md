# Análise de Reis e Almeida (2018)

PDF analisado: [`essentia,+12860-32532-1-SM.pdf`](./essentia,+12860-32532-1-SM.pdf)

Referência: REIS, Gabriela Cacilda Godinho dos; ALMEIDA, Rodolfo Maduro. *Caracterização e análise da malha viária urbana de Santarém/PA utilizando medida de centralidade por intermediação em teoria dos grafos*. Anais do XXI Encontro Nacional de Modelagem Computacional e IX Encontro de Ciências e Tecnologia de Materiais, Búzios, 2018.

## Ideia central

O trabalho representa a rede viária de Santarém como um grafo primal, obtido do OpenStreetMap, e usa centralidade de intermediação de arestas para localizar trechos presentes em muitos caminhos mínimos. A rede é analisada nas versões não dirigida e dirigida, ponderada por distância. Os autores também cruzam a importância estrutural das vias com a condição de pavimentação cadastrada.

O fluxo usa QGIS, PostgreSQL, PostGIS e pgRouting para preparar os dados e R/igraph para calcular caminhos mínimos e intermediação. Os atributos `source`, `target`, `oneway` e cobertura da via são preservados; o sistema de referência é convertido de WGS84 para SIRGAS 2000 / UTM zona 21S.

Os mapas destacam eixos como as avenidas Cuiabá, Engenheiro Fernando Guilhon e Curuá-Una e identificam conexões importantes, porém não pavimentadas, entre Santarenzinho e o restante da cidade. A rede dirigida apresenta centralidade máxima menor, mas distribuição espacial semelhante à não dirigida, atribuída ao grande número de vias de duplo sentido. O artigo relata, para a rede dirigida, aproximadamente 20% de trechos com intermediação baixa, mais de 70% média e menos de 10% alta.

## Como ajuda o projeto

1. **É um exemplo brasileiro de OSM e intermediação.** O estudo demonstra, em linguagem aplicada, como transformar uma malha viária brasileira em grafo e mapear trechos estruturalmente importantes. Ele se relaciona diretamente com `src/ic/centrality.py` e com os mapas de rankings do projeto.

2. **Justifica a auditoria dirigido versus não dirigido.** A comparação das Figuras 3 e 4 mostra que o sentido das vias pode alterar valores e interpretação. Isso reforça `representation_audit.py`: o MultiDiGraph dirigido deve ser preservado para roteamento, enquanto o grafo simples não dirigido precisa ser apresentado como outra abstração, adequada a perguntas diferentes.

3. **Conecta topologia a atributos OSM.** O cruzamento entre intermediação e pavimentação é uma inspiração direta para `functional_relations.py`, `road_hierarchy.py` e `vulnerability_index.py`. O projeto pode localizar trechos com alta importância estrutural e `surface` ausente ou não pavimentada, tratando-os como candidatos para investigação.

4. **Ajuda a comunicar resultados.** Mapas contínuos de intermediação e histogramas tornam claro que poucos segmentos concentram valores altos. Esse par mapa-distribuição é mais informativo que uma lista isolada das dez vias mais centrais.

5. **Fornece uma cautela essencial.** A própria seção 3 reconhece que intermediação tradicional, sozinha, não explica fluxo de tráfego porque ignora volume, tempo, capacidade e restrições dinâmicas. Essa ressalva combina exatamente com o contrato científico do projeto.

## O que vale incorporar

- apresentar lado a lado intermediação de arestas dirigida e não dirigida, com a finalidade de cada representação;
- produzir histogramas, distribuição acumulada e medidas de concentração dos valores;
- cruzar os principais segmentos com `surface`, `highway`, `lanes`, `maxspeed` e `oneway`, sempre mostrando cobertura e valores ausentes;
- criar uma tabela de candidatos com centralidade, classe viária, pavimentação informada e impacto nas curvas de robustez;
- formular esses resultados como hipóteses de priorização para vistoria ou validação externa;
- manter distância em metros como peso estrutural e não transformar pavimentação em “tempo” sem uma função de impedância justificada.

## Cuidados e limitações

O artigo não informa a data do download OSM, versão dos programas, filtros de vias, regra de simplificação, extensão exata do recorte ou tratamento de componentes desconectadas. Portanto, o estudo é pouco reproduzível pelos padrões atuais do projeto.

Há uma tensão interna importante: a seção 3 afirma corretamente que intermediação tradicional não é suficiente para analisar tráfego, mas os resultados depois sugerem congestionamentos, acidentes e correspondência com o tráfego cotidiano sem apresentar contagens veiculares ou validação independente. O projeto deve manter a formulação mais rigorosa: alta intermediação significa dependência de caminhos mínimos no modelo, não fluxo observado.

A interpretação modal também exige cuidado. Tornar a rede não dirigida não basta para representar caminhada ou bicicleta, porque esses modos têm acessos, restrições e `network_type` próprios. Da mesma forma, `surface` no OSM pode estar incompleta; ausência de tag não significa ausência de pavimentação. As porcentagens baixa/média/alta dependem ainda de cortes que o artigo não documenta claramente.

## Roteiro de grifo

O artigo não possui numeração impressa útil; use a página exibida pelo leitor de PDF.

| Página do PDF | Onde grifar | Por que é importante |
|---:|---|---|
| 1 | Resumo e último parágrafo da introdução | Define representação primal e objetivo aplicado a Santarém. |
| 3 | Definição e Equação 1 da centralidade de intermediação | É a base conceitual do método. |
| 3-4 | Final da seção 3, de “Para a análise de fluxo…” até “priorizadas para asfaltamento” | É a ressalva mais importante: centralidade estrutural não incorpora dinâmica do tráfego. |
| 4 | Início da seção 4 e seção 4.1 | Resume as duas etapas e as ferramentas usadas. |
| 5 | Parágrafos sobre SIRGAS 2000 / UTM e atributos `source`, `target`, `oneway` e cobertura | Mostra cuidados geográficos e atributos necessários para repetir a análise. |
| 5 | Seção 4.3 e parágrafo final da metodologia | Explica Dijkstra, pesos e as comparações dirigido/não dirigido e centralidade/pavimentação. |
| 6 | Figura 2 e parágrafo seguinte | Permite comparar cobertura das vias com importância estrutural. |
| 7 | Figuras 3 e 4 | Comparação visual direta da intermediação sem e com sentido de via. |
| 8 | Três primeiros parágrafos e Figura 5 | Registra a diferença entre as representações e a análise das distribuições. |
| 9 | Figura 6 e primeiro parágrafo após a figura | Contém as proporções relatadas e o cruzamento com pavimentação. |
| 9 | Parágrafo que começa por “De acordo os mapas 3 e 4…” | Grife a ideia de candidato estrutural, mas anote ao lado: “não é tráfego observado”. |
| 9 | Conclusão | Útil para entender a aplicação pretendida, mas marque como afirmação mais forte que a evidência disponível. |

## Uso recomendado na escrita

Esta referência funciona melhor como estudo de caso brasileiro e ponte entre intermediação, direção das vias e atributos de pavimentação. Ela não deve ser a principal fonte teórica de robustez nem ser usada para afirmar congestionamento. A formulação segura é: o artigo identifica **trechos candidatos estruturalmente importantes** que podem orientar validação de campo, dados de tráfego ou análise de investimento.
