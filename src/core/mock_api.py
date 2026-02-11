from fastapi import FastAPI, Header, HTTPException, Body
from typing import Dict, Any
import uuid
import asyncio
import random

app = FastAPI(title="MOCK_API_G6 - ASIS TaxTech")


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

