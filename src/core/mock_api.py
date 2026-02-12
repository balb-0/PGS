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

app = FastAPI(title="MOCK_API_G6 - ASIS TaxTech", version="1.1.0")


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
