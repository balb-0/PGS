<Table>
  <tr>
    <td><a href= "link"><img src="img/logo.png" alt="Nome" border="0"></td>
    <td>
      <a href= "https://www.inteli.edu.br/"><img src="img/logo-Inteli.png" alt="Inteli - Instituto de Tecnologia e Liderança" border="0"></a>
    </td>
  </tr>
</table>

# Nome do Projeto: <nome do projeto>

## Nome do Grupo: <nome do grupo>

## Integrantes:

- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>
- <a href="https://www.linkedin.com/in/username/">Nome</a>

# Sumário

incluir Sumário

# 1. Business Drivers

## 1.1 DN1 (Blue Team) - Latência de Ingestão
- SLA: 90% dos arquivos de auditoria devem gerar um ID de processo em até 500ms (P90 <= 500ms).
- Este direcionador simula o processo em que o sistema Kolossus receba e processe lotes de documentos fiscais dentro dos parâmetros de performance necessários para não impactar a operação dos clientes.

### Especificação da API_MOCK_G6

A API foi projetada para seguir a estrutura de referência exigida, mapeando as necessidades da ASIS:

- sessao_cliente: Identificador único da sessão de auditoria.

- valor: Volume de documentos fiscais submetidos no lote.

- destino: Módulo fiscal de destino (ex: 'EFD_ICMS_IPI', 'NCM_AUDIT').

### Métricas de SLA e Alertas

- SLA de Latência: ≤ 500 ms (90% das requisições).

- Alerta de Lentidão Crítica: Disparo automático de sinalização caso o tempo exceda 650 ms (30% acima do SLA).

- Status de Efetivação: A transação é considerada válida apenas com o retorno HTTP 201 Created.

### Metodologia de Testagem (Blue Team)

&emsp;A aferição foi conduzida utilizando uma abordagem Test Data Driven (TDD) através do script src/tests/blue_team/response_time.py.

&emsp;Serviços de Apoio: Implementação de mecanismos de Autenticação (account-key/app-key), Rastreio (geração de ID de processo) e Efetivação (validação de persistência assíncrona).

&emsp;Ambiente: Execução via CLI conectada a um servidor Mock que replica o comportamento assíncrono da ASIS API.

### Resultados Obtidos

&emsp;A suíte de testes validou a resiliência do sistema com os seguintes indicadores:

- Status Final: APROVADO

- Taxa de Conformidade: 100.00%

- Latência Média: 373.43 ms

- Comportamento de Alerta: O código monitorou proativamente os limites, não detectando violações de 650 ms durante o ciclo de teste.

## 1.2 DN2 (Blue Team) - Integridade dos Dados Fiscais na Ingestão

### Objetivo

Garantir a validação rigorosa de payloads fiscais **antes do processamento**, evitando erros de integridade de dados na ingestão de documentos fiscais. Este direcionador assegura que apenas lotes válidos sejam processados, protegendo a integridade dos dados da ASIS TaxTech.

### Regras de Negócio

**DN2.1 - Validação de Campos Obrigatórios**

- A API deve rejeitar requisições com campos obrigatórios ausentes: `sessao_cliente`, `valor`, `destino`
- Retorna HTTP 400 com mensagem clara
- Garante rastreabilidade e roteamento correto das auditorias

**DN2.2 - Validação de Valor Positivo**

- A API deve rejeitar requisições onde `valor` ≤ 0
- Aceita valores inteiros e decimais positivos
- O tipo deve ser numérico (int ou float)
- Fundamenta-se na impossibilidade lógica de auditar lotes com volume zero ou negativo

**DN2.3 & DN2.4 - Sem Processamento em Erro**

- A API **NÃO** gera `tracking_id` para payloads inválidos
- A API **NÃO** inicia processamento assíncrono para payloads inválidos
- Validação ocorre **ANTES** de qualquer operação assíncrona (`await`)
- Evita alocação desnecessária de recursos e garante atomicidade

**DN2.5 - Preservação de Contrato**

- Payloads válidos mantêm o comportamento original da API
- Resposta preserva mesma estrutura: id, status, tracking_id, detalhes, etc.
- Headers obrigatórios (account-key, app-key) continuam sendo validados

### Especificação Técnica

**Endpoint afetado:** `POST /api/v1/auditar`

**Validações implementadas em src/core/mock_api.py:**

```python
# DN2.1: Verificação de campos (sessao_cliente, valor, destino)
if sessao is None or modulo_fiscal is None or volume_docs is None:
    raise HTTPException(status_code=400, detail="Parâmetros obrigatórios ausentes")

# DN2.2: Validação de tipo e magnitude numérica
if not isinstance(volume_docs, (int, float)) or volume_docs <= 0:
    raise HTTPException(status_code=400, detail="Valor deve ser um número maior que zero")

# DN2.4 & DN2.5: Processamento e geração de tracking_id apenas após validações
await asyncio.sleep(random.uniform(0.1, 0.5))
return { "tracking_id": str(uuid.uuid4()), ... }
```

### Metodologia de Testagem (TDD)

A validação foi conduzida através de abordagem Test Data Driven (TDD) com 17 testes automatizados em `src/tests/test_mock_api.py`:

**TestDN2IntegrityValidation (14 testes)**

- 3 testes: Campos obrigatórios ausentes (sessao_cliente, valor, destino)
- 4 testes: Validação de valor (negativo, zero, zero decimal, tipo string)
- 4 testes: Payloads válidos (inteiro, decimal, valor mínimo, valor máximo)
- 3 testes: Robustez (múltiplos campos ausentes, payload vazio, campos extras)

**TestDN2ContractValidation (3 testes)**

- Endpoint e status code HTTP
- Headers obrigatórios ainda validados
- Estrutura completa de resposta preservada

### Resultados Obtidos

&emsp;A suíte de testes validou a implementação do DN2 com os seguintes indicadores:

- **Status Final:** APROVADO ✅

- **Taxa de Cobertura:** 100% (17/17 testes passando)

- **Cenários Testados:**
  - 7 cenários de rejeição (erro HTTP 400)
  - 7 cenários de aceitação (sucesso HTTP 201)
  - 3 validações de contrato

- **Verificações de Negócio:**
  - DN2.1: Campos obrigatórios → 3 testes ✅
  - DN2.2: Valor > 0 → 4 testes ✅
  - DN2.3: HTTP 400 para inválidos → 7 testes ✅
  - DN2.4: Sem tracking_id em erro → 7 testes ✅
  - DN2.5: Contrato preservado → 6 testes ✅

### Execução dos Testes

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar todos os testes DN2
pytest src/tests/blue_team/validation.py -v

# Executar apenas testes de integridade
pytest src/tests/blue_team/validation.py::TestDN2IntegrityValidation -v

# Executar apenas testes de contrato
pytest src/tests/blue_team/validation.py::TestDN2ContractValidation -v
```

### Impacto na Qualidade

Este direcionador contribui para:

- **Confiabilidade:** Rejeição proativa de dados malformados
- **Performance:** Validação anterior ao processamento assíncrono economiza recursos
- **Rastreabilidade:** Garante que apenas lotes válidos recebem tracking_id
- **Manutenibilidade:** Código testado com 14 cenários de negócio documentados

## 2.1 DN1 (Red Team) - Testes Adversariais de Latência (SLA)

### Objetivo do Ativo Adversarial

&emsp;Validar se a API de auditoria resiste a cenários de **estresse e carga** que visam **quebrar o SLA de latência** (DN1). O Red Team tenta degradar a resposta para além de 500 ms (alvo) e 650 ms (limite de alerta), de forma a expor fragilidades que o Blue Team não exercita.

### Critérios de Ataque

- **SLA alvo:** ≤ 500 ms (90% das requisições), conforme Blue Team.
- **Limite de alerta:** 650 ms (30% acima do SLA). Qualquer resposta acima disso conta como violação.
- **Sucesso do Red Team:** se ≥ 10% das requisições em um cenário ultrapassarem 650 ms (ou a média/p95 estourar), o teste **falha** e o ativo é considerado vulnerável ao cenário.

### Bateria de Testes e Evolução da Carga

&emsp;A suíte em `src/tests/red_team/response_time_red.py` foi evoluída em etapas, com **aumento progressivo da carga** até tentar quebrar o SLA. Abaixo, o que cada teste faz e os parâmetros usados na última versão:

| Teste                 | Descrição                                                                              | Carga (versão final)                                  |
| :-------------------- | :------------------------------------------------------------------------------------- | :---------------------------------------------------- |
| **Baseline**          | Uma requisição válida; garante que o ambiente não já está lento.                       | 1 req                                                 |
| **Burst sequencial**  | Muitas requisições leves em sequência para ver degradação por volume.                  | **600 req**                                           |
| **Payload pesado**    | Um único JSON com milhares de campos extras (schema pollution) para estressar parsing. | **70.000 campos × 300 chars** (~21 MB)                |
| **String gigante**    | Campo `destino` com string massiva para estressar memória e serialização.              | **10 MB**                                             |
| **Burst concorrente** | Requisições em paralelo (threads) para simular pico de tráfego.                        | **60 workers × 12 req = 720 req** simultâneas         |
| **Burst pesado**      | Sequência de requisições, cada uma com payload grande (volume + parsing).              | **100 req × 40.000 campos × 120 chars** (~4,8 MB/req) |

**Evolução dos parâmetros (aumento progressivo):**

- **Burst sequencial:** 30 → 100 → 250 → **600** requisições.
- **Payload pesado:** 5k×50 → 15k×100 → 35k×200 → **70k×300** (campos × caracteres).
- **String gigante:** 1 MB → 2 MB → 5 MB → **10 MB**.
- **Burst concorrente:** 30×6 (180) → **60×12 (720)**.
- **Burst pesado:** 50×20k×80 → **100×40k×120**.

### Métricas e Logs

&emsp;Cada cenário que gera múltiplos tempos (burst sequencial, concorrente e burst pesado) calcula e exibe:

- **min, max, média e p95** (percentil 95) em ms.
- **Conformidade:** quantidade e percentual de respostas com tempo ≤ 650 ms.

&emsp;Exemplo de saída (burst):

```
[RED] Burst – resumo
      min=109.68ms | max=492.39ms | média=310.27ms | p95=472.2ms
      dentro do SLA (≤650ms): 100/100 (100.0%)
```

### Resultados Obtidos

&emsp;Em todas as rodadas, **todos os testes passaram**: a API manteve respostas dentro do limite de 650 ms e, nos cenários com múltiplas requisições, a conformidade permaneceu ≥ 90%. Ou seja, nas condições atuais (ambiente local, TestClient in-process), o **Red Team não conseguiu quebrar o SLA**; o ativo se mostrou resiliente à bateria aplicada.

- **Status final da suíte:** 6 testes, todos **PASSED**.
- **Interpretação:** O ativo está preparado para os cenários de estresse documentados; em ambientes mais limitados (menos CPU/memória) ou com rede real, a mesma bateria pode ser reexecutada para revalidar.

### Execução

```bash
# Via Makefile (recomendado)
make stress

# Direto com pytest
.venv/bin/python -m pytest src/tests/red_team/response_time_red.py -v -s
```

## 2.2 DN2 (Red Team) - Integridade dos Dados Fiscais na Ingestão

### Objetivo do Ativo Adversarial

&emsp;Esta seção apresenta os resultados da análise de segurança e robustez realizada pelo **Red Team** sobre o Direcionador de Negócio 2 (DN2 - Integridade de Dados). O objetivo é validar se o sistema de auditoria da **ASIS TaxTech** é capaz de resistir a entradas malformadas ou extremas que visam comprometer a integridade dos dados fiscais.

### Mapa de Direcionadores de Negócio - Red Team (DN2)

&emsp;Foram implementados 5 direcionadores que testam os limites da lógica de validação:

| ID         | Direcionador Adversarial      | Objetivo Técnico                                                                      | Status   |
| :--------- | :---------------------------- | :------------------------------------------------------------------------------------ | :------- |
| **DN2.R1** | **Script Injection**          | Validar se o sistema trata payloads maliciosos (`<script>`) como texto comum.         | **PASS** |
| **DN2.R2** | **Extreme Number Resilience** | Testar o comportamento da API com valores não finitos (`inf`, `nan`) ou astronômicos. | **FAIL** |
| **DN2.R3** | **Schema Pollution**          | Verificar se o excesso de campos (5.000+) causa degradação de performance.            | **PASS** |
| **DN2.R4** | **Strict Type Validation**    | Tentar enviar estruturas complexas (listas) onde se espera um valor numérico.         | **PASS** |
| **DN2.R5** | **Buffer Stability**          | Enviar strings massivas (1MB) para testar limites de memória do endpoint.             | **PASS** |

### Métodos de Testagem

O teste foi conduzido utilizando o framework **pytest-9.0.2** em ambiente **Python 3.13.3**.

- **Abordagem**: Foi utilizado o `FastAPI TestClient` para simular ataques de injeção de dados e poluição de schema.
- **Escopo**: Foco exclusivo na validação de entrada (Input Validation) antes da geração do `tracking_id` e do processamento assíncrono.

### Análise dos Resultados (Logs de Execução)

A execução automatizada (`validation_red.py`) coletou 7 itens e identificou vulnerabilidades críticas no tratamento de números:

### **Sucessos de Resiliência**

- **Injeção de Scripts**: O sistema tratou tags HTML/JS como literais, impedindo ataques de Cross-Site Scripting (XSS).
- **Poluição de Schema**: A API processou 5.000 campos extras sem violar o SLA de tempo de resposta.
- **Tipagem**: Tentativas de enviar listas no campo `valor` foram barradas com HTTP 400.

### **Falhas Críticas Identificadas**

O teste de **Resiliência Numérica** falhou em três cenários específicos:

1. **ValueError (inf/nan)**: O `json.encoder` padrão do Python não é compatível com valores `inf` e `nan` fora do padrão JSON (RFC 8259). Isso causou a interrupção do cliente de teste.
2. **Bypass de Regra (1e308)**: O sistema retornou **HTTP 201 Created** para um valor de $1 \times 10^{308}$, que embora positivo, é computacionalmente extremo e fiscalmente impossível. O sistema deveria ter retornado **HTTP 400**.

### Argumentação e Ações Corretivas

Para que este ativo de software atinja o padrão de excelência, as seguintes ações de engenharia são necessárias:

- **Validação de Finitude**: Implementar `math.isfinite(valor)` na `mock_api.py` para rejeitar infinitos.
- **Limites de Sanidade**: Estabelecer um teto máximo para o campo `valor` condizente com a realidade de lotes fiscais da ASIS.

---

## 1.3 DN3 (Blue Team) - Disponibilidade e Resiliência da API

### Objetivo
Garantir a **disponibilidade contínua e resiliência** da API de auditoria fiscal da ASIS TaxTech, implementando mecanismos de proteção contra sobrecarga, falhas em cascata e reprocessamentos indevidos. Este direcionador assegura que o sistema Kolossus permaneça operacional sob condições adversas, com degradação graciosa em vez de falha total.

### Regras de Negócio

**DN3.1 - Rate Limiting (Controle de Taxa)**
- A API deve limitar requisições por `account-key` dentro de uma janela deslizante de 60 segundos
- Máximo de 10 requisições por janela temporal por conta
- Requisições excedentes retornam HTTP 429 (Too Many Requests)
- O isolamento entre contas garante que um cliente não afete outro

**DN3.2 - Circuit Breaker (Disjuntor de Circuito)**
- Após 5 falhas consecutivas, o circuit breaker **abre** e bloqueia novas requisições
- O circuito transita por 3 estados: `CLOSED` → `OPEN` → `HALF_OPEN`
- Após período de recuperação (30s), permite uma requisição de teste (`HALF_OPEN`)
- Um sucesso em `HALF_OPEN` reseta o circuito para `CLOSED`

**DN3.3 - Health Check (Monitoramento de Saúde)**
- Endpoint `GET /api/v1/health` retorna o estado operacional da API
- Inclui: uptime, total de requisições, taxa de erro, estado do circuit breaker
- Status `healthy` quando taxa de erro < 30%; `degraded` quando ≥ 30%
- Não exige autenticação (monitoramento externo)

**DN3.4 - Idempotência de Requisições**
- Requisições com header `idempotency-key` retornam o mesmo resultado se duplicadas
- A primeira execução processa normalmente; duplicatas retornam o resultado armazenado
- Campo `idempotent_replay: true` indica que é uma resposta cacheada
- Sem `idempotency-key`, cada requisição gera resultado novo

**DN3.5 - Degradação Graciosa**
- Quando o circuit breaker está aberto, a API retorna HTTP 503 com resposta de fallback
- A resposta degradada preserva os dados do cliente e informa `retry_after_seconds`
- Status 207 (Multi-Status) com diagnóstico "Degradado" e motivo detalhado

**DN3.6 - Alertas de Disponibilidade**
- Alerta emitido quando taxa de erro excede 30% (limiar padrão DN1)
- Alerta emitido quando circuit breaker está no estado `OPEN`
- Alerta emitido quando restam menos de 30% das requisições no rate limit
- Todos os alertas seguem o padrão `ALERTA DISPONIBILIDADE: [mensagem]`

### Especificação da API — Endpoints de Resiliência

**Endpoint principal:** `POST /api/v1/auditar/resilient`

A API estende o endpoint original (`/api/v1/auditar`) com uma camada completa de resiliência. Os mesmos campos de entrada são utilizados:

- `sessao_cliente`: Identificador único da sessão de auditoria.
- `valor`: Volume de documentos fiscais submetidos no lote.
- `destino`: Módulo fiscal de destino (ex: `EFD_ICMS_IPI`, `NCM_AUDIT`).

**Headers obrigatórios:** `account-key`, `app-key`
**Header opcional:** `idempotency-key` (chave de idempotência)

A resposta inclui todos os campos originais (DN2) mais o bloco `availability`:

```json
{
  "id": 25000,
  "status": 201,
  "tracking_id": "uuid-v4",
  "arquivold": 22500,
  "diagnostico": "Conforme",
  "detalhes": { "cliente": "...", "volume_processado": 3200, "modulo": "..." },
  "availability": {
    "circuit_state": "CLOSED",
    "rate_limit_remaining": 8,
    "idempotent_replay": false,
    "alert": null
  }
}
```

**Endpoint de monitoramento:** `GET /api/v1/health`

```json
{
  "status": "healthy",
  "uptime_seconds": 120.5,
  "total_requests": 45,
  "total_errors": 2,
  "error_rate_percent": 4.44,
  "timestamp": "2026-02-12T12:00:00.000000+00:00",
  "version": "1.2.0",
  "circuit_breaker": "CLOSED",
  "availability_alert": null,
  "circuit_alert": null
}
```

### Mapa de Direcionadores de Negócio — Blue Team (DN3)

&emsp;Foram implementados 6 direcionadores que garantem a disponibilidade e resiliência completas:

| ID | Direcionador de Negócio | SLA / Critério de Aceite | Status |
| :--- | :--- | :--- | :--- |
| **DN3.1** | **Rate Limiting** | Máximo 10 req/min por account-key; isolamento entre contas; HTTP 429 ao exceder. | **PASS** |
| **DN3.2** | **Circuit Breaker** | Abertura após 5 falhas; transição CLOSED→OPEN→HALF_OPEN; reset com sucesso. | **PASS** |
| **DN3.3** | **Health Check** | Endpoint público retorna status, uptime, taxa de erro e estado do circuito. | **PASS** |
| **DN3.4** | **Idempotência** | Requisições duplicadas com mesma chave retornam resultado idêntico sem reprocessar. | **PASS** |
| **DN3.5** | **Degradação Graciosa** | Fallback com HTTP 503/207, dados do cliente preservados, `retry_after` informado. | **PASS** |
| **DN3.6** | **Alerta de Disponibilidade** | Alertas automáticos para taxa de erro >30%, circuit breaker aberto e rate limit próximo. | **PASS** |

### Implementação Técnica

**Módulo de disponibilidade (`src/core/availability.py`):**

```python
# DN3.1: Rate Limiter com janela deslizante
class RateLimiter:
    def is_allowed(account_key) -> bool:
    def remaining(account_key) -> int:

# DN3.2: Circuit Breaker com 3 estados
class CircuitBreaker:
    def allow_request() -> bool:
    def record_success():
    def record_failure():

# DN3.3: Health Check com métricas
class HealthChecker:
    def record_request(success: bool):
    def get_status() -> dict:

# DN3.4: Store de idempotência
class IdempotencyStore:
    def generate_key(account_key, payload) -> str:
    def get(key) -> Optional[dict]:
    def store(key, response):

# DN3.5: Degradação graciosa
def build_degraded_response(payload, reason) -> dict:

# DN3.6: Alertas de disponibilidade
def check_availability_alert(health) -> Optional[str]:
def check_circuit_alert(cb) -> Optional[str]:
def check_rate_limit_alert(rl, account_key) -> Optional[str]:
```

### Metodologia de Testagem (Blue Team — TDD)

&emsp;A aferição foi conduzida utilizando abordagem Test Data Driven (TDD) através do script `src/tests/blue_team/availability.py`.

&emsp;**Cada cenário de teste é executado 3 vezes** (iterações parametrizadas via `@pytest.mark.parametrize`) para garantir consistência e reprodutibilidade dos resultados.

&emsp;**Massa de testes não-funcionais:** Os payloads de teste simulam sessões reais de auditoria fiscal com volumes variados (`PAYLOAD_VALIDO`: 3200.00 docs para EFD_ICMS_IPI; `PAYLOAD_ALTERNATIVO`: 8100.75 docs para NCM_AUDIT).

&emsp;**Versão da API testada:** v1.2.0 — `POST /api/v1/auditar/resilient` | `GET /api/v1/health`

**Estrutura dos testes (8 classes, 36 cenários × 3 iterações = 108 execuções):**

| Classe de Teste | Cenários | Direcionador |
| :--- | :--- | :--- |
| `TestDN3RateLimiting` | 5 testes × 3 iter | DN3.1 |
| `TestDN3CircuitBreaker` | 5 testes × 3 iter | DN3.2 |
| `TestDN3HealthCheck` | 6 testes × 3 iter | DN3.3 |
| `TestDN3Idempotencia` | 5 testes × 3 iter | DN3.4 |
| `TestDN3DegradacaoGraciosa` | 4 testes × 3 iter | DN3.5 |
| `TestDN3Alertas` | 7 testes × 3 iter | DN3.6 |
| `TestDN3ContratoAPI` | 4 testes × 3 iter | Contrato |

### Resultados Obtidos

&emsp;A suíte de testes validou a implementação do DN3 com os seguintes indicadores:

- **Status Final:** APROVADO ✅

- **Taxa de Cobertura:** 100% (36 cenários × 3 iterações = 108 execuções passando)

- **Cenários Testados:**
  - 15 cenários de rate limiting (DN3.1)
  - 15 cenários de circuit breaker (DN3.2)
  - 18 cenários de health check (DN3.3)
  - 15 cenários de idempotência (DN3.4)
  - 12 cenários de degradação graciosa (DN3.5)
  - 21 cenários de alertas de disponibilidade (DN3.6)
  - 12 cenários de contrato da API

- **Verificações de Negócio:**
  - DN3.1: Rate limiting por conta → 5 testes ✅
  - DN3.2: Circuit breaker 3 estados → 5 testes ✅
  - DN3.3: Health check público → 6 testes ✅
  - DN3.4: Idempotência de requisições → 5 testes ✅
  - DN3.5: Degradação graciosa → 4 testes ✅
  - DN3.6: Alertas de disponibilidade → 7 testes ✅
  - Contrato API preservado → 4 testes ✅

### Execução dos Testes

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar todos os testes DN3 (Blue Team)
pytest src/tests/blue_team/availability.py -v

# Executar apenas testes de rate limiting
pytest src/tests/blue_team/availability.py::TestDN3RateLimiting -v

# Executar apenas testes de circuit breaker
pytest src/tests/blue_team/availability.py::TestDN3CircuitBreaker -v

# Executar apenas testes de health check
pytest src/tests/blue_team/availability.py::TestDN3HealthCheck -v

# Executar apenas testes de idempotência
pytest src/tests/blue_team/availability.py::TestDN3Idempotencia -v

# Executar apenas testes de degradação graciosa
pytest src/tests/blue_team/availability.py::TestDN3DegradacaoGraciosa -v

# Executar apenas testes de alertas
pytest src/tests/blue_team/availability.py::TestDN3Alertas -v

# Executar apenas testes de contrato
pytest src/tests/blue_team/availability.py::TestDN3ContratoAPI -v
```

### Impacto na Qualidade

Este direcionador contribui para:
- **Disponibilidade:** Rate limiting e circuit breaker previnem sobrecarga e falhas em cascata
- **Resiliência:** Degradação graciosa garante operação parcial em vez de falha total
- **Observabilidade:** Health check e alertas permitem monitoramento contínuo e proativo
- **Confiabilidade:** Idempotência impede reprocessamentos indevidos e duplicidades fiscais
- **Escalabilidade:** Isolamento de rate limit por conta permite crescimento controlado
- **Operabilidade:** Informações de `retry_after` e `rate_limit_remaining` facilitam integração por clientes

---

## 1.4 DN4 (Blue Team) - Não-Repúdio de Transações de Auditoria Fiscal

### Objetivo
Garantir que todas as transações de auditoria fiscal sejam realizadas com **mecanismos criptográficos de não-repúdio**, impedindo que qualquer das partes negue a realização de uma transação. Este direcionador subsidia as áreas de segurança e suporte aos clientes da ASIS TaxTech, fornecendo evidências criptográficas de **quem** realizou a transação, **o quê** foi transacionado, e **quando** ocorreu.

### Especificação da API — Endpoint de Não-Repúdio

**Endpoint:** `POST /api/v1/auditar/nr`

A API estende o endpoint original (`/api/v1/auditar`) com uma camada completa de não-repúdio. Os mesmos campos de entrada são utilizados:

- `sessao_cliente`: Identificador único da sessão de auditoria.
- `valor`: Volume de documentos fiscais submetidos no lote.
- `destino`: Módulo fiscal de destino (ex: `EFD_ICMS_IPI`, `NCM_AUDIT`).

**Headers obrigatórios:** `account-key`, `app-key`

A resposta inclui todos os campos originais (DN2) mais o bloco `non_repudiation`:

```json
{
  "id": 25000,
  "status": 201,
  "tracking_id": "uuid-v4",
  "arquivold": 22500,
  "diagnostico": "Conforme",
  "detalhes": { "cliente": "...", "volume_processado": 2500, "modulo": "..." },
  "non_repudiation": {
    "signature": "hmac-sha256-hex-64-chars",
    "timestamp": "2026-02-12T12:00:00.000000+00:00",
    "actor": "sha256-hex-64-chars",
    "receipt": {
      "signature": "...",
      "timestamp": "...",
      "actor": "...",
      "tracking_id": "...",
      "payload_hash": "sha256-hex-64-chars"
    },
    "log_position": 0,
    "log_entry_hash": "sha256-hex-64-chars",
    "alert": null,
    "chain_alert": null
  }
}
```

**Endpoints auxiliares de auditoria:**
- `GET /api/v1/audit-log` — Retorna o log completo com status de integridade da cadeia de hash.
- `GET /api/v1/audit-log/{position}` — Retorna uma entrada específica do log.

### Mapa de Direcionadores de Negócio — Blue Team (DN4)

&emsp;Foram implementados 6 direcionadores que garantem o não-repúdio completo das transações:

| ID | Direcionador de Negócio | SLA / Critério de Aceite | Status |
| :--- | :--- | :--- | :--- |
| **DN4.1** | **Assinatura Digital (HMAC-SHA256)** | 100% das transações válidas retornam assinatura HMAC-SHA256 verificável sobre payload + timestamp. | **PASS** |
| **DN4.2** | **Carimbo Temporal Imutável** | 100% das transações incluem timestamp ISO 8601 server-side; tolerância ≤ 2s do horário real. | **PASS** |
| **DN4.3** | **Cadeia de Autenticação** | Toda resposta registra o `actor` (SHA-256 da account-key), vinculando identidade à transação. | **PASS** |
| **DN4.4** | **Recibo Digital Completo** | Respostas válidas incluem recibo com: `signature`, `timestamp`, `actor`, `tracking_id`, `payload_hash`. | **PASS** |
| **DN4.5** | **Integridade do Log de Auditoria** | Log com cadeia de hash (hash chain); cada entrada referencia `prev_hash` da anterior. Cadeia verificável. | **PASS** |
| **DN4.6** | **Alerta de Violação de Não-Repúdio** | Sistema emite `ALERTA` quando campos de não-repúdio estão ausentes ou cadeia de hash comprometida. Limiar de 30% (padrão DN1). | **PASS** |

### Implementação Técnica

**Módulo de não-repúdio (`src/core/non_repudiation.py`):**

```python
# DN4.1: Assinatura digital HMAC-SHA256
def sign_transaction(payload, timestamp, secret) -> str:
    message = json.dumps(payload, sort_keys=True) + "|" + timestamp
    return hmac.new(secret.encode(), message.encode(), hashlib.sha256).hexdigest()

# DN4.2: Carimbo temporal imutável (server-side, UTC)
def generate_timestamp() -> str:
    return datetime.now(timezone.utc).isoformat()

# DN4.3: Hash do ator autenticado
def hash_actor(account_key) -> str:
    return hashlib.sha256(account_key.encode()).hexdigest()

# DN4.4: Recibo digital completo
def build_receipt(signature, timestamp, actor, tracking_id, payload) -> dict:
    return {"signature": ..., "timestamp": ..., "actor": ...,
            "tracking_id": ..., "payload_hash": hash_payload(payload)}

# DN4.5: Log de auditoria com hash chain
class AuditLog:
    def append(self, receipt) -> dict:  # Adiciona entrada com prev_hash encadeado
    def verify_chain(self) -> bool:      # Verifica integridade da cadeia completa

# DN4.6: Alertas de violação
def check_alert(receipt) -> Optional[str]:       # Campos ausentes no recibo
def check_chain_alert(log) -> Optional[str]:     # Cadeia de hash comprometida
```

### Metodologia de Testagem (Blue Team — TDD)

&emsp;A aferição foi conduzida utilizando abordagem Test Data Driven (TDD) através do script `src/tests/blue_team/non_repudiation.py`.

&emsp;**Cada cenário de teste é executado 3 vezes** (iterações parametrizadas via `@pytest.mark.parametrize`) para garantir consistência e reprodutibilidade dos resultados.

&emsp;**Massa de testes não-funcionais:** Os payloads de teste simulam sessões reais de auditoria fiscal com volumes variados (`PAYLOAD_VALIDO`: 2500.00 docs para EFD_ICMS_IPI; `PAYLOAD_ALTERNATIVO`: 7500.50 docs para NCM_AUDIT).

&emsp;**Versão da API testada:** v1.1.0 — `POST /api/v1/auditar/nr`

**Estrutura dos testes (7 classes, 24 cenários × 3 iterações = 72 execuções):**

| Classe de Teste | Cenários | Direcionador |
| :--- | :--- | :--- |
| `TestDN4AssinaturaDigital` | 4 testes × 3 iter | DN4.1 |
| `TestDN4CarimboTemporal` | 3 testes × 3 iter | DN4.2 |
| `TestDN4CadeiaAutenticacao` | 3 testes × 3 iter | DN4.3 |
| `TestDN4ReciboDigital` | 4 testes × 3 iter | DN4.4 |
| `TestDN4LogAuditoria` | 4 testes × 3 iter | DN4.5 |
| `TestDN4Alertas` | 5 testes × 3 iter | DN4.6 |
| `TestDN4ContratoAPI` | 3 testes × 3 iter | Contrato |
| `TestDN4ConsultaLog` | 3 testes × 3 iter | DN4.5 |

### Resultados Obtidos

&emsp;A suíte de testes validou a implementação do DN4 com os seguintes indicadores:

- **Status Final:** APROVADO

- **Taxa de Cobertura:** 100% (29 cenários × 3 iterações = 87 execuções passando)

- **Cenários Testados:**
  - 12 cenários de assinatura e criptografia (DN4.1)
  - 9 cenários de carimbo temporal (DN4.2)
  - 9 cenários de cadeia de autenticação (DN4.3)
  - 12 cenários de recibo digital (DN4.4)
  - 12 cenários de integridade do log (DN4.5)
  - 15 cenários de alertas (DN4.6)
  - 9 cenários de contrato da API
  - 9 cenários de consulta do log

- **Verificações de Negócio:**
  - DN4.1: Assinatura HMAC-SHA256 → 4 testes
  - DN4.2: Timestamp ISO 8601 ≤ 2s → 3 testes
  - DN4.3: Actor SHA-256 → 3 testes
  - DN4.4: Recibo completo → 4 testes
  - DN4.5: Hash chain íntegra → 4 testes
  - DN4.6: Alertas de violação → 5 testes
  - Contrato API preservado → 3 testes
  - Consulta de log → 3 testes

### Execução dos Testes

```bash
# Instalar dependências
pip install -r requirements.txt

# Executar todos os testes DN4 (Blue Team)
pytest src/tests/blue_team/non_repudiation.py -v

# Executar apenas testes de assinatura digital
pytest src/tests/blue_team/non_repudiation.py::TestDN4AssinaturaDigital -v

# Executar apenas testes de carimbo temporal
pytest src/tests/blue_team/non_repudiation.py::TestDN4CarimboTemporal -v

# Executar apenas testes de cadeia de autenticação
pytest src/tests/blue_team/non_repudiation.py::TestDN4CadeiaAutenticacao -v

# Executar apenas testes de recibo digital
pytest src/tests/blue_team/non_repudiation.py::TestDN4ReciboDigital -v

# Executar apenas testes de log de auditoria
pytest src/tests/blue_team/non_repudiation.py::TestDN4LogAuditoria -v

# Executar apenas testes de alertas
pytest src/tests/blue_team/non_repudiation.py::TestDN4Alertas -v

# Executar apenas testes de contrato
pytest src/tests/blue_team/non_repudiation.py::TestDN4ContratoAPI -v
```

### Impacto na Qualidade

Este direcionador contribui para:
- **Não-Repúdio:** Evidência criptográfica irrefutável de cada transação fiscal processada
- **Segurança:** Assinatura HMAC-SHA256 impede adulteração de conteúdo pós-processamento
- **Rastreabilidade:** Cadeia de autenticação vincula cada transação a um ator específico
- **Auditabilidade:** Log com hash chain permite verificação retroativa de integridade
- **Suporte ao Cliente:** Recibo digital completo serve como prova de processamento
- **Monitoramento:** Sistema de alertas detecta proativamente anomalias nos mecanismos de não-repúdio

---

## 1.5 DN4 (Red Team) - Não-Repúdio sob Perspectiva Adversarial

### Objetivo do Ativo Adversarial
&emsp;Esta seção documenta a validação ofensiva do DN4 para medir resistência a ataques de **replay**, **impersonação via headers** e **exposição de trilha de auditoria**. O foco é verificar se os mecanismos de não-repúdio permanecem robustos quando um atacante tenta abusar de lacunas de autenticação e autorização.

### Mapa de Direcionadores de Negócio - Red Team (DN4)
&emsp;Foram implementados 5 direcionadores adversariais:

| ID | Direcionador Adversarial | Objetivo Técnico | Status |
| :--- | :--- | :--- | :--- |
| **DN4.R1** | **Replay Blocking** | Reenviar payload idêntico em janela curta e validar bloqueio por anti-replay. | **FAIL** |
| **DN4.R2** | **Header Impersonation** | Forjar `account-key` de terceiro e validar rejeição de identidade não autenticada. | **FAIL** |
| **DN4.R3** | **Signature Binding** | Confirmar que assinatura HMAC não valida payload adulterado. | **PASS** |
| **DN4.R4** | **Audit Log Authorization** | Tentar ler `/api/v1/audit-log` com credenciais não relacionadas ao ator original. | **FAIL** |
| **DN4.R5** | **Tamper Detection** | Adulterar hash de entrada e validar detecção de quebra de cadeia. | **PASS** |

### Métodos de Testagem
- Script adversarial: `src/tests/red_team/non_repudiation_red.py`
- Abordagem: `FastAPI TestClient` com simulação de atacante e intruso entre contas.
- Escopo: endpoint `POST /api/v1/auditar/nr` e consultas `GET /api/v1/audit-log`.

### Análise de Resultados
- **Pontos fortes**: HMAC está corretamente vinculado ao payload/timestamp; adulteração da hash chain é detectada com alerta.
- **Lacunas críticas**: ausência de anti-replay e ausência de controle real de autenticação/autorização baseado em `account-key`/`app-key`.

### Ações Corretivas Recomendadas
- Implementar autenticação forte para `account-key`/`app-key` (assinatura de request, chave registrada e verificação server-side).
- Adicionar proteção anti-replay (nonce + janela temporal + armazenamento de IDs de idempotência).
- Restringir leitura de log por escopo de ator/tenant e aplicar checagem de permissão nos endpoints `GET /api/v1/audit-log*`.
