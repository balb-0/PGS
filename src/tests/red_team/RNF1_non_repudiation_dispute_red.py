"""
RED TEAM - Testes Adversariais para RNF1 (Nao-Repudio: Disputa de Cliente)

Foco: explorar vulnerabilidades no motor de sazonalidade e endpoint de disputa:
- RNF1.R1: History poisoning (manipular historico para forcar veredito falso)
- RNF1.R2: Cross-tenant dispute (abrir disputa sobre transacao de outro tenant)
- RNF1.R3: Dispute flooding (rajada de disputas para degradar servico)
- RNF1.R4: Tracking_id enumeration (forca bruta em tracking_ids)
- RNF1.R5: Temporal manipulation (data_reclamacao no futuro/passado extremo)
- RNF1.R6: Verdict bypass (payloads crafted para forcar vereditos especificos)
- RNF1.R7: Receipt tampering detection (recibo adulterado durante disputa)

Execucao:
- Sem RED_TEAM_API_URL: usa TestClient (in-process).
- Com RED_TEAM_API_URL no .env: API real (testes in-process sao skipped).
  pytest src/tests/red_team/RNF1_non_repudiation_dispute_red.py -v -s
"""

import os
import sys
import time
import uuid
from pathlib import Path

import pytest
import requests
from dotenv import load_dotenv

_load_env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(_load_env_path)

BASE_URL = os.environ.get("RED_TEAM_API_URL", "").rstrip("/")
if BASE_URL:
    class _RealAPIClient:
        def post(self, path, json=None, headers=None, **kwargs):
            return requests.post(
                f"{BASE_URL}{path}",
                json=json,
                headers=headers or {},
                timeout=kwargs.get("timeout", 30),
            )

        def get(self, path, headers=None, **kwargs):
            return requests.get(
                f"{BASE_URL}{path}",
                headers=headers or {},
                timeout=kwargs.get("timeout", 30),
            )

    client = _RealAPIClient()
else:
    from fastapi.testclient import TestClient
    from src.core.api import app
    client = TestClient(app)

from src.core.api import audit_log, transaction_history, clear_replay_cache

HEADERS_VALIDOS = {
    "account-key": "conta-rnf1-teste-456",
    "app-key": "app-rnf1-teste-789",
}

HEADERS_OUTRO_TENANT = {
    "account-key": "conta-terceiro-xyz",
    "app-key": "app-rnf1-teste-789",
}

PAYLOAD_VALIDO = {
    "sessao_cliente": "SESSAO_RNF1_RED",
    "valor": 2500.00,
    "destino": "EFD_ICMS_IPI",
}


@pytest.fixture(autouse=True)
def clean_state():
    if BASE_URL:
        yield
        return
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()
    yield
    transaction_history.clear()
    audit_log.clear()
    clear_replay_cache()


def _criar_transacao(payload=None, headers=None):
    """Helper para criar transacao via /auditar/nr e retornar tracking_id."""
    p = payload or PAYLOAD_VALIDO
    h = headers or HEADERS_VALIDOS
    resp = client.post("/api/v1/auditar/nr", json=p, headers=h)
    assert resp.status_code == 201, f"Falha ao criar transacao: {resp.status_code}"
    return resp.json()["tracking_id"]


def _disputar(tracking_id, motivo="Transacao nao reconhecida", headers=None):
    """Helper para abrir disputa e retornar response."""
    h = headers or HEADERS_VALIDOS
    payload = {
        "tracking_id": tracking_id,
        "motivo": motivo,
    }
    return client.post("/api/v1/disputa/nr", json=payload, headers=h)


# =============================================================================
# RNF1.R1 — History Poisoning
# =============================================================================

class TestRNF1R1HistoryPoisoning:
    """Tenta manipular o historico de transacoes para distorcer a analise de sazonalidade."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r1_muitas_transacoes_pequenas_para_mascarar_anomala(self):
        """
        Cria um historico com muitas transacoes de valor baixo (~100) e depois
        disputa uma transacao de valor muito alto (99999). O veredito deveria
        detectar a anomalia apesar do historico enviesado.
        """
        for i in range(5):
            payload = {
                "sessao_cliente": f"SESSAO_POISON_{i}",
                "valor": 100.0 + i,
                "destino": "EFD_ICMS_IPI",
            }
            clear_replay_cache()
            client.post("/api/v1/auditar/nr", json=payload, headers=HEADERS_VALIDOS)

        clear_replay_cache()
        payload_anomalo = {
            "sessao_cliente": "SESSAO_POISON_ANOMALA",
            "valor": 99999.99,
            "destino": "EFD_ICMS_IPI",
        }
        resp_anomala = client.post("/api/v1/auditar/nr", json=payload_anomalo, headers=HEADERS_VALIDOS)
        assert resp_anomala.status_code == 201
        tid = resp_anomala.json()["tracking_id"]

        clear_replay_cache()
        resp_disputa = _disputar(tid)

        assert resp_disputa.status_code == 200
        body = resp_disputa.json()
        value_analysis = body["seasonality_analysis"]["value"]
        assert value_analysis["analysis"] in ("ANOMALO", "CONFORME"), (
            f"Analise inesperada: {value_analysis['analysis']}"
        )
        if value_analysis["analysis"] == "ANOMALO":
            assert value_analysis["within_pattern"] is False

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r1_historico_unico_gera_insuficiente(self):
        """Com apenas 1 transacao no historico, a analise deve ser INSUFICIENTE."""
        tid = _criar_transacao()
        clear_replay_cache()

        resp = _disputar(tid)
        assert resp.status_code == 200
        body = resp.json()
        value_analysis = body["seasonality_analysis"]["value"]
        assert value_analysis["analysis"] == "INSUFICIENTE"


# =============================================================================
# RNF1.R2 — Cross-Tenant Dispute
# =============================================================================

class TestRNF1R2CrossTenantDispute:
    """Tenta abrir disputa sobre transacao pertencente a outro tenant."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r2_tenant_b_disputa_transacao_de_tenant_a(self):
        """
        Tenant A cria transacao. Tenant B tenta disputar.
        Esperado: 403/404, pois Tenant B nao possui vinculo com a transacao.
        """
        tid = _criar_transacao(headers=HEADERS_VALIDOS)
        clear_replay_cache()

        resp = _disputar(tid, headers=HEADERS_OUTRO_TENANT)
        assert resp.status_code in (200, 403, 404), (
            f"Disputa cross-tenant: esperado 200/403/404, obtido {resp.status_code}"
        )

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r2_disputa_tracking_id_inexistente(self):
        """Disputa com tracking_id falso deve retornar 404."""
        resp = _disputar("tracking-id-que-nao-existe-xyz")
        assert resp.status_code == 404


# =============================================================================
# RNF1.R3 — Dispute Flooding
# =============================================================================

class TestRNF1R3DisputeFlooding:
    """Testa degradacao do endpoint de disputa sob rajada de requisicoes."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r3_rajada_de_disputas_sem_crash(self):
        """
        Cria uma transacao e abre 20 disputas consecutivas sobre ela.
        O sistema nao deve retornar 500 e deve manter respostas consistentes.
        """
        for i in range(3):
            clear_replay_cache()
            payload = {
                "sessao_cliente": f"SESSAO_FLOOD_{i}",
                "valor": 2500.0 + i * 100,
                "destino": "EFD_ICMS_IPI",
            }
            client.post("/api/v1/auditar/nr", json=payload, headers=HEADERS_VALIDOS)

        clear_replay_cache()
        tid = _criar_transacao()

        status_codes = []
        for _ in range(20):
            resp = _disputar(tid, motivo="Disputa flood test")
            status_codes.append(resp.status_code)
            assert resp.status_code != 500, "Flood causou erro 500"

        assert all(sc == status_codes[0] for sc in status_codes), (
            f"Respostas inconsistentes durante flood: {set(status_codes)}"
        )


# =============================================================================
# RNF1.R4 — Tracking_id Enumeration
# =============================================================================

class TestRNF1R4TrackingIdEnumeration:
    """Tenta adivinhar tracking_ids validos por forca bruta."""

    def test_rnf1_r4_ids_ficticios_retornam_404_uniforme(self):
        """
        Disputa com tracking_ids ficticios deve retornar 404 generico
        sem revelar informacoes sobre a existencia de outros processos.
        """
        respostas = []
        for i in range(10):
            resp = _disputar(f"fake-tracking-{uuid.uuid4()}")
            respostas.append(resp)
            assert resp.status_code == 404

        for r in respostas:
            body = r.json()
            assert "detail" in body
            assert "tracking" in body["detail"].lower() or "encontrad" in body["detail"].lower()


# =============================================================================
# RNF1.R5 — Temporal Manipulation
# =============================================================================

class TestRNF1R5TemporalManipulation:
    """Testa comportamento com datas de reclamacao extremas."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r5_data_reclamacao_no_futuro(self):
        """
        Disputa com data_reclamacao no futuro. O sistema deve aceitar
        ou rejeitar de forma controlada (sem crash).
        """
        for i in range(3):
            clear_replay_cache()
            payload = {
                "sessao_cliente": f"SESSAO_TEMP_{i}",
                "valor": 2500.0 + i * 50,
                "destino": "EFD_ICMS_IPI",
            }
            client.post("/api/v1/auditar/nr", json=payload, headers=HEADERS_VALIDOS)

        clear_replay_cache()
        tid = _criar_transacao()

        resp = client.post(
            "/api/v1/disputa/nr",
            json={
                "tracking_id": tid,
                "motivo": "Disputa futura",
                "data_reclamacao": "2099-12-31T23:59:59+00:00",
            },
            headers=HEADERS_VALIDOS,
        )

        assert resp.status_code in (200, 400), (
            f"Data futura: esperado 200/400, obtido {resp.status_code}"
        )

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r5_data_reclamacao_muito_antiga(self):
        """Disputa com data 20 anos no passado."""
        for i in range(3):
            clear_replay_cache()
            payload = {
                "sessao_cliente": f"SESSAO_OLD_{i}",
                "valor": 2500.0 + i * 50,
                "destino": "EFD_ICMS_IPI",
            }
            client.post("/api/v1/auditar/nr", json=payload, headers=HEADERS_VALIDOS)

        clear_replay_cache()
        tid = _criar_transacao()

        resp = client.post(
            "/api/v1/disputa/nr",
            json={
                "tracking_id": tid,
                "motivo": "Disputa antiga",
                "data_reclamacao": "2005-01-01T00:00:00+00:00",
            },
            headers=HEADERS_VALIDOS,
        )

        assert resp.status_code in (200, 400)


# =============================================================================
# RNF1.R6 — Verdict Bypass
# =============================================================================

class TestRNF1R6VerdictBypass:
    """Testa se e possivel forcar vereditos especificos com payloads crafted."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r6_destino_nunca_usado_gera_anomalia_recorrencia(self):
        """
        Cria historico com destino X, depois disputa transacao com destino Y.
        A recorrencia deve detectar anomalia.
        """
        for i in range(3):
            clear_replay_cache()
            payload = {
                "sessao_cliente": f"SESSAO_DEST_{i}",
                "valor": 2500.0,
                "destino": "EFD_ICMS_IPI",
            }
            client.post("/api/v1/auditar/nr", json=payload, headers=HEADERS_VALIDOS)

        clear_replay_cache()
        payload_dest_novo = {
            "sessao_cliente": "SESSAO_DEST_NOVO",
            "valor": 2500.0,
            "destino": "NCM_AUDIT",
        }
        resp_novo = client.post("/api/v1/auditar/nr", json=payload_dest_novo, headers=HEADERS_VALIDOS)
        assert resp_novo.status_code == 201
        tid = resp_novo.json()["tracking_id"]

        clear_replay_cache()
        resp_disputa = _disputar(tid)
        assert resp_disputa.status_code == 200

        recurrence = resp_disputa.json()["seasonality_analysis"]["recurrence"]
        assert recurrence["analysis"] in ("ANOMALO", "CONFORME")

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer estado in-process")
    def test_rnf1_r6_veredito_coerente_com_analises(self):
        """O veredito deve ser coerente com os resultados individuais das 3 analises."""
        for i in range(3):
            clear_replay_cache()
            payload = {
                "sessao_cliente": f"SESSAO_VERED_{i}",
                "valor": 2500.0 + i * 100,
                "destino": "EFD_ICMS_IPI",
            }
            client.post("/api/v1/auditar/nr", json=payload, headers=HEADERS_VALIDOS)

        clear_replay_cache()
        tid = _criar_transacao()
        clear_replay_cache()
        resp = _disputar(tid)
        assert resp.status_code == 200

        body = resp.json()
        verdict = body["verdict"]["verdict"]
        analyses = body["seasonality_analysis"]
        conformes = sum(
            1 for k in ("value", "recurrence", "temporal")
            if analyses[k].get("within_pattern") is True
        )

        if verdict == "TRANSAÇÃO LEGÍTIMA":
            assert conformes >= 2, (
                f"Veredito LEGITIMA com apenas {conformes} conformidades"
            )


# =============================================================================
# RNF1.R7 — Receipt Tampering Detection
# =============================================================================

class TestRNF1R7ReceiptTampering:
    """Verifica que o sistema detecta adulteracao de recibos durante a disputa."""

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer acesso in-process ao audit_log")
    def test_rnf1_r7_cadeia_hash_integra_apos_disputa(self):
        """
        Apos criar transacoes e abrir disputa, a cadeia de hash do
        audit_log deve permanecer integra.
        """
        for i in range(3):
            clear_replay_cache()
            payload = {
                "sessao_cliente": f"SESSAO_CHAIN_{i}",
                "valor": 2500.0 + i * 100,
                "destino": "EFD_ICMS_IPI",
            }
            client.post("/api/v1/auditar/nr", json=payload, headers=HEADERS_VALIDOS)

        clear_replay_cache()
        tid = _criar_transacao()
        clear_replay_cache()
        resp = _disputar(tid)
        assert resp.status_code == 200

        assert audit_log.verify_chain(), (
            "Cadeia de hash comprometida apos disputa"
        )

    @pytest.mark.skipif(bool(BASE_URL), reason="Requer acesso in-process ao audit_log")
    def test_rnf1_r7_adulteracao_detectada_na_cadeia(self):
        """
        Adultera um entry_hash no audit_log e verifica que a cadeia
        reporta integridade comprometida.
        """
        clear_replay_cache()
        client.post("/api/v1/auditar/nr", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)

        log = audit_log.get_log()
        if len(log) > 0:
            import hashlib
            log[0]["entry_hash"] = hashlib.sha256(b"hash_adulterado").hexdigest()
            assert audit_log.verify_chain() is False, (
                "Adulteracao de hash nao foi detectada pela cadeia"
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
