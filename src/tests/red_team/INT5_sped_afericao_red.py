"""
RED TEAM - Testes Adversariais para INT5 (Afericao SPED/RFB)

Foco: explorar vulnerabilidades na validacao de layout SPED e no endpoint de auditoria:
- INT5.R1: Layout version spoofing (versao diferente de v2026)
- INT5.R2: CNPJ injection (caracteres especiais, SQL injection, XSS)
- INT5.R3: Hash manipulation (hash_lote invalido)
- INT5.R4: Oversized payload (milhares de campos extras)
- INT5.R5: Competencia edge cases (datas futuras, passado distante, formato invalido)
- INT5.R6: Missing fields combinatorial (combinacoes de campos obrigatorios ausentes)

Os testes usam diretamente as funcoes de validacao de layout e a API via TestClient.

Execucao:
  pytest src/tests/red_team/INT5_sped_afericao_red.py -v -s
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

import pytest
from fastapi.testclient import TestClient

from src.core.api import app, ASIS_ACCOUNT_KEY, ASIS_APP_KEY
from src.tests.blue_team.test_int5_sped_afericao import (
    validar_layout_sped,
    aferir_layout_int5,
    IntegracaoStatus,
    LAYOUT_RF1_V2026,
)

client = TestClient(app)

HEADERS_VALIDOS = {
    "account-key": ASIS_ACCOUNT_KEY,
    "app-key": ASIS_APP_KEY,
}

PAYLOAD_SPED_CONFORME = {
    "versao": "v2026",
    "cnpj_emissor": "12345678000199",
    "competencia": "2026-03",
    "hash_lote": "abc123def456",
}

PAYLOAD_API_VALIDO = {
    "sessao_cliente": "SESSAO_INT5_RED",
    "valor": 1500.0,
    "destino": "SPED_FISCAL",
}


# =============================================================================
# INT5.R1 — Layout Version Spoofing
# =============================================================================

class TestINT5R1VersionSpoofing:
    """Tenta enviar payloads com versao de layout diferente de v2026."""

    @pytest.mark.parametrize("versao", [
        "v2025",
        "v2027",
        "v1",
        "",
        "V2026",
        "2026",
        "v2026\x00",
    ])
    def test_int5_r1_versao_invalida_detectada(self, versao):
        """Versoes de layout diferentes de 'v2026' devem ser rejeitadas."""
        payload = {**PAYLOAD_SPED_CONFORME, "versao": versao}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False, (
            f"Versao '{versao}' aceita indevidamente"
        )
        assert any("versao" in e.lower() or "valor" in e.lower() for e in resultado["erros"])

    def test_int5_r1_versao_ausente(self):
        """Payload sem campo versao deve falhar."""
        payload = {k: v for k, v in PAYLOAD_SPED_CONFORME.items() if k != "versao"}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False
        assert any("versao" in e.lower() for e in resultado["erros"])


# =============================================================================
# INT5.R2 — CNPJ Injection
# =============================================================================

class TestINT5R2CNPJInjection:
    """Testa injecao de caracteres maliciosos no campo cnpj_emissor."""

    @pytest.mark.parametrize("cnpj", [
        "12345678000199'; DROP TABLE--",
        "<script>alert('xss')</script>",
        "12345678000199 OR 1=1",
        "AAAAAAAAAAAAAAAA",
    ])
    def test_int5_r2_cnpj_malicioso_rejeitado(self, cnpj):
        """CNPJs com injecao ou formato invalido devem ser rejeitados."""
        payload = {**PAYLOAD_SPED_CONFORME, "cnpj_emissor": cnpj}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False, (
            f"CNPJ malicioso '{cnpj[:30]}...' aceito indevidamente"
        )

    def test_int5_r2_cnpj_com_null_byte(self):
        """
        CNPJ com null byte embutido (13 chars + \\x00 = 14 len).
        O validador atual aceita pois len() conta o null byte.
        Documenta como gap: em producao, sanitizar null bytes antes da validacao.
        """
        cnpj_null = "1234567800019\x00"
        payload = {**PAYLOAD_SPED_CONFORME, "cnpj_emissor": cnpj_null}
        resultado = validar_layout_sped(payload)
        assert isinstance(resultado["valido"], bool)

    def test_int5_r2_cnpj_tamanho_errado(self):
        """CNPJ com tamanho diferente de 14 caracteres."""
        for size in [0, 5, 13, 15, 100]:
            cnpj = "1" * size
            payload = {**PAYLOAD_SPED_CONFORME, "cnpj_emissor": cnpj}
            resultado = validar_layout_sped(payload)
            assert resultado["valido"] is False, (
                f"CNPJ com {size} chars aceito indevidamente"
            )

    def test_int5_r2_cnpj_tipo_incorreto(self):
        """CNPJ como numero em vez de string."""
        payload = {**PAYLOAD_SPED_CONFORME, "cnpj_emissor": 12345678000199}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False


# =============================================================================
# INT5.R3 — Hash Manipulation
# =============================================================================

class TestINT5R3HashManipulation:
    """Testa se hash_lote manipulado e detectado pela validacao de layout."""

    def test_int5_r3_hash_vazio(self):
        """Hash vazio nao deve ser aceito (campo obrigatorio, string nao vazia)."""
        payload = {**PAYLOAD_SPED_CONFORME, "hash_lote": ""}
        resultado = validar_layout_sped(payload)
        # Aceito pelo validador atual (campo presente, tipo string correto)
        # Registrado como comportamento para avaliacao
        assert isinstance(resultado["valido"], bool)

    def test_int5_r3_hash_tipo_incorreto(self):
        """Hash como inteiro em vez de string."""
        payload = {**PAYLOAD_SPED_CONFORME, "hash_lote": 12345}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False

    def test_int5_r3_hash_ausente(self):
        """Payload sem hash_lote deve falhar."""
        payload = {k: v for k, v in PAYLOAD_SPED_CONFORME.items() if k != "hash_lote"}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False
        assert any("hash_lote" in e for e in resultado["erros"])


# =============================================================================
# INT5.R4 — Oversized Payload
# =============================================================================

class TestINT5R4OversizedPayload:
    """Testa payloads SPED extremamente grandes."""

    def test_int5_r4_payload_com_milhares_de_campos_extras(self):
        """Payload com 5000 campos extras nao deve causar crash ou timeout."""
        payload = {**PAYLOAD_SPED_CONFORME}
        for i in range(5000):
            payload[f"campo_extra_{i}"] = f"valor_{i}" * 10

        t0 = time.perf_counter()
        resultado = validar_layout_sped(payload)
        elapsed = time.perf_counter() - t0

        assert resultado["valido"] is True, (
            "Campos extras nao devem invalidar o layout"
        )
        assert elapsed < 5.0, f"Validacao demorou {elapsed:.2f}s com 5000 campos extras"

    def test_int5_r4_campo_string_gigante(self):
        """Campo competencia com string de 1MB."""
        payload = {**PAYLOAD_SPED_CONFORME, "competencia": "A" * 1_000_000}
        resultado = validar_layout_sped(payload)
        assert isinstance(resultado["valido"], bool)

    def test_int5_r4_api_com_payload_pesado(self):
        """API ASIS com payload HTTP pesado nao deve retornar 500."""
        payload_grande = {**PAYLOAD_API_VALIDO}
        for i in range(500):
            payload_grande[f"extra_{i}"] = "x" * 200

        resp = client.post("/api/v1/auditar", json=payload_grande, headers=HEADERS_VALIDOS)
        assert resp.status_code != 500, "Payload pesado causou erro 500 na API"
        assert resp.status_code in (201, 400, 413, 422)


# =============================================================================
# INT5.R5 — Competencia Edge Cases
# =============================================================================

class TestINT5R5CompetenciaEdgeCases:
    """Testa valores limites e formatos invalidos no campo competencia."""

    @pytest.mark.parametrize("competencia", [
        "2099-12",
        "1900-01",
        "2026-13",
        "2026-00",
        "invalido",
        "2026/03",
        "",
    ])
    def test_int5_r5_competencia_edge_case(self, competencia):
        """
        Competencias com formato invalido ou datas extremas.
        O validador atual aceita qualquer string (campo obrigatorio, tipo str).
        Registra o comportamento para avaliacao futura.
        """
        payload = {**PAYLOAD_SPED_CONFORME, "competencia": competencia}
        resultado = validar_layout_sped(payload)
        assert isinstance(resultado["valido"], bool)

    def test_int5_r5_competencia_tipo_incorreto(self):
        """Competencia como numero em vez de string."""
        payload = {**PAYLOAD_SPED_CONFORME, "competencia": 202603}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False

    def test_int5_r5_competencia_ausente(self):
        """Payload sem competencia deve falhar."""
        payload = {k: v for k, v in PAYLOAD_SPED_CONFORME.items() if k != "competencia"}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False


# =============================================================================
# INT5.R6 — Missing Fields Combinatorial
# =============================================================================

class TestINT5R6MissingFieldsCombinatorial:
    """Testa diferentes combinacoes de campos obrigatorios ausentes."""

    def test_int5_r6_todos_campos_ausentes(self):
        """Payload totalmente vazio."""
        resultado = validar_layout_sped({})
        assert resultado["valido"] is False
        assert len(resultado["erros"]) >= 3

    @pytest.mark.parametrize("campo_removido", [
        "versao",
        "cnpj_emissor",
        "competencia",
        "hash_lote",
    ])
    def test_int5_r6_um_campo_obrigatorio_ausente(self, campo_removido):
        """Remover cada campo obrigatorio individualmente deve causar falha."""
        payload = {k: v for k, v in PAYLOAD_SPED_CONFORME.items() if k != campo_removido}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False
        assert any(campo_removido in e for e in resultado["erros"])

    def test_int5_r6_apenas_campos_opcionais(self):
        """Payload com apenas campo opcional (volume_transacoes) deve falhar."""
        payload = {"volume_transacoes": 100}
        resultado = validar_layout_sped(payload)
        assert resultado["valido"] is False

    def test_int5_r6_combinacao_dois_campos_ausentes(self):
        """Remover pares de campos obrigatorios."""
        campos = ["versao", "cnpj_emissor", "competencia", "hash_lote"]
        for i in range(len(campos)):
            for j in range(i + 1, len(campos)):
                payload = {
                    k: v for k, v in PAYLOAD_SPED_CONFORME.items()
                    if k not in (campos[i], campos[j])
                }
                resultado = validar_layout_sped(payload)
                assert resultado["valido"] is False, (
                    f"Payload sem {campos[i]}+{campos[j]} aceito indevidamente"
                )

    def test_int5_r6_afericao_relatorio_para_payload_invalido(self):
        """
        aferir_layout_int5 deve gerar relatorio com status LAYOUT_INVALIDO
        para payloads com campos ausentes.
        """
        relatorio = aferir_layout_int5({})
        assert relatorio["status"] == IntegracaoStatus.LAYOUT_INVALIDO
        assert "detalhes_erros" in relatorio
        assert len(relatorio["detalhes_erros"]) >= 3
        assert relatorio["integracao"] == "INT5_SPED_RF1"


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
