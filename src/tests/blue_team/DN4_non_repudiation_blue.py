"""
Testes automatizados para DN4 - Não-Repúdio de Transações de Auditoria Fiscal
Projeto ASIS TaxTech - Grupo 06 - Abordagem Test Data Driven (TDD)

Este módulo implementa a aferição das regras de negócio do DN4 (Não-Repúdio),
validando que todas as transações possuem mecanismos criptográficos que impedem
a negação da sua realização por qualquer das partes.

Direcionadores de Negócio testados:
- DN4.1: Assinatura Digital (HMAC-SHA256)
- DN4.2: Carimbo Temporal Imutável (ISO 8601)
- DN4.3: Cadeia de Autenticação (hash do ator)
- DN4.4: Recibo Digital Completo
- DN4.5: Integridade do Log de Auditoria (hash chain)
- DN4.6: Alertas de Violação de Não-Repúdio

Massa de testes: Cada cenário é executado 3 vezes (iterações parametrizadas)
para garantir consistência e reprodutibilidade dos resultados.

Versão da API: v1.1.0 — POST /api/v1/auditar/nr
"""

import pytest
import json
import hashlib
import hmac
from datetime import datetime, timezone, timedelta
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Adicionar o caminho ao src para importar os módulos
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.api import app
from core.api import (
    sign_transaction,
    verify_signature,
    generate_timestamp,
    hash_actor,
    hash_payload,
    build_receipt,
    AuditLog,
    audit_log,
    check_alert,
    check_chain_alert,
    NR_SECRET_KEY,
)

# Cliente de teste para a API
client = TestClient(app)

# Headers obrigatórios para todas as requisições
HEADERS_VALIDOS = {
    "account-key": "conta-nr-teste-123",
    "app-key": "app-nr-teste-456"
}

# Payload padrão válido para testes de não-repúdio
PAYLOAD_VALIDO = {
    "sessao_cliente": "SESSAO_NR_G06",
    "valor": 2500.00,
    "destino": "EFD_ICMS_IPI"
}

# Payload alternativo para testes de variação
PAYLOAD_ALTERNATIVO = {
    "sessao_cliente": "SESSAO_NR_ALT",
    "valor": 7500.50,
    "destino": "NCM_AUDIT"
}

# Iterações parametrizadas: cada teste é executado 3 vezes (TDD)
ITERACOES = [1, 2, 3]


# ===========================================================================
# Fixture: Limpar o audit_log antes de cada teste que depende do log
# ===========================================================================

@pytest.fixture(autouse=True)
def setup_teardown():
    """Isola as configurações globais antes de cada cenário de teste."""
    from core.api import clear_replay_cache
    audit_log.clear()
    clear_replay_cache()
    yield
    audit_log.clear()
    clear_replay_cache()


# ===========================================================================
# DN4.1 — Assinatura Digital (HMAC-SHA256)
# ===========================================================================

class TestDN4AssinaturaDigital:
    """
    Testes para DN4.1 - Assinatura Digital (HMAC-SHA256)

    Objetivo: Validar que 100% das transações válidas retornam uma assinatura
    HMAC-SHA256 computada sobre o payload + timestamp, garantindo não-repúdio
    de conteúdo.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_assinatura_presente_em_transacao_valida(self, iteracao):
        """
        DN4.1: Toda transação válida deve conter campo 'signature' no bloco
        de não-repúdio.

        Iteração: {iteracao}/3
        Resultado esperado: HTTP 201, campo 'signature' presente e não vazio.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        assert response.status_code == 201
        data = response.json()
        assert "non_repudiation" in data
        assert "signature" in data["non_repudiation"]
        assert isinstance(data["non_repudiation"]["signature"], str)
        assert len(data["non_repudiation"]["signature"]) == 64  # SHA-256 hex

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_assinatura_verificavel(self, iteracao):
        """
        DN4.1: A assinatura retornada deve ser verificável com a mesma chave
        secreta, payload e timestamp.

        Iteração: {iteracao}/3
        Resultado esperado: verify_signature retorna True.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        nr = data["non_repudiation"]

        # Verificar que a assinatura é válida
        assert verify_signature(
            PAYLOAD_VALIDO,
            nr["timestamp"],
            nr["signature"]
        ) is True

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_assinatura_diferente_para_payloads_diferentes(self, iteracao):
        """
        DN4.1: Payloads diferentes devem gerar assinaturas diferentes,
        garantindo unicidade criptográfica.

        Iteração: {iteracao}/3
        Resultado esperado: Assinaturas distintas para payloads distintos.
        """
        resp1 = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )
        resp2 = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_ALTERNATIVO,
            headers=HEADERS_VALIDOS
        )

        sig1 = resp1.json()["non_repudiation"]["signature"]
        sig2 = resp2.json()["non_repudiation"]["signature"]

        assert sig1 != sig2

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_assinatura_em_payload_invalido(self, iteracao):
        """
        DN4.1: Payloads inválidos (HTTP 400) NÃO devem conter assinatura,
        pois a transação não foi processada.

        Iteração: {iteracao}/3
        Resultado esperado: HTTP 400, sem bloco 'non_repudiation'.
        """
        payload_invalido = {
            "sessao_cliente": "SESSAO_NR_G06",
            "valor": -100,  # Valor inválido
            "destino": "EFD_ICMS_IPI"
        }

        response = client.post(
            "/api/v1/auditar/nr",
            json=payload_invalido,
            headers=HEADERS_VALIDOS
        )

        assert response.status_code == 400
        assert "non_repudiation" not in response.json()


# ===========================================================================
# DN4.2 — Carimbo Temporal Imutável
# ===========================================================================

class TestDN4CarimboTemporal:
    """
    Testes para DN4.2 - Carimbo Temporal Imutável (ISO 8601)

    Objetivo: Validar que 100% das transações incluem um timestamp ISO 8601
    gerado pelo servidor (server-side), com tolerância ≤ 2 segundos.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_timestamp_formato_iso8601(self, iteracao):
        """
        DN4.2: O timestamp retornado deve estar em formato ISO 8601 válido.

        Iteração: {iteracao}/3
        Resultado esperado: Parsing do timestamp sem exceção.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        timestamp_str = data["non_repudiation"]["timestamp"]

        # Deve parsear sem erro como ISO 8601
        parsed = datetime.fromisoformat(timestamp_str)
        assert parsed.tzinfo is not None  # Deve ter timezone

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_timestamp_tolerancia_2_segundos(self, iteracao):
        """
        DN4.2: O timestamp do servidor deve estar dentro de 2 segundos
        do horário atual (UTC), garantindo sincronização temporal.

        Iteração: {iteracao}/3
        Resultado esperado: Diferença ≤ 2 segundos.
        """
        antes = datetime.now(timezone.utc)

        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        depois = datetime.now(timezone.utc)
        data = response.json()
        timestamp_str = data["non_repudiation"]["timestamp"]
        ts_server = datetime.fromisoformat(timestamp_str)

        # O timestamp do servidor deve estar entre 'antes' e 'depois + 2s'
        assert ts_server >= antes - timedelta(seconds=2)
        assert ts_server <= depois + timedelta(seconds=2)

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_timestamp_server_side_nao_cliente(self, iteracao):
        """
        DN4.2: O timestamp deve ser gerado pelo servidor, não pelo cliente.
        Mesmo enviando um timestamp no payload, o servidor deve usar o próprio.

        Iteração: {iteracao}/3
        Resultado esperado: Timestamp no response diferente do enviado no payload.
        """
        payload_com_ts = {
            **PAYLOAD_VALIDO,
            "timestamp_cliente": "2020-01-01T00:00:00+00:00"
        }

        response = client.post(
            "/api/v1/auditar/nr",
            json=payload_com_ts,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        ts_server = data["non_repudiation"]["timestamp"]

        # O timestamp do servidor NÃO deve ser o mesmo enviado pelo cliente
        assert ts_server != "2020-01-01T00:00:00+00:00"

        # Deve ser um timestamp recente (do ano corrente)
        parsed = datetime.fromisoformat(ts_server)
        assert parsed.year >= 2026


# ===========================================================================
# DN4.3 — Cadeia de Autenticação
# ===========================================================================

class TestDN4CadeiaAutenticacao:
    """
    Testes para DN4.3 - Cadeia de Autenticação (hash do ator)

    Objetivo: Validar que toda transação registra o ator autenticado via
    hash SHA-256 da account-key, vinculando a identidade à transação.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_actor_presente_na_resposta(self, iteracao):
        """
        DN4.3: O campo 'actor' deve estar presente no bloco de não-repúdio.

        Iteração: {iteracao}/3
        Resultado esperado: Campo 'actor' presente e com 64 caracteres hex.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        actor = data["non_repudiation"]["actor"]

        assert isinstance(actor, str)
        assert len(actor) == 64  # SHA-256 hex

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_actor_derivado_da_account_key(self, iteracao):
        """
        DN4.3: O 'actor' deve ser o hash SHA-256 da account-key enviada
        nos headers, permitindo rastrear a identidade.

        Iteração: {iteracao}/3
        Resultado esperado: actor == SHA-256(account-key).
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        actor_retornado = data["non_repudiation"]["actor"]

        # Calcular o hash esperado
        expected_actor = hashlib.sha256(
            HEADERS_VALIDOS["account-key"].encode("utf-8")
        ).hexdigest()

        assert actor_retornado == expected_actor

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_actors_diferentes_para_keys_diferentes(self, iteracao):
        """
        DN4.3: Account-keys diferentes devem gerar actors diferentes,
        garantindo distinção de identidades.

        Iteração: {iteracao}/3
        Resultado esperado: Actors distintos para chaves distintas.
        """
        headers_alt = {
            "account-key": "outra-conta-xyz-789",
            "app-key": "app-nr-teste-456"
        }

        resp1 = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )
        resp2 = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=headers_alt
        )

        actor1 = resp1.json()["non_repudiation"]["actor"]
        actor2 = resp2.json()["non_repudiation"]["actor"]

        assert actor1 != actor2


# ===========================================================================
# DN4.4 — Recibo Digital Completo
# ===========================================================================

class TestDN4ReciboDigital:
    """
    Testes para DN4.4 - Recibo Digital de Não-Repúdio

    Objetivo: Validar que transações válidas retornam um recibo digital
    completo contendo todas as evidências criptográficas necessárias.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_recibo_contem_todos_os_campos(self, iteracao):
        """
        DN4.4: O recibo deve conter os 5 campos obrigatórios:
        signature, timestamp, actor, tracking_id, payload_hash.

        Iteração: {iteracao}/3
        Resultado esperado: Todos os campos presentes e não vazios.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        receipt = data["non_repudiation"]["receipt"]

        campos_obrigatorios = [
            "signature", "timestamp", "actor", "tracking_id", "payload_hash"
        ]
        for campo in campos_obrigatorios:
            assert campo in receipt, f"Campo obrigatório '{campo}' ausente no recibo"
            assert receipt[campo], f"Campo '{campo}' está vazio no recibo"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_recibo_tracking_id_corresponde(self, iteracao):
        """
        DN4.4: O tracking_id no recibo deve ser idêntico ao tracking_id
        da resposta principal, garantindo vinculação.

        Iteração: {iteracao}/3
        Resultado esperado: tracking_id no recibo == tracking_id na raiz.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        assert data["non_repudiation"]["receipt"]["tracking_id"] == data["tracking_id"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_recibo_payload_hash_corresponde(self, iteracao):
        """
        DN4.4: O payload_hash no recibo deve ser o SHA-256 do payload
        enviado, provando o conteúdo exato da transação.

        Iteração: {iteracao}/3
        Resultado esperado: payload_hash == SHA-256(payload serializado).
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        payload_hash_retornado = data["non_repudiation"]["receipt"]["payload_hash"]

        # Calcular hash esperado
        expected_hash = hash_payload(PAYLOAD_VALIDO)

        assert payload_hash_retornado == expected_hash

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_recibo_em_payload_invalido(self, iteracao):
        """
        DN4.4: Payloads inválidos NÃO devem gerar recibo digital.

        Iteração: {iteracao}/3
        Resultado esperado: HTTP 400, sem bloco 'non_repudiation'.
        """
        payload_invalido = {"valor": 100}  # Campos obrigatórios ausentes

        response = client.post(
            "/api/v1/auditar/nr",
            json=payload_invalido,
            headers=HEADERS_VALIDOS
        )

        assert response.status_code == 400
        assert "non_repudiation" not in response.json()


# ===========================================================================
# DN4.5 — Integridade do Log de Auditoria (Hash Chain)
# ===========================================================================

class TestDN4LogAuditoria:
    """
    Testes para DN4.5 - Integridade do Log de Auditoria

    Objetivo: Validar que o sistema mantém um log de auditoria com cadeia
    de hash (hash chain), onde cada entrada referencia o hash da anterior.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_entrada_adicionada_ao_log(self, iteracao):
        """
        DN4.5: Cada transação válida deve gerar uma entrada no log de auditoria.

        Iteração: {iteracao}/3
        Resultado esperado: log_position presente e incrementando.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        assert "log_position" in data["non_repudiation"]
        assert isinstance(data["non_repudiation"]["log_position"], int)
        assert data["non_repudiation"]["log_position"] >= 0

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_cadeia_hash_valida_apos_multiplas_transacoes(self, iteracao):
        """
        DN4.5: Após múltiplas transações, a cadeia de hash do log deve
        permanecer íntegra e verificável.

        Iteração: {iteracao}/3
        Resultado esperado: verify_chain() retorna True após 3 transações.
        """
        # Inserir 3 transações
        for i in range(3):
            payload = {**PAYLOAD_VALIDO, "teste_idx": i}
            client.post(
                "/api/v1/auditar/nr",
                json=payload,
                headers=HEADERS_VALIDOS
            )

        # Verificar integridade da cadeia
        assert audit_log.verify_chain() is True
        assert audit_log.size() == 3

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_prev_hash_encadeia_entradas(self, iteracao):
        """
        DN4.5: O prev_hash de cada entrada deve corresponder ao entry_hash
        da entrada anterior, formando a cadeia.

        Iteração: {iteracao}/3
        Resultado esperado: entry[n].prev_hash == entry[n-1].entry_hash.
        """
        # Inserir 3 transações
        for i in range(3):
            payload = {**PAYLOAD_VALIDO, "teste_idx": i}
            client.post(
                "/api/v1/auditar/nr",
                json=payload,
                headers=HEADERS_VALIDOS
            )

        log = audit_log.get_log()
        assert len(log) == 3

        # Primeira entrada deve ter prev_hash == "GENESIS"
        assert log[0]["prev_hash"] == "GENESIS"

        # Entradas subsequentes devem referenciar a anterior
        for i in range(1, len(log)):
            assert log[i]["prev_hash"] == log[i - 1]["entry_hash"]

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_cadeia_detecta_adulteracao(self, iteracao):
        """
        DN4.5: Se uma entrada do log for adulterada, verify_chain() deve
        detectar e retornar False.

        Iteração: {iteracao}/3
        Resultado esperado: verify_chain() retorna False após adulteração.
        """
        # Criar log isolado para teste de adulteração
        log_teste = AuditLog()

        receipt1 = build_receipt("sig1", "ts1", "actor1", "tid1", {"test": 1})
        receipt2 = build_receipt("sig2", "ts2", "actor2", "tid2", {"test": 2})

        log_teste.append(receipt1)
        log_teste.append(receipt2)

        assert log_teste.verify_chain() is True

        # Adulterar uma entrada
        log_teste._log[0]["receipt"]["signature"] = "ADULTERADO"
        # Recalcular entry_hash NÃO é feito, então a cadeia deve quebrar
        # Na verdade, a adulteração do receipt não muda o entry_hash armazenado,
        # mas a verificação recalcula e detecta a inconsistência
        # Vamos adulterar o entry_hash diretamente para quebrar a cadeia
        log_teste._log[0]["entry_hash"] = "hash_falso_adulterado"

        assert log_teste.verify_chain() is False


# ===========================================================================
# DN4.6 — Alertas de Violação de Não-Repúdio
# ===========================================================================

class TestDN4Alertas:
    """
    Testes para DN4.6 - Alertas de Violação de Não-Repúdio

    Objetivo: Validar que o sistema emite alertas quando mecanismos de
    não-repúdio apresentam anomalias ou campos ausentes.
    O limiar de alerta segue o padrão DN1 (30% acima do normal).
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_recibo_ausente(self, iteracao):
        """
        DN4.6: O sistema deve emitir alerta quando o recibo digital é None.

        Iteração: {iteracao}/3
        Resultado esperado: Mensagem de alerta contendo 'ALERTA'.
        """
        alert = check_alert(None)

        assert alert is not None
        assert "ALERTA" in alert
        assert "ausente" in alert.lower()

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_campos_faltando_no_recibo(self, iteracao):
        """
        DN4.6: O sistema deve emitir alerta quando campos obrigatórios
        estão ausentes no recibo.

        Iteração: {iteracao}/3
        Resultado esperado: Mensagem de alerta listando campos ausentes.
        """
        recibo_incompleto = {
            "signature": "abc123",
            "timestamp": "2026-01-01T00:00:00+00:00",
            # "actor": ausente
            # "tracking_id": ausente
            "payload_hash": "def456"
        }

        alert = check_alert(recibo_incompleto)

        assert alert is not None
        assert "ALERTA" in alert
        assert "actor" in alert
        assert "tracking_id" in alert

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_alerta_em_transacao_valida(self, iteracao):
        """
        DN4.6: Transações válidas com todos os campos de não-repúdio
        presentes NÃO devem gerar alertas.

        Iteração: {iteracao}/3
        Resultado esperado: alert == None no response.
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()
        assert data["non_repudiation"]["alert"] is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_alerta_cadeia_quebrada(self, iteracao):
        """
        DN4.6: O sistema deve emitir alerta quando a cadeia de hash
        do log está comprometida.

        Iteração: {iteracao}/3
        Resultado esperado: Mensagem de alerta sobre cadeia comprometida.
        """
        log_teste = AuditLog()

        receipt = build_receipt("sig", "ts", "actor", "tid", {"t": 1})
        log_teste.append(receipt)

        # Adulterar a cadeia
        log_teste._log[0]["entry_hash"] = "ADULTERADO"

        alert = check_chain_alert(log_teste)

        assert alert is not None
        assert "ALERTA" in alert
        assert "comprometida" in alert.lower()

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_sem_alerta_cadeia_integra(self, iteracao):
        """
        DN4.6: Quando a cadeia de hash está íntegra, nenhum alerta
        de cadeia deve ser emitido.

        Iteração: {iteracao}/3
        Resultado esperado: chain_alert == None.
        """
        log_teste = AuditLog()

        receipt1 = build_receipt("sig1", "ts1", "actor1", "tid1", {"t": 1})
        receipt2 = build_receipt("sig2", "ts2", "actor2", "tid2", {"t": 2})
        log_teste.append(receipt1)
        log_teste.append(receipt2)

        alert = check_chain_alert(log_teste)
        assert alert is None


# ===========================================================================
# Testes de Contrato da API — DN4
# ===========================================================================

class TestDN4ContratoAPI:
    """
    Testes de contrato para garantir que o endpoint /api/v1/auditar/nr
    mantém a estrutura esperada e é compatível com o endpoint original.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_endpoint_nr_existe_e_retorna_201(self, iteracao):
        """
        Validar que POST /api/v1/auditar/nr existe e retorna HTTP 201
        para payload válido.

        Iteração: {iteracao}/3
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        assert response.status_code == 201

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_estrutura_resposta_completa_com_nr(self, iteracao):
        """
        Validar que a resposta contém tanto os campos originais (DN2)
        quanto o bloco de não-repúdio (DN4).

        Iteração: {iteracao}/3
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO,
            headers=HEADERS_VALIDOS
        )

        data = response.json()

        # Campos originais (contrato DN2 preservado)
        campos_originais = [
            "id", "status", "tracking_id", "arquivold", "diagnostico", "detalhes"
        ]
        for campo in campos_originais:
            assert campo in data, f"Campo original '{campo}' ausente"

        # Bloco de não-repúdio (DN4)
        assert "non_repudiation" in data
        campos_nr = [
            "signature", "timestamp", "actor", "receipt",
            "log_position", "log_entry_hash", "alert", "chain_alert"
        ]
        for campo in campos_nr:
            assert campo in data["non_repudiation"], \
                f"Campo NR '{campo}' ausente no bloco non_repudiation"

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_headers_obrigatorios_nr(self, iteracao):
        """
        Validar que headers account-key e app-key são obrigatórios
        no endpoint de não-repúdio.

        Iteração: {iteracao}/3
        """
        response = client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_VALIDO
            # Sem headers
        )

        assert response.status_code == 422  # FastAPI validation error


# ===========================================================================
# Testes do Endpoint de Consulta do Log de Auditoria
# ===========================================================================

class TestDN4ConsultaLog:
    """
    Testes para os endpoints de consulta do log de auditoria (GET).
    Verificam que o log pode ser auditado externamente.
    """

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_consulta_log_completo(self, iteracao):
        """
        DN4.5: O endpoint GET /api/v1/audit-log deve retornar o log
        completo com status de integridade.

        Iteração: {iteracao}/3
        """
        # Criar algumas entradas
        client.post("/api/v1/auditar/nr", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)
        client.post("/api/v1/auditar/nr", json=PAYLOAD_ALTERNATIVO, headers=HEADERS_VALIDOS)

        response = client.get("/api/v1/audit-log", headers=HEADERS_VALIDOS)

        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert data["total_entries"] == 2
        assert data["chain_integrity"] is True
        assert data["chain_alert"] is None

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_consulta_entrada_especifica(self, iteracao):
        """
        DN4.5: O endpoint GET /api/v1/audit-log/{position} deve retornar
        uma entrada específica do log.

        Iteração: {iteracao}/3
        """
        client.post("/api/v1/auditar/nr", json=PAYLOAD_VALIDO, headers=HEADERS_VALIDOS)

        response = client.get("/api/v1/audit-log/0", headers=HEADERS_VALIDOS)

        assert response.status_code == 200
        data = response.json()
        assert data["position"] == 0
        assert "receipt" in data
        assert "entry_hash" in data

    @pytest.mark.parametrize("iteracao", ITERACOES)
    def test_consulta_entrada_inexistente(self, iteracao):
        """
        DN4.5: Consultar posição inexistente retorna HTTP 404.

        Iteração: {iteracao}/3
        """
        response = client.get("/api/v1/audit-log/999", headers=HEADERS_VALIDOS)

        assert response.status_code == 404


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--tb=short"])
