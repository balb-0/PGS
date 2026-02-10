from fastapi import FastAPI, Header, HTTPException, Body
import uuid
import asyncio
import random

app = FastAPI(title="MOCK_API_G6 - ASIS TaxTech")

@app.post("/api/v1/auditar", status_code=201)
async def processar_auditoria(
    account_key: str = Header(...),
    app_key: str = Header(...),     
    payload: dict = Body(...)
):
    sessao = payload.get("sessao_cliente")
    volume_docs = payload.get("valor") # Representa o 'valor' do lote fiscal
    modulo_fiscal = payload.get("destino") # Representa o 'destino' da auditoria

    if not all([sessao, volume_docs, modulo_fiscal]):
        raise HTTPException(status_code=400, detail="Parâmetros obrigatórios ausentes")

    await asyncio.sleep(random.uniform(0.1, 0.5))

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