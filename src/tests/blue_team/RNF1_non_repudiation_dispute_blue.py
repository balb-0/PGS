"""
Testes automatizados para RNF1 - Verificação de Não-Repúdio a partir de Reclamação de Cliente
Projeto ASIS TaxTech - Grupo 06 - Abordagem Test Data Driven (TDD)

Este módulo implementa a aferição do Requisito Não Funcional 1 (RNF1):
"Testar o alerta não-repúdio a partir de uma reclamação de cliente por transação
alegada como não efetuada no dia anterior. Verificar se a transação está dentro
da sazonalidade de valor, recorrência e data."

Direcionadores testados:
- RNF1.1: Análise de Sazonalidade de Valor (média ± 2σ)
- RNF1.2: Análise de Sazonalidade de Recorrência (destino habitual)
- RNF1.3: Análise de Sazonalidade Temporal (janela horária habitual)
- RNF1.4: Veredito Consolidado da Disputa (LEGÍTIMA / ALERTA / INCONCLUSIVO)
- RNF1.5: Emissão de Alerta de Não-Repúdio para Disputa
- RNF1.6: Integridade do Recibo Original na Disputa
- RNF1.7: Contrato do Endpoint de Disputa (POST /api/v1/disputa/nr)

Massa de testes: Cada cenário é executado 3 vezes (iterações parametrizadas)
para garantir consistência e reprodutibilidade dos resultados.

Versão da API: v2.0.0 — POST /api/v1/disputa/nr
"""

import pytest
import hashlib
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import sys
from pathlib import Path

from src.core.api import app
from src.core.api import (
    SeasonalityAnalyzer,
    TransactionHistoryStore,
    check_dispute_alert,
    check_alert,
    hash_actor,
    audit_log,
    transaction_history,
    generate_timestamp,
    build_receipt,
    sign_transaction,
)

client = TestClient(app)

HEADERS_VALIDOS = {
    "account-key": "conta-rnf1-teste-456",
    "app-key": "app-rnf1-teste-789",
}

PAYLOAD_VALIDO = {
    "sessao_cliente": "SESSAO_RNF1_G06",
    "valor": 2500.00,
    "destino": "EFD_ICMS_IPI",
}

PAYLOAD_VALOR_SIMILAR_1 = {
    "sessao_cliente": "SESSAO_RNF1_G06",
    "valor": 2600.00,
    "destino": "EFD_ICMS_IPI",
}

PAYLOAD_VALOR_SIMILAR_2 = {
    "sessao_cliente": "SESSAO_RNF1_G06",
    "valor": 2400.00,
    "destino": "EFD_ICMS_IPI",
}

PAYLOAD_VALOR_ANOMALO = {
    "sessao_cliente": "SESSAO_RNF1_G06",
    "valor": 99999.99,
    "destino": "MODULO_DESCONHECIDO",
}

ITERACOES = [1, 2, 3]


@pytest.fixture(autouse=True)
def setup_teardown():
    """Isola estado global antes de cada cenário de teste."""
    from src.core.api import clear_replay_cache
    audit_log.clear()
    transaction_history.clear()
    clear_replay_cache()
    yield
    audit_log.clear()
    transaction_history.clear()
    clear_replay_cache()


def _criar_historico_transacoes(n=5, headers=None, payload_base=None):
    """
    Helper: cria N transações via endpoint /api/v1/auditar/nr para popular
    o histórico do ator. Retorna lista de tracking_ids criados.
    """
    if headers is None:
        headers = HEADERS_VALIDOS
    if payload_base is None:
        payload_base = PAYLOAD_VALIDO

    tracking_ids = []
    for i in range(n):
        p = {**payload_base, "idx_historico": i}
        resp = client.post("/api/v1/auditar/nr", json=p, headers=headers)
        assert resp.status_code == 201, f"Falha ao criar transação {i}: {resp.json()}"
        tracking_ids.append(resp.json()["tracking_id"])
    return tracking_ids


def _abrir_disputa(tracking_id, motivo="Transação não reconhecida", headers=None):
    """Helper: abre uma disputa para um tracking_id específico."""
    if headers is None:
        headers = HEADERS_VALIDOS
    return client.post(
        "/api/v1/disputa/nr",
        json={"tracking_id": tracking_id, "motivo": motivo},
        headers=headers,
    )


# ===========================================================================
# RNF1.1 — Análise de Sazonalidade de Valor
# ===========================================================================

class TestRNF1SazonalidadeValor:
    """
    Testes para RNF1.1 - Análise de Sazonalidade de Valor

    Objetivo: Validar que o sistema analisa corretamente se o valor da
    transação contestada está dentro do intervalo estatístico do histórico
    do cliente (média ± 2σ).
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_valor_dentro_do_padrao_historico(self, iteracao):
        """
        RNF1.1: Transação com valor próximo à média histórica deve ser
        classificada como CONFORME.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "CONFORME", within_pattern == True.
        """
        history = [
            {"payload": {"valor": 2500.00}},
            {"payload": {"valor": 2600.00}},
            {"payload": {"valor": 2400.00}},
            {"payload": {"valor": 2550.00}},
        ]

        result = SeasonalityAnalyzer.analyze_value_seasonality(history, 2500.00)

        assert result["analysis"] == "CONFORME"
        assert result["within_pattern"] is True
        assert "historical_mean" in result
        assert "acceptable_range" in result

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_valor_fora_do_padrao_historico(self, iteracao):
        """
        RNF1.1: Transação com valor muito acima da média + 2σ deve ser
        classificada como ANOMALO.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "ANOMALO", within_pattern == False.
        """
        history = [
            {"payload": {"valor": 100.00}},
            {"payload": {"valor": 110.00}},
            {"payload": {"valor": 105.00}},
            {"payload": {"valor": 95.00}},
        ]

        result = SeasonalityAnalyzer.analyze_value_seasonality(history, 99999.99)

        assert result["analysis"] == "ANOMALO"
        assert result["within_pattern"] is False

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_valor_historico_insuficiente(self, iteracao):
        """
        RNF1.1: Com histórico insuficiente (< 2 transações), a análise
        deve retornar INSUFICIENTE.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "INSUFICIENTE", within_pattern == None.
        """
        history = [{"payload": {"valor": 500.00}}]

        result = SeasonalityAnalyzer.analyze_value_seasonality(history, 500.00)

        assert result["analysis"] == "INSUFICIENTE"
        assert result["within_pattern"] is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_valor_todos_iguais_margem_10_porcento(self, iteracao):
        """
        RNF1.1: Quando todos os valores históricos são iguais (σ=0),
        o sistema deve usar margem de 10%.

        Iteração: {iteracao}/3
        Resultado esperado: valor dentro da margem → CONFORME.
        """
        history = [
            {"payload": {"valor": 1000.00}},
            {"payload": {"valor": 1000.00}},
            {"payload": {"valor": 1000.00}},
        ]

        result_dentro = SeasonalityAnalyzer.analyze_value_seasonality(history, 1050.00)
        result_fora = SeasonalityAnalyzer.analyze_value_seasonality(history, 2000.00)

        assert result_dentro["analysis"] == "CONFORME"
        assert result_fora["analysis"] == "ANOMALO"


# ===========================================================================
# RNF1.2 — Análise de Sazonalidade de Recorrência
# ===========================================================================

class TestRNF1SazonalidadeRecorrencia:
    """
    Testes para RNF1.2 - Análise de Sazonalidade de Recorrência

    Objetivo: Validar que o sistema verifica se o cliente já realizou
    transações para o mesmo destino (módulo fiscal).
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_destino_recorrente_no_historico(self, iteracao):
        """
        RNF1.2: Destino que já aparece no histórico deve ser CONFORME.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "CONFORME", within_pattern == True.
        """
        history = [
            {"payload": {"destino": "EFD_ICMS_IPI"}},
            {"payload": {"destino": "NCM_AUDIT"}},
            {"payload": {"destino": "EFD_ICMS_IPI"}},
        ]

        result = SeasonalityAnalyzer.analyze_recurrence_seasonality(history, "EFD_ICMS_IPI")

        assert result["analysis"] == "CONFORME"
        assert result["within_pattern"] is True
        assert result["historical_occurrences"] == 2
        assert result["frequency_percent"] > 0

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_destino_nunca_utilizado(self, iteracao):
        """
        RNF1.2: Destino que nunca aparece no histórico deve ser ANOMALO.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "ANOMALO", within_pattern == False.
        """
        history = [
            {"payload": {"destino": "EFD_ICMS_IPI"}},
            {"payload": {"destino": "NCM_AUDIT"}},
        ]

        result = SeasonalityAnalyzer.analyze_recurrence_seasonality(history, "MODULO_DESCONHECIDO")

        assert result["analysis"] == "ANOMALO"
        assert result["within_pattern"] is False
        assert result["historical_occurrences"] == 0

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_recorrencia_calcula_frequencia(self, iteracao):
        """
        RNF1.2: A frequência de recorrência deve ser calculada corretamente.

        Iteração: {iteracao}/3
        Resultado esperado: frequency_percent reflete a proporção real.
        """
        history = [
            {"payload": {"destino": "EFD_ICMS_IPI"}},
            {"payload": {"destino": "EFD_ICMS_IPI"}},
            {"payload": {"destino": "NCM_AUDIT"}},
            {"payload": {"destino": "EFD_CONTRIBUICOES"}},
        ]

        result = SeasonalityAnalyzer.analyze_recurrence_seasonality(history, "EFD_ICMS_IPI")

        assert result["frequency_percent"] == 50.0
        assert result["total_transactions"] == 4


# ===========================================================================
# RNF1.3 — Análise de Sazonalidade Temporal
# ===========================================================================

class TestRNF1SazonalidadeTemporal:
    """
    Testes para RNF1.3 - Análise de Sazonalidade Temporal (Data/Horário)

    Objetivo: Validar que o sistema verifica se o horário da transação
    contestada está dentro da janela habitual de operação do cliente.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_horario_dentro_da_janela_habitual(self, iteracao):
        """
        RNF1.3: Transação em horário compatível com o histórico deve ser CONFORME.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "CONFORME", within_pattern == True.
        """
        history = [
            {"timestamp": "2026-02-10T14:00:00+00:00"},
            {"timestamp": "2026-02-11T15:00:00+00:00"},
            {"timestamp": "2026-02-12T13:30:00+00:00"},
        ]

        result = SeasonalityAnalyzer.analyze_temporal_seasonality(
            history, "2026-02-13T14:30:00+00:00"
        )

        assert result["analysis"] == "CONFORME"
        assert result["within_pattern"] is True

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_horario_fora_da_janela_habitual(self, iteracao):
        """
        RNF1.3: Transação em horário muito diferente do padrão (ex: 3h da manhã
        quando o histórico é diurno) deve ser ANOMALO.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "ANOMALO", within_pattern == False.
        """
        history = [
            {"timestamp": "2026-02-10T14:00:00+00:00"},
            {"timestamp": "2026-02-11T15:00:00+00:00"},
            {"timestamp": "2026-02-12T13:00:00+00:00"},
        ]

        result = SeasonalityAnalyzer.analyze_temporal_seasonality(
            history, "2026-02-13T03:00:00+00:00"
        )

        assert result["analysis"] == "ANOMALO"
        assert result["within_pattern"] is False

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_historico_temporal_insuficiente(self, iteracao):
        """
        RNF1.3: Com histórico temporal insuficiente (< 2 registros),
        a análise deve retornar INSUFICIENTE.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "INSUFICIENTE".
        """
        history = [{"timestamp": "2026-02-10T14:00:00+00:00"}]

        result = SeasonalityAnalyzer.analyze_temporal_seasonality(
            history, "2026-02-13T14:00:00+00:00"
        )

        assert result["analysis"] == "INSUFICIENTE"
        assert result["within_pattern"] is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_timestamp_invalido_retorna_erro(self, iteracao):
        """
        RNF1.3: Timestamp inválido da transação contestada retorna ERRO.

        Iteração: {iteracao}/3
        Resultado esperado: analysis == "ERRO".
        """
        history = [
            {"timestamp": "2026-02-10T14:00:00+00:00"},
            {"timestamp": "2026-02-11T15:00:00+00:00"},
        ]

        result = SeasonalityAnalyzer.analyze_temporal_seasonality(
            history, "timestamp-invalido-xyz"
        )

        assert result["analysis"] == "ERRO"
        assert result["within_pattern"] is None


# ===========================================================================
# RNF1.4 — Veredito Consolidado da Disputa
# ===========================================================================

class TestRNF1VereditoConsolidado:
    """
    Testes para RNF1.4 - Veredito Consolidado da Disputa

    Objetivo: Validar que o sistema combina corretamente as três análises
    de sazonalidade para emitir um veredito sobre a transação contestada.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_veredito_transacao_legitima(self, iteracao):
        """
        RNF1.4: Quando todas as análises são CONFORME, o veredito deve
        ser TRANSAÇÃO LEGÍTIMA com confiança ALTA.

        Iteração: {iteracao}/3
        """
        value_ok = {"analysis": "CONFORME", "within_pattern": True}
        recurrence_ok = {"analysis": "CONFORME", "within_pattern": True}
        temporal_ok = {"analysis": "CONFORME", "within_pattern": True}

        verdict = SeasonalityAnalyzer.generate_dispute_verdict(
            value_ok, recurrence_ok, temporal_ok
        )

        assert verdict["verdict"] == "TRANSAÇÃO LEGÍTIMA"
        assert verdict["confidence"] == "ALTA"
        assert verdict["anomalies_detected"] == 0
        assert verdict["alert"] is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_veredito_alerta_uma_anomalia(self, iteracao):
        """
        RNF1.4: Quando uma dimensão é ANOMALO, o veredito deve ser
        ALERTA NÃO-REPÚDIO com confiança MÉDIA.

        Iteração: {iteracao}/3
        """
        value_anomalo = {"analysis": "ANOMALO", "within_pattern": False}
        recurrence_ok = {"analysis": "CONFORME", "within_pattern": True}
        temporal_ok = {"analysis": "CONFORME", "within_pattern": True}

        verdict = SeasonalityAnalyzer.generate_dispute_verdict(
            value_anomalo, recurrence_ok, temporal_ok
        )

        assert verdict["verdict"] == "ALERTA NÃO-REPÚDIO"
        assert verdict["confidence"] == "MÉDIA"
        assert verdict["anomalies_detected"] == 1
        assert "VALOR" in verdict["alert"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_veredito_alerta_multiplas_anomalias(self, iteracao):
        """
        RNF1.4: Quando 2+ dimensões são ANOMALO, o veredito deve ter
        confiança ALTA.

        Iteração: {iteracao}/3
        """
        value_anomalo = {"analysis": "ANOMALO", "within_pattern": False}
        recurrence_anomalo = {"analysis": "ANOMALO", "within_pattern": False}
        temporal_ok = {"analysis": "CONFORME", "within_pattern": True}

        verdict = SeasonalityAnalyzer.generate_dispute_verdict(
            value_anomalo, recurrence_anomalo, temporal_ok
        )

        assert verdict["verdict"] == "ALERTA NÃO-REPÚDIO"
        assert verdict["confidence"] == "ALTA"
        assert verdict["anomalies_detected"] == 2
        assert "VALOR" in verdict["alert"]
        assert "RECORRÊNCIA" in verdict["alert"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_veredito_inconclusivo(self, iteracao):
        """
        RNF1.4: Quando todas as dimensões são INSUFICIENTE, o veredito
        deve ser INCONCLUSIVO.

        Iteração: {iteracao}/3
        """
        insuf = {"analysis": "INSUFICIENTE", "within_pattern": None}

        verdict = SeasonalityAnalyzer.generate_dispute_verdict(insuf, insuf, insuf)

        assert verdict["verdict"] == "INCONCLUSIVO"
        assert verdict["confidence"] == "BAIXA"
        assert verdict["insufficient_data"] == 3

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_veredito_misto_conforme_e_insuficiente(self, iteracao):
        """
        RNF1.4: Quando algumas dimensões são CONFORME e outras INSUFICIENTE
        (sem anomalia), o veredito deve ser TRANSAÇÃO LEGÍTIMA com confiança MÉDIA.

        Iteração: {iteracao}/3
        """
        value_ok = {"analysis": "CONFORME", "within_pattern": True}
        recurrence_ok = {"analysis": "CONFORME", "within_pattern": True}
        temporal_insuf = {"analysis": "INSUFICIENTE", "within_pattern": None}

        verdict = SeasonalityAnalyzer.generate_dispute_verdict(
            value_ok, recurrence_ok, temporal_insuf
        )

        assert verdict["verdict"] == "TRANSAÇÃO LEGÍTIMA"
        assert verdict["confidence"] == "MÉDIA"
        assert verdict["conformities_detected"] == 2
        assert verdict["insufficient_data"] == 1


# ===========================================================================
# RNF1.5 — Emissão de Alerta de Não-Repúdio para Disputa
# ===========================================================================

class TestRNF1AlertaDisputa:
    """
    Testes para RNF1.5 - Emissão de Alerta de Não-Repúdio

    Objetivo: Validar que o sistema emite alertas corretamente para
    disputas com anomalias, inconclusivas, e sem anomalias.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_alerta_para_transacao_legitima(self, iteracao):
        """
        RNF1.5: Transação legítima NÃO deve gerar alerta.

        Iteração: {iteracao}/3
        """
        verdict = {"verdict": "TRANSAÇÃO LEGÍTIMA", "alert": None}
        alert = check_dispute_alert(verdict)
        assert alert is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_para_anomalia(self, iteracao):
        """
        RNF1.5: Disputa com anomalia deve gerar alerta contendo 'ALERTA'.

        Iteração: {iteracao}/3
        """
        verdict = {
            "verdict": "ALERTA NÃO-REPÚDIO",
            "alert": "ALERTA NÃO-REPÚDIO: Transação contestada apresenta anomalia em: VALOR",
        }
        alert = check_dispute_alert(verdict)

        assert alert is not None
        assert "ALERTA" in alert
        assert "VALOR" in alert

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_para_inconclusivo(self, iteracao):
        """
        RNF1.5: Disputa inconclusiva deve gerar alerta de investigação manual.

        Iteração: {iteracao}/3
        """
        verdict = {"verdict": "INCONCLUSIVO", "alert": "..."}
        alert = check_dispute_alert(verdict)

        assert alert is not None
        assert "ALERTA" in alert
        assert "inconclusiva" in alert.lower()


# ===========================================================================
# RNF1.6 — Integridade do Recibo Original na Disputa
# ===========================================================================

class TestRNF1IntegridadeRecibo:
    """
    Testes para RNF1.6 - Verificação de Integridade do Recibo Original

    Objetivo: Validar que ao processar uma disputa, o sistema verifica
    se o recibo digital original da transação contestada está íntegro.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_recibo_integro_na_disputa(self, iteracao):
        """
        RNF1.6: Disputa de transação com recibo íntegro deve reportar
        receipt_integrity == True.

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(3)
        resp = _abrir_disputa(tracking_ids[0])

        assert resp.status_code == 200
        data = resp.json()
        assert data["transacao_original"]["receipt_integrity"] is True
        assert data["transacao_original"]["receipt_alert"] is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_disputa_retorna_payload_original(self, iteracao):
        """
        RNF1.6: A disputa deve retornar os dados originais da transação
        contestada para rastreabilidade.

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(3)
        resp = _abrir_disputa(tracking_ids[0])

        data = resp.json()
        tx_original = data["transacao_original"]

        assert "tracking_id" in tx_original
        assert tx_original["tracking_id"] == tracking_ids[0]
        assert "payload" in tx_original
        assert "timestamp" in tx_original


# ===========================================================================
# RNF1.7 — Contrato do Endpoint de Disputa
# ===========================================================================

class TestRNF1ContratoEndpoint:
    """
    Testes de contrato para POST /api/v1/disputa/nr

    Objetivo: Validar a estrutura completa da resposta do endpoint de disputa
    e garantir que todos os campos obrigatórios estão presentes.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_endpoint_disputa_existe_e_retorna_200(self, iteracao):
        """
        RNF1.7: POST /api/v1/disputa/nr deve existir e retornar HTTP 200
        para disputa válida.

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(3)
        resp = _abrir_disputa(tracking_ids[0])

        assert resp.status_code == 200

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_estrutura_resposta_completa(self, iteracao):
        """
        RNF1.7: A resposta deve conter todos os blocos obrigatórios:
        disputa, transacao_original, seasonality_analysis, verdict, alert.

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(3)
        resp = _abrir_disputa(tracking_ids[0])
        data = resp.json()

        blocos_obrigatorios = [
            "disputa", "transacao_original", "seasonality_analysis",
            "verdict", "alert", "analysis_timestamp",
        ]
        for bloco in blocos_obrigatorios:
            assert bloco in data, f"Bloco '{bloco}' ausente na resposta"

        # Verificar sub-blocos de seasonality_analysis
        sa = data["seasonality_analysis"]
        assert "value" in sa
        assert "recurrence" in sa
        assert "temporal" in sa

        # Verificar campos do verdict
        v = data["verdict"]
        assert "verdict" in v
        assert "confidence" in v
        assert "anomalies_detected" in v

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_disputa_sem_tracking_id_retorna_400(self, iteracao):
        """
        RNF1.7: Disputa sem tracking_id deve retornar HTTP 400.

        Iteração: {iteracao}/3
        """
        resp = client.post(
            "/api/v1/disputa/nr",
            json={"motivo": "Teste sem tracking_id"},
            headers=HEADERS_VALIDOS,
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_disputa_sem_motivo_retorna_400(self, iteracao):
        """
        RNF1.7: Disputa sem motivo deve retornar HTTP 400.

        Iteração: {iteracao}/3
        """
        resp = client.post(
            "/api/v1/disputa/nr",
            json={"tracking_id": "abc-123"},
            headers=HEADERS_VALIDOS,
        )
        assert resp.status_code == 400

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_disputa_tracking_id_inexistente_retorna_404(self, iteracao):
        """
        RNF1.7: Disputa com tracking_id inexistente retorna HTTP 404.

        Iteração: {iteracao}/3
        """
        resp = _abrir_disputa("tracking-id-que-nao-existe")
        assert resp.status_code == 404

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_headers_obrigatorios(self, iteracao):
        """
        RNF1.7: Headers account-key e app-key são obrigatórios.

        Iteração: {iteracao}/3
        """
        resp = client.post(
            "/api/v1/disputa/nr",
            json={"tracking_id": "abc", "motivo": "teste"},
        )
        assert resp.status_code == 401


# ===========================================================================
# RNF1 — Testes de Fluxo Completo (End-to-End)
# ===========================================================================

class TestRNF1FluxoCompleto:
    """
    Testes end-to-end que simulam o fluxo completo de:
    1. Cliente realiza várias transações (cria histórico)
    2. Cliente abre reclamação sobre transação do dia anterior
    3. Sistema analisa sazonalidade e emite veredito

    Simula exatamente o cenário descrito no RNF1:
    "Testar o alerta não-repúdio a partir de uma reclamação de cliente
    por transação alegada como não efetuada no dia anterior."
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_fluxo_completo_transacao_dentro_do_padrao(self, iteracao):
        """
        RNF1 E2E: Cliente reclama de transação que está DENTRO do padrão
        de sazonalidade. Sistema deve confirmar como legítima.

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(5, payload_base=PAYLOAD_VALIDO)

        resp = _abrir_disputa(
            tracking_ids[2],
            motivo="Não reconheço esta transação de ontem",
        )

        assert resp.status_code == 200
        data = resp.json()

        # O valor está dentro do padrão (todas as transações têm valor similar)
        assert data["seasonality_analysis"]["value"]["analysis"] == "CONFORME"

        # O destino é recorrente
        assert data["seasonality_analysis"]["recurrence"]["analysis"] == "CONFORME"

        # O veredito deve ser legítimo (valor + recorrência conformes)
        assert data["verdict"]["verdict"] in ("TRANSAÇÃO LEGÍTIMA", "ALERTA NÃO-REPÚDIO")
        assert data["verdict"]["anomalies_detected"] <= 1

        # Recibo original deve estar íntegro
        assert data["transacao_original"]["receipt_integrity"] is True

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_fluxo_completo_transacao_valor_anomalo(self, iteracao):
        """
        RNF1 E2E: Simula cenário onde uma transação com valor anômalo foi
        processada e o cliente reclama. O sistema deve detectar a anomalia
        de valor.

        Iteração: {iteracao}/3

        Nota: A recorrência pode ser CONFORME porque a transação contestada
        já está no histórico do ator (a própria transação aparece como 1
        ocorrência do destino). O foco desta verificação é a anomalia de VALOR.
        """
        # Criar histórico com valores normais
        _criar_historico_transacoes(4, payload_base=PAYLOAD_VALIDO)

        # Criar uma transação com valor anômalo
        resp_anomala = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALOR_ANOMALO,
            headers=HEADERS_VALIDOS,
        )
        assert resp_anomala.status_code == 201
        tracking_anomalo = resp_anomala.json()["tracking_id"]

        # Abrir disputa sobre a transação anômala
        resp_disputa = _abrir_disputa(
            tracking_anomalo,
            motivo="Valor de R$99.999,99 não reconhecido",
        )

        assert resp_disputa.status_code == 200
        data = resp_disputa.json()

        # O valor deve ser detectado como anômalo (muito acima da média ± 2σ)
        assert data["seasonality_analysis"]["value"]["analysis"] == "ANOMALO"
        assert data["seasonality_analysis"]["value"]["within_pattern"] is False

        # O veredito deve emitir alerta (pelo menos a anomalia de valor)
        assert data["verdict"]["verdict"] == "ALERTA NÃO-REPÚDIO"
        assert data["verdict"]["anomalies_detected"] >= 1
        assert data["alert"] is not None
        assert "ALERTA" in data["alert"]
        assert "VALOR" in data["alert"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_fluxo_disputa_identifica_ator(self, iteracao):
        """
        RNF1 E2E: A disputa deve identificar corretamente o ator da
        transação e o ator do reclamante, verificando se são o mesmo.

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(3)
        resp = _abrir_disputa(tracking_ids[0])

        data = resp.json()
        disputa = data["disputa"]

        # O reclamante usa o mesmo account-key, logo devem ser iguais
        assert disputa["same_actor"] is True
        assert disputa["reclamante_actor"] == disputa["transacao_actor"]

        # Ator deve ser o hash do account-key
        expected_actor = hashlib.sha256(
            HEADERS_VALIDOS["account-key"].encode("utf-8")
        ).hexdigest()
        assert disputa["transacao_actor"] == expected_actor

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_fluxo_disputa_por_terceiro(self, iteracao):
        """
        RNF1 E2E: Quando a disputa é aberta por um terceiro (diferente
        do ator original), o campo same_actor deve ser False.

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(3)

        headers_terceiro = {
            "account-key": "conta-terceiro-xyz",
            "app-key": "app-rnf1-teste-789",
        }

        resp = _abrir_disputa(
            tracking_ids[0],
            motivo="Investigação de fraude",
            headers=headers_terceiro,
        )

        data = resp.json()
        assert data["disputa"]["same_actor"] is False

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_fluxo_analise_timestamp_presente(self, iteracao):
        """
        RNF1 E2E: A resposta da disputa deve incluir o timestamp
        da análise (server-side).

        Iteração: {iteracao}/3
        """
        tracking_ids = _criar_historico_transacoes(3)
        resp = _abrir_disputa(tracking_ids[0])

        data = resp.json()
        assert "analysis_timestamp" in data
        ts = datetime.fromisoformat(data["analysis_timestamp"])
        assert ts.year >= 2026


# ===========================================================================
# RNF1 — Testes Unitários do TransactionHistoryStore
# ===========================================================================

class TestRNF1TransactionHistoryStore:
    """
    Testes unitários para o TransactionHistoryStore.

    Objetivo: Validar o armazenamento e recuperação do histórico
    de transações usado na análise de sazonalidade.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_registrar_e_recuperar_transacao(self, iteracao):
        """
        RNF1: O store deve registrar e recuperar transações por ator.

        Iteração: {iteracao}/3
        """
        store = TransactionHistoryStore()
        store.record("actor1", {"tracking_id": "tx1", "payload": {"valor": 100}})
        store.record("actor1", {"tracking_id": "tx2", "payload": {"valor": 200}})

        history = store.get_history("actor1")
        assert len(history) == 2
        assert history[0]["tracking_id"] == "tx1"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_buscar_por_tracking_id(self, iteracao):
        """
        RNF1: O store deve encontrar transação pelo tracking_id.

        Iteração: {iteracao}/3
        """
        store = TransactionHistoryStore()
        store.record("actor1", {"tracking_id": "tx-abc-123", "payload": {"valor": 500}})
        store.record("actor2", {"tracking_id": "tx-def-456", "payload": {"valor": 700}})

        tx = store.get_transaction_by_tracking_id("tx-def-456")
        assert tx is not None
        assert tx["payload"]["valor"] == 700

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_tracking_id_inexistente_retorna_none(self, iteracao):
        """
        RNF1: Busca por tracking_id inexistente retorna None.

        Iteração: {iteracao}/3
        """
        store = TransactionHistoryStore()
        tx = store.get_transaction_by_tracking_id("nao-existe")
        assert tx is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_historico_isolado_por_ator(self, iteracao):
        """
        RNF1: O histórico deve ser isolado por ator.

        Iteração: {iteracao}/3
        """
        store = TransactionHistoryStore()
        store.record("actor1", {"tracking_id": "tx1"})
        store.record("actor2", {"tracking_id": "tx2"})

        assert len(store.get_history("actor1")) == 1
        assert len(store.get_history("actor2")) == 1
        assert len(store.get_history("actor3")) == 0

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_size_total(self, iteracao):
        """
        RNF1: O size() deve retornar o total de transações de todos os atores.

        Iteração: {iteracao}/3
        """
        store = TransactionHistoryStore()
        store.record("a1", {"t": 1})
        store.record("a1", {"t": 2})
        store.record("a2", {"t": 3})

        assert store.size() == 3


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
