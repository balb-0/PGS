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

## 1.2 DN2 (Red Team) - Integridade dos Dados Fiscais na Ingestão

### Objetivo do Ativo Adversarial
&emsp;Esta seção apresenta os resultados da análise de segurança e robustez realizada pelo **Red Team** sobre o Direcionador de Negócio 2 (DN2 - Integridade de Dados). O objetivo é validar se o sistema de auditoria da **ASIS TaxTech** é capaz de resistir a entradas malformadas ou extremas que visam comprometer a integridade dos dados fiscais.

### Mapa de Direcionadores de Negócio - Red Team (DN2)
&emsp;Foram implementados 5 direcionadores que testam os limites da lógica de validação:

| ID | Direcionador Adversarial | Objetivo Técnico | Status |
| :--- | :--- | :--- | :--- |
| **DN2.R1** | **Script Injection** | Validar se o sistema trata payloads maliciosos (`<script>`) como texto comum. | **PASS** |
| **DN2.R2** | **Extreme Number Resilience** | Testar o comportamento da API com valores não finitos (`inf`, `nan`) ou astronômicos. | **FAIL** |
| **DN2.R3** | **Schema Pollution** | Verificar se o excesso de campos (5.000+) causa degradação de performance. | **PASS** |
| **DN2.R4** | **Strict Type Validation** | Tentar enviar estruturas complexas (listas) onde se espera um valor numérico. | **PASS** |
| **DN2.R5** | **Buffer Stability** | Enviar strings massivas (1MB) para testar limites de memória do endpoint. | **PASS** |

### Métodos de Testagem
O teste foi conduzido utilizando o framework **pytest-9.0.2** em ambiente **Python 3.13.3**.
* **Abordagem**: Foi utilizado o `FastAPI TestClient` para simular ataques de injeção de dados e poluição de schema.
* **Escopo**: Foco exclusivo na validação de entrada (Input Validation) antes da geração do `tracking_id` e do processamento assíncrono.

### Análise dos Resultados (Logs de Execução)

A execução automatizada (`validation_red.py`) coletou 7 itens e identificou vulnerabilidades críticas no tratamento de números:

### **Sucessos de Resiliência**
* **Injeção de Scripts**: O sistema tratou tags HTML/JS como literais, impedindo ataques de Cross-Site Scripting (XSS).
* **Poluição de Schema**: A API processou 5.000 campos extras sem violar o SLA de tempo de resposta.
* **Tipagem**: Tentativas de enviar listas no campo `valor` foram barradas com HTTP 400.

### **Falhas Críticas Identificadas**
O teste de **Resiliência Numérica** falhou em três cenários específicos:
1. **ValueError (inf/nan)**: O `json.encoder` padrão do Python não é compatível com valores `inf` e `nan` fora do padrão JSON (RFC 8259). Isso causou a interrupção do cliente de teste.
2. **Bypass de Regra (1e308)**: O sistema retornou **HTTP 201 Created** para um valor de $1 \times 10^{308}$, que embora positivo, é computacionalmente extremo e fiscalmente impossível. O sistema deveria ter retornado **HTTP 400**.

### Argumentação e Ações Corretivas
Para que este ativo de software atinja o padrão de excelência, as seguintes ações de engenharia são necessárias:
* **Validação de Finitude**: Implementar `math.isfinite(valor)` na `mock_api.py` para rejeitar infinitos.
* **Limites de Sanidade**: Estabelecer um teto máximo para o campo `valor` condizente com a realidade de lotes fiscais da ASIS.

---

