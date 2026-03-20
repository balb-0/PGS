"""
Blue Team - RNF2 (Seguranca: Autenticidade)

Valida autenticacao em endpoints protegidos:
- 401 para credenciais ausentes
- 403 para credenciais invalidas
- 201 para credenciais validas
- endpoint /health publico
- isolamento entre tenants
"""

import pytest
from fastapi.testclient import TestClient

from src.core.api import app, audit_log, transaction_history, clear_replay_cache


client = TestClient(app)

HEADERS_TENANT_ALPHA = {
    "account-key": "tenant-alpha-account",
    "app-key": "tenant-alpha-app",
}

HEADERS_TENANT_BETA = {
    "account-key": "tenant-beta-account",
    "app-key": "tenant-beta-app",
}

PAYLOAD_VALIDO = {
    "sessao_cliente": "sessao-rnf2-01",
    "valor": 1250.5,
    "destino": "EFD_ICMS_IPI",
}


@pytest.fixture(autouse=True)
def clean_state():
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()
    yield
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()


class TestRNF2Authenticity:
    def test_rnf2_ca1_rejeita_ausencia_de_credenciais(self):
        response = client.post("/api/v1/auditar", json=PAYLOAD_VALIDO)

        assert response.status_code == 401
        assert response.json()["detail"] == "Credenciais de autenticação ausentes"

    def test_rnf2_ca2_rejeita_account_key_invalida(self):
        response = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "conta-invalida", "app-key": "tenant-alpha-app"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Credenciais inválidas"

    def test_rnf2_ca3_rejeita_app_key_invalida(self):
        response = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers={"account-key": "tenant-alpha-account", "app-key": "app-invalida"},
        )

        assert response.status_code == 403
        assert response.json()["detail"] == "Credenciais inválidas"

    def test_rnf2_ca4_aceita_credenciais_validas(self):
        response = client.post(
            "/api/v1/auditar",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_TENANT_ALPHA,
        )

        assert response.status_code == 201
        body = response.json()
        assert "tracking_id" in body

    def test_rnf2_ca5_health_publico_sem_auth(self):
        response = client.get("/api/v1/health")

        assert response.status_code == 200

    def test_rnf2_ca6_isolamento_entre_tenants(self):
        create_resp = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_TENANT_ALPHA,
        )
        assert create_resp.status_code == 201

        actor_hash = create_resp.json()["non_repudiation"]["actor"]

        forbidden_resp = client.get(
            f"/api/v1/historico/{actor_hash}",
            headers=HEADERS_TENANT_BETA,
        )
        assert forbidden_resp.status_code == 403

        own_resp = client.get(
            f"/api/v1/historico/{actor_hash}",
            headers=HEADERS_TENANT_ALPHA,
        )
        assert own_resp.status_code == 200


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
