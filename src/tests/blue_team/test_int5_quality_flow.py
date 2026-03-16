import sys
import time
from pathlib import Path

from fastapi.testclient import TestClient

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core import api as core_api
from src.core.api import app, ASIS_ACCOUNT_KEY, ASIS_APP_KEY
from src.tests.blue_team.test_int5_sped_afericao import (
    EXPECTED_VERSION,
    IntegracaoStatus,
    aferir_layout_int5,
)


client = TestClient(app)

HEADERS_VALIDOS = {
    "account-key": ASIS_ACCOUNT_KEY,
    "app-key": ASIS_APP_KEY,
}

PAYLOAD_VALIDO = {
    "sessao_cliente": "SESSAO_INT5_QUALITY",
    "valor": 2750.0,
    "destino": "SPED_FISCAL",
}


async def _falha_externa_forcada(*args, **kwargs):
    raise TimeoutError("falha externa simulada para validar fallback INT5")


def test_int5_fluxo_responde_com_contrato_no_tempo_esperado(monkeypatch):
    monkeypatch.setattr(core_api, "asis_upload_file", _falha_externa_forcada)

    inicio = time.perf_counter()
    resposta = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)
    duracao = time.perf_counter() - inicio

    assert resposta.status_code == 201
    assert duracao < 1.0

    dados = resposta.json()
    assert dados["diagnostico"] == "Conforme (Fallback Mock)"
    assert "payload_sped_gerado" in dados
    assert dados["payload_sped_gerado"]["versao"] == EXPECTED_VERSION


def test_int5_afericao_confirma_contrato_gerado(monkeypatch):
    monkeypatch.setattr(core_api, "asis_upload_file", _falha_externa_forcada)

    resposta = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)

    assert resposta.status_code == 201
    contrato = resposta.json()["payload_sped_gerado"]
    relatorio = aferir_layout_int5(contrato)

    assert relatorio["integracao"] == "INT5_SPED_RF1"
    assert relatorio["versao_layout"] == EXPECTED_VERSION
    assert relatorio["status"] == IntegracaoStatus.CONFORME


def test_int5_payload_invalido_retorna_400_sem_gerar_contrato():
    resposta = client.post(
        "/api/v1/auditar",
        json={"sessao_cliente": "SESSAO_INVALIDA", "destino": "SPED_FISCAL"},
        headers=HEADERS_VALIDOS,
    )

    assert resposta.status_code == 400
    assert resposta.json()["detail"] == "Parâmetros obrigatórios ausentes"
