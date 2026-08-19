# IC — Estrutura e robustez de redes viárias urbanas

Pipeline reprodutível para construir grafos viários do OpenStreetMap, medir sua estrutura e
avaliar a degradação da conectividade sob remoções controladas. O recorte empírico atualmente
disponível contém quatro municípios paulistas — Campinas, Jundiaí, Sorocaba e Valinhos — e deve
ser apresentado como **estudo de caso exploratório**, não como retrato de toda a rede viária
brasileira.

## O que o projeto mede

- estrutura topológica, centralidades, comunidades e caminhos mínimos;
- robustez estrutural sob remoção de arestas, vértices e ligações entre comunidades;
- gargalos, redundância estrutural de rotas e impactos de bloqueios espaciais estilizados;
- orientação, morfologia e candidatos a subcentros como **proxies topológicos**;
- sensibilidade à representação do grafo, à escala espacial e às aproximações numéricas;
- qualidade, proveniência, integridade e comparabilidade dos artefatos.

Os experimentos não observam tráfego, demanda origem–destino, tempo de viagem, recuperação após
um evento nem desempenho socioeconômico. Por isso, o termo correto para as curvas implementadas é
**robustez estrutural**. “Resiliência” só deve aparecer como nome legado de comandos/arquivos ou
como definição operacional explicitamente limitada; resiliência em sentido forte exigiria uma
dinâmica de recuperação no tempo.

## Instalação reproduzível por versão

Requer Python 3.11 ou superior; o ambiente validado e a integração contínua usam Python 3.12.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install -U pip
python -m pip install -r requirements-lock.txt
python -m pip install -e . --no-deps
python -m unittest discover -s tests -v
```

`requirements-lock.txt` fixa as versões do ambiente validado. Ele ainda não contém hashes dos
pacotes, portanto não oferece reprodução bit a bit nem verificação completa da cadeia de
fornecimento. `requirements.txt` e `pyproject.toml` continuam adequados para acompanhar versões
compatíveis mais recentes, desde que a suíte seja executada novamente.

## Fluxo principal

```bash
ic download --config config/comparable/campinas.yaml
ic preprocess --city campinas_admin
ic structural --city campinas_admin
ic centrality --city campinas_admin
ic representation-audit --city campinas_admin
ic validate-approximations --city campinas_admin
ic communities --city campinas_admin

ic resilience --city campinas_admin --strategy targeted --evaluation-seed 104729
ic node-resilience --city campinas_admin --strategy targeted --evaluation-seed 104729
ic random-resilience-stats --city campinas_admin --mode both --repetitions 30 \
  --master-seed 42 --evaluation-seed 104729 --bootstrap-resamples 2000
ic community-resilience --city campinas_admin --strategy targeted
ic intra-community-resilience --city campinas_admin --strategy targeted

ic vulnerability-index --city campinas_admin
ic structural-bottlenecks --city campinas_admin
ic route-redundancy --city campinas_admin
ic spatial-multiscale --city campinas_admin
ic spatial-robustness --city campinas_admin
ic road-hierarchy --city campinas_admin
ic urban-morphology --city campinas_admin
ic od-efficiency --city campinas_admin
ic subcenters --city campinas_admin
ic urban-barriers --city campinas_admin
ic network-scale-profile --city campinas_admin

ic robustness-summary campinas_admin jundiai_admin sorocaba_admin valinhos_admin
ic inventory --city campinas_admin
ic report --city campinas_admin
ic dashboard --city campinas_admin
ic artifact-integrity --city campinas_admin
ic comparison-audit campinas_admin jundiai_admin sorocaba_admin valinhos_admin \
  --profile cientifico --snapshot-policy same
```

Esse exemplo mantém o mesmo identificador administrativo do download ao relatório. Os YAMLs na
raiz de `config/` representam recortes bbox distintos e geram datasets sem o sufixo `_admin`;
eles não devem ser misturados com `config/comparable/` na mesma comparação.

Os comandos que recebem `--year ANO` usam o identificador histórico correspondente. A lista
completa de exemplos está em [config/comandos.md](config/comandos.md).

## Contratos científicos incorporados

- Ataques aleatórios usam, por padrão, 30 sementes distintas e bootstrap de 95%.
- A semente do ataque é separada da semente usada para estimar eficiência.
- Desvio e intervalo de confiança ficam vazios quando há uma única execução; zero nunca significa
  “incerteza inexistente”.
- A síntese de robustez falha se faltar alguma modalidade/estratégia, salvo liberação explícita
  com `--allow-incomplete`.
- `--output-dir` isola também os resumos por cidade, evitando regravar resultados canônicos.
- Centralidade de arestas possui arquivo completo; rankings truncados não podem alimentar índices
  de vulnerabilidade ou gargalos.
- O inventário separa extensão dirigida de roteamento da extensão física colapsada usada como
  proxy de densidade viária.
- A similaridade entre cidades usa um conjunto teórico reduzido e exige ao menos oito datasets;
  uma amostra menor requer `--allow-small-sample-exploration` e permanece descritiva.
- Cada comando grava uma linha de proveniência com argumentos efetivos, versões, Git, hashes de
  entradas e artefatos em `outputs/experiments/cli_runs.jsonl` e no log do dataset.
- O tipo de rede (`drive`, `walk`, `bike`, `all` etc.) é inferido do metadado e propagado pelos
  módulos; caminhos de arquivo não pressupõem mais `drive` silenciosamente.

## Como interpretar módulos exploratórios

- `route-redundancy` bloqueia todos os arcos direcionados da melhor rota; é um cenário estrito de
  alternativa disjunta, não uma simulação probabilística de incidente.
- `spatial-robustness` representa bloqueios regionais estilizados, sem hazard ou probabilidade
  observada. A amostra de eficiência é aleatória e independente do impacto na LCC.
- `urban-morphology` gera classes heurísticas de orientação/conectividade.
- `subcenters` detecta células candidatas de alta centralidade topológica; não observa empregos,
  população, atividades ou fluxos e não comprova policentralidade urbana.
- `network-scale-profile` mede sensibilidade descritiva à grade, não robustez espacial.
- correlações com `maxspeed`, `lanes` e `surface` são associações com tags OSM e dependem de sua
  cobertura; não constituem validação funcional externa.

## Saídas e confiança

Cada dataset usa `outputs/<dataset>/metrics`, `figures`, `maps` e `logs`, além do dashboard,
relatório e manifesto. O manifesto v2 inclui hashes SHA-256 das entradas/saídas existentes,
ambiente, comando real, estado do Git e últimas execuções registradas.

Um arquivo presente não é automaticamente um resultado válido. Antes de interpretar comparações:

1. confirme integridade e frescor dos artefatos;
2. execute a auditoria científica de comparabilidade;
3. exija a matriz completa de curvas;
4. confira cobertura e incerteza;
5. trate outputs antigos, sem proveniência v2, como legado a regenerar.

`artifact-integrity` e `comparison-audit` retornam código de processo diferente de zero quando o
gate não libera os dados. Auditorias com `--stages` explícitas usam arquivos sufixados pelo escopo
e um `PASS` certifica somente essas etapas; não substituem a auditoria completa. Hashes declarados
são verificados sem limite de tamanho por padrão.

Dados e mapas derivados de OpenStreetMap devem atribuir **© OpenStreetMap contributors** e indicar
a licença ODbL: <https://www.openstreetmap.org/copyright>.

## Documentação científica

- [documentação formal para o orientador](docs/documentacao_aprimoramentos_para_orientador.md);
- [roteiro falado para apresentação](docs/roteiro_falado_apresentacao_orientador.md);
- [matriz literal de aderência ao plano](docs/matriz_aderencia_plano_trabalho.md);
- [revisão bibliográfica](docs/revisao_bibliografica_projeto_ic.md);
- [matriz de aderência e lacunas](docs/analise_lacunas_projeto_ic.md);
- [protocolo de comparação](docs/protocolo_comparacao_cidades.md);
- [protocolo histórico OSM](docs/protocolo_analise_historica_osm.md);
- [registro desta grande revisão](docs/registro_aprimoramentos_2026-08-18.md);
- [dicionário de dados](docs/dicionario_dados.md).

O PDF-base [`_Projeto_2026__Lucas_Soares.pdf`](_Projeto_2026__Lucas_Soares.pdf) foi anexado e
conferido integral e visualmente em 18 de agosto de 2026. A matriz de aderência acima registra o
vínculo literal entre objetivos, atividades, resultados esperados, implementação e lacunas.
