# Revisão bibliográfica orientada ao projeto de IC

## 1. Escopo identificado no repositório

O projeto **Análise Estrutural da Rede Viária Urbana Brasileira Utilizando Métricas de
Redes Complexas** constrói, a partir do OpenStreetMap (OSM), grafos viários de Campinas,
Jundiaí, Sorocaba e Valinhos. O conjunto principal usa limites administrativos e um protocolo
comum. A implementação cobre:

- representação primal da rede: interseções e finais de via como nós, segmentos como arestas;
- métricas estruturais, distribuição de grau e centralidades;
- comunidades e modularidade;
- robustez sob remoção aleatória e dirigida de nós e arestas;
- robustez entre comunidades e dentro de comunidades;
- eficiência global aproximada, gargalos, vulnerabilidade e redundância de rotas;
- morfologia, orientação, circuity, análise espacial e multiescala;
- comparação entre cidades e auditoria da qualidade histórica do OSM.

O PDF-base [`_Projeto_2026__Lucas_Soares.pdf`](../_Projeto_2026__Lucas_Soares.pdf) foi anexado e
conferido integral e visualmente em 18 de agosto de 2026. Esta revisão foi reconciliada com seus
objetivos, atividades e resultados esperados; a correspondência literal está registrada em
[`matriz_aderencia_plano_trabalho.md`](matriz_aderencia_plano_trabalho.md).

## 2. Enquadramento científico recomendado

O trabalho deve ser apresentado como um **estudo comparativo e exploratório da estrutura e da
robustez de redes viárias municipais**, e não como uma avaliação direta de tráfego, mobilidade
real ou qualidade do planejamento urbano. O grafo descreve oportunidades estruturais de
conexão; não contém demanda OD observada, volume de tráfego, capacidade real das vias nem
tempos observados.

Uma formulação central defensável é:

> Como a estrutura topológica e espacial das redes viárias de quatro municípios paulistas se
> diferencia, e em que medida essas diferenças estão associadas à manutenção da conectividade
> e da eficiência sob falhas aleatórias e remoções dirigidas?

Perguntas secundárias:

1. Quais propriedades estruturais distinguem as quatro redes sob recortes e parâmetros comuns?
2. Quais redes preservam melhor a maior componente e a eficiência sob remoção de nós e arestas?
3. A remoção dirigida por intermediação degrada as redes mais rapidamente que a remoção
   aleatória?
4. As comunidades dependem de poucas conexões intercomunitárias, e sua fragilidade interna é
   heterogênea?
5. Resultados globais permanecem consistentes em escalas espaciais diferentes?

Hipóteses testáveis:

- **H1:** ataques dirigidos por centralidade reduzem conectividade e eficiência mais rapidamente
  que falhas aleatórias;
- **H2:** maior conectividade local e maior redundância de rotas estão associadas a menor perda
  de eficiência sob remoções;
- **H3:** redes com conexões intercomunitárias mais concentradas apresentam maior fragilidade no
  grafo agregado de comunidades;
- **H4:** rankings de cidades variam conforme a resposta observada (LCC, eficiência topológica ou
  eficiência ponderada), portanto robustez não deve ser reduzida a um único indicador.

## 3. Trabalhos diretamente relacionados

### 3.1 Fundamentos de redes espaciais e redes viárias

1. **Barthélemy (2011), _Spatial Networks_.** Revisão teórica fundamental para explicar por que
   redes viárias não devem ser tratadas como grafos abstratos comuns: custo de comprimento,
   geometria, quase planaridade e restrições espaciais moldam sua topologia.
   DOI: [10.1016/j.physrep.2010.11.002](https://doi.org/10.1016/j.physrep.2010.11.002).

   - **Relação com o projeto:** fornece o enquadramento geral para quase todos os módulos. A rede
     viária é uma rede espacial: posições, comprimentos, custo de construção e restrições
     geométricas limitam grau, caminhos e redundância. Isso explica por que resultados de redes
     sociais ou da Internet não podem ser transferidos automaticamente para ruas.
   - **O que aproveitar:** usar na fundamentação para definir redes espaciais; justificar a leitura
     conjunta de topologia e geometria; explicar quase planaridade, custo, comprimento de arestas,
     acessibilidade e efeitos de escala. Também ajuda a defender métricas ponderadas por distância e
     a análise multiescala, em vez de depender apenas de grau e densidade.
   - **Cuidado:** é uma revisão ampla, não um protocolo específico para municípios brasileiros.
     Deve sustentar conceitos e escolhas, não servir como evidência de que um resultado observado
     nas quatro cidades é universal.

2. **Porta, Crucitti e Latora (2006), _The Network Analysis of Urban Streets: A Primal
   Approach_.** É a referência mais próxima da representação principal deste projeto. Discute a
   rede primal e o papel de centralidades na leitura da estrutura urbana.
   DOI: [10.1068/b32045](https://doi.org/10.1068/b32045).

   - **Relação com o projeto:** o repositório adota a mesma ideia de representação primal:
     interseções/finais como nós e trechos como arestas. O artigo discute como essa representação
     preserva a localização geográfica e permite estudar centralidade no espaço urbano.
   - **O que aproveitar:** citar na seção de construção do grafo e na justificativa de grau,
     proximidade e intermediação. A discussão entre abordagens primal e dual pode fundamentar por
     que o projeto prioriza pontos de interseção e segmentos físicos, e não ruas inteiras como nós.
     O texto também oferece vocabulário para ligar centralidade a acessibilidade, proximidade,
     conectividade, custo e esforço.
   - **Cuidado:** a representação escolhida condiciona o significado das métricas. Uma via
     importante no grafo dual pode não ocupar a mesma posição no primal; por isso, não se deve
     apresentar o resultado como uma importância absoluta da rua.

3. **Crucitti, Latora e Porta (2006), _Centrality Measures in Spatial Networks of Urban
   Streets_.** Fundamenta grau, proximidade, intermediação e centralidades em redes de ruas e
   ajuda a interpretar que cada medida representa uma forma distinta de importância.
   DOI: [10.1103/PhysRevE.73.036125](https://doi.org/10.1103/PhysRevE.73.036125).

   - **Relação com o projeto:** é a referência mais direta para `centrality.py`, para os mapas de
     nós críticos e para a comparação de distribuições de centralidade. O trabalho usa múltiplos
     índices porque cada um capta uma forma diferente de “ser central”.
   - **O que aproveitar:** estruturar a interpretação separando grau (conectividade local),
     proximidade (distância aos demais), intermediação (participação em caminhos mínimos) e
     autovetor (inserção em vizinhanças importantes). A ideia de _multiple centrality assessment_
     sustenta mapas e rankings múltiplos, evitando eleger uma única medida. O agrupamento baseado
     nas distribuições também se relaciona a `city_similarity.py`.
   - **Cuidado:** o artigo não demonstra que centralidade seja tráfego observado. Ele propõe que
     índices estruturais podem se relacionar a dinâmicas urbanas, relação que precisa ser testada
     com dados externos. Além disso, o projeto não implementa todas as medidas do artigo, como
     straightness e information centrality.

4. **Lin e Ban (2017), _Comparative Analysis on Topological Structures of Urban Street
   Networks_.** Exemplo de comparação entre cidades com métricas topológicas e atenção à
   planaridade.
   DOI: [10.3390/ijgi6100295](https://doi.org/10.3390/ijgi6100295).

   - **Relação com o projeto:** oferece um exemplo de comparação de redes de cidades com tamanhos,
     histórias e padrões de crescimento diferentes, usando métricas de conectividade,
     acessibilidade e interconexão e considerando a planaridade da malha.
   - **O que aproveitar:** usar como modelo para organizar uma tabela comparativa coerente e para
     discutir como estrutura e morfologia diferem entre cidades. Reforça a necessidade de explicar
     representação, recorte e normalização antes de interpretar diferenças numéricas.
   - **Cuidado:** três estudos de caso não estabelecem regularidades universais, assim como as
     quatro cidades deste projeto não representam toda a rede viária urbana brasileira. As métricas
     e representações dos dois estudos não são idênticas; a comparação deve ser conceitual.

5. **Boeing (2020), _A Multi-Scale Analysis of 27,000 Urban Street Networks_.** Sustenta a
   necessidade de definições consistentes de recorte e escala e mostra como métricas mudam entre
   municípios, áreas urbanizadas e bairros.
   DOI: [10.1177/2399808318784595](https://doi.org/10.1177/2399808318784595).

   - **Relação com o projeto:** mostra empiricamente que a unidade espacial — município, área
     urbanizada ou bairro — altera os indicadores. Isso se conecta ao protocolo administrativo,
     ao `spatial_multiscale.py` e ao `network_scale_profile.py`.
   - **O que aproveitar:** justificar definições explícitas de extensão e recorte, apresentar
     indicadores por área e executar sensibilidade de escala. O desenho de grande escala também é
     um bom exemplo de coleta automatizada, parâmetros consistentes e indicadores reprodutíveis.
   - **Cuidado:** limites administrativos iguais em natureza não tornam municípios equivalentes:
     proporções rurais, formas do polígono e efeitos de borda continuam distintos. Os resultados
     empíricos dos Estados Unidos não devem ser usados como valores de referência esperados para
     cidades paulistas.

### 3.2 Aquisição e modelagem com OSM/OSMnx

6. **Boeing (2017), _OSMnx: New Methods for Acquiring, Constructing, Analyzing, and Visualizing
   Complex Street Networks_.** Referência metodológica obrigatória para aquisição, simplificação
   topológica e construção reprodutível dos grafos a partir do OSM.
   DOI: [10.1016/j.compenvurbsys.2017.05.004](https://doi.org/10.1016/j.compenvurbsys.2017.05.004).

   - **Relação com o projeto:** fundamenta `download.py`, `preprocess.py`, o uso de GraphML e a
     criação dos grafos com OSMnx. O trabalho foi criado justamente para tornar aquisição,
     correção topológica, análise e visualização consistentes e automatizáveis.
   - **O que aproveitar:** descrever consulta por polígono, filtro de rede dirigível, correção e
     simplificação topológica, projeção, armazenamento e reprodutibilidade. Na metodologia, devem
     aparecer versão do OSMnx, data do dado, consulta, `network_type`, política de truncamento,
     retenção de componentes e tratamento de atributos.
   - **Cuidado:** o artigo descreve uma versão inicial do software. Como o projeto exige
     `osmnx>=2.0`, decisões e nomes de API devem ser documentados também com Boeing (2025) e com a
     versão efetivamente registrada no manifesto experimental.

7. **Boeing (2025), _Modeling and Analyzing Urban Networks and Amenities With OSMnx_.**
   Atualização conceitual e técnica do ecossistema usado pelo projeto.
   DOI: [10.1111/gean.70009](https://doi.org/10.1111/gean.70009).

   - **Relação com o projeto:** descreve a representação moderna do OSMnx como grafo primal,
     não planar, ponderado, dirigido e multigrafo. Isso corresponde ao `MultiDiGraph` de entrada
     antes de o pipeline produzir versões simples para análises estruturais.
   - **O que aproveitar:** explicar corretamente vias de mão única, pares de arestas recíprocas,
     viadutos que se cruzam sem formar interseção, simplificação de arestas, consolidação de
     interseções complexas e problema do perímetro artificial. Também sustenta a dimensão de
     ciência aberta e a importância de tornar pequenas decisões de modelagem explícitas.
   - **Cuidado:** o fato de o OSMnx oferecer consolidação de interseções não prova que ela foi
     aplicada pelo projeto. O relatório precisa descrever o comportamento real do pipeline e não
     apenas todas as capacidades da biblioteca.

8. **Boeing (2020), _Planarity and Street Network Representation in Urban Form Analysis_.**
   Fundamenta a necessidade de declarar se o grafo é dirigido, não dirigido, planar, simplificado
   e se preserva cruzamentos em níveis diferentes.
   DOI: [10.1177/2399808318802941](https://doi.org/10.1177/2399808318802941).

   - **Relação com o projeto:** sustenta a decisão de manter a topologia real de viadutos,
     túneis e cruzamentos em níveis diferentes. Um cruzamento desenhado no plano só deve virar nó
     quando existe conexão viária real.
   - **O que aproveitar:** incluir uma subseção sobre não planaridade e representação. A
     referência ajuda a explicar por que planarizar indevidamente o grafo altera grau,
     conectividade, rotas, centralidades e densidade de interseções. Também orienta a leitura de
     diferenças entre redes caminháveis e dirigíveis.
   - **Cuidado:** converter o `MultiDiGraph` para grafo simples não dirigido não equivale a
     planarizá-lo, mas elimina direção e paralelismo. Essas transformações são problemas distintos
     e devem ser relatadas separadamente.

### 3.3 Robustez, eficiência e ataques

9. **Albert, Jeong e Barabási (2000), _Error and Attack Tolerance of Complex Networks_.** Base
   clássica para contrastar falhas aleatórias e ataques dirigidos. Deve ser usada como fundamento
   geral, sem afirmar que redes viárias sejam necessariamente livres de escala.
   DOI: [10.1038/35019019](https://doi.org/10.1038/35019019).

   - **Relação com o projeto:** fornece o desenho clássico que contrasta remoção aleatória e
     remoção dirigida de componentes importantes, exatamente a lógica das estratégias `random` e
     `targeted` dos módulos de robustez.
   - **O que aproveitar:** fundamentar H1, explicar falha aleatória versus ataque intencional e
     usar a maior componente e medidas de distância como respostas de degradação. A noção
     “robusto a erros, frágil a ataques” é uma hipótese a testar nas quatro cidades, não uma
     conclusão prévia.
   - **Cuidado:** o resultado clássico foi associado a redes heterogêneas/livres de escala. Redes
     viárias primais têm fortes restrições espaciais e grau baixo. Não afirmar que são livres de
     escala apenas porque a distribuição foi desenhada em eixos log-log, nem presumir que repetirão
     o comportamento do artigo.

10. **Latora e Marchiori (2001), _Efficient Behavior of Small-World Networks_.** Origem da
    eficiência global usada nas curvas de degradação. É especialmente útil porque a eficiência
    continua definida quando o grafo se fragmenta.
    DOI: [10.1103/PhysRevLett.87.198701](https://doi.org/10.1103/PhysRevLett.87.198701).

    - **Relação com o projeto:** é a base matemática de `approximate_global_efficiency` e das
      colunas de eficiência retida nas curvas de remoção. A média de inversos das distâncias trata
      pares desconectados como contribuição zero.
    - **O que aproveitar:** apresentar a fórmula, diferenciar eficiência global e local e explicar
      por que a eficiência é mais adequada que o caminho médio quando a rede se fragmenta. Para a
      eficiência ponderada, declarar que `length` representa custo em metros e interpretar
      principalmente a fração retida em relação ao estado inicial.
    - **Cuidado:** valores ponderados brutos exigem normalização para comparação entre redes. A
      eficiência topológica não mede capacidade, congestionamento nem tempo real de viagem; no
      projeto ela é um indicador estrutural aproximado calculado por amostragem.

11. **Iyer et al. (2013), _Attack Robustness and Centrality of Complex Networks_.** Compara
    critérios de remoção por diferentes centralidades e sustenta a análise de ataques dirigidos.
    DOI: [10.1371/journal.pone.0059613](https://doi.org/10.1371/journal.pone.0059613).

    - **Relação com o projeto:** estuda remoção de vértices aleatória e dirigida por diferentes
      centralidades em redes modelo e empíricas. Relaciona-se diretamente a `node_resilience.py` e
      à escolha de intermediação para ordenar os ataques.
    - **O que aproveitar:** justificar que o critério de ataque é parte do experimento e pode
      alterar o ranking de robustez. O trabalho sugere uma análise adicional útil: comparar ataques
      por grau, intermediação, proximidade e autovetor, todos já calculados pelo pipeline.
    - **Cuidado:** a centralidade mais destrutiva depende da topologia. Intermediação não deve ser
      assumida como critério universalmente superior; deve ser comparada. O artigo também não é
      específico de redes viárias espaciais.

12. **Duan e Lu (2013), _Structural Robustness of City Road Networks Based on Community_.** É o
    trabalho mais diretamente relacionado aos módulos `community_resilience` e
    `intra_community_resilience`: usa perspectiva comunitária e ataques aleatórios/intencionais
    para comparar redes viárias.
    DOI: [10.1016/j.compenvurbsys.2013.03.002](https://doi.org/10.1016/j.compenvurbsys.2013.03.002).

    - **Relação com o projeto:** é a referência de maior aderência a
      `community_resilience.py`. Reconstrói redes viárias como grafos de comunidades, aplica três
      estratégias de ataque e mede eficiência e fragmentação em seis cidades.
    - **O que aproveitar:** usar como precedente direto para agregar comunidades, analisar
      conexões intercomunitárias e separar vulnerabilidade local de fragilidade mesoscópica. Seus
      resultados — robustez maior a falhas aleatórias e fragilidade a ataques intencionais — podem
      ser confrontados explicitamente com as curvas das quatro cidades.
    - **Cuidado:** o projeto não deve dizer que replicou o artigo sem demonstrar equivalência de
      representação, algoritmo, parâmetros e respostas. O próprio estudo reconhece que a detecção
      de comunidades em redes espaciais exige investigação. Comunidades topológicas também não
      equivalem automaticamente a bairros ou zonas de tráfego.

13. **Tian et al. (2019), _Robustness Analysis of Urban Street Networks Using Complex Network
    Method_.** Analisa 50 redes obtidas do OSM sob remoções sucessivas e falhas em cascata.
    DOI: [10.13203/j.whugis20150334](https://doi.org/10.13203/j.whugis20150334).

    - **Relação com o projeto:** trabalha com 50 redes OSM e compara remoção sucessiva e falha em
      cascata sob ataques por grau e intermediação. Encontrou sensibilidade ao modelo de ataque e
      maior efeito destrutivo da intermediação naquele desenho.
    - **O que aproveitar:** comparar os resultados de ataques sucessivos do projeto com um estudo
      internacional maior; discutir por que nós/arestas de alta intermediação concentram caminhos;
      e usar assortatividade como possível variável explicativa da robustez. O modelo em cascata é
      uma extensão futura clara.
    - **Cuidado:** `targeted_adaptive` recalcula centralidade durante remoções, mas não é uma falha
      em cascata: não há redistribuição de carga, capacidade nem propagação endógena. Não usar os
      termos como sinônimos.

14. **Ip e Wang (2011), _Resilience and Friability of Transportation Networks_.** Ajuda a
    separar medidas de conectividade, redundância e vulnerabilidade no domínio de transportes.
    DOI: [10.1109/JSYST.2010.2096670](https://doi.org/10.1109/JSYST.2010.2096670).

    - **Relação com o projeto:** avalia resiliência pela disponibilidade de caminhos confiáveis
      entre pares e define friabilidade como perda causada pela remoção de componentes. Isso se
      relaciona a `route_redundancy.py`, aos gargalos e à busca de rotas alternativas.
    - **O que aproveitar:** fundamentar que conectividade binária é insuficiente: número e
      confiabilidade de alternativas também importam. A referência pode apoiar a análise da taxa de
      pares que permanecem conectados e do aumento de custo após bloquear a melhor rota, além da
      discussão sobre priorização de melhorias estruturais.
    - **Cuidado:** o artigo representa cidades como nós de uma rede de transporte mais ampla,
      enquanto este projeto representa interseções dentro de municípios. O conceito é aproveitável,
      mas fórmula, escala e unidade de análise não são equivalentes.

### 3.4 Comunidades, morfologia, rotas e comparação

15. **Newman (2006), _Modularity and Community Structure in Networks_.** Fundamento da
    modularidade e da detecção de comunidades. Necessário para explicar o que uma comunidade
    topológica significa e o que ela não significa territorialmente.
    DOI: [10.1073/pnas.0601602103](https://doi.org/10.1073/pnas.0601602103).

    - **Relação com o projeto:** fundamenta a modularidade registrada em `communities.py`: uma
      partição é avaliada comparando arestas internas observadas com as esperadas sob um modelo
      nulo relacionado à distribuição de graus.
    - **O que aproveitar:** definir formalmente modularidade, explicar estrutura mesoscópica e
      justificar por que grupos densamente conectados e fracamente ligados ao restante podem
      revelar dependência de poucas ligações. O valor de modularidade deve aparecer junto do número
      e tamanho das comunidades.
    - **Cuidado:** o artigo propõe um método espectral; o padrão do projeto é
      `greedy_modularity_communities`, portanto Newman sustenta o conceito, não documenta sozinho o
      algoritmo usado. Otimização de modularidade possui limite de resolução e soluções quase
      ótimas distintas; comparar algoritmos e estabilidade é necessário.

16. **Boeing (2019), _Urban Spatial Order: Street Network Orientation, Configuration, and
    Entropy_.** Referência direta para entropia de orientação e classificação morfológica; compara
    cem cidades com OSMnx.
    DOI: [10.1007/s41109-019-0189-1](https://doi.org/10.1007/s41109-019-0189-1).

    - **Relação com o projeto:** é a base mais próxima de `urban_morphology.py`, que usa bearings,
      entropia angular, dominância de orientações e conectividade. O artigo mede entropia ponderada
      e não ponderada, circuity, comprimento, grau e tipos de interseção em cem cidades.
    - **O que aproveitar:** definir entropia de orientação, justificar histogramas bidirecionais de
      bearings e relacionar ordem geométrica, conectividade e circuity. O desenho com clusterização
      pode orientar uma classificação empírica das cidades/células a partir das métricas, em vez de
      apenas limiares escolhidos manualmente.
    - **Cuidado:** as classes `gradeada`, `radial_linear`, `organica`, `fragmentada` e `mista` e os
      limiares atuais são uma construção do projeto, não uma reprodução validada pelo artigo. Além
      disso, o estudo original compara cidades inteiras; a classificação de células de 1 km exige
      validação própria e análise de sensibilidade.

17. **Boeing (2019), _The Morphology and Circuity of Walkable and Drivable Street Networks_.**
    Sustenta circuity, amostragem de pares OD e a distinção entre redes dirigíveis e caminháveis.
    DOI: [10.1007/978-3-030-12381-9_12](https://doi.org/10.1007/978-3-030-12381-9_12).

    - **Relação com o projeto:** corresponde a `od_efficiency.py`: seleciona pares, calcula
      caminhos mínimos e compara distância em rede com distância em linha reta. Também evidencia
      que redes caminháveis e dirigíveis têm estruturas diferentes.
    - **O que aproveitar:** definir circuity; justificar distância de rede em vez de distância
      euclidiana; relatar algoritmo de caminho mínimo; e realizar estudo de convergência do número
      de pares. O artigo usou 50 mil pares por cidade e declarou explicitamente que pares aleatórios
      caracterizam estrutura, não demanda real.
    - **Cuidado:** as 100 amostras padrão do projeto são pequenas diante do estudo de referência e
      precisam de sensibilidade. Pares uniformemente aleatórios não representam viagens observadas,
      população ou empregos. Como o projeto usa apenas rede `drive`, não pode concluir sobre
      caminhabilidade sem construir e comparar outro grafo.

18. **Spadon et al. (2018), _Caracterização topológica de redes viárias por meio da análise de
    vetores de características e técnicas de agrupamento_.** Antecedente brasileiro muito próximo
    ao módulo de similaridade: extrai métricas do OSM e agrupa 645 municípios do estado de São
    Paulo.
    DOI: [10.5753/sbbd.2018.22227](https://doi.org/10.5753/sbbd.2018.22227).

    - **Relação com o projeto:** é o antecedente brasileiro mais próximo de
      `city_similarity.py`. Representa redes viárias como vetores de características globais e usa
      projeção multidimensional e agrupamento para comparar 645 municípios paulistas.
    - **O que aproveitar:** adotar sua lógica explícita de “cidade como vetor”, documentar seleção
      e padronização de atributos e interpretar agrupamentos pelas métricas que os separam. Também
      fornece uma referência regional para mostrar que cidades distantes podem compartilhar
      propriedades topológicas.
    - **Cuidado:** PCA e agrupamento com apenas quatro observações são instáveis e essencialmente
      descritivos. O grande número de métricas do inventário em relação ao número de cidades aumenta
      o risco de distâncias pouco interpretáveis; é necessário selecionar indicadores por teoria e
      testar sensibilidade.

19. **Lima e Ribeiro (2020), _Distribuição de atividades econômicas e centralidades em redes
    espaciais urbanas: estudo de caso: Lorena (Brasil)_.** Referência brasileira para ligar
    centralidade estrutural e atributos urbanos sem confundir associação com causalidade.
    DOI: [10.24220/2318-0919v17e2020a4338](https://doi.org/10.24220/2318-0919v17e2020a4338).

    - **Relação com o projeto:** mostra, em Lorena (SP), como centralidades geométricas podem ser
      comparadas estatisticamente com uma variável urbana externa. O estudo encontrou associações
      moderadas entre atividades econômicas e medidas geométricas de proximidade/excentricidade.
    - **O que aproveitar:** usar como modelo para uma validação externa futura: associar
      centralidade a estabelecimentos, empregos ou serviços e reportar método, unidade espacial e
      coeficiente de correlação. Ajuda a transformar rankings topológicos em uma pergunta urbana
      testável, especialmente para subcentros.
    - **Cuidado:** `functional_relations.py` relaciona centralidade a atributos das próprias vias,
      não a atividades econômicas, portanto ainda não replica esse tipo de validação. Correlação
      moderada em um caso não prova causalidade nem garante o mesmo padrão nas quatro cidades.

### 3.5 Qualidade e história do OpenStreetMap

20. **Barron, Neis e Zipf (2014), _A Comprehensive Framework for Intrinsic OpenStreetMap Quality
    Analysis_.** Fornece dimensões e indicadores para avaliar qualidade do OSM usando o histórico
    da própria base.
    DOI: [10.1111/tgis.12073](https://doi.org/10.1111/tgis.12073).

    - **Relação com o projeto:** fundamenta `historical_quality.py` e a necessidade de auditar a
      base antes de comparar anos ou atributos. O artigo reúne mais de 25 métodos/indicadores de
      qualidade intrínseca baseados no histórico OSM, sem exigir uma base oficial externa.
    - **O que aproveitar:** organizar qualidade em dimensões e ampliar o relatório com evolução de
      objetos, atividade de edição/contribuidores, estabilidade, completude aparente de tags e
      padrões espaciais. A abordagem reprodutível e extensível combina bem com os manifestos do
      projeto.
    - **Cuidado:** avaliação intrínseca produz indícios, não mede diretamente completude contra a
      realidade. Uma região estável pode estar completa ou simplesmente abandonada. Quando a
      conclusão exigir mudança urbana real, permanece necessária uma fonte externa independente.

21. **Minghini e Frassinelli (2019), _OpenStreetMap History for Intrinsic Quality Assessment: Is
    OSM Up-to-date?_.** Sustenta diretamente a auditoria histórica e a análise de atualização,
    completude e evolução do mapeamento.
    DOI: [10.1186/s40965-019-0067-x](https://doi.org/10.1186/s40965-019-0067-x).

    - **Relação com o projeto:** fornece revisão e ferramenta de avaliação de atualização baseada
      no histórico de objetos OSM. Sustenta a separação entre evolução do banco colaborativo e
      evolução física da cidade feita pelo protocolo histórico.
    - **O que aproveitar:** discutir atualização, temporalidade, _fitness for use_ e heterogeneidade
      espacial da qualidade; incorporar idade/recência das edições e versões dos objetos; e
      justificar por que os anos devem ser classificados antes de qualquer inferência temporal.
    - **Cuidado:** o artigo alerta que IDs de nodes, ways e relations não são identificadores
      permanentes de objetos do mundo real: uma feição pode mudar de ID ou de tipo ao ser editada.
      Como `historical_quality.py` usa interseções de `osmid`, o “núcleo comum” pode subestimar
      correspondências reais. Essa limitação deve entrar no relatório e, idealmente, motivar
      correspondência também por geometria, nome e proximidade.

## 4. Matriz: qual referência sustenta qual parte do projeto

| Parte do projeto | Referências principais | Uso no texto |
|---|---|---|
| Grafo primal e centralidades | Porta et al.; Crucitti et al.; Barthélemy | representação, fórmulas e interpretação |
| Download e simplificação OSM | Boeing 2017; Boeing 2025 | fonte, filtros, topologia, reprodutibilidade |
| Recorte e comparação | Boeing 2020 multiescala; Lin e Ban | escala, normalização e comparabilidade |
| Eficiência | Latora e Marchiori | definição da eficiência global e pares desconectados |
| Ataques aleatórios/dirigidos | Albert et al.; Iyer et al.; Tian et al. | cenários de falha e critérios de remoção |
| Robustez por comunidades | Newman; Duan e Lu | modularidade, grafo agregado e conexões críticas |
| Morfologia e orientação | Boeing 2019 | entropia angular e ordem espacial |
| Circuity e OD amostrado | Boeing 2019, morfologia/circuity | distância em rede versus linha reta |
| Similaridade de cidades | Spadon et al. | vetores, padronização e agrupamento em cidades paulistas |
| Qualidade histórica OSM | Barron et al.; Minghini e Frassinelli | viés de cobertura e limites da inferência temporal |

## 5. Correções conceituais necessárias antes da escrita

1. **Robustez versus resiliência.** As curvas atuais medem robustez: capacidade de manter
   conectividade/eficiência durante remoções. Resiliência, em sentido amplo, inclui absorção,
   adaptação e recuperação no tempo. No texto, usar “robustez estrutural” ou declarar uma definição
   operacional restrita de resiliência. Bruneau et al. (2003) fundamentam a distinção entre
   robustez, redundância, rapidez e recursos; Kozhabek e Chai (2025) oferecem comparação recente de
   estratégias de perturbação em redes viárias. A CLI e a documentação principal foram corrigidas;
   nomes de arquivo com `resilience` permanecem apenas por compatibilidade.

2. **Estrutura não é desempenho real.** Betweenness topológica estima concentração de caminhos
   mínimos; não é fluxo observado. Eficiência ponderada por comprimento não é tempo de viagem.

3. **Grafo simples não dirigido.** Essa transformação é adequada para isolamento da estrutura,
   mas elimina mão única, arestas paralelas e partes funcionais. Resultados do grafo dirigido e do
   não dirigido devem aparecer em blocos distintos.

4. **Maior componente conectada.** Facilita métricas de caminhos, mas exclui componentes menores.
   Informar sua fração em relação à rede original e discutir o que foi removido.

5. **Densidade não é boa métrica comparativa isolada.** Em grafos viários planares, ela cai
   mecanicamente com o número de nós. Priorizar grau, densidade de interseções/viária por área,
   proporções de tipos de interseção, circuity, eficiência normalizada e curvas de robustez.

6. **Limite administrativo não elimina efeitos de escala.** Municípios têm áreas rurais e formas
   distintas. Indicadores por km² ajudam, mas não tornam os recortes morfologicamente equivalentes.

7. **Comunidades dependem do método e da resolução.** Comunidade topológica não equivale
   automaticamente a bairro. Clauset, Newman e Moore (2004) e Blondel et al. (2008) fundamentam os
   métodos disponíveis; Fortunato e Barthélemy (2007) mostram o limite de resolução da modularidade.
   Comparar greedy e Louvain, repetir sementes e medir estabilidade fortaleceria a análise.

8. **Aproximações.** A boa correlação de ranking nos subgrafos valida o procedimento naquele
   desenho experimental, não prova erro igual no grafo municipal completo.

9. **Ataques aleatórios.** A implementação revisada usa 30 repetições por padrão, separa a semente
   do ataque da avaliação e produz IC bootstrap. Outputs legados com cinco sementes ou desvio zero
   em uma única execução devem ser regenerados.

10. **Atributos OSM ausentes.** `surface`, `maxspeed` e `lanes` têm coberturas muito diferentes
    entre cidades. Estimar ausentes pela proporção observada pressupõe ausência ao acaso, hipótese
    forte. Tratar essas análises como exploratórias e reportar a cobertura junto de cada resultado.

11. **História do OSM.** Crescimento de nós, arestas ou extensão pode representar crescimento do
    mapeamento. Anos classificados como não confiáveis não devem apoiar conclusões sobre evolução
    urbana.

12. **Índice composto de vulnerabilidade.** Pesos e normalizações precisam de análise de
    sensibilidade; sem isso, o índice é ferramenta de priorização exploratória, não medida validada.

## 6. Estrutura sugerida para o relatório ou artigo

### 1. Introdução

- importância das redes viárias como redes espaciais;
- problema: diferenças estruturais podem produzir diferentes padrões de vulnerabilidade;
- lacuna: comparação reprodutível de municípios paulistas sob protocolo comum e múltiplos níveis
  de robustez;
- objetivo geral, objetivos específicos, perguntas e hipóteses;
- contribuições pretendidas: pipeline, protocolo para construir uma base comparável, análise
  multi-indicador e discussão de limitações do OSM.

### 2. Fundamentação teórica e trabalhos relacionados

Organizar por conceitos, não por uma lista cronológica de autores:

1. redes complexas espaciais e representação de ruas;
2. métricas estruturais e centralidades;
3. robustez, eficiência e ataques;
4. comunidades e organização mesoscópica;
5. OSM, reprodutibilidade e qualidade de dados;
6. estudos comparativos e brasileiros.

Ao fim de cada subseção, dizer explicitamente como a literatura orienta uma escolha do projeto.

### 3. Materiais e métodos

- cidades, justificativa da amostra e unidade de análise;
- data do snapshot OSM, filtro `drive`, limites administrativos e versões;
- construção do `MultiDiGraph` e transformação para grafo simples não dirigido;
- componente analisada e atributos preservados;
- definição matemática de cada métrica realmente interpretada;
- algoritmos de comunidades e parâmetros;
- cenários de remoção, fração máxima, passos, amostras, sementes e critérios de ataque;
- respostas: LCC, componentes e eficiências retidas;
- protocolo de comparação e normalização;
- validação das aproximações e análise de sensibilidade;
- limitações e manifesto de reprodutibilidade.

### 4. Resultados

Separar descrição de interpretação:

1. qualidade/cobertura da base;
2. estrutura global comparada;
3. centralidades e elementos críticos;
4. curvas de robustez com incerteza;
5. estrutura e robustez das comunidades;
6. resultados espaciais e multiescala;
7. síntese das hipóteses, uma tabela com “apoiada / não apoiada / inconclusiva”.

### 5. Discussão

- explicar mecanismos possíveis, sem linguagem causal;
- confrontar resultados com trabalhos semelhantes;
- discutir efeito de área, geometria, hierarquia viária e qualidade do OSM;
- distinguir significância estatística, magnitude do efeito e relevância urbana;
- explicitar o que os resultados não permitem concluir.

### 6. Conclusão

- responder diretamente à pergunta central;
- sintetizar diferenças observadas sem eleger uma “melhor cidade” por um único número;
- apresentar contribuições, limites e próximos passos.

## 7. Análises mínimas recomendadas antes do texto final

1. **Implementado com contrato fail-closed:** calcular uma área sob cada curva de robustez (AUC) para LCC e eficiências
   retidas, com a mesma faixa de remoção em todas as cidades. O comando `robustness-summary`
   também calcula perdas padronizadas e limiares de degradação.
2. **Implementado no software; pendente regenerar os quatro datasets:** ataques aleatórios com 30
   repetições, média, distribuição e intervalo de confiança, mantendo sementes registradas.
3. Reportar diferenças entre ataque aleatório e dirigido como tamanho de efeito, não apenas por
   inspeção visual.
4. Fazer análise de sensibilidade de `k_edge`, `k_node`, número de fontes de eficiência e tamanho
   das células espaciais.
5. Comparar ao menos greedy e Louvain para comunidades, incluindo modularidade e estabilidade da
   partição.
6. Criar modelos nulos compatíveis com redes espaciais ou, no mínimo, comparar com controles que
   preservem tamanho e distribuição de grau; não usar Erdős-Rényi como único controle.
7. Separar uma tabela de indicadores primários, ligados às hipóteses, das dezenas de indicadores
   exploratórios para reduzir risco de seleção posterior de resultados.
8. Validar manualmente uma amostra de nós/arestas críticos no mapa e documentar casos em que a
   abstração topológica não corresponde a um gargalo funcional real.

## 8. Prioridade de leitura

Se houver tempo para apenas oito leituras, a ordem recomendada é:

1. Barthélemy (2011);
2. Porta, Crucitti e Latora (2006);
3. Boeing (2017, OSMnx);
4. Latora e Marchiori (2001);
5. Duan e Lu (2013);
6. Boeing (2020, multiescala);
7. Spadon et al. (2018);
8. Barron, Neis e Zipf (2014).

Leituras metodológicas adicionais agora incluídas no BibTeX: Clauset, Newman e Moore (2004),
Blondel et al. (2008), Fortunato e Barthélemy (2007), Bruneau et al. (2003), Kozhabek e Chai
(2025) e a licença/atribuição oficial do OpenStreetMap.

As entradas BibTeX correspondentes estão em `docs/referencias_ic.bib`.

## 9. Funções computacionais sugeridas pela revisão

O cruzamento detalhado entre a literatura, os módulos existentes e as próximas implementações está
em [Próximas funções computacionais orientadas pela revisão bibliográfica](proximas_funcoes_computacionais_bibliografia.md).

A prioridade não é adicionar métricas indiscriminadamente. A síntese das curvas de robustez por
AUC, a incerteza com 30 repetições e a auditoria das representações já foram implementadas; os
próximos itens são regenerar os experimentos, aprofundar a auditoria de sensibilidade e avaliar a
estabilidade das comunidades. As expansões
mais aderentes ao tema são caminhos alternativos independentes e simulação de recuperação
estrutural.
