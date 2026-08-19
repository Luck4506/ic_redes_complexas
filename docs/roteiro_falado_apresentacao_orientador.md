# Roteiro falado para apresentar os aprimoramentos ao orientador

Este roteiro foi escrito para ser falado, não lido como um artigo. As frases podem ser adaptadas
ao seu jeito de falar. O ponto central é diferenciar **o que o programa já faz** de **quais
conclusões científicas já podem ser defendidas**.

## Versão principal — aproximadamente 6 a 8 minutos

Professor, eu organizei esta evolução do projeto tomando como referência direta o plano de
trabalho da Iniciação Científica. O objetivo não foi simplesmente acrescentar mais análises, mas
transformar o que existia em uma base computacional mais rigorosa, rastreável e adequada para
produzir resultados científicos depois.

O plano propõe cinco frentes principais: calcular métricas estruturais, analisar centralidades,
avaliar a rede pela remoção de vértices e arestas, comparar diferentes cidades e criar
visualizações interativas. Hoje existe implementação computacional para essas cinco frentes,
embora nem todas já estejam encerradas como resultado científico.

No começo, o projeto já tinha várias análises e muitos arquivos gerados, mas havia um problema
importante: a existência de um arquivo não comprovava que ele tinha sido produzido com a mesma
versão dos dados, o mesmo recorte territorial, os mesmos parâmetros e o mesmo código dos outros
resultados. Isso poderia levar a uma comparação aparentemente correta, mas metodologicamente
frágil.

Por isso, a principal melhoria foi estruturar o projeto como uma pipeline científica. Agora cada
execução pode registrar quais dados entraram, quais parâmetros foram usados, qual versão do código
estava ativa, quais arquivos foram produzidos e quais são os seus hashes. Também foram criadas
auditorias que bloqueiam automaticamente resultados incompletos, antigos ou sem evidência
suficiente. A ideia foi fazer o sistema dizer “esta comparação ainda não está comprovada” quando
não houver evidência, em vez de aceitar silenciosamente arquivos incompatíveis.

Na primeira parte do plano, sobre métricas estruturais, o sistema calcula distribuição de graus,
clustering, caminhos médios, diâmetro, densidade e assortatividade. Também foram implementadas as
quatro centralidades previstas no PDF: grau, intermediação, proximidade e autovetor. Os rankings
passaram a ser completos, e não somente listas reduzidas para apresentação. Foi criado um arquivo
completo de centralidade das arestas, porque um ranking apenas dos primeiros trechos não é
suficiente para alimentar análises posteriores de vulnerabilidade.

Algumas correções metodológicas foram feitas nessa parte. A aproximação da centralidade de
proximidade foi corrigida, e as métricas aproximadas passaram a ser comparadas com cálculos exatos
em subgrafos controlados. Betweenness e closeness apresentaram boa estabilidade de ranking nesses
testes, enquanto o clustering aproximado exige mais cautela. Isso é importante porque os grafos
municipais são grandes e alguns cálculos exatos seriam muito caros, mas uma aproximação não deve
ser usada sem avaliar o erro.

Outra melhoria relevante foi a auditoria da representação do grafo. A mesma rede pode ser
representada como grafo dirigido ou não dirigido, com vias paralelas ou com essas vias colapsadas.
Essa escolha altera o resultado. Nas quatro cidades avaliadas, o comprimento físico estimado ficou
aproximadamente 40% a 43% menor que a soma dirigida usada para roteamento. Também houve mudanças
importantes nos rankings de nós. Por isso, o projeto agora separa claramente a extensão dirigida,
adequada para rotas, da extensão física, mais apropriada como proxy de densidade viária. Assim, os
dois sentidos de uma mesma rua não são automaticamente contados como duas ruas físicas.

Na parte de remoções, o plano usa o termo resiliência. No código e na documentação, eu passei a
usar uma definição mais precisa: robustez estrutural sob remoção. O sistema mede quanto a
conectividade e a eficiência se degradam quando nós ou arestas são retirados. Ele não observa
reparo, adaptação ou recuperação ao longo do tempo; por isso, chamar simplesmente de resiliência
poderia dar ao experimento um significado maior do que ele realmente possui.

Foram implementadas remoções de arestas e vértices com três estratégias: aleatória, dirigida pela
importância inicial e dirigida adaptativa, que recalcula a importância durante o ataque. Também
existem análises entre comunidades e dentro das comunidades. Dessa forma, é possível verificar
não apenas se a rede inteira se fragmenta, mas também se certas regiões topológicas dependem de
poucas ligações.

Os ataques aleatórios agora usam trinta repetições por padrão. O projeto calcula média, desvio,
erro-padrão, quantis e intervalo de confiança por bootstrap. Antes, uma única execução poderia
parecer uma medida definitiva. Agora o resultado incorpora a variação causada pelo sorteio das
remoções. Quando há somente uma repetição, a incerteza fica como não disponível, em vez de aparecer
como zero e transmitir uma falsa precisão.

Para a comparação entre cidades, foram organizados recortes de Campinas, Jundiaí, Sorocaba e
Valinhos, além de métricas normalizadas por área. Aqui é importante separar a capacidade do
sistema de comparar cidades da validade científica das comparações já armazenadas.

O programa consegue gerar tabelas, gráficos, mapas e dashboards comparativos. Porém, os arquivos
antigos não possuem toda a proveniência exigida pelo protocolo atual. Dos dez artefatos
obrigatórios por cidade, somente dois têm a cobertura de proveniência necessária. Também faltam
evidências completas do instante consultado no OpenStreetMap e da identidade dos limites. Por
isso, os seis pares possíveis entre as quatro cidades estão classificados como “comparabilidade
não comprovada”. Isso não significa que os valores estejam necessariamente errados; significa
que ainda não existe evidência suficiente para tratá-los como comparação científica final.

Essa distinção é fundamental: a suíte de software está validada por 104 testes automatizados, mas
teste de software não substitui validação científica dos dados. Os testes mostram que regras,
cálculos e bloqueios funcionam como esperado. Para validar conclusões entre cidades, ainda é
necessário regenerar os quatro conjuntos com o código atual, um snapshot OSM documentado, limites
verificáveis e parâmetros homogêneos, e depois obter aprovação nos gates de integridade e
comparabilidade.

Também foram adicionados módulos que aprofundam pontos da justificativa e dos resultados esperados
do plano: pontes e articulações, gargalos estruturais, redundância de rotas, vulnerabilidade por
região, hierarquia viária, comunidades e mapas de elementos críticos. Outros módulos, como
morfologia, candidatos a subcentros, barreiras e análise multiescala, são tratados como
exploratórios. Eles ajudam a formular hipóteses, mas não são apresentados como validação urbana
sem dados de tráfego, população, empregos ou atividades.

Neste momento, a conclusão segura é que o projeto avançou muito em capacidade computacional,
rigor metodológico e reprodutibilidade. O que já está comprovado é o funcionamento da pipeline, a
cobertura computacional dos objetivos, as correções dos contratos de cálculo e a importância da
representação do grafo. O que ainda não deve ser afirmado são padrões universais das cidades
brasileiras, relações causais com o transporte ou um ranking científico definitivo entre as quatro
cidades.

Os próximos passos são executar novamente toda a pipeline de forma homogênea, liberar os
resultados pelos gates, formular perguntas e hipóteses explícitas, interpretar quantitativa e
qualitativamente os dados e ampliar a diversidade geográfica da amostra antes de discutir padrões
nacionais. Também permanecem as entregas acadêmicas previstas no cronograma, como relatório
parcial, participação no encontro, artigo e relatório final.

Em resumo, o projeto deixou de ser apenas um conjunto amplo de scripts e resultados para se tornar
uma infraestrutura de pesquisa que sabe calcular, registrar, verificar e, quando necessário,
recusar uma conclusão sem evidência suficiente. Esse é o principal avanço: não apenas produzir
mais resultados, mas tornar os próximos resultados mais confiáveis e defensáveis.

## Versão curta — aproximadamente 1 minuto

Professor, eu revisei o repositório usando os objetivos do plano original como referência. Hoje
existe implementação para as cinco frentes computacionais previstas: métricas estruturais,
centralidades, remoção de nós e arestas, comparação entre cidades e visualizações interativas.

O principal avanço foi transformar o projeto em uma pipeline científica rastreável. Cada execução
pode registrar dados, parâmetros, versões, código e arquivos gerados, e novas auditorias impedem o
uso de resultados antigos ou incompatíveis. A suíte passou de 29 para 104 testes.

Também refinei a análise de robustez, com remoções aleatórias, dirigidas e adaptativas, trinta
repetições e intervalos de confiança. Corrigi contratos de centralidade e auditei como a
representação do grafo altera as métricas.

Ao mesmo tempo, separei capacidade computacional de conclusão científica. Os quatro municípios
atuais são estudos de caso paulistas, e os outputs antigos ainda não têm proveniência suficiente
para sustentar comparações definitivas. O próximo passo é regenerar tudo com snapshot OSM e
limites documentados, passar pelos gates e então realizar a interpretação científica. Portanto, a
base ficou muito mais completa e defensável, mas sem antecipar conclusões que os dados ainda não
comprovam.

## Perguntas prováveis e respostas seguras

### “O projeto está concluído?”

A parte computacional do núcleo do plano tem cobertura ampla, mas o projeto científico não está
concluído. Ainda faltam a execução homogênea, a interpretação dos resultados, a avaliação
quantitativa e qualitativa e as entregas acadêmicas A2, A4, A7 e A8.

### “Se os 104 testes passam, por que os resultados não estão liberados?”

Os testes verificam o comportamento do software. A liberação científica depende também da origem
e da compatibilidade dos dados. Os outputs antigos não registram integralmente o snapshot do OSM,
a identidade dos limites e a proveniência dos artefatos. Código correto não torna automaticamente
dados antigos comparáveis.

### “Então os resultados antigos estão errados?”

Não necessariamente. O estado correto é “não comprovados”, não “errados”. Eles continuam úteis
para demonstração e exploração, mas precisam ser regenerados antes de sustentar conclusões.

### “Por que trocar resiliência por robustez estrutural?”

Porque o experimento mede degradação sob remoção. Resiliência, em sentido mais amplo, incluiria
recuperação e adaptação temporal. É possível dizer que o projeto operacionaliza uma dimensão
estrutural da resiliência, mas a medida implementada é, com mais precisão, robustez.

### “Quatro cidades permitem falar da rede viária brasileira?”

Não como conclusão geral. As quatro cidades formam um estudo de caso regional. Elas permitem
testar o método e gerar hipóteses, mas afirmações nacionais ou universais exigem uma amostra maior
e geograficamente diversa.

### “Qual foi a melhoria mais importante?”

A criação da cadeia de evidência. Antes, um arquivo existente podia ser tratado como resultado.
Agora o sistema verifica origem, parâmetros, versões, hashes, integridade e comparabilidade, e
bloqueia a conclusão quando a evidência é insuficiente.

### “Qual resultado concreto já apareceu?”

O resultado metodológico mais sólido é que a representação do grafo afeta materialmente as
medidas. Nas quatro cidades, a extensão física colapsada ficou cerca de 40% a 43% abaixo da soma
dirigida, e alguns rankings de centralidade mudaram bastante.

### “As aproximações são confiáveis?”

Nos subgrafos controlados, betweenness e closeness mostraram boa estabilidade de ranking. Isso
sustenta seu uso exploratório, mas não prova que o erro seja igual no grafo municipal completo. O
clustering aproximado mostrou maior instabilidade e exige cautela.

### “Como os módulos extras se relacionam com o PDF?”

Pontes, articulações, gargalos, vulnerabilidade, comunidades e redundância aprofundam a
identificação de pontos críticos e o estudo de remoções. Morfologia, subcentros e barreiras são
extensões exploratórias e não substituem os objetivos centrais.

### “Foi estabelecida relação entre topologia e funcionamento do transporte?”

Ainda apenas de forma descritiva, usando atributos do OSM. Isso não comprova fluxo,
congestionamento, demanda ou causalidade. Uma validação forte exigiria dados externos, como
tráfego, população, empregos ou viagens observadas.

### “Por que usar limites administrativos?”

Eles oferecem uma regra repetível e mais padronizada do que caixas geográficas arbitrárias. Mesmo
assim, limite administrativo não é sinônimo de mancha urbanizada; por isso, convém fazer análise
de sensibilidade ao recorte.

### “O que falta imediatamente?”

Documentar o snapshot do OSM e os limites, regenerar as quatro cidades com o código atual,
produzir todos os artefatos, passar nas auditorias e só então atualizar tabelas e conclusões.

### “Você encontrou algum problema no próprio plano?”

Sim. A capa e o texto indicam setembro de 2026 a agosto de 2027, mas o cabeçalho da Tabela 6.1
mostra 2025 e 2026. Parece uma inconsistência editorial e deve ser corrigida para 2026 e 2027.

## Vocabulário recomendado

| Prefira dizer | Evite dizer |
|---|---|
| “Existe implementação computacional para os cinco objetivos.” | “O projeto científico está 100% concluído.” |
| “Os resultados atuais são exploratórios até a regeneração.” | “Os testes comprovam que as cidades são comparáveis.” |
| “A comparabilidade ainda não foi comprovada.” | “As quatro cidades representam o Brasil.” |
| “O módulo mede robustez estrutural sob remoção.” | “A rede é resiliente em situações reais.” |
| “Foram identificados candidatos topológicos a pontos críticos.” | “Os pontos mais críticos no trânsito real foram provados.” |
| “Os quatro municípios constituem estudos de caso regionais.” | “Foram descobertos padrões universais brasileiros.” |
| “A associação usa atributos OSM, sem inferência causal.” | “A análise explica o funcionamento real do transporte.” |

## Checklist para a reunião

- apresentar primeiro os cinco objetivos do PDF;
- explicar a diferença entre implementação, validação científica e entrega acadêmica;
- usar os 104 testes como evidência de engenharia, não como prova urbana;
- mostrar um exemplo concreto: extensão física 40%–43% menor que a dirigida;
- dizer espontaneamente que os outputs antigos estão `nao_comprovada`;
- explicar os passos objetivos para liberá-los;
- reservar módulos heurísticos para a seção de expansões;
- apontar a inconsistência 2025–2026 versus 2026–2027 no cronograma;
- encerrar com o plano de regeneração, análise e escrita acadêmica.
