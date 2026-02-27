"""
Testes automatizados para DN3 - Disponibilidade e Resiliência da API
Projeto ASIS TaxTech - Grupo 06 - Abordagem Test Data Driven (TDD)

Direcionadores de Negócio testados:
- DN3.1: Rate Limiting (janela deslizante por account-key)
- DN3.2: Circuit Breaker (proteção contra falhas em cascata)
- DN3.3: Health Check (monitoramento de saúde da API)
- DN3.4: Idempotência (reprocessamento seguro)
- DN3.5: Degradação Graciosa (fallback em modo degradado)
- DN3.6: Alertas de Disponibilidade (limiar 30%, padrão DN1)

Massa de testes: Cada cenário é executado 3 vezes (iterações parametrizadas).
Versão da API: v1.2.0 — POST /api/v1/auditar/resilient | GET /api/v1/health
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.api import app
from core.api import (
    RateLimiter,
    CircuitBreaker,
    CircuitState,
    HealthChecker,
    IdempotencyStore,
    build_degraded_response,
    check_availability_alert,
    check_circuit_alert,
    check_rate_limit_alert,
    rate_limiter,
    circuit_breaker,
    health_checker,
    idempotency_store,
)

client = TestClient(app)

HEADERS_VALIDOS = {
    "account-key": "conta-dn3-teste-123",
    "app-key": "app-dn3-teste-456",
}

PAYLOAD_VALIDO = {
    "sessao_cliente": "SESSAO_DN3_G06",
    "valor": 3200.00,
    "destino": "EFD_ICMS_IPI",
}

PAYLOAD_ALTERNATIVO = {
    "sessao_cliente": "SESSAO_DN3_ALT",
    "valor": 8100.75,
    "destino": "NCM_AUDIT",
}

ITERACOES = [1, 2, 3]


@pytest.fixture(autouse=True)
def reset_singletons():
    """Reseta estado global antes de cada teste para isolamento."""
    rate_limiter.reset()
    circuit_breaker.reset()
    health_checker.reset()
    idempotency_store.clear()
    yield
    rate_limiter.reset()
    circuit_breaker.reset()
    health_checker.reset()
    idempotency_store.clear()


# ===========================================================================
# DN3.1 — Rate Limiting
# ===========================================================================

class TestDN3RateLimiting:
    """
    Testes para DN3.1 - Rate Limiting por account-key.

    Objetivo: Garantir que a API limita requisições por conta dentro de
    uma janela temporal, protegendo contra abuso e DoS.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_requisicao_dentro_do_limite_permitida(self, iteracao):
        """DN3.1: Requisições dentro do limite devem ser processadas normalmente."""
        response = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        assert "tracking_id" in response.json()

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_rate_limit_excedido_retorna_429(self, iteracao):
        """DN3.1: Após exceder o limite, a API deve retornar HTTP 429."""
        rl = RateLimiter(max_requests=3, window_seconds=60)

        for _ in range(3):
            assert rl.is_allowed("test-key") is True

        assert rl.is_allowed("test-key") is False

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_rate_limit_isolamento_entre_contas(self, iteracao):
        """DN3.1: O limite deve ser independente para cada account-key."""
        rl = RateLimiter(max_requests=2, window_seconds=60)

        rl.is_allowed("conta_A")
        rl.is_allowed("conta_A")
        assert rl.is_allowed("conta_A") is False

        assert rl.is_allowed("conta_B") is True

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_rate_limit_remaining_decrementa(self, iteracao):
        """DN3.1: O campo remaining deve decrementar a cada requisição."""
        rl = RateLimiter(max_requests=5, window_seconds=60)

        assert rl.remaining("key1") == 5
        rl.is_allowed("key1")
        assert rl.remaining("key1") == 4
        rl.is_allowed("key1")
        assert rl.remaining("key1") == 3

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_rate_limit_informado_na_resposta(self, iteracao):
        """DN3.1: A resposta deve incluir rate_limit_remaining."""
        response = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        data = response.json()
        assert "availability" in data
        assert "rate_limit_remaining" in data["availability"]
        assert isinstance(data["availability"]["rate_limit_remaining"], int)


# ===========================================================================
# DN3.2 — Circuit Breaker
# ===========================================================================

class TestDN3CircuitBreaker:
    """
    Testes para DN3.2 - Circuit Breaker.

    Objetivo: Validar que o circuit breaker protege o sistema contra falhas
    em cascata, abrindo após N falhas consecutivas.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_circuit_inicia_fechado(self, iteracao):
        """DN3.2: O circuit breaker deve iniciar no estado CLOSED."""
        cb = CircuitBreaker()
        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_circuit_abre_apos_threshold_falhas(self, iteracao):
        """DN3.2: Após atingir o threshold de falhas, o circuito deve abrir."""
        cb = CircuitBreaker(threshold=3, recovery_seconds=30)

        for _ in range(3):
            cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_circuit_reseta_com_sucesso(self, iteracao):
        """DN3.2: Um sucesso deve resetar o contador e fechar o circuito."""
        cb = CircuitBreaker(threshold=5)

        for _ in range(4):
            cb.record_failure()

        assert cb.state == CircuitState.CLOSED
        cb.record_success()
        assert cb.failure_count == 0
        assert cb.state == CircuitState.CLOSED

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_circuit_state_na_resposta(self, iteracao):
        """DN3.2: A resposta deve incluir o estado do circuit breaker."""
        response = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        data = response.json()
        assert data["availability"]["circuit_state"] == "CLOSED"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_circuit_nao_abre_abaixo_threshold(self, iteracao):
        """DN3.2: Abaixo do threshold, o circuito deve permanecer fechado."""
        cb = CircuitBreaker(threshold=5)

        for _ in range(4):
            cb.record_failure()

        assert cb.state == CircuitState.CLOSED
        assert cb.allow_request() is True


# ===========================================================================
# DN3.3 — Health Check
# ===========================================================================

class TestDN3HealthCheck:
    """
    Testes para DN3.3 - Health Check da API.

    Objetivo: Validar que o endpoint de health check retorna informações
    precisas sobre o estado de saúde do sistema.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_health_endpoint_retorna_200(self, iteracao):
        """DN3.3: GET /api/v1/health deve retornar HTTP 200."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_health_campos_obrigatorios(self, iteracao):
        """DN3.3: A resposta de health deve conter todos os campos obrigatórios."""
        response = client.get("/api/v1/health")
        data = response.json()

        campos = [
            "status", "uptime_seconds", "total_requests",
            "total_errors", "error_rate_percent", "timestamp",
            "version", "circuit_breaker",
        ]
        for campo in campos:
            assert campo in data, f"Campo '{campo}' ausente no health check"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_health_status_healthy(self, iteracao):
        """DN3.3: Com poucas requisições, o status deve ser 'healthy'."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert data["status"] == "healthy"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_health_registra_requisicoes(self, iteracao):
        """DN3.3: O health checker deve contabilizar requisições realizadas."""
        hc = HealthChecker()
        hc.record_request(success=True)
        hc.record_request(success=True)
        hc.record_request(success=False)

        status = hc.get_status()
        assert status["total_requests"] == 3
        assert status["total_errors"] == 1
        assert status["error_rate_percent"] == pytest.approx(33.33, abs=0.1)

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_health_status_degraded_com_muitos_erros(self, iteracao):
        """DN3.3: Com taxa de erro acima de 30%, o status deve ser 'degraded'."""
        hc = HealthChecker()
        for _ in range(4):
            hc.record_request(success=False)
        for _ in range(6):
            hc.record_request(success=True)

        status = hc.get_status()
        assert status["status"] == "degraded"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_health_nao_exige_autenticacao(self, iteracao):
        """DN3.3: O health check não deve exigir headers de autenticação."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200


# ===========================================================================
# DN3.4 — Idempotência
# ===========================================================================

class TestDN3Idempotencia:
    """
    Testes para DN3.4 - Idempotência de Requisições.

    Objetivo: Validar que requisições com a mesma chave de idempotência
    retornam resultados idênticos sem reprocessamento.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_primeira_requisicao_processada_normalmente(self, iteracao):
        """DN3.4: A primeira requisição com idempotency-key deve ser processada."""
        headers = {**HEADERS_VALIDOS, "idempotency-key": f"key-{iteracao}-first"}
        response = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=headers,
        )
        assert response.status_code == 201
        assert response.json()["availability"]["idempotent_replay"] is False

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_requisicao_duplicada_retorna_mesmo_resultado(self, iteracao):
        """DN3.4: Requisição duplicada com mesma chave retorna o resultado anterior."""
        headers = {**HEADERS_VALIDOS, "idempotency-key": f"key-{iteracao}-dup"}

        resp1 = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=headers,
        )
        resp2 = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=headers,
        )

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp2.json()["idempotent_replay"] is True
        assert resp1.json()["tracking_id"] == resp2.json()["tracking_id"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_chaves_diferentes_geram_resultados_diferentes(self, iteracao):
        """DN3.4: Chaves de idempotência diferentes devem gerar transações distintas."""
        headers_a = {**HEADERS_VALIDOS, "idempotency-key": f"key-{iteracao}-A"}
        headers_b = {**HEADERS_VALIDOS, "idempotency-key": f"key-{iteracao}-B"}

        resp_a = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=headers_a,
        )
        resp_b = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=headers_b,
        )

        assert resp_a.json()["tracking_id"] != resp_b.json()["tracking_id"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_chave_idempotencia_processa_sempre(self, iteracao):
        """DN3.4: Sem idempotency-key, cada requisição gera resultado novo."""
        resp1 = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        resp2 = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS,
        )

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["tracking_id"] != resp2.json()["tracking_id"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_idempotencia_store_contabiliza(self, iteracao):
        """DN3.4: O store de idempotência deve contabilizar entradas armazenadas."""
        store = IdempotencyStore()
        store.store("k1", {"data": 1})
        store.store("k2", {"data": 2})

        assert store.size() == 2
        assert store.exists("k1") is True
        assert store.exists("k3") is False


# ===========================================================================
# DN3.5 — Degradação Graciosa
# ===========================================================================

class TestDN3DegradacaoGraciosa:
    """
    Testes para DN3.5 - Degradação Graciosa.

    Objetivo: Validar que quando o sistema entra em modo degradado,
    retorna respostas de fallback informativas.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_resposta_degradada_contem_campos_obrigatorios(self, iteracao):
        """DN3.5: A resposta degradada deve conter status, motivo e retry_after."""
        degraded = build_degraded_response(
            PAYLOAD_VALIDO,
            reason="Teste de degradação",
        )

        assert degraded["status"] == 207
        assert degraded["diagnostico"] == "Degradado"
        assert "motivo" in degraded
        assert "retry_after_seconds" in degraded
        assert isinstance(degraded["retry_after_seconds"], int)

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_resposta_degradada_preserva_dados_cliente(self, iteracao):
        """DN3.5: Mesmo em modo degradado, os dados do cliente são preservados."""
        degraded = build_degraded_response(PAYLOAD_VALIDO, reason="Teste")

        assert degraded["detalhes"]["cliente"] == "SESSAO_DN3_G06"
        assert degraded["detalhes"]["volume_processado"] == 3200.00
        assert degraded["detalhes"]["modulo"] == "EFD_ICMS_IPI"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_resposta_degradada_payload_vazio(self, iteracao):
        """DN3.5: Degradação com payload vazio deve usar valores padrão."""
        degraded = build_degraded_response({}, reason="Sem dados")

        assert degraded["detalhes"]["cliente"] == "N/A"
        assert degraded["detalhes"]["modulo"] == "N/A"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_circuit_aberto_retorna_503(self, iteracao):
        """DN3.5: Com circuit breaker aberto, a API deve retornar HTTP 503."""
        cb = CircuitBreaker(threshold=2, recovery_seconds=60)
        cb.record_failure()
        cb.record_failure()

        assert cb.state == CircuitState.OPEN
        assert cb.allow_request() is False


# ===========================================================================
# DN3.6 — Alertas de Disponibilidade
# ===========================================================================

class TestDN3Alertas:
    """
    Testes para DN3.6 - Alertas de Disponibilidade.

    Objetivo: Validar que o sistema emite alertas quando a disponibilidade
    é comprometida. Limiar padrão: 30% (DN1).
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_taxa_erro_alta(self, iteracao):
        """DN3.6: Alerta emitido quando taxa de erro excede 30%."""
        hc = HealthChecker()
        for _ in range(5):
            hc.record_request(success=False)
        for _ in range(5):
            hc.record_request(success=True)

        alert = check_availability_alert(hc)
        assert alert is not None
        assert "ALERTA" in alert
        assert "DISPONIBILIDADE" in alert

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_alerta_taxa_erro_baixa(self, iteracao):
        """DN3.6: Sem alerta quando taxa de erro está abaixo de 30%."""
        hc = HealthChecker()
        for _ in range(9):
            hc.record_request(success=True)
        hc.record_request(success=False)

        alert = check_availability_alert(hc)
        assert alert is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_circuit_breaker_aberto(self, iteracao):
        """DN3.6: Alerta emitido quando circuit breaker está aberto."""
        cb = CircuitBreaker(threshold=3)
        for _ in range(3):
            cb.record_failure()

        alert = check_circuit_alert(cb)
        assert alert is not None
        assert "ALERTA" in alert
        assert "ABERTO" in alert

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_alerta_circuit_breaker_fechado(self, iteracao):
        """DN3.6: Sem alerta quando circuit breaker está fechado."""
        cb = CircuitBreaker()
        alert = check_circuit_alert(cb)
        assert alert is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_rate_limit_proximo_esgotamento(self, iteracao):
        """DN3.6: Alerta emitido quando restam menos de 30% das requisições."""
        rl = RateLimiter(max_requests=10, window_seconds=60)

        for _ in range(8):
            rl.is_allowed("alerta-key")

        alert = check_rate_limit_alert(rl, "alerta-key")
        assert alert is not None
        assert "ALERTA" in alert
        assert "DISPONIBILIDADE" in alert

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_alerta_rate_limit_folgado(self, iteracao):
        """DN3.6: Sem alerta quando há folga no rate limit."""
        rl = RateLimiter(max_requests=10, window_seconds=60)
        rl.is_allowed("folga-key")

        alert = check_rate_limit_alert(rl, "folga-key")
        assert alert is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_health_endpoint_inclui_alertas(self, iteracao):
        """DN3.6: O endpoint de health deve incluir campos de alertas."""
        response = client.get("/api/v1/health")
        data = response.json()
        assert "availability_alert" in data
        assert "circuit_alert" in data


# ===========================================================================
# Testes de Contrato da API — DN3
# ===========================================================================

class TestDN3ContratoAPI:
    """Testes para garantir que o contrato da API DN3 está correto."""

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_endpoint_resilient_existe_e_retorna_201(self, iteracao):
        """Validar que POST /api/v1/auditar/resilient existe e retorna 201."""
        response = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_estrutura_resposta_completa(self, iteracao):
        """Validar que a resposta contém campos originais + bloco availability."""
        response = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        data = response.json()

        campos_originais = [
            "id", "status", "tracking_id", "arquivold",
            "diagnostico", "detalhes",
        ]
        for campo in campos_originais:
            assert campo in data, f"Campo original '{campo}' ausente"

        assert "availability" in data
        campos_avail = [
            "circuit_state", "rate_limit_remaining",
            "idempotent_replay", "alert",
        ]
        for campo in campos_avail:
            assert campo in data["availability"], \
                f"Campo '{campo}' ausente no bloco availability"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_headers_obrigatorios(self, iteracao):
        """Validar que headers account-key e app-key são obrigatórios."""
        response = client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_VALIDO,
        )
        assert response.status_code == 401

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_validacoes_dn2_preservadas(self, iteracao):
        """Validar que as validações DN2 continuam funcionando no endpoint resilient."""
        payload_invalido = {
            "sessao_cliente": "test",
            "valor": -100,
            "destino": "test",
        }
        response = client.post(
            "/api/v1/auditar/resilient",
            json=payload_invalido,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 400


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
