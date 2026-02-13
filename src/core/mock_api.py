from fastapi import FastAPI, Header, HTTPException, Body
from typing import Dict, Any
import uuid
import asyncio
import random

from core.non_repudiation import (
    sign_transaction,
    verify_signature,
    generate_timestamp,
    hash_actor,
    hash_payload,
    build_receipt,
    audit_log,
    check_alert,
    check_chain_alert,
)

from core.availability import (
    rate_limiter,
    circuit_breaker,
    health_checker,
    idempotency_store,
    build_degraded_response,
    check_availability_alert,
    check_circuit_alert,
    check_rate_limit_alert,
    CircuitState,
)

app = FastAPI(title="MOCK_API_G6 - ASIS TaxTech", version="1.2.0")


@app.post("/api/v1/auditar", status_code=201)
async def processar_auditoria(
    account_key: str = Header(...),
    app_key: str = Header(...),
    payload: Dict[str, Any] = Body(...)
):
    """
    DN2 - Integridade dos Dados Fiscais na Ingestão

    Valida requisições antes de gerar tracking_id ou iniciar processamento assíncrono.
    Regras:
    1. Todos os campos obrigatórios devem estar presentes
    2. "valor" deve ser maior que zero
    3. Erros retornam HTTP 400 sem processamento
    """
    # Extrair campos obrigatórios
    sessao = payload.get("sessao_cliente")
    volume_docs = payload.get("valor")  # Representa o 'valor' do lote fiscal
    modulo_fiscal = payload.get("destino")  # Representa o 'destino' da auditoria

    # DN2.1: Validar presença de campos obrigatórios
    # Nota: Campos devem estar presentes (não None) e ter valores válidos
    if sessao is None or modulo_fiscal is None or volume_docs is None:
        raise HTTPException(status_code=400, detail="Parâmetros obrigatórios ausentes")

    # DN2.2: Validar que "valor" é maior que zero
    if not isinstance(volume_docs, (int, float)) or volume_docs <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser um número maior que zero")

    # DN2.5: Apenas após validação completa, iniciar processamento assíncrono
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # DN2.4: Gerar tracking_id apenas para payloads válidos
    return {
        "id": random.randint(20000, 30000),
        "status": 201,
        "tracking_id": str(uuid.uuid4()),
        "arquivold": random.randint(22000, 23000),
        "diagnostico": "Conforme",
        "detalhes": {
            "cliente": sessao,
            "volume_processado": volume_docs,
            "modulo": modulo_fiscal
        }
    }


# =============================================================================
# DN4 — Não-Repúdio de Transações de Auditoria Fiscal
# =============================================================================

@app.post("/api/v1/auditar/nr", status_code=201)
async def processar_auditoria_nr(
    account_key: str = Header(...),
    app_key: str = Header(...),
    payload: Dict[str, Any] = Body(...)
):
    """
    DN4 - Não-Repúdio de Transações

    Endpoint de auditoria fiscal com mecanismos completos de não-repúdio.
    Reutiliza validações do DN2 e adiciona camada criptográfica:
    - DN4.1: Assinatura digital HMAC-SHA256
    - DN4.2: Carimbo temporal imutável (server-side)
    - DN4.3: Cadeia de autenticação (hash do ator)
    - DN4.4: Recibo digital completo
    - DN4.5: Registro em log de auditoria com cadeia de hash
    - DN4.6: Verificação de alertas de não-repúdio
    """
    # --- Reutilizar validações DN2 ---
    sessao = payload.get("sessao_cliente")
    volume_docs = payload.get("valor")
    modulo_fiscal = payload.get("destino")

    if sessao is None or modulo_fiscal is None or volume_docs is None:
        raise HTTPException(status_code=400, detail="Parâmetros obrigatórios ausentes")

    if not isinstance(volume_docs, (int, float)) or volume_docs <= 0:
        raise HTTPException(status_code=400, detail="Valor deve ser um número maior que zero")

    # --- DN4.2: Carimbo temporal imutável (server-side) ---
    timestamp = generate_timestamp()

    # --- Processamento assíncrono (simulação) ---
    await asyncio.sleep(random.uniform(0.1, 0.5))

    # --- Gerar dados base da transação ---
    tracking_id = str(uuid.uuid4())
    transaction_id = random.randint(20000, 30000)

    # --- DN4.1: Assinatura digital HMAC-SHA256 ---
    signature = sign_transaction(payload, timestamp)

    # --- DN4.3: Cadeia de autenticação ---
    actor = hash_actor(account_key)

    # --- DN4.4: Recibo digital completo ---
    receipt = build_receipt(signature, timestamp, actor, tracking_id, payload)

    # --- DN4.6: Verificação de alertas ---
    alert = check_alert(receipt)
    chain_alert = check_chain_alert(audit_log)

    # --- DN4.5: Registro no log de auditoria com cadeia de hash ---
    log_entry = audit_log.append(receipt)

    return {
        "id": transaction_id,
        "status": 201,
        "tracking_id": tracking_id,
        "arquivold": random.randint(22000, 23000),
        "diagnostico": "Conforme",
        "detalhes": {
            "cliente": sessao,
            "volume_processado": volume_docs,
            "modulo": modulo_fiscal
        },
        "non_repudiation": {
            "signature": signature,
            "timestamp": timestamp,
            "actor": actor,
            "receipt": receipt,
            "log_position": log_entry["position"],
            "log_entry_hash": log_entry["entry_hash"],
            "alert": alert,
            "chain_alert": chain_alert
        }
    }


@app.get("/api/v1/audit-log", status_code=200)
async def get_audit_log(
    account_key: str = Header(...),
    app_key: str = Header(...),
):
    """
    DN4.5 - Consulta do Log de Auditoria

    Retorna o log completo de auditoria e o status de integridade da cadeia de hash.
    """
    chain_valid = audit_log.verify_chain()
    chain_alert = check_chain_alert(audit_log)

    return {
        "total_entries": audit_log.size(),
        "chain_integrity": chain_valid,
        "chain_alert": chain_alert,
        "entries": audit_log.get_log()
    }


@app.get("/api/v1/audit-log/{position}", status_code=200)
async def get_audit_log_entry(
    position: int,
    account_key: str = Header(...),
    app_key: str = Header(...),
):
    """
    DN4.5 - Consulta de Entrada Específica do Log de Auditoria
    """
    entry = audit_log.get_entry(position)
    if entry is None:
        raise HTTPException(status_code=404, detail="Entrada não encontrada no log de auditoria")
    return entry


# =============================================================================
# DN3 — Disponibilidade e Resiliência da API
# =============================================================================

@app.get("/api/v1/health", status_code=200)
async def health_check():
    """
    DN3.3 - Health Check da API

    Retorna o estado de saúde da API, incluindo uptime, taxa de erro,
    estado do circuit breaker e rate limiter.
    """
    status = health_checker.get_status()
    status["circuit_breaker"] = circuit_breaker.state.value
    status["availability_alert"] = check_availability_alert(health_checker)
    status["circuit_alert"] = check_circuit_alert(circuit_breaker)
    return status


@app.post("/api/v1/auditar/resilient", status_code=201)
async def processar_auditoria_resiliente(
    account_key: str = Header(...),
    app_key: str = Header(...),
    idempotency_key: str = Header(None),
    payload: Dict[str, Any] = Body(...)
):
    """
    DN3 - Endpoint de auditoria com camada completa de resiliência.

    Aplica rate limiting, circuit breaker, idempotência e degradação
    graciosa sobre o processamento de auditoria fiscal.
    """
    # DN3.1: Rate Limiting
    if not rate_limiter.is_allowed(account_key):
        health_checker.record_request(success=False)
        raise HTTPException(
            status_code=429,
            detail="Rate limit excedido. Tente novamente mais tarde."
        )

    # DN3.4: Idempotência — se a chave já existe, retorna resultado anterior
    if idempotency_key:
        cached = idempotency_store.get(idempotency_key)
        if cached is not None:
            health_checker.record_request(success=True)
            cached["idempotent_replay"] = True
            return cached

    # DN3.2: Circuit Breaker
    if not circuit_breaker.allow_request():
        health_checker.record_request(success=False)
        # DN3.5: Degradação Graciosa
        degraded = build_degraded_response(
            payload,
            reason="Circuit breaker aberto — serviço temporariamente indisponível"
        )
        degraded["availability"] = {
            "circuit_state": circuit_breaker.state.value,
            "alert": check_circuit_alert(circuit_breaker),
        }
        raise HTTPException(status_code=503, detail=degraded)

    # --- Reutilizar validações DN2 ---
    sessao = payload.get("sessao_cliente")
    volume_docs = payload.get("valor")
    modulo_fiscal = payload.get("destino")

    if sessao is None or modulo_fiscal is None or volume_docs is None:
        health_checker.record_request(success=False)
        circuit_breaker.record_failure()
        raise HTTPException(status_code=400, detail="Parâmetros obrigatórios ausentes")

    if not isinstance(volume_docs, (int, float)) or volume_docs <= 0:
        health_checker.record_request(success=False)
        circuit_breaker.record_failure()
        raise HTTPException(status_code=400, detail="Valor deve ser um número maior que zero")

    try:
        await asyncio.sleep(random.uniform(0.1, 0.5))

        response_data = {
            "id": random.randint(20000, 30000),
            "status": 201,
            "tracking_id": str(uuid.uuid4()),
            "arquivold": random.randint(22000, 23000),
            "diagnostico": "Conforme",
            "detalhes": {
                "cliente": sessao,
                "volume_processado": volume_docs,
                "modulo": modulo_fiscal
            },
            "availability": {
                "circuit_state": circuit_breaker.state.value,
                "rate_limit_remaining": rate_limiter.remaining(account_key),
                "idempotent_replay": False,
                "alert": check_rate_limit_alert(rate_limiter, account_key),
            }
        }

        circuit_breaker.record_success()
        health_checker.record_request(success=True)

        # DN3.4: Armazenar resultado para idempotência
        if idempotency_key:
            idempotency_store.store(idempotency_key, response_data)

        return response_data

    except HTTPException:
        raise
    except Exception:
        circuit_breaker.record_failure()
        health_checker.record_request(success=False)
        degraded = build_degraded_response(payload, reason="Erro interno no processamento")
        raise HTTPException(status_code=503, detail=degraded)
