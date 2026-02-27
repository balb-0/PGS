# Mapa do Business Drivers (seleção e rastreabilidade)

1. Disponibilidade & Resiliência (DN3)
   - Motivador: garantir serviço online e resposta mesmo com falhas externas.
   - Artefatos de código relacionados:
     - `src/core/api.py` — `processar_auditoria_resiliente` (rate limiter, circuit breaker, idempotência)
     - `src/tests/blue_team/DN3_availability_blue.py` — testes de disponibilidade
   - Indicadores de qualidade:
     - Latência média e percentis (p50/p95/p99)
     - Taxa de erros (4xx/5xx)
     - Cobertura de testes automáticos para degradação e recuperação

2. Não-Repúdio (DN4)
   - Motivador: assegurar integridade, autoria e não-rejeição de transações fiscais.
   - Artefatos de código relacionados:
     - `src/core/api.py` — endpoints `/api/v1/auditar/nr`, `sign_transaction`, `verify_signature`, `AuditLog`
     - `src/tests/red_team/DN4_non_repudiation_red.py` — testes adversariais (replay, impersonation, assinatura)
   - Indicadores de qualidade:
     - Testes de assinatura (HMAC) e verificação de binding entre payload e timestamp
     - Validação de isolamento e integridade do `audit_log` (hash chain)
     - Tempo de resposta do endpoint NR sob carga

Rastreabilidade (mapa simples):

- DN3 → `processar_auditoria_resiliente()` → testes em `src/tests/blue_team/DN3_availability_blue.py`
- DN4 → `processar_auditoria_nr()` + `audit_log` → testes em `src/tests/red_team/DN4_non_repudiation_red.py`

Notas:
- Os testes já presentes no repositório são usados como massa e referência; este mapa liga requisitos (drivers) ao código e aos testes existentes.

## Detalhamento: script `ponderada_ovidio/run_dn_tests.py`

Esta seção descreve, passo a passo, o que o script `run_dn_tests.py` verifica e por quê. O objetivo do script é prover checks concisos e executáveis que validam os dois Business Drivers selecionados (DN3 e DN4) em modo in-process, garantindo isolamento de estado entre cenários.

- Execução e contexto:
  - O script cria um `TestClient(api.app)` para executar os endpoints localmente (sem rede).
  - Antes de cada cenário crítico ele limpa singletons/estado compartilhado (ex.: `api.audit_log.clear()`, `api.clear_replay_cache()`, `api.rate_limiter.reset()`), garantindo testes determinísticos e reprodutíveis.

- DN3 — Rate limiter / Disponibilidade (`run_dn3_rate_limit`):
  - O que envia: `max_requests + 1` requisições para `POST /api/v1/auditar/resilient` usando a mesma `account-key`.
  - Comportamento esperado (validação):
    - Pelo menos uma resposta `201` (serviço processa requisições válidas).
    - Pelo menos uma resposta `429` (rate limiter bloqueou requisições quando o limite foi excedido).
  - Significado: confirma que o sistema implementa proteção contra excesso de uso por account (mecanismo de disponibilidade coletivo).

- DN4 — Não-repúdio (`run_dn4_nonrepudiation`):
  - Preparação: limpa `audit_log` e `_replay_cache` para começar com cadeia e cache vazios.
  - Replay protection:
    - Envia duas requisições idênticas para `POST /api/v1/auditar/nr` com os mesmos headers válidos.
    - Espera: primeira resposta `201`, segunda `409` (Conflict) ou `429` (Too Many Requests).
    - Interpretação: o servidor gera um `replay_token` e impede reprocessamento imediato da mesma transação.
  - Impersonation check:
    - Envia uma requisição com header `account-key` diferente (simulando actor forjado).
    - Espera: resposta `401`/`403` (ou `409` caso o replay check ocorra antes) — valida que a conta não autorizada não consegue registrar transações em nome de outra.
  - Signature binding:
    - Recupera `signature` e `timestamp` do recibo da primeira requisição bem-sucedida.
    - Tenta validar essa mesma assinatura contra um `payload` adulterado; espera que `verify_signature()` retorne `False`.
    - Interpretação: garante que a assinatura HMAC está vinculada ao payload e timestamp, evitando reutilização em dados alterados.

- Resultado agregado e critérios de falha:
  - O script imprime uma linha por teste com `OK` ou `FAIL` e encerra com código de saída não-zero quando alguma verificação falha.
  - Esses critérios são deliberadamente simples para uso em pipelines rápidos ou como verificação manual local.

- Como usar (resumo rápido):
  - Execute com `PYTHONPATH=src python ponderada_ovidio/run_dn_tests.py` (ou configure `PYTHONPATH` no seu ambiente).
  - Saída clara: cada driver tem uma linha de resultado e um código de saída indicativo.
