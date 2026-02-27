# Mapa do Business Drivers (seleção, intenção e rastreabilidade)

Este documento liga de forma explícita os Business Drivers (motivações de negócio) ao código implementado, à intenção por trás das regras e aos artefatos de teste que validam essas regras. 

## 1. Disponibilidade & Resiliência (DN3) 
- Motivador (porquê): garantir que o serviço continue respondendo mesmo sob picos de requisições ou falhas de dependências; proteger a experiência do cliente evitando consumo excessivo por tenant.
- Intenção do negócio (clareza): limitar requisições por `account-key`, degradar graciosamente quando serviços externos falham e fornecer indicadores de saúde para alertas operacionais.
- Artefatos de código relacionados:
  - [src/core/api.py](src/core/api.py#L312-L388) — `RateLimiter`, `processar_auditoria_resiliente` (aplica rate-limit e retorna `rate_limit_remaining`).
  - [src/core/api.py](src/core/api.py#L388-L482) — `CircuitBreaker`, `build_degraded_response` (degradação e circuit breaker).
  - [ponderada_ovidio/run_dn_tests.py](ponderada_ovidio/run_dn_tests.py#L1-L200) — cenários de validação em-process (simples, reprodutíveis).
- Relação código ↔ regra (rastreabilidade): `DN3` é exercitado por `processar_auditoria_resiliente()` e verificado por `run_dn3_rate_limit()` que confirma comportamento 201 vs 429.


## 2. Não-Repúdio (DN4) 
- Motivador (porquê): provar autoria, integridade e momento de uma transação para evitar disputas fiscais e fraudes.
- Intenção do negócio (clareza): gerar evidências criptográficas (assinatura HMAC + timestamp), armazenar recibos em `AuditLog` com hash chain e prevenir replay/impersonation.
- Artefatos de código relacionados:
  - [src/core/api.py](src/core/api.py#L430-L560) — `sign_transaction`, `verify_signature`, `generate_timestamp`, `build_receipt`.
  - [src/core/api.py](src/core/api.py#L560-L860) — `AuditLog`, `append`, `verify_chain`, `processar_auditoria_nr` endpoint.
  - [ponderada_ovidio/run_dn_tests.py](ponderada_ovidio/run_dn_tests.py#L1-L200) — checagens de replay, impersonation e signature binding.
- Relação código ↔ regra (rastreabilidade): `DN4` é validado por `processar_auditoria_nr()` e por testes que verificam: (1) replay -> 409, (2) impersonation -> 403/401, (3) assinatura vinculada ao payload.


## 3. Estratégia e massa de testes 
- Estratégia: testes in-process via `TestClient` (rápidos, determinísticos), limpeza de estado entre cenários (`audit_log.clear()`, `clear_replay_cache()`, `rate_limiter.reset()`), e validações automáticas de respostas esperadas.
- Massa de testes: payload base em `ponderada_ovidio/run_dn_tests.py` com valores representativos; acrescentamos um cenário de erro (payload inválido) para demonstrar tratamento DN2.


## 4. Codificação como documentação de testes 
- Naming & legibilidade: funções em `run_dn_tests.py` usam nomes que explicam o propósito (`run_dn3_rate_limit`, `run_dn4_nonrepudiation`, `run_dn2_invalid_payload`) e variáveis claras (`PAYLOAD_BASE`, `HEADERS_VALIDOS`).
- Comentários e explicações: este documento e docstrings no script `run_dn_tests.py` descrevem cenário, intenção e critérios de sucesso.
- Coerência do código com a regra de negócio: as checagens no script refletem exatamente as expectativas do DN3/DN4 (códigos HTTP, presença de assinatura/timestamp, falha em payload adulterado).

---


