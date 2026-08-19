# Protocolo de comparação entre cidades

## Regra principal

Uma comparação só pode sustentar interpretação científica quando cada requisito abaixo possui
evidência verificável. Ausência de metadado é **não comprovado**, nunca equivalência presumida.

Estados permitidos:

- `confirmada`: todos os critérios obrigatórios foram verificados;
- `nao_comprovada`: pode haver homogeneidade, mas falta evidência de um ou mais critérios;
- `incomparavel`: há diferença conhecida que invalida a comparação pretendida.

`exploratorio` é um **perfil separado**, menos estrito e gravado em artefatos próprios; não é
um quarto estado. Ele também retorna apenas os três estados acima e serve à descrição e à
geração de hipóteses, nunca à confirmação científica.

## Critérios obrigatórios

1. Mesma definição da unidade espacial: tipo de limite e identidade verificável — relação/geometria
   para `place`, ou parâmetros canônicos para bbox/radius; áreas parecidas não provam equivalência.
2. Mesmo `network_type`, política de simplificação e regras de pré-processamento.
3. Mesmo snapshot histórico do OSM. Uma consulta “atual” sem data congelada deve ser marcada como
   `live_unfrozen`; duas consultas ao vivo não são automaticamente coetâneas.
4. Mesma versão do código, ou diferenças documentadas, incluindo commit, estado sujo e hash do
   diff quando aplicável.
5. Mesmos argumentos resolvidos e configurações, com sementes do ataque e da avaliação separadas.
6. Hashes SHA-256 dos grafos raw/clean e dos produtos científicos primários.
7. Matriz obrigatória de artefatos completa, íntegra e mais recente que suas entradas.
8. Mesma representação para cada estimando: dirigida/múltipla para roteamento; simples não
   dirigida apenas quando o objetivo topológico justificar a perda de direção/multiplicidade.
9. Mesma fração de remoção efetivamente observada e mesma definição do eixo. AUC de nós e arestas
   não é diretamente intercambiável: a unidade removida é diferente.
10. Mesma regra de incerteza; ataques aleatórios devem ter ao menos 30 repetições ou justificativa
    explícita, com intervalo de confiança.

## Indicadores normalizados

Relate sempre tamanho bruto e denominador:

- nós por km²;
- extensão física colapsada por km², separada da extensão dirigida de roteamento;
- fração da maior componente em relação ao grafo raw e ao clean;
- cobertura de tags OSM e quantidade de valores desconhecidos;
- fração amostrada/avaliada em procedimentos aproximados.

Limites administrativos incluem áreas rurais em proporções diferentes. A análise de sensibilidade
município × mancha urbanizada é necessária antes de atribuir diferenças à forma urbana.

## Situação dos quatro datasets administrativos

`campinas_admin`, `jundiai_admin`, `sorocaba_admin` e `valinhos_admin` correspondem aos YAMLs de
`config/comparable/`, com limite municipal, `network_type=drive` e simplificação. Os YAMLs bbox
na raiz de `config/` constituem outro desenho e não podem ser misturados. A homogeneidade declarada
dos recortes administrativos sustenta, no máximo,
**homogeneidade protocolar exploratória**.

Os metadados legados registram `historical_date=null` e criação local, mas não congelam o snapshot
OSM nem comprovam que as quatro consultas observaram a mesma versão da base. Também não contêm,
de forma completa, hashes de limite, configuração, entradas/saídas, argumentos, sementes e estado
do código por etapa. Portanto, o CSV legado que os chamou de `comparavel` não deve ser citado como
confirmação científica. Os datasets precisam ser regenerados com a proveniência atual ou receber
evidência equivalente antes de alcançar o estado `confirmada`.

## Regra de amostra e alcance

Quatro municípios vizinhos do interior paulista permitem um estudo de caso comparativo e geração
de hipóteses. Não sustentam “padrões universais”, uma tipologia de cidades brasileiras nem a
generalização para a rede viária urbana nacional. Para essa ambição, pré-defina uma amostra com
regiões, portes e formas urbanas diversas e inclua covariáveis externas.

## Sequência de liberação

1. validar metadados e proveniência;
2. auditar integridade/frescor;
3. auditar representação do grafo;
4. verificar completude e incerteza das curvas;
5. executar a auditoria científica fail-closed;
6. só então gerar tabelas comparativas e formular conclusões.

Os gates são operacionais: `artifact-integrity` e `comparison-audit` retornam código diferente de
zero quando o estado não permite liberação. Em automação, não interprete a simples criação dos CSVs
como sucesso científico.
