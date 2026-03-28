import pytest
from fastapi.testclient import TestClient

from src.core.api import app, process_store, MODULOS_FISCAIS_VALIDOS  # type: ignore


client = TestClient(app)


HEADERS_VALIDOS = {
    "account-key": "conta-teste-123",
    "app-key": "app-teste-456",
}


PAYLOAD_VALIDO = {
    "sessao_cliente": "SESSAO_RF_G06",
    "valor": 3200.0,
    "destino": "EFD_ICMS_IPI",
}


@pytest.fixture(autouse=True)
def limpar_store_processos():
    # Limpa o store de processos entre os testes para isolar estado.
    # A API nao expõe um clear, entao resetamos o objeto global diretamente.
    from src.core.api import ProcessStore  # type: ignore

    global process_store  # type: ignore
    process_store = ProcessStore()
    yield
    process_store = ProcessStore()


class TestRF1ConsultaStatusProcesso:
    def test_rf1_ca1_tracking_id_recente_e_consultavel(self):
        # Submete uma auditoria válida para obter tracking_id
        resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)
        assert resp.status_code == 201
        tracking_id = resp.json()["tracking_id"]

        # Consulta o status do processamento pelo tracking_id
        status_resp = client.get(f"/api/v1/processo/{tracking_id}", headers=HEADERS_VALIDOS)
        assert status_resp.status_code == 200
        body = status_resp.json()

        assert body["tracking_id"] == tracking_id
        assert body["status"] in {"pendente", "processando", "concluido"}
        assert body["sessao_cliente"] == PAYLOAD_VALIDO["sessao_cliente"]
        assert body["destino"] == PAYLOAD_VALIDO["destino"]
        assert body["valor"] == PAYLOAD_VALIDO["valor"]
        assert "submitted_at" in body
        assert "updated_at" in body

    def test_rf1_ca3_tracking_id_inexistente_retorna_404(self):
        resp = client.get("/api/v1/processo/nao-existe", headers=HEADERS_VALIDOS)
        assert resp.status_code == 404
        assert resp.json()["detail"] == "Processo não encontrado"


class TestRF2ValidacaoModuloFiscalDestino:
    def test_rf2_ca1_destino_valido_aceito(self):
        resp = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)
        assert resp.status_code == 201

    def test_rf2_ca2_destino_invalido_rejeitado(self):
        payload = {**PAYLOAD_VALIDO, "destino": "MODULO_INEXISTENTE"}
        resp = client.post("/api/v1/auditar", json=payload, headers=HEADERS_VALIDOS)
        assert resp.status_code == 400
        detail = resp.json()["detail"]
        assert "Modulo fiscal de destino invalido" in detail

    def test_rf2_ca3_validacao_case_insensitive(self):
        payload = {**PAYLOAD_VALIDO, "destino": "efd_icms_ipi"}
        resp = client.post("/api/v1/auditar", json=payload, headers=HEADERS_VALIDOS)
        assert resp.status_code == 201
        body = resp.json()
        assert body["detalhes"]["modulo"] == "EFD_ICMS_IPI"

    def test_rf2_ca5_todos_os_modulos_validos_sao_aceitos(self):
        for modulo in MODULOS_FISCAIS_VALIDOS:
            payload = {**PAYLOAD_VALIDO, "destino": modulo}
            resp = client.post("/api/v1/auditar", json=payload, headers=HEADERS_VALIDOS)
            assert resp.status_code == 201

