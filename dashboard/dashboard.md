# Dashboards do Frontend

## Visao Geral

O diretorio `dashboard/frontend` contem a aplicacao Next.js responsavel pela camada de consumo executivo e operacional dos dashboards da ASIS. O objetivo desse frontend nao e substituir o Grafana nem replicar toda a experiencia de observabilidade: ele organiza leituras orientadas a decisao para tres necessidades diferentes.

As experiencias principais sao:

- ` /business `: leitura de negocio, SLA e impacto operacional.
- ` /system-health `: leitura de estabilidade, disponibilidade e resposta a incidentes.
- ` /ai-search `: descoberta de graficos existentes por linguagem natural.

Em todas as telas, a aplicacao combina tres camadas:

1. **Resumo executivo** com KPIs e blocos narrativos.
2. **Leituras sinteticas** vindas do backend agregado de dashboards.
3. **Embeds diretos do Grafana** para manter fidelidade visual e tecnica aos paineis originais.

Essa separacao e importante porque o frontend foi desenhado para traduzir observabilidade em decisao. Em vez de jogar o usuario diretamente em um dashboard tecnico unico, cada rota organiza os sinais mais relevantes para um publico e um objetivo diferentes.

## Objetivo da Aplicacao

O app Next.js serve como uma camada de apresentacao para tres contextos complementares:

- **Saude do sistema**: apoiar engenharia, SRE, operacao e suporte na deteccao rapida de incidentes e degradacoes.
- **Stakeholders de negocio**: apoiar lideranca e gestao na leitura de impacto, eficiencia, qualidade e risco de SLA.
- **Busca com IA**: apoiar qualquer usuario que saiba o que quer investigar, mas nao saiba em qual painel procurar.

Na pratica, isso significa que o frontend nao exibe dados apenas para monitorar. Ele exibe dados para orientar perguntas concretas, como:

- O sistema esta saudável o suficiente para sustentar o volume atual?
- Existe risco de violacao de SLA com impacto em cliente ou receita?
- Os erros atuais sao falhas tecnicas, falhas de entrada ou pressao estrutural?
- Qual painel existente ajuda a investigar um problema descrito em linguagem natural?

## Arquitetura de Dados

### Fluxo principal

O fluxo de dados do frontend segue o modelo abaixo:

```text
Usuario
  -> Frontend Next.js (`dashboard/frontend/app/...`)
  -> Rotas internas (`/api/dashboard/[kind]` e `/api/ai-search`)
  -> Backend de dashboards (`/api/v1/dashboard/...`)
  -> Prometheus / servicos instrumentados
  -> Grafana para renderizacao dos paineis embedados
```

### Papel de cada camada

- O **frontend Next.js** organiza a experiencia, a navegacao e a narrativa de decisao.
- A rota interna `dashboard/frontend/app/api/dashboard/[kind]/route.ts` protege o browser de acessar credenciais sensiveis diretamente e encaminha a consulta ao backend.
- O backend agregado em `src/core/dashboard_services.py` monta os blocos `summary`, `breakdown`, `trends` e `degradation`.
- Os paineis embedados usam iframes gerados por `dashboard/frontend/components/GrafanaEmbedCard.tsx`, apontando para dashboards provisionados no Grafana.
- A busca inteligente usa `dashboard/frontend/app/api/ai-search/route.ts`, `dashboard/frontend/lib/ai.ts` e `dashboard/frontend/lib/graphCatalog.ts` para selecionar graficos existentes.

### Diferenca entre KPI agregado e painel Grafana

Os cards de KPI do topo e os embeds do Grafana se complementam, mas nem sempre sao a mesma consulta.

- Os **KPIs do topo** normalmente vem do backend agregado, que sintetiza varias leituras e aplica alguma regra de negocio.
- Os **embeds do Grafana** representam as queries e configuracoes dos dashboards originais.

Por isso, a documentacao deve ser lida com a expectativa correta: o topo resume, o Grafana detalha. Pequenas diferencas visuais ou numericas podem acontecer por janela temporal, agregacao, arredondamento ou regra de calculo.

### Degradacao e fallback

O frontend foi preparado para continuar util mesmo quando uma dependencia externa nao esta ideal:

- Se o backend de dashboards estiver indisponivel, as paginas de `business` e `system-health` exibem estado de erro.
- Se o Prometheus estiver degradado, o backend informa esse estado em `degradation.prometheus`.
- Se a OpenAI nao estiver configurada ou falhar, a busca inteligente entra automaticamente em **fallback local**, baseado em tags e descricoes do catalogo.

Isso garante que a experiencia de busca nao dependa exclusivamente de IA externa e que a leitura de operacao exponha quando a origem de metricas esta degradada.

## Estrutura das Rotas

### Landing page

Arquivo: `dashboard/frontend/app/page.tsx`

A pagina inicial apresenta as tres formas principais de consumo:

- Negocio
- Saude do Sistema
- Busca IA

Ela existe como camada de orientacao, deixando claro que os dashboards nao competem entre si. Eles atendem perspectivas diferentes sobre o mesmo ecossistema operacional.

### Navegacao compartilhada

Arquivo: `dashboard/frontend/components/DashboardShell.tsx`

O `DashboardShell` padroniza:

- barra superior com navegacao entre dashboards;
- titulo e subtitulo de contexto;
- enquadramento visual da leitura executiva;
- troca de tema claro/escuro.

Essa estrutura reforca uma ideia importante: o frontend e uma console de decisao, nao apenas uma colecao de iframes do Grafana.

## Dashboard de Negocio

Arquivo principal: `dashboard/frontend/app/business/page.tsx`

### Publico-alvo

Esse dashboard atende principalmente:

- lideranca de produto e operacao;
- gestores de negocio;
- stakeholders que precisam entender impacto e risco sem entrar em detalhe de observabilidade pura;
- decisores que precisam priorizar capacidade, estabilidade e qualidade.

### Proposito

O dashboard de negocio transforma sinais tecnicos em leitura de impacto operacional. Ele ajuda a responder se a plataforma esta entregando com qualidade suficiente para sustentar volume, crescimento e compromisso de SLA.

Nao e um painel de troubleshooting profundo. E uma tela para priorizacao e leitura executiva.

### Dados consumidos

O frontend consulta `getDashboard("business", { interval: "6h", step: "5m" })`, que chega ao endpoint `GET /api/v1/dashboard/business`.

Do backend, a pagina usa principalmente:

- `summary.success_rate_percent`
- `summary.p90_latency_ms`
- `summary.throughput_rps`
- `summary.process_store_size`
- `summary.sla_status`
- `summary.total_errors`
- `summary.total_requests`
- `degradation.prometheus`
- `trends.p90_latency`

### KPIs exibidos e como ajudam o negocio

#### Sucesso

Card: `Sucesso`

Mostra a taxa de sucesso da operacao. Para negocio, esse indicador ajuda a responder se a plataforma esta convertendo demanda em entrega bem-sucedida ou se ha perda operacional por falhas evitaveis.

Valor pratico:

- mede confiabilidade percebida da operacao;
- ajuda a identificar risco de retrabalho e friccao na jornada;
- serve como sinal de estabilidade para lideranca.

#### P90 Latencia

Card: `P90 Latencia`

Mostra o percentil 90 de latencia. Esse numero e relevante porque revela o comportamento de uma faixa ampla das requisicoes, nao apenas a media.

Valor pratico:

- evidencia risco de violacao de SLA;
- ajuda a antecipar insatisfacao do cliente;
- permite priorizar otimizacoes antes que haja ruptura operacional.

No backend, o status de SLA e classificado como:

- `healthy` quando a latencia esta abaixo do limite de atencao;
- `warning` quando ultrapassa o nivel de alerta;
- `critical` quando entra em zona mais grave.

#### Throughput

Card: `Throughput`

Mostra a vazao atual em requisicoes por segundo.

Valor pratico:

- ajuda a entender se o sistema esta sustentando o ritmo atual do negocio;
- permite correlacionar aumento de demanda com degradacao de qualidade;
- apoia decisoes de capacidade e scaling.

#### Processos

Card: `Processos`

Mostra o tamanho do `ProcessStore` agregado.

Valor pratico:

- sinaliza volume estrutural em andamento;
- ajuda a entender pressao operacional acumulada;
- pode indicar crescimento persistente de carga ou backlog de processamento.

### Tendencia principal

Grafico local: `Tendencia de Latencia P90`

Esse grafico sintetiza a evolucao temporal da latencia P90 e ajuda o negocio a responder se houve deterioracao gradual, pico pontual ou estabilizacao no periodo recente.

Ele e especialmente importante para diferenciar:

- incidente agudo;
- degradacao progressiva;
- melhoria apos ajuste operacional.

### Sinais para decisao

O bloco textual adicional mostra:

- `Status SLA`
- `Erros atuais`
- `Requisicoes totais`
- estado de `Fonte Prometheus`

Esse conjunto existe para transformar dados tecnicos em leitura executiva imediata. Em vez de exigir navegacao por multiplos paineis, ele concentra os sinais que mais impactam a percepcao de risco de entrega.

### Paineis embedados do Grafana

Os paineis exibidos nessa pagina sao definidos em `decisionPanels`.

#### Taxa de Sucesso

Mostra consistencia operacional. Ajuda a identificar se o volume transacionado esta virando entrega valida ou se parte relevante esta sendo perdida por erro.

#### Latencia P90 (SLA)

Traduz risco de cumprimento de SLA em um painel de leitura direta. E um dos principais sinais para tomada de decisao executiva porque conecta desempenho tecnico a compromisso de servico.

#### Throughput Atual

Mostra a capacidade efetiva no momento. Ajuda a avaliar se o sistema acompanha a demanda ou se esta sob pressao.

#### Tendencia P50/P90/P99

Permite comparar comportamento mediano, ruim e extremo da latencia. Essa leitura ajuda a identificar quando a experiencia de uma minoria crescente de usuarios esta se deteriorando, mesmo que a media ainda pareca aceitavel.

#### Volume por Endpoint

Identifica concentracao de demanda por rota.

Valor de negocio:

- ajuda a localizar onde otimizar primeiro;
- revela onde o trafego esta gerando mais pressao;
- apoia priorizacao de investimento tecnico.

#### Erros por Status/Fonte

Compara erros por origem e status.

Valor de negocio:

- separa problema real de ambiente simulado ou mock;
- ajuda a medir impacto de falhas em producao real;
- orienta governanca de qualidade.

#### Erros de Validacao

Mostra falhas de entrada e qualidade de dados.

Valor de negocio:

- aponta friccao na entrada de dados;
- ajuda a reduzir retrabalho;
- revela perda operacional que nao depende apenas da infraestrutura.

#### Throughput por Metodo

Segmenta a vazao por operacao da API.

Valor de negocio:

- ajuda a localizar gargalos com retorno rapido;
- evidencia operacoes mais relevantes para eficiencia;
- orienta ajuste fino por tipo de fluxo.

### Como esse dashboard ajuda stakeholders de negocio

Esse dashboard ajuda stakeholders de negocio porque traduz observabilidade em impacto:

- mostra se a operacao esta saudavel o suficiente para sustentar receita e compromisso;
- ajuda a priorizar iniciativas de performance com base em risco real;
- torna visivel o custo de erros e validacoes ruins;
- da contexto para conversar com engenharia usando sinais concretos, nao percepcoes isoladas.

Em resumo, ele responde menos "o que quebrou tecnicamente" e mais "qual risco operacional isso gera para o negocio".

## Dashboard de Saude do Sistema

Arquivo principal: `dashboard/frontend/app/system-health/page.tsx`

### Publico-alvo

Esse dashboard atende principalmente:

- engenharia de plataforma;
- SRE e observabilidade;
- operacao tecnica;
- suporte e times de resposta a incidente.

### Proposito

O dashboard de saude do sistema existe para leitura operacional de confiabilidade. Ele ajuda a responder se o ambiente esta estavel, onde ha degradacao e quais sinais pedem acao imediata.

Essa tela privilegia triagem rapida, saturacao, risco de incidente e capacidade estrutural.

### Dados consumidos

O frontend consulta `getDashboard("system-health", { interval: "6h", step: "1m" })`, que chega ao endpoint `GET /api/v1/dashboard/system-health`.

Do backend, a pagina usa principalmente:

- `summary.health_score`
- `summary.error_rate_percent`
- `summary.circuit_breaker_state`
- `summary.firing_alerts`
- `breakdown.rate_limit_pressure`
- `trends.error_rate`

### KPIs exibidos e como ajudam a operacao

#### Health Score

Card: `Health Score`

Resume o risco operacional em um indicador sintetico.

Valor pratico:

- acelera triagem inicial;
- ajuda a perceber piora geral sem ler cada grafico separadamente;
- permite escalar rapidamente o grau de atencao necessaria.

No backend, esse score parte da taxa de erro e sofre penalizacao adicional quando o circuit breaker esta em `OPEN`.

#### Error Rate

Card: `Error Rate`

Mostra a taxa de erro percentual da operacao.

Valor pratico:

- indica disponibilidade percebida;
- ajuda a detectar incidentes em curso;
- permite medir severidade e persistencia do problema.

#### Circuit

Card: `Circuit`

Exibe o estado do circuit breaker.

Valor pratico:

- informa se o sistema entrou em protecao contra falhas em cascata;
- ajuda a distinguir erro comum de degradacao controlada;
- apoia a leitura de resiliência do ambiente.

#### Alertas

Card: `Alertas`

Exibe a quantidade de alertas em estado `firing`.

Valor pratico:

- concentra a urgencia operacional em um numero simples;
- ajuda a saber se ha alarme ativo antes de abrir a ferramenta completa;
- acelera priorizacao durante incidentes.

### Tendencia principal

Grafico local: `Tendencia da Taxa de Erro`

Mostra a evolucao temporal da taxa de erro. Esse grafico ajuda a diferenciar:

- falha pontual;
- piora progressiva;
- recuperacao apos mitigacao;
- oscilacao intermitente.

Para operacao, essa leitura temporal e tao importante quanto o valor absoluto atual.

### Pressao de Rate Limit

O bloco `Pressao de Rate Limit` usa `breakdown.rate_limit_pressure` e lista contas com menor saldo restante na janela.

Isso ajuda a operacao porque:

- mostra saturacao por tenant;
- antecipa degradacao localizada antes de virar incidente geral;
- evidencia quais contas estao mais proximas do limite.

O identificador exibido e `account_key_hash`, nao a chave bruta da conta. Isso preserva seguranca e ainda permite rastreabilidade operacional.

### Paineis embedados do Grafana

Os paineis exibidos nessa pagina sao definidos em `operationsPanels`.

#### Health Score

Resume saude operacional em um unico indicador e ajuda a abrir a analise com uma leitura macro.

#### Taxa de Erro

Mostra o nivel atual de falha. Ajuda a avaliar impacto imediato na disponibilidade.

#### Uptime

Mostra continuidade do servico no periodo.

Valor operacional:

- ajuda a validar estabilidade historica recente;
- torna visivel recorrencia de quedas;
- complementa a leitura do error rate.

#### Circuit Breaker

Mostra se o mecanismo de protecao esta fechado, aberto ou em recuperacao.

Valor operacional:

- ajuda a interpretar comportamento do sistema sob estresse;
- diferencia resiliencia ativa de falha bruta;
- apoia a investigacao de cascata de erro.

#### Tendencia de Error Rate

Expande a leitura temporal da falha e ajuda a identificar padrao de incidente.

#### Rate Limit por Conta

Mostra pressao operacional por tenant.

Valor operacional:

- ajuda a localizar hotspots de consumo;
- orienta mitigacao seletiva;
- evita tratar como falha global o que e pressao concentrada.

#### Alertas Ativos

Concentra eventos criticos correntes.

Valor operacional:

- acelera resposta;
- prioriza atencao;
- conecta a tela a sinais formais de monitoracao.

#### Capacidade dos Stores

Mostra consumo estrutural de memoria e persistencia.

Valor operacional:

- ajuda a prevenir gargalos antes de impacto severo;
- revela crescimento estrutural anormal;
- apoia leitura de sustentabilidade operacional.

### Como esse dashboard ajuda o time tecnico

Esse dashboard ajuda a operacao tecnica porque entrega contexto de incidente em poucos segundos:

- resume saude atual;
- mostra se o erro esta crescendo ou recuando;
- revela se ha mecanismo de protecao ativo;
- aponta saturacao por conta;
- expõe alertas e capacidade estrutural.

Em vez de obrigar o operador a navegar imediatamente por varios dashboards e consultas, a pagina oferece uma primeira resposta para a pergunta mais importante: **o que merece atencao agora?**

## Busca Inteligente com IA

Arquivo principal: `dashboard/frontend/app/ai-search/page.tsx`

### Publico-alvo

Essa tela atende qualquer usuario que:

- saiba o problema que quer investigar;
- nao saiba qual painel abrir;
- precise navegar entre negocio, saude e catalogo tecnico com menos atrito.

Ela e especialmente util para:

- lideranca que nao conhece a estrutura de dashboards;
- suporte que precisa chegar rapido ao painel certo;
- engenharia que quer descobrir visualizacoes existentes por intencao.

### Proposito

O dashboard de busca com IA reduz a friccao de descoberta. Em vez de o usuario precisar memorizar a organizacao dos paineis, ele descreve sua necessidade em linguagem natural e recebe os graficos mais relevantes que ja existem.

Isso significa que a IA aqui funciona como camada de selecao, nao como geradora de novos dashboards.

### Como funciona

O fluxo da busca e:

1. O usuario escreve uma consulta no `SearchBar`.
2. O frontend faz `POST /api/ai-search`.
3. A rota tenta usar OpenAI para interpretar a intencao e escolher IDs validos do catalogo.
4. Se OpenAI nao estiver disponivel, entra o fallback local por similaridade semantica simples com tags e descricoes.
5. O frontend converte os `graph_id` retornados em paineis reais usando `graphCatalogById`.
6. Os paineis sao exibidos com embed Grafana e uma justificativa textual (`reason`).

### Catalogo de origem

O catalogo usado pela busca esta em `dashboard/frontend/lib/graphCatalog.ts`.

Ele inclui graficos de:

- `business`
- `system-health`
- `testing-gap`

Mesmo que o frontend principal destaque apenas `business`, `system-health` e `ai-search`, a busca pode retornar graficos do catalogo `testing-gap` porque eles existem como ativos validos no repositório.

### Elementos exibidos na tela

#### Status do provedor

O `SearchBar` exibe um estado visual para:

- `IA conectada`
- `Fallback local`
- `Aguardando busca`

Isso e importante para transparência operacional. O usuario sabe se a selecao foi guiada pela OpenAI ou por heuristica local.

#### Intencao detectada

Quando ha resultado, a tela mostra a intencao interpretada.

Esse bloco ajuda o usuario a validar se a plataforma entendeu corretamente o objetivo da busca, por exemplo investigar erro, performance, cobertura ou algum tipo de risco operacional.

#### Paineis retornados

Cada resultado e renderizado como `GrafanaEmbedCard` com:

- titulo do grafico;
- razao da recomendacao (`reason`);
- embed do painel;
- opcao de expandir;
- opcao de abrir no Grafana.

### O que a IA resolve para o usuario

Essa experiencia ajuda porque:

- reduz tempo de descoberta do painel certo;
- evita navegação manual por varios dashboards;
- aproxima usuarios nao tecnicos de um catalogo tecnico sem exigir familiaridade previa;
- reaproveita ativos existentes, preservando governanca e consistencia visual.

### O que a IA nao faz

Esse ponto deve ficar explicito na documentacao:

- a IA **nao cria novos graficos**;
- a IA **nao altera dashboards existentes**;
- a IA **nao consulta uma base separada de metricas**;
- a IA **apenas seleciona paineis validos do catalogo existente**.

Ou seja: a inteligencia esta na descoberta, nao na geracao de observabilidade.

### Como o fallback local funciona

Quando a OpenAI nao esta disponivel, `aiSearchFallbackLocal` calcula relevancia com base em:

- tokens da busca;
- titulo do grafico;
- descricao do grafico;
- tags do catalogo;
- reforcos para temas como erro, latencia e cobertura.

O score retornado serve para ordenacao. Ele nao deve ser interpretado como probabilidade matematica, garantia de qualidade ou confianca estatistica formal. E um indice de ranking para ajudar a trazer primeiro o painel mais util.

### Como a busca com IA ajuda cada publico

- Para negocio: ajuda a chegar rapido a um painel relevante sem precisar conhecer toda a estrutura de observabilidade.
- Para operacao: acelera descoberta durante investigacao sob pressao.
- Para engenharia: facilita reutilizacao de paineis existentes e reduz duplicacao de visualizacoes.

## Como os Dashboards se Complementam

As tres experiencias foram desenhadas para se complementar, nao para competir.

### Negocio

Foca em impacto, risco e capacidade de sustentar entrega.

Pergunta principal:

**Como a saude tecnica afeta o resultado e a confiabilidade percebida pelo negocio?**

### Saude do Sistema

Foca em incidente, degradacao e confiabilidade operacional.

Pergunta principal:

**O que esta acontecendo tecnicamente agora e qual a urgencia de resposta?**

### Busca com IA

Foca em descoberta e navegacao assistida.

Pergunta principal:

**Qual painel existente eu devo abrir para investigar o que preciso?**

Essa organizacao melhora a experiencia porque o usuario nao precisa adaptar sua pergunta a um dashboard unico. O produto e que se adapta ao contexto do usuario.

## Janela Temporal e Interacao com o Grafana

Os embeds usam janelas temporais predefinidas:

- `business`: `now-6h`
- `system-health`: `now-6h`
- `ai-search`: `now-24h`

Cada card Grafana pode ser expandido, e o modal permite abrir diretamente no Grafana completo.

Isso importa porque:

- a visao embedada privilegia foco e rapidez;
- a abertura no Grafana permite analise aprofundada;
- filtros e exploracao mais avancada permanecem disponiveis na ferramenta original.

## Observacoes Importantes para Interpretacao

### 1. Os dashboards sao orientados a decisao

Eles nao tentam expor todo o universo de metricas. Eles mostram o que e mais util para cada publico agir com rapidez e contexto.

### 2. KPI local e painel Grafana podem divergir ligeiramente

Isso pode acontecer por:

- regras de agregacao no backend;
- arredondamento;
- diferenca de janela temporal;
- regra de negocio adicional, como o `health_score` penalizado por circuit breaker aberto.

### 3. O estado de degradacao importa

Se `degradation.prometheus` estiver ruim, a leitura precisa considerar que a origem de metricas pode estar incompleta ou degradada.

### 4. A busca IA e governada por catalogo

So entram resultados que existem no catalogo validado. Isso protege consistencia e evita alucinacao de paineis inexistentes.

### 5. O frontend nao substitui observabilidade raiz

Ele acelera a leitura e a tomada de decisao, mas a investigacao aprofundada continua podendo exigir Grafana, Prometheus e analise do backend instrumentado.

## Catalogo Resumido de Paineis do Frontend

### Business

| Painel | Leitura principal | Como ajuda |
|---|---|---|
| Taxa de Sucesso | Confiabilidade operacional | Mostra perda ou consistencia da entrega |
| Latencia P90 (SLA) | Risco de SLA | Ajuda a antecipar impacto em experiencia e compromisso |
| Throughput Atual | Capacidade atual | Mostra se o sistema acompanha o ritmo do negocio |
| Tendencia P50/P90/P99 | Evolucao da performance | Ajuda a detectar degradacao gradual ou cauda ruim |
| Volume por Endpoint | Distribuicao da demanda | Orienta investimento tecnico onde ha maior pressao |
| Erros por Status/Fonte | Origem e natureza da falha | Separa falha sistemica de comportamento localizado |
| Erros de Validacao | Qualidade da entrada | Evidencia retrabalho e perda operacional |
| Throughput por Metodo | Vazao por tipo de operacao | Ajuda a localizar gargalos e ganhos rapidos |

### System Health

| Painel | Leitura principal | Como ajuda |
|---|---|---|
| Health Score | Saude sintetica | Acelera triagem operacional |
| Taxa de Erro | Falha corrente | Mostra severidade percebida da degradacao |
| Uptime | Continuidade do servico | Ajuda a avaliar estabilidade recente |
| Circuit Breaker | Protecao contra cascata | Mostra resiliência ativa do sistema |
| Tendencia de Error Rate | Evolucao da falha | Ajuda a ler padrao do incidente |
| Rate Limit por Conta | Saturacao por tenant | Antecipacao de hotspots operacionais |
| Alertas Ativos | Eventos criticos | Prioriza acao imediata |
| Capacidade dos Stores | Pressao estrutural | Ajuda a prevenir gargalos de memoria e persistencia |

### AI Search

| Elemento | Leitura principal | Como ajuda |
|---|---|---|
| Consulta em linguagem natural | Intencao do usuario | Reduz friccao de descoberta |
| Status do provider | Origem da selecao | Traz transparencia sobre OpenAI ou fallback |
| Intencao detectada | Interpretacao da busca | Ajuda a validar entendimento da plataforma |
| Lista de paineis recomendados | Reaproveitamento do catalogo | Leva rapidamente ao grafico certo |
| Reason por grafico | Justificativa da recomendacao | Explica por que o painel foi escolhido |

## Referencias Tecnicas

### Frontend

- `dashboard/frontend/app/page.tsx`
- `dashboard/frontend/app/business/page.tsx`
- `dashboard/frontend/app/system-health/page.tsx`
- `dashboard/frontend/app/ai-search/page.tsx`
- `dashboard/frontend/components/DashboardShell.tsx`
- `dashboard/frontend/components/GrafanaEmbedCard.tsx`
- `dashboard/frontend/components/SearchBar.tsx`
- `dashboard/frontend/components/TrendChart.tsx`
- `dashboard/frontend/lib/dashboardApi.ts`
- `dashboard/frontend/lib/graphCatalog.ts`
- `dashboard/frontend/lib/ai.ts`
- `dashboard/frontend/app/api/dashboard/[kind]/route.ts`
- `dashboard/frontend/app/api/ai-search/route.ts`

### Backend e observabilidade

- `src/core/dashboard_services.py`
- `src/core/api.py`
- `src/core/metrics.py`
- `docs/dashboard.md`
- `grafana/dashboards/asis-business-dashboard.json`
- `grafana/dashboards/asis-system-health-dashboard.json`
- `grafana/dashboards/asis-testing-gap-dashboard.json`
- `rules.yml`

## Conclusao

O frontend de dashboards foi desenhado para servir tres camadas diferentes de decisao:

- leitura executiva de risco e impacto;
- leitura operacional de estabilidade e incidente;
- descoberta guiada de graficos existentes.

Essa separacao torna a observabilidade mais acionavel. Em vez de centralizar tudo em uma unica tela generica, a aplicacao organiza os sinais certos para a pessoa certa, no contexto certo.

Para stakeholders de negocio, os dados ajudam a traduzir saude tecnica em risco de entrega, eficiencia e impacto operacional. Para times tecnicos, ajudam a responder com rapidez a degradacoes, alertas e pressao estrutural. Para usuarios que nao conhecem o catalogo, a busca com IA transforma necessidade em caminho de analise, mantendo governanca sobre os paineis existentes.
# Dashboards do Frontend

## Visão Geral

O diretório `dashboard/frontend` contém a aplicação Next.js responsável pela camada de consumo executivo e operacional dos dashboards da ASIS. O objetivo desse frontend não é substituir o Grafana nem replicar toda a experiência de observabilidade: ele organiza leituras orientadas à decisão para três necessidades diferentes.

As experiências principais são:

- `/business`: leitura de negócio, SLA e impacto operacional.
- `/system-health`: leitura de estabilidade, disponibilidade e resposta a incidentes.
- `/ai-search`: descoberta de gráficos existentes por linguagem natural.

Em todas as telas, a aplicação combina três camadas:

1. **Resumo executivo** com KPIs e blocos narrativos.
2. **Leituras sintéticas** vindas do backend agregado de dashboards.
3. **Embeds diretos do Grafana** para manter fidelidade visual e técnica aos painéis originais.

Essa separação é importante porque o frontend foi desenhado para traduzir observabilidade em decisão. Em vez de jogar o usuário diretamente em um dashboard técnico único, cada rota organiza os sinais mais relevantes para um público e um objetivo diferentes.

## Objetivo da Aplicação

O app Next.js serve como uma camada de apresentação para três contextos complementares:

- **Saúde do sistema**: apoiar engenharia, SRE, operação e suporte na detecção rápida de incidentes e degradações.
- **Stakeholders de negócio**: apoiar liderança e gestão na leitura de impacto, eficiência, qualidade e risco de SLA.
- **Busca com IA**: apoiar qualquer usuário que saiba o que quer investigar, mas não saiba em qual painel procurar.

Na prática, isso significa que o frontend não exibe dados apenas para monitorar. Ele exibe dados para orientar perguntas concretas, como:

- O sistema está saudável o suficiente para sustentar o volume atual?
- Existe risco de violação de SLA com impacto em cliente ou receita?
- Os erros atuais são falhas técnicas, falhas de entrada ou pressão estrutural?
- Qual painel existente ajuda a investigar um problema descrito em linguagem natural?

## Arquitetura de Dados

### Fluxo principal

O fluxo de dados do frontend segue o modelo abaixo:

```text
Usuário
  -> Frontend Next.js (`dashboard/frontend/app/...`)
  -> Rotas internas (`/api/dashboard/[kind]` e `/api/ai-search`)
  -> Backend de dashboards (`/api/v1/dashboard/...`)
  -> Prometheus / serviços instrumentados
  -> Grafana para renderização dos painéis embedados
```

### Papel de cada camada

- O **frontend Next.js** organiza a experiência, a navegação e a narrativa de decisão.
- A rota interna `dashboard/frontend/app/api/dashboard/[kind]/route.ts` protege o browser de acessar credenciais sensíveis diretamente e encaminha a consulta ao backend.
- O backend agregado em `src/core/dashboard_services.py` monta os blocos `summary`, `breakdown`, `trends` e `degradation`.
- Os painéis embedados usam iframes gerados por `dashboard/frontend/components/GrafanaEmbedCard.tsx`, apontando para dashboards provisionados no Grafana.
- A busca inteligente usa `dashboard/frontend/app/api/ai-search/route.ts`, `dashboard/frontend/lib/ai.ts` e `dashboard/frontend/lib/graphCatalog.ts` para selecionar gráficos existentes.

### Diferença entre KPI agregado e painel Grafana

Os cards de KPI do topo e os embeds do Grafana se complementam, mas nem sempre são a mesma consulta.

- Os **KPIs do topo** normalmente vêm do backend agregado, que sintetiza várias leituras e aplica alguma regra de negócio.
- Os **embeds do Grafana** representam as queries e configurações dos dashboards originais.

Por isso, a documentação deve ser lida com a expectativa correta: o topo resume, o Grafana detalha. Pequenas diferenças visuais ou numéricas podem acontecer por janela temporal, agregação, arredondamento ou regra de cálculo.

### Degradação e fallback

O frontend foi preparado para continuar útil mesmo quando uma dependência externa não está ideal:

- Se o backend de dashboards estiver indisponível, as páginas de `business` e `system-health` exibem estado de erro.
- Se o Prometheus estiver degradado, o backend informa esse estado em `degradation.prometheus`.
- Se a OpenAI não estiver configurada ou falhar, a busca inteligente entra automaticamente em **fallback local**, baseado em tags e descrições do catálogo.

Isso garante que a experiência de busca não dependa exclusivamente de IA externa e que a leitura de operação exponha quando a origem de métricas está degradada.

## Estrutura das Rotas

### Landing page

Arquivo: `dashboard/frontend/app/page.tsx`

A página inicial apresenta as três formas principais de consumo:

- Negócio
- Saúde do Sistema
- Busca IA

Ela existe como camada de orientação, deixando claro que os dashboards não competem entre si. Eles atendem perspectivas diferentes sobre o mesmo ecossistema operacional.

### Navegação compartilhada

Arquivo: `dashboard/frontend/components/DashboardShell.tsx`

O `DashboardShell` padroniza:

- barra superior com navegação entre dashboards;
- título e subtítulo de contexto;
- enquadramento visual da leitura executiva;
- troca de tema claro/escuro.

Essa estrutura reforça uma ideia importante: o frontend é uma console de decisão, não apenas uma coleção de iframes do Grafana.

## Dashboard de Negócio

Arquivo principal: `dashboard/frontend/app/business/page.tsx`

### Público-alvo

Esse dashboard atende principalmente:

- liderança de produto e operação;
- gestores de negócio;
- stakeholders que precisam entender impacto e risco sem entrar em detalhe de observabilidade pura;
- decisores que precisam priorizar capacidade, estabilidade e qualidade.

### Propósito

O dashboard de negócio transforma sinais técnicos em leitura de impacto operacional. Ele ajuda a responder se a plataforma está entregando com qualidade suficiente para sustentar volume, crescimento e compromisso de SLA.

Não é um painel de troubleshooting profundo. É uma tela para priorização e leitura executiva.

### Dados consumidos

O frontend consulta `getDashboard("business", { interval: "6h", step: "5m" })`, que chega ao endpoint `GET /api/v1/dashboard/business`.

Do backend, a página usa principalmente:

- `summary.success_rate_percent`
- `summary.p90_latency_ms`
- `summary.throughput_rps`
- `summary.process_store_size`
- `summary.sla_status`
- `summary.total_errors`
- `summary.total_requests`
- `degradation.prometheus`
- `trends.p90_latency`

### KPIs exibidos e como ajudam o negócio

#### Sucesso

Card: `Sucesso`

Mostra a taxa de sucesso da operação. Para negócio, esse indicador ajuda a responder se a plataforma está convertendo demanda em entrega bem-sucedida ou se há perda operacional por falhas evitáveis.

Valor prático:

- mede confiabilidade percebida da operação;
- ajuda a identificar risco de retrabalho e fricção na jornada;
- serve como sinal de estabilidade para liderança.

#### P90 Latência

Card: `P90 Latência`

Mostra o percentil 90 de latência. Esse número é relevante porque revela o comportamento de uma faixa ampla das requisições, não apenas a média.

Valor prático:

- evidencia risco de violação de SLA;
- ajuda a antecipar insatisfação do cliente;
- permite priorizar otimizações antes que haja ruptura operacional.

No backend, o status de SLA é classificado como:

- `healthy` quando a latência está abaixo do limite de atenção;
- `warning` quando ultrapassa o nível de alerta;
- `critical` quando entra em zona mais grave.

#### Throughput

Card: `Throughput`

Mostra a vazão atual em requisições por segundo.

Valor prático:

- ajuda a entender se o sistema está sustentando o ritmo atual do negócio;
- permite correlacionar aumento de demanda com degradação de qualidade;
- apoia decisões de capacidade e scaling.

#### Processos

Card: `Processos`

Mostra o tamanho do `ProcessStore` agregado.

Valor prático:

- sinaliza volume estrutural em andamento;
- ajuda a entender pressão operacional acumulada;
- pode indicar crescimento persistente de carga ou backlog de processamento.

### Tendência principal

Gráfico local: `Tendência de Latência P90`

Esse gráfico sintetiza a evolução temporal da latência P90 e ajuda o negócio a responder se houve deterioração gradual, pico pontual ou estabilização no período recente.

Ele é especialmente importante para diferenciar:

- incidente agudo;
- degradação progressiva;
- melhoria após ajuste operacional.

### Sinais para decisão

O bloco textual adicional mostra:

- `Status SLA`
- `Erros atuais`
- `Requisições totais`
- estado de `Fonte Prometheus`

Esse conjunto existe para transformar dados técnicos em leitura executiva imediata. Em vez de exigir navegação por múltiplos painéis, ele concentra os sinais que mais impactam a percepção de risco de entrega.

### Painéis embedados do Grafana

Os painéis exibidos nessa página são definidos em `decisionPanels`.

#### Taxa de Sucesso

Mostra consistência operacional. Ajuda a identificar se o volume transacionado está virando entrega válida ou se parte relevante está sendo perdida por erro.

#### Latência P90 (SLA)

Traduz risco de cumprimento de SLA em um painel de leitura direta. É um dos principais sinais para tomada de decisão executiva porque conecta desempenho técnico a compromisso de serviço.

#### Throughput Atual

Mostra a capacidade efetiva no momento. Ajuda a avaliar se o sistema acompanha a demanda ou se está sob pressão.

#### Tendência P50/P90/P99

Permite comparar comportamento mediano, ruim e extremo da latência. Essa leitura ajuda a identificar quando a experiência de uma minoria crescente de usuários está se deteriorando, mesmo que a média ainda pareça aceitável.

#### Volume por Endpoint

Identifica concentração de demanda por rota.

Valor de negócio:

- ajuda a localizar onde otimizar primeiro;
- revela onde o tráfego está gerando mais pressão;
- apoia priorização de investimento técnico.

#### Erros por Status/Fonte

Compara erros por origem e status.

Valor de negócio:

- separa problema real de ambiente simulado ou mock;
- ajuda a medir impacto de falhas em produção real;
- orienta governança de qualidade.

#### Erros de Validação

Mostra falhas de entrada e qualidade de dados.

Valor de negócio:

- aponta fricção na entrada de dados;
- ajuda a reduzir retrabalho;
- revela perda operacional que não depende apenas da infraestrutura.

#### Throughput por Método

Segmenta a vazão por operação da API.

Valor de negócio:

- ajuda a localizar gargalos com retorno rápido;
- evidencia operações mais relevantes para eficiência;
- orienta ajuste fino por tipo de fluxo.

### Como esse dashboard ajuda stakeholders de negócio

Esse dashboard ajuda stakeholders de negócio porque traduz observabilidade em impacto:

- mostra se a operação está saudável o suficiente para sustentar receita e compromisso;
- ajuda a priorizar iniciativas de performance com base em risco real;
- torna visível o custo de erros e validações ruins;
- dá contexto para conversar com engenharia usando sinais concretos, não percepções isoladas.

Em resumo, ele responde menos "o que quebrou tecnicamente" e mais "qual risco operacional isso gera para o negócio".

## Dashboard de Saúde do Sistema

Arquivo principal: `dashboard/frontend/app/system-health/page.tsx`

### Público-alvo

Esse dashboard atende principalmente:

- engenharia de plataforma;
- SRE e observabilidade;
- operação técnica;
- suporte e times de resposta a incidente.

### Propósito

O dashboard de saúde do sistema existe para leitura operacional de confiabilidade. Ele ajuda a responder se o ambiente está estável, onde há degradação e quais sinais pedem ação imediata.

Essa tela privilegia triagem rápida, saturação, risco de incidente e capacidade estrutural.

### Dados consumidos

O frontend consulta `getDashboard("system-health", { interval: "6h", step: "1m" })`, que chega ao endpoint `GET /api/v1/dashboard/system-health`.

Do backend, a página usa principalmente:

- `summary.health_score`
- `summary.error_rate_percent`
- `summary.circuit_breaker_state`
- `summary.firing_alerts`
- `breakdown.rate_limit_pressure`
- `trends.error_rate`

### KPIs exibidos e como ajudam a operação

#### Health Score

Card: `Health Score`

Resume o risco operacional em um indicador sintético.

Valor prático:

- acelera triagem inicial;
- ajuda a perceber piora geral sem ler cada gráfico separadamente;
- permite escalar rapidamente o grau de atenção necessária.

No backend, esse score parte da taxa de erro e sofre penalização adicional quando o circuit breaker está em `OPEN`.

#### Error Rate

Card: `Error Rate`

Mostra a taxa de erro percentual da operação.

Valor prático:

- indica disponibilidade percebida;
- ajuda a detectar incidentes em curso;
- permite medir severidade e persistência do problema.

#### Circuit

Card: `Circuit`

Exibe o estado do circuit breaker.

Valor prático:

- informa se o sistema entrou em proteção contra falhas em cascata;
- ajuda a distinguir erro comum de degradação controlada;
- apoia a leitura de resiliência do ambiente.

#### Alertas

Card: `Alertas`

Exibe a quantidade de alertas em estado `firing`.

Valor prático:

- concentra a urgência operacional em um número simples;
- ajuda a saber se há alarme ativo antes de abrir a ferramenta completa;
- acelera priorização durante incidentes.

### Tendência principal

Gráfico local: `Tendência da Taxa de Erro`

Mostra a evolução temporal da taxa de erro. Esse gráfico ajuda a diferenciar:

- falha pontual;
- piora progressiva;
- recuperação após mitigação;
- oscilação intermitente.

Para operação, essa leitura temporal é tão importante quanto o valor absoluto atual.

### Pressão de Rate Limit

O bloco `Pressão de Rate Limit` usa `breakdown.rate_limit_pressure` e lista contas com menor saldo restante na janela.

Isso ajuda a operação porque:

- mostra saturação por tenant;
- antecipa degradação localizada antes de virar incidente geral;
- evidencia quais contas estão mais próximas do limite.

O identificador exibido é `account_key_hash`, não a chave bruta da conta. Isso preserva segurança e ainda permite rastreabilidade operacional.

### Painéis embedados do Grafana

Os painéis exibidos nessa página são definidos em `operationsPanels`.

#### Health Score

Resume saúde operacional em um único indicador e ajuda a abrir a análise com uma leitura macro.

#### Taxa de Erro

Mostra o nível atual de falha. Ajuda a avaliar impacto imediato na disponibilidade.

#### Uptime

Mostra continuidade do serviço no período.

Valor operacional:

- ajuda a validar estabilidade histórica recente;
- torna visível recorrência de quedas;
- complementa a leitura do error rate.

#### Circuit Breaker

Mostra se o mecanismo de proteção está fechado, aberto ou em recuperação.

Valor operacional:

- ajuda a interpretar comportamento do sistema sob estresse;
- diferencia resiliência ativa de falha bruta;
- apoia a investigação de cascata de erro.

#### Tendência de Error Rate

Expande a leitura temporal da falha e ajuda a identificar padrão de incidente.

#### Rate Limit por Conta

Mostra pressão operacional por tenant.

Valor operacional:

- ajuda a localizar hotspots de consumo;
- orienta mitigação seletiva;
- evita tratar como falha global o que é pressão concentrada.

#### Alertas Ativos

Concentra eventos críticos correntes.

Valor operacional:

- acelera resposta;
- prioriza atenção;
- conecta a tela a sinais formais de monitoração.

#### Capacidade dos Stores

Mostra consumo estrutural de memória e persistência.

Valor operacional:

- ajuda a prevenir gargalos antes de impacto severo;
- revela crescimento estrutural anormal;
- apoia leitura de sustentabilidade operacional.

### Como esse dashboard ajuda o time técnico

Esse dashboard ajuda a operação técnica porque entrega contexto de incidente em poucos segundos:

- resume saúde atual;
- mostra se o erro está crescendo ou recuando;
- revela se há mecanismo de proteção ativo;
- aponta saturação por conta;
- expõe alertas e capacidade estrutural.

Em vez de obrigar o operador a navegar imediatamente por vários dashboards e consultas, a página oferece uma primeira resposta para a pergunta mais importante: **o que merece atenção agora?**

## Busca Inteligente com IA

Arquivo principal: `dashboard/frontend/app/ai-search/page.tsx`

### Público-alvo

Essa tela atende qualquer usuário que:

- saiba o problema que quer investigar;
- não saiba qual painel abrir;
- precise navegar entre negócio, saúde e catálogo técnico com menos atrito.

Ela é especialmente útil para:

- liderança que não conhece a estrutura de dashboards;
- suporte que precisa chegar rápido ao painel certo;
- engenharia que quer descobrir visualizações existentes por intenção.

### Propósito

O dashboard de busca com IA reduz a fricção de descoberta. Em vez de o usuário precisar memorizar a organização dos painéis, ele descreve sua necessidade em linguagem natural e recebe os gráficos mais relevantes que já existem.

Isso significa que a IA aqui funciona como camada de seleção, não como geradora de novos dashboards.

### Como funciona

O fluxo da busca é:

1. O usuário escreve uma consulta no `SearchBar`.
2. O frontend faz `POST /api/ai-search`.
3. A rota tenta usar OpenAI para interpretar a intenção e escolher IDs válidos do catálogo.
4. Se OpenAI não estiver disponível, entra o fallback local por similaridade semântica simples com tags e descrições.
5. O frontend converte os `graph_id` retornados em painéis reais usando `graphCatalogById`.
6. Os painéis são exibidos com embed Grafana e uma justificativa textual (`reason`).

### Catálogo de origem

O catálogo usado pela busca está em `dashboard/frontend/lib/graphCatalog.ts`.

Ele inclui gráficos de:

- `business`
- `system-health`
- `testing-gap`

Mesmo que o frontend principal destaque apenas `business`, `system-health` e `ai-search`, a busca pode retornar gráficos do catálogo `testing-gap` porque eles existem como ativos válidos no repositório.

### Elementos exibidos na tela

#### Status do provedor

O `SearchBar` exibe um estado visual para:

- `IA conectada`
- `Fallback local`
- `Aguardando busca`

Isso é importante para transparência operacional. O usuário sabe se a seleção foi guiada pela OpenAI ou por heurística local.

#### Intenção detectada

Quando há resultado, a tela mostra a intenção interpretada.

Esse bloco ajuda o usuário a validar se a plataforma entendeu corretamente o objetivo da busca, por exemplo investigar erro, performance, cobertura ou algum tipo de risco operacional.

#### Painéis retornados

Cada resultado é renderizado como `GrafanaEmbedCard` com:

- título do gráfico;
- razão da recomendação (`reason`);
- embed do painel;
- opção de expandir;
- opção de abrir no Grafana.

### O que a IA resolve para o usuário

Essa experiência ajuda porque:

- reduz tempo de descoberta do painel certo;
- evita navegação manual por vários dashboards;
- aproxima usuários não técnicos de um catálogo técnico sem exigir familiaridade prévia;
- reaproveita ativos existentes, preservando governança e consistência visual.

### O que a IA não faz

Esse ponto deve ficar explícito na documentação:

- a IA **não cria novos gráficos**;
- a IA **não altera dashboards existentes**;
- a IA **não consulta uma base separada de métricas**;
- a IA **apenas seleciona painéis válidos do catálogo existente**.

Ou seja: a inteligência está na descoberta, não na geração de observabilidade.

### Como o fallback local funciona

Quando a OpenAI não está disponível, `aiSearchFallbackLocal` calcula relevância com base em:

- tokens da busca;
- título do gráfico;
- descrição do gráfico;
- tags do catálogo;
- reforços para temas como erro, latência e cobertura.

O score retornado serve para ordenação. Ele não deve ser interpretado como probabilidade matemática, garantia de qualidade ou confiança estatística formal. É um índice de ranking para ajudar a trazer primeiro o painel mais útil.

### Como a busca com IA ajuda cada público

- Para negócio: ajuda a chegar rápido a um painel relevante sem precisar conhecer toda a estrutura de observabilidade.
- Para operação: acelera descoberta durante investigação sob pressão.
- Para engenharia: facilita reutilização de painéis existentes e reduz duplicação de visualizações.

## Como os Dashboards se Complementam

As três experiências foram desenhadas para se complementar, não para competir.

### Negócio

Foca em impacto, risco e capacidade de sustentar entrega.

Pergunta principal:

**Como a saúde técnica afeta o resultado e a confiabilidade percebida pelo negócio?**

### Saúde do Sistema

Foca em incidente, degradação e confiabilidade operacional.

Pergunta principal:

**O que está acontecendo tecnicamente agora e qual a urgência de resposta?**

### Busca com IA

Foca em descoberta e navegação assistida.

Pergunta principal:

**Qual painel existente eu devo abrir para investigar o que preciso?**

Essa organização melhora a experiência porque o usuário não precisa adaptar sua pergunta a um dashboard único. O produto é que se adapta ao contexto do usuário.

## Janela Temporal e Interação com o Grafana

Os embeds usam janelas temporais predefinidas:

- `business`: `now-6h`
- `system-health`: `now-6h`
- `ai-search`: `now-24h`

Cada card Grafana pode ser expandido, e o modal permite abrir diretamente no Grafana completo.

Isso importa porque:

- a visão embedada privilegia foco e rapidez;
- a abertura no Grafana permite análise aprofundada;
- filtros e exploração mais avançada permanecem disponíveis na ferramenta original.

## Observações Importantes para Interpretação

### 1. Os dashboards são orientados à decisão

Eles não tentam expor todo o universo de métricas. Eles mostram o que é mais útil para cada público agir com rapidez e contexto.

### 2. KPI local e painel Grafana podem divergir ligeiramente

Isso pode acontecer por:

- regras de agregação no backend;
- arredondamento;
- diferença de janela temporal;
- regra de negócio adicional, como o `health_score` penalizado por circuit breaker aberto.

### 3. O estado de degradação importa

Se `degradation.prometheus` estiver ruim, a leitura precisa considerar que a origem de métricas pode estar incompleta ou degradada.

### 4. A busca IA é governada por catálogo

Só entram resultados que existem no catálogo validado. Isso protege consistência e evita alucinação de painéis inexistentes.

### 5. O frontend não substitui observabilidade raiz

Ele acelera a leitura e a tomada de decisão, mas a investigação aprofundada continua podendo exigir Grafana, Prometheus e análise do backend instrumentado.

## Catálogo Resumido de Painéis do Frontend

### Business

| Painel | Leitura principal | Como ajuda |
|---|---|---|
| Taxa de Sucesso | Confiabilidade operacional | Mostra perda ou consistência da entrega |
| Latência P90 (SLA) | Risco de SLA | Ajuda a antecipar impacto em experiência e compromisso |
| Throughput Atual | Capacidade atual | Mostra se o sistema acompanha o ritmo do negócio |
| Tendência P50/P90/P99 | Evolução da performance | Ajuda a detectar degradação gradual ou cauda ruim |
| Volume por Endpoint | Distribuição da demanda | Orienta investimento técnico onde há maior pressão |
| Erros por Status/Fonte | Origem e natureza da falha | Separa falha sistêmica de comportamento localizado |
| Erros de Validação | Qualidade da entrada | Evidencia retrabalho e perda operacional |
| Throughput por Método | Vazão por tipo de operação | Ajuda a localizar gargalos e ganhos rápidos |

### System Health

| Painel | Leitura principal | Como ajuda |
|---|---|---|
| Health Score | Saúde sintética | Acelera triagem operacional |
| Taxa de Erro | Falha corrente | Mostra severidade percebida da degradação |
| Uptime | Continuidade do serviço | Ajuda a avaliar estabilidade recente |
| Circuit Breaker | Proteção contra cascata | Mostra resiliência ativa do sistema |
| Tendência de Error Rate | Evolução da falha | Ajuda a ler padrão do incidente |
| Rate Limit por Conta | Saturação por tenant | Antecipação de hotspots operacionais |
| Alertas Ativos | Eventos críticos | Prioriza ação imediata |
| Capacidade dos Stores | Pressão estrutural | Ajuda a prevenir gargalos de memória e persistência |

### AI Search

| Elemento | Leitura principal | Como ajuda |
|---|---|---|
| Consulta em linguagem natural | Intenção do usuário | Reduz fricção de descoberta |
| Status do provider | Origem da seleção | Traz transparência sobre OpenAI ou fallback |
| Intenção detectada | Interpretação da busca | Ajuda a validar entendimento da plataforma |
| Lista de painéis recomendados | Reaproveitamento do catálogo | Leva rapidamente ao gráfico certo |
| Reason por gráfico | Justificativa da recomendação | Explica por que o painel foi escolhido |

## Referências Técnicas

### Frontend

- `dashboard/frontend/app/page.tsx`
- `dashboard/frontend/app/business/page.tsx`
- `dashboard/frontend/app/system-health/page.tsx`
- `dashboard/frontend/app/ai-search/page.tsx`
- `dashboard/frontend/components/DashboardShell.tsx`
- `dashboard/frontend/components/GrafanaEmbedCard.tsx`
- `dashboard/frontend/components/SearchBar.tsx`
- `dashboard/frontend/components/TrendChart.tsx`
- `dashboard/frontend/lib/dashboardApi.ts`
- `dashboard/frontend/lib/graphCatalog.ts`
- `dashboard/frontend/lib/ai.ts`
- `dashboard/frontend/app/api/dashboard/[kind]/route.ts`
- `dashboard/frontend/app/api/ai-search/route.ts`

### Backend e observabilidade

- `src/core/dashboard_services.py`
- `src/core/api.py`
- `src/core/metrics.py`
- `docs/dashboard.md`
- `grafana/dashboards/asis-business-dashboard.json`
- `grafana/dashboards/asis-system-health-dashboard.json`
- `grafana/dashboards/asis-testing-gap-dashboard.json`
- `rules.yml`

## Conclusão

O frontend de dashboards foi desenhado para servir três camadas diferentes de decisão:

- leitura executiva de risco e impacto;
- leitura operacional de estabilidade e incidente;
- descoberta guiada de gráficos existentes.

Essa separação torna a observabilidade mais acionável. Em vez de centralizar tudo em uma única tela genérica, a aplicação organiza os sinais certos para a pessoa certa, no contexto certo.

Para stakeholders de negócio, os dados ajudam a traduzir saúde técnica em risco de entrega, eficiência e impacto operacional. Para times técnicos, ajudam a responder com rapidez a degradações, alertas e pressão estrutural. Para usuários que não conhecem o catálogo, a busca com IA transforma necessidade em caminho de análise, mantendo governança sobre os painéis existentes.
