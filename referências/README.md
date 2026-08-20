# Quatro referências acadêmicas selecionadas para o projeto

Seleção preparada em 20 de agosto de 2026 após a leitura do plano de trabalho, da
documentação científica e dos módulos do repositório. Os quatro trabalhos abaixo têm DOI,
publicação acadêmica e uma versão integral de acesso aberto para download.

## Como esta seleção foi feita

O projeto atual:

- constrói, com OpenStreetMap e OSMnx, grafos primais das redes dirigíveis de Campinas,
  Jundiaí, Sorocaba e Valinhos;
- calcula métricas estruturais, centralidades, comunidades, caminhos mínimos e proxies de
  morfologia urbana;
- avalia **robustez estrutural** por remoções aleatórias e dirigidas de nós, arestas e ligações
  comunitárias, observando a maior componente conectada e eficiências topológica e ponderada;
- compara cidades e escalas, mas ainda deve tratar as quatro cidades como estudo de caso
  exploratório, não como amostra representativa do Brasil;
- ainda precisa regenerar os quatro conjuntos com recorte, snapshot OSM e proveniência comuns
  antes de transformar os resultados existentes em conclusões científicas.

Por isso, foram priorizados trabalhos que ajudam diretamente em quatro decisões do projeto:
comparar cidades, desenhar os ensaios de robustez, controlar escala/representação e interpretar
centralidades. Não foram escolhidos estudos que dependem principalmente de tráfego observado,
pois esse tipo de dado ainda não faz parte do recorte principal.

## Visão rápida

| Referência | Eixo coberto | Relação mais direta com o repositório | Prioridade |
|---|---|---|---|
| Spadon, Gimenes e Rodrigues-Jr. (2018) **[BRASIL]** | comparação de cidades | `city_similarity.py`, seleção de métricas e ampliação da amostra | muito alta |
| Kozhabek e Chai (2025) | robustez sob perturbações | `node_resilience.py`, `random_resilience_stats.py`, `spatial_robustness.py` | muito alta |
| Boeing (2020) | OSMnx, recorte e multiescala | `download.py`, `representation_audit.py`, `network_scale_profile.py` | muito alta |
| Crucitti, Latora e Porta (2006) | centralidades espaciais | `centrality.py`, `od_efficiency.py`, `vulnerability_index.py` | alta |

---

## 1. Spadon, Gimenes e Rodrigues-Jr. (2018) - referência brasileira

**Referência:** SPADON, Gabriel; GIMENES, Gabriel; RODRIGUES-JR., Jose F. *Topological
Street-Network Characterization Through Feature-Vector and Cluster Analysis*. In:
Computational Science - ICCS 2018. Lecture Notes in Computer Science, v. 10860, p. 274-287,
2018. DOI: 10.1007/978-3-319-93698-7_21.

- [Página oficial/DOI](https://doi.org/10.1007/978-3-319-93698-7_21)
- [Baixar PDF aberto no arquivo oficial do ICCS](https://www.iccs-meeting.org/archive/iccs2018/papers/108600275.pdf)
- Nome sugerido: `01_spadon_gimenes_rodrigues_2018_comparacao_cidades_sp.pdf`

### Por que é muito parecido

É o antecedente brasileiro mais próximo da comparação proposta no repositório. O estudo usa
mapas digitais e redes complexas para representar **645 municípios do estado de São Paulo**,
extrai métricas globais, transforma cada cidade em um vetor de características e aplica projeção
multidimensional e agrupamento. As quatro cidades atuais do projeto estão no mesmo estado e o
módulo `city_similarity.py` segue a mesma lógica geral de comparar vetores de métricas.

### Pontos fortes aproveitáveis

- amostra grande o bastante para estudar grupos de cidades, em vez de interpretar um agrupamento
  construído sobre apenas quatro observações;
- separação clara entre aquisição/preparo, extração/seleção de características e análise dos
  vetores;
- redução de métricas redundantes por correlação antes da projeção e do agrupamento;
- comparação topológica acompanhada de indicadores territoriais e demográficos para interpretar,
  sem misturar, estrutura da rede e contexto urbano.

### Como incorporar ao projeto

1. Usar o artigo para fundamentar a seção de trabalhos brasileiros relacionados e a representação
   de cada cidade como vetor de métricas.
2. Manter a comparação atual de quatro cidades explicitamente descritiva e ampliar a amostra antes
   de afirmar a existência de classes, padrões universais ou um retrato brasileiro.
3. Antes de PCA ou agrupamento, publicar uma matriz de correlação e selecionar um conjunto
   pequeno de métricas não redundantes com justificativa teórica. O conjunto reduzido já previsto
   em `city_similarity.py` é um bom ponto de partida.
4. Testar estabilidade: repetir o agrupamento com padronizações, subconjuntos de métricas e
   reamostragens diferentes; relatar quando a posição de uma cidade muda.
5. Usar população, área e densidade urbana apenas como variáveis externas de interpretação, não
   como substitutas silenciosas das métricas topológicas.

**Cuidado:** métricas só são diretamente comparáveis se recorte, versão do OSM, construção do
grafo, direção, pesos e simplificação forem comuns. O tamanho da amostra do artigo não corrige
diferenças metodológicas entre datasets.

---

## 2. Kozhabek e Chai (2025) - o espelho mais próximo dos ensaios de robustez

**Referência:** KOZHABEK, Assemgul; CHAI, Wei Koong. *Robustness Assessment of Urban
Road Networks in Densely Populated Cities*. Applied Network Science, v. 10, art. 29, 2025.
DOI: 10.1007/s41109-025-00707-w.

- [Página oficial/DOI](https://doi.org/10.1007/s41109-025-00707-w)
- [Baixar PDF oficial aberto (CC BY)](https://appliednetsci.springeropen.com/counter/pdf/10.1007/s41109-025-00707-w.pdf)
- Nome sugerido: `02_kozhabek_chai_2025_robustez_redes_viarias.pdf`

### Por que é muito parecido

O artigo compara dez redes viárias reais por remoção iterativa de nós. Usa cinco estratégias
dirigidas baseadas em centralidade - grau, intermediação, proximidade, Katz e carga - e duas
estratégias aleatórias. A resposta é medida por maior componente conectada, eficiência global e
eficiência local. Isso coincide diretamente com os módulos de robustez por vértices e com a síntese
de curvas do projeto.

### Pontos fortes aproveitáveis

- compara vários critérios de ataque, evitando que “ataque dirigido” signifique apenas uma única
  ordenação;
- separa impacto global, conectividade e efeito local;
- repete os cenários estocásticos e apresenta intervalos de confiança;
- usa checkpoints e limiares de degradação, o que facilita comparações entre redes de tamanhos
  diferentes;
- inclui um cenário aleatório regional, mais próximo de um bloqueio espacial do que remoções
  independentes distribuídas pela cidade.

### Como incorporar ao projeto

1. Preservar LCC e eficiências topológica/ponderada como respostas primárias; elas já permitem
   comparação direta com o desenho do artigo.
2. Acrescentar, como análise de sensibilidade, ataques de nós por grau e proximidade, além da
   intermediação já implementada. Carga ou Katz podem ficar para uma segunda etapa.
3. Publicar perdas nos mesmos checkpoints para todas as cidades - por exemplo 5%, 10% e 15% - e
   limiares para quedas de 25%, 50% e 90%, além da AUC já calculada.
4. Comparar explicitamente ranking estático e ataque adaptativo. O repositório já possui as duas
   ideias e deve tratá-las como cenários distintos, não como execuções equivalentes.
5. Usar o cenário de “área aleatória” como inspiração para conectar `spatial_robustness.py` aos
   ensaios estocásticos, com múltiplas sementes e intervalo de confiança.
6. Se eficiência local for adicionada, documentar que ela pode aumentar depois de uma remoção
   porque muda a composição das vizinhanças; ela não é uma curva necessariamente monotônica.

**Cuidado:** o artigo continua as remoções sobre a nova maior componente depois da fragmentação,
enquanto o projeto também conserva denominadores ligados ao conjunto original. As duas convenções
podem produzir curvas diferentes; a convenção usada deve aparecer no método e nos nomes das
colunas.

---

## 3. Boeing (2020) - protocolo comparativo, OSMnx e efeito de escala

**Referência:** BOEING, Geoff. *A Multi-Scale Analysis of 27,000 Urban Street Networks: Every
US City, Town, Urbanized Area, and Zillow Neighborhood*. Environment and Planning B: Urban
Analytics and City Science, v. 47, n. 4, p. 590-608, 2020. DOI:
10.1177/2399808318784595.

- [Página oficial/DOI](https://doi.org/10.1177/2399808318784595)
- [Baixar manuscrito integral no arXiv](https://arxiv.org/pdf/1705.02198)
- Nome sugerido: `03_boeing_2020_multiescala_osmnx.pdf`

### Por que é muito parecido

O estudo usa OpenStreetMap e OSMnx para adquirir e analisar 27 mil redes de ruas em escalas
metropolitana, municipal e de bairro. Trabalha com grafos primais, dirigidos, ponderados e não
planares, e discute estrutura, conectividade, densidade, centralidade, morfologia e reprodutibilidade.
É a melhor referência para justificar a fonte de dados, o recorte espacial e a análise multiescalar
do projeto.

### Pontos fortes aproveitáveis

- definições explícitas de rede, área de estudo e extensão espacial;
- coleta automatizada e consistente em grande escala;
- uso de buffer antes do recorte final para reduzir efeitos artificiais nas bordas;
- separação entre comprimento dirigido usado no roteamento e comprimento físico de ruas;
- normalização de métricas por área e comparação de resultados entre escalas;
- preservação de direção, multiplicidade e não planaridade na representação principal.

### Como incorporar ao projeto

1. Na metodologia, registrar para cada dataset: limite, data/snapshot OSM, consulta, versão do
   OSMnx, `network_type`, política de buffer/truncamento, simplificação e retenção de componentes.
2. Usar `representation_audit.py` para mostrar quanto os resultados mudam entre o MultiDiGraph
   dirigido original e o grafo simples não dirigido empregado por várias métricas.
3. Apresentar densidade viária física e extensão dirigida separadamente, evitando contar duas vezes
   uma rua bidirecional como infraestrutura construída.
4. Repetir um subconjunto das métricas em pelo menos dois recortes comparáveis - limite
   administrativo e janela/área urbanizada padronizada - e usar `network_scale_profile.py` para
   relatar sensibilidade.
5. Congelar a aquisição e executar os quatro municípios com a mesma versão de código e os mesmos
   parâmetros antes da tabela comparativa final.

**Cuidado:** os resultados empíricos dos Estados Unidos não são valores de referência esperados
para municípios paulistas. O que deve ser transferido é o protocolo de coleta, representação,
normalização e sensibilidade à escala.

---

## 4. Crucitti, Latora e Porta (2006) - centralidades em redes urbanas espaciais

**Referência:** CRUCITTI, Paolo; LATORA, Vito; PORTA, Sergio. *Centrality Measures in Spatial
Networks of Urban Streets*. Physical Review E, v. 73, 036125, 2006. DOI:
10.1103/PhysRevE.73.036125.

- [Página oficial/DOI](https://doi.org/10.1103/PhysRevE.73.036125)
- [Baixar manuscrito integral no arXiv](https://arxiv.org/pdf/physics/0504163)
- Nome sugerido: `04_crucitti_latora_porta_2006_centralidades.pdf`

### Por que é muito parecido

O artigo representa dezoito redes urbanas - incluindo Brasília - como grafos primais espaciais e
métricos. Compara proximidade, intermediação, *straightness* e centralidade de informação, produz
mapas temáticos e analisa distribuições de centralidade para distinguir padrões urbanos. Ele
fundamenta a ideia já presente no projeto de que diferentes centralidades respondem a perguntas
diferentes.

### Pontos fortes aproveitáveis

- preserva a geografia e o comprimento das arestas, em vez de analisar apenas número de saltos;
- usa avaliação por múltiplas centralidades, sem eleger uma medida universal;
- compara distribuições e padrões espaciais, não somente os maiores valores de um ranking;
- usa amostras de mesma área, tornando explícito o controle de escala;
- conecta centralidade de informação à perda de eficiência provocada pela retirada de um elemento.

### Como incorporar ao projeto

1. Separar claramente centralidade topológica e centralidade ponderada por comprimento em metros;
   as duas têm interpretações diferentes.
2. Acrescentar mapas e estatísticas das distribuições - quantis, concentração/Gini e correlações
   entre medidas - além dos rankings de nós mais centrais.
3. Implementar *straightness centrality* como extensão de `centrality.py` ou relacioná-la
   explicitamente aos resultados de circuity e eficiência origem-destino já disponíveis.
4. Implementar centralidade de informação como medida direta da queda de eficiência após a
   retirada de cada nó/aresta, comparando-a ao índice composto de vulnerabilidade.
5. Repetir a análise em janelas de área semelhante como teste de sensibilidade aos limites
   administrativos.

**Cuidado:** centralidade estrutural indica posição no grafo; não comprova volume de tráfego,
demanda de viagens, atividade econômica ou importância social. Essas interpretações exigem dados
externos.

---

## Ordem recomendada de incorporação

### Etapa 1 - necessária para o relatório atual, sem ampliar o código

1. Citar Boeing para justificar aquisição, representação, recorte e controle de escala.
2. Citar Crucitti, Latora e Porta para justificar a leitura conjunta de centralidades.
3. Citar Kozhabek e Chai para definir robustez estrutural, respostas e estratégias de remoção.
4. Citar Spadon, Gimenes e Rodrigues-Jr. como antecedente brasileiro e limitar a comparação atual a
   quatro estudos de caso.
5. Regenerar os quatro datasets sob um protocolo comum antes de interpretar diferenças.

### Etapa 2 - melhorias de baixo a médio esforço

1. Acrescentar ataques por grau e proximidade e compará-los à intermediação.
2. Padronizar checkpoints, limiares e AUC em todas as curvas.
3. Publicar matriz de correlação e análise de sensibilidade do vetor de similaridade.
4. Comparar recorte administrativo com um segundo recorte espacial padronizado.

### Etapa 3 - extensões para uma versão posterior do trabalho

1. Ampliar e diversificar a amostra de cidades antes de usar PCA ou agrupamentos inferenciais.
2. Implementar *straightness* e centralidade de informação.
3. Avaliar eficiência local e perturbações espaciais estocásticas.
4. Validar centralidades e vulnerabilidades com uma fonte externa, se o escopo passar a incluir
   tráfego, atividades ou perigos observados.

## Parágrafo-base para a seção de trabalhos relacionados

> Estudos de redes viárias urbanas mostram que a comparabilidade depende simultaneamente da
> representação do grafo, da escala espacial e da seleção das métricas. No contexto brasileiro,
> Spadon, Gimenes e Rodrigues-Jr. (2018) representaram 645 municípios paulistas por vetores de
> características topológicas e aplicaram projeção e agrupamento para identificar similaridades.
> Em escala mais ampla, Boeing (2020) utilizou OpenStreetMap e OSMnx para analisar 27 mil redes em
> diferentes extensões espaciais, enfatizando definições reprodutíveis de recorte e representação.
> Para a leitura da importância estrutural de interseções, Crucitti, Latora e Porta (2006)
> demonstraram que múltiplas centralidades métricas oferecem visões complementares da forma
> urbana. Finalmente, Kozhabek e Chai (2025) avaliaram a degradação de redes viárias sob remoções
> aleatórias e dirigidas por diferentes centralidades, acompanhando conectividade e eficiência.
> Esses trabalhos sustentam uma comparação exploratória das redes viárias paulistas baseada em
> protocolo comum, múltiplas respostas de robustez e interpretação cautelosa de proxies
> estruturais.

O parágrafo é uma síntese original preparada para este projeto; ajuste-o à norma bibliográfica e à
seção em que será usado.

## Arquivos complementares desta pasta

- [`links_para_download.md`](links_para_download.md): lista curta dos quatro PDFs para baixar;
- [`referencias_selecionadas.bib`](referencias_selecionadas.bib): entradas BibTeX prontas para o
  gerenciador de referências ou LaTeX.
