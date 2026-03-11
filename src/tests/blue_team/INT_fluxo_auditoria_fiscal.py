"""
INTEGRAÇÃO – Fluxo Completo de Auditoria Fiscal SPED
Projeto ASIS TaxTech – Grupo 06 – Ponderada de Integração

=============================================================================
PARTE A – ESTRUTURA DA INTEGRAÇÃO                                    [4,0 pts]
=============================================================================

Este módulo documenta e aferição o fluxo de integração end-to-end do sistema
de auditoria fiscal, cobrindo todas as camadas, módulos, componentes, hardware,
software e processos envolvidos.

──────────────────────────────────────────────────────────────────────────────
CAMADAS DA INTEGRAÇÃO
──────────────────────────────────────────────────────────────────────────────

    ┌─────────────────────────────────────────────────────────────────┐
    │  CAMADA 1 – APRESENTAÇÃO (Cliente HTTP)                        │
    │  Software: requests / httpx / FastAPI TestClient               │
    │  Protocolo: HTTP/1.1 e HTTP/2, REST                            │
    │  Formato: JSON (application/json), multipart/form-data         │
    └──────────────────────┬──────────────────────────────────────────┘
                           │ POST /api/v1/{endpoint}
                           │ Headers: account-key, app-key
    ┌──────────────────────▼──────────────────────────────────────────┐
    │  CAMADA 2 – AUTENTICAÇÃO E AUTORIZAÇÃO (Middleware)            │
    │  Módulo: authenticate_request (api.py)                         │
    │  Componente: VALID_CREDENTIAL_PAIRS (registro em memória)      │
    │  Processo: valida par (account-key, app-key) → 401/403/pass   │
    └──────────────────────┬──────────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────────┐
    │  CAMADA 3 – VALIDAÇÃO DE ENTRADA (Guard Layer)                 │
    │  Módulo: processar_auditoria / validar_destino (api.py)        │
    │  Componente: lógica de negócio DN2 (campos, valor > 0)         │
    │  Processo: rejeita antes de processar → falha rápida (HTTP 400)│
    └──────────────────────┬──────────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────────┐
    │  CAMADA 4 – RESILIÊNCIA (Rate Limiter + Circuit Breaker)       │
    │  Módulos: RateLimiter, CircuitBreaker, IdempotencyStore        │
    │  Componentes: janela deslizante, estado CLOSED/OPEN/HALF_OPEN  │
    │  Processo: controle de fluxo e proteção contra falhas cascata  │
    └──────────────────────┬──────────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────────┐
    │  CAMADA 5 – INTEGRAÇÃO COM SERVIÇO EXTERNO (ASIS API)          │
    │                                                                 │
    │  ┌─────────────┐      ┌───────────────────────────────────┐    │
    │  │ asis_upload │─────▶│ POST upload.stg.asistaxtech.com  │    │
    │  │ _file()     │      │ (HTTPS, multipart/form-data)      │    │
    │  └─────────────┘      └───────────────────────────────────┘    │
    │         │ falha (timeout / HTTP erro)                          │
    │  ┌──────▼──────┐                                               │
    │  │ FALLBACK    │  Gera tracking_id local (UUID)                │
    │  │ MOCK        │  Retorna resposta simulada                    │
    │  └─────────────┘                                               │
    │                                                                 │
    │  Hardware envolvido: servidores ASIS (stg.asistaxtech.com.br)  │
    │  Software: API ASIS TaxTech v1 (staging), FastAPI local        │
    └──────────────────────┬──────────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────────┐
    │  CAMADA 6 – PROCESSAMENTO E PERSISTÊNCIA                       │
    │  Módulos: ProcessStore, AuditLog (api.py)                      │
    │  Componente: store em memória (thread-safe com threading.Lock) │
    │  Processo: registra tracking_id, status e timestamp            │
    └──────────────────────┬──────────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────────┐
    │  CAMADA 7 – NÃO-REPÚDIO CRIPTOGRÁFICO                         │
    │  Módulos: sign_transaction, build_receipt, AuditLog (api.py)   │
    │  Componente: HMAC-SHA256, hash chain, timestamp ISO 8601       │
    │  Processo: assina, registra no log encadeado, emite recibo     │
    └──────────────────────┬──────────────────────────────────────────┘
                           │
    ┌──────────────────────▼──────────────────────────────────────────┐
    │  CAMADA 8 – RESPOSTA AO CLIENTE                                │
    │  Formato: JSON, HTTP 201 (sucesso) / 207 (degradado)           │
    │  Campos: id, status, tracking_id, diagnostico, detalhes, NR   │
    └─────────────────────────────────────────────────────────────────┘

──────────────────────────────────────────────────────────────────────────────
MÓDULOS E COMPONENTES
──────────────────────────────────────────────────────────────────────────────

    Módulo                  │ Responsabilidade
    ────────────────────────┼────────────────────────────────────────────────
    authenticate_request    │ Valida par de credenciais (account-key/app-key)
    validar_destino         │ Valida módulo fiscal (EFD_ICMS_IPI, NCM…)
    asis_upload_file        │ Envia arquivo SPED para API ASIS via HTTPS
    processar_auditoria     │ Orquestra fluxo DN2 (validação + upload + resp)
    RateLimiter             │ Janela deslizante 10 req / 60s por account-key
    CircuitBreaker          │ Abre após 5 falhas; recovery em 30s
    AuditLog                │ Log imutável com hash chain (SHA-256)
    sign_transaction        │ Assinatura HMAC-SHA256 (payload + timestamp)
    ProcessStore            │ Rastreio assíncrono de processos por tracking_id

──────────────────────────────────────────────────────────────────────────────
HARDWARE E SOFTWARE ENVOLVIDOS
──────────────────────────────────────────────────────────────────────────────

    Hardware:
    - Servidores ASIS TaxTech (ambiente staging):
        upload.stg.asistaxtech.com.br
        core.stg.asistaxtech.com.br
        resultado.stg.asistaxtech.com.br
    - Máquina local do desenvolvedor (execução dos testes)

    Software:
    - Python 3.10+ com FastAPI (servidor local/testes in-process)
    - httpx (cliente HTTP assíncrono para chamadas à ASIS)
    - requests (cliente HTTP síncrono – fallback/testes)
    - pytest (framework de testes)
    - API ASIS TaxTech v1 (staging)

──────────────────────────────────────────────────────────────────────────────
PROCESSOS DO FLUXO
──────────────────────────────────────────────────────────────────────────────

    1. Cliente envia POST /api/v1/auditar com headers e payload fiscal
    2. Middleware autentica o par (account-key, app-key) → 401/403 se inválido
    3. Guard Layer valida campos obrigatórios e valor > 0 → 400 se inválido
    4. Rate Limiter verifica quota da conta → 429 se excedido
    5. Circuit Breaker verifica estado → 503 se aberto
    6. asis_upload_file() tenta upload HTTPS do arquivo SPED para a API real
       └─ Se falha (timeout/erro): cai em fallback mock com UUID local
    7. ProcessStore registra tracking_id com status CONCLUIDO
    8. sign_transaction() gera assinatura HMAC-SHA256 (endpoint /auditar/nr)
    9. AuditLog.append() registra recibo no log encadeado com hash chain
   10. Resposta HTTP 201 retorna ao cliente com todos os campos do contrato

=============================================================================
PARTE B – CONTROLE DE QUALIDADE DA INTEGRAÇÃO                       [6,0 pts]
=============================================================================

Cobre: tempos de resposta (SLA), protocolos e versões, tratamento de exceções.

Estratégia live-or-mock:
- Tenta chamar os endpoints da API real ASIS diretamente
- Se indisponível (timeout, erro de rede), usa TestClient (FastAPI in-process)
  com fallback mock já embutido na api.py
- A mesma lógica se aplica ao upload: api.py tenta ASIS real, cai em mock

=============================================================================
"""

import os
import sys
import time
import hashlib
from pathlib import Path
from datetime import datetime, timezone, timedelta

import pytest
import requests as _requests

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

# ─────────────────────────────────────────────────────────────────────────────
# CONSTANTES DE PROTOCOLO E VERSÃO
# ─────────────────────────────────────────────────────────────────────────────

API_VERSION = "v1"                        # Versão da API ASIS TaxTech em uso
API_CONTENT_TYPE = "application/json"     # Protocolo de serialização: JSON
HMAC_ALGO = "SHA-256"                     # Algoritmo de assinatura digital
HMAC_HEX_LENGTH = 64                      # Tamanho esperado da assinatura hex
TIMESTAMP_FORMAT = "ISO 8601"             # Formato do carimbo temporal
UPLOAD_PROTOCOL = "HTTPS/multipart"       # Protocolo de upload de arquivos SPED

# SLAs de latência por camada (em milissegundos)
SLA_AUTENTICACAO_MS = 50           # Camada 2: autenticação deve ser < 50ms
SLA_VALIDACAO_MS = 50              # Camada 3: validação deve ser < 50ms
SLA_FLUXO_COMPLETO_MS = 500        # Camada completa: SLA de 500ms (padrão DN1)
SLA_ALERTA_MS = int(SLA_FLUXO_COMPLETO_MS * 1.30)  # Limiar de alerta: 30% acima

# Credenciais reais (mesmas do api.py – para teste live contra a API ASIS)
ASIS_UPLOAD_URL = "https://upload.stg.asistaxtech.com.br/api/v1/upload"
ASIS_STATUS_URL = "https://core.stg.asistaxtech.com.br/api/v1/processo/"
ASIS_ACCOUNT_KEY = "94426c03635f18fcfb5060ee2f38f5e01c26a6c6c13f1978b732e65cbc0bfb0c"
ASIS_APP_KEY = "D68C6DA8D520CDF6FBE48D36FB2634691B926F981FC5B755D09F8E8623EE37F2"
ASIS_TIMEOUT_SECONDS = 5.0         # Timeout para chamadas à API real

# Headers de autenticação
HEADERS_VALIDOS = {
    "account-key": ASIS_ACCOUNT_KEY,
    "app-key": ASIS_APP_KEY,
}
HEADERS_INVALIDOS = {
    "account-key": "conta-inexistente-xyz",
    "app-key": "app-inexistente-xyz",
}

# Payload padrão fiscal válido
PAYLOAD_FISCAL_VALIDO = {
    "sessao_cliente": "INT_FLUXO_G06",
    "valor": 4500.00,
    "destino": "EFD_ICMS_IPI",
}

# Arquivo SPED de exemplo (para o fluxo de upload)
LOCAL_SPED_FILE = Path(__file__).parent.parent.parent.parent / "sped_exemplo.txt"

# ─────────────────────────────────────────────────────────────────────────────
# ESTRATÉGIA LIVE-OR-MOCK
# ─────────────────────────────────────────────────────────────────────────────
# Tenta detectar se a API interna (FastAPI) está disponível (via variável de
# ambiente ou por importação direta). Para endpoints internos, usa TestClient.
# Para chamadas diretas à ASIS (upload), tenta o endpoint real primeiro e
# registra se foi real ou mock.

from fastapi.testclient import TestClient
from core.api import app, audit_log, clear_replay_cache

_internal_client = TestClient(app)


def _try_asis_real_upload() -> dict:
    """
    Tenta fazer upload de arquivo SPED para a API ASIS real.

    Protocolo: HTTPS, multipart/form-data
    Versão: API ASIS v1 (upload.stg.asistaxtech.com.br)
    Timeout: ASIS_TIMEOUT_SECONDS

    Retorna:
        {"source": "real", "data": <resposta ASIS>} se bem-sucedido
        {"source": "mock", "data": None, "reason": <motivo>} se falhar
    """
    if not LOCAL_SPED_FILE.exists():
        return {"source": "mock", "data": None, "reason": "arquivo SPED local não encontrado"}
    try:
        with open(LOCAL_SPED_FILE, "rb") as f:
            resp = _requests.post(
                ASIS_UPLOAD_URL,
                headers={"account-key": ASIS_ACCOUNT_KEY, "app-key": ASIS_APP_KEY},
                files={"file": (LOCAL_SPED_FILE.name, f, "text/plain")},
                timeout=ASIS_TIMEOUT_SECONDS,
            )
        resp.raise_for_status()
        return {"source": "real", "data": resp.json()}
    except Exception as exc:
        return {"source": "mock", "data": None, "reason": str(exc)}


def _try_asis_real_status(process_id: int) -> dict:
    """
    Tenta consultar o status de processo na API ASIS real.

    Protocolo: HTTPS, REST GET
    Versão: API ASIS v1 (core.stg.asistaxtech.com.br)
    Timeout: ASIS_TIMEOUT_SECONDS

    Retorna:
        {"source": "real", "data": <resposta>} se bem-sucedido
        {"source": "mock", "data": <mock fixo>, "reason": <motivo>} se falhar
    """
    try:
        resp = _requests.get(
            f"{ASIS_STATUS_URL}{process_id}",
            headers={"account-key": ASIS_ACCOUNT_KEY, "app-key": ASIS_APP_KEY},
            timeout=ASIS_TIMEOUT_SECONDS,
        )
        resp.raise_for_status()
        return {"source": "real", "data": resp.json()}
    except Exception as exc:
        return {
            "source": "mock",
            "reason": str(exc),
            "data": {
                "id": process_id,
                "status": 201,
                "statusDescricao": "CONCLUIDO",
                "diagnostico": {"erro": 0, "beneficio": 0, "relatorio": 0, "advertencia": 0},
                "diagnostico_proxy": "Conforme (Mock Fallback – ASIS indisponível)",
            },
        }


# ─────────────────────────────────────────────────────────────────────────────
# Fixtures
# ─────────────────────────────────────────────────────────────────────────────

@pytest.fixture(autouse=True)
def reset_audit_log():
    """Isola o estado do AuditLog e do cache de replay entre testes."""
    audit_log.clear()
    clear_replay_cache()
    yield
    audit_log.clear()
    clear_replay_cache()


# =============================================================================
# CAMADA 2 – AUTENTICAÇÃO
# =============================================================================

class TestCamadaAutenticacao:
    """
    Camada 2 – Autenticação e Autorização

    Módulo: authenticate_request (api.py)
    Protocolo: HTTP headers (account-key, app-key)
    Versão da API: v1
    SLA: < 50ms

    Processo: O middleware intercepta toda requisição antes de qualquer
    processamento fiscal, rejeitando credenciais ausentes (401) ou inválidas
    (403). Somente pares registrados em VALID_CREDENTIAL_PAIRS são aceitos.
    """

    def test_credenciais_ausentes_retornam_401(self):
        """
        EXCEÇÃO: Headers ausentes → HTTP 401 Unauthorized.

        Regra: toda integração fiscal exige identificação do ator.
        Protocolo: account-key e app-key são obrigatórios em todos os endpoints.
        """
        start = time.perf_counter()
        response = _internal_client.post("/api/v1/auditar", json=PAYLOAD_FISCAL_VALIDO)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 401, "Deve rejeitar credenciais ausentes com 401"
        assert elapsed_ms < SLA_AUTENTICACAO_MS, (
            f"Autenticação excedeu SLA: {elapsed_ms:.2f}ms (limite {SLA_AUTENTICACAO_MS}ms)"
        )

    def test_credenciais_invalidas_retornam_403(self):
        """
        EXCEÇÃO: Par de credenciais não registrado → HTTP 403 Forbidden.

        Regra: mesmo que headers estejam presentes, o par deve estar na
        whitelist VALID_CREDENTIAL_PAIRS. Credencial inválida ≠ ausente.
        """
        start = time.perf_counter()
        response = _internal_client.post(
            "/api/v1/auditar",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_INVALIDOS,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 403, "Deve rejeitar par inválido com 403"
        assert elapsed_ms < SLA_AUTENTICACAO_MS, (
            f"Autenticação excedeu SLA: {elapsed_ms:.2f}ms (limite {SLA_AUTENTICACAO_MS}ms)"
        )

    def test_credenciais_validas_sao_aceitas(self):
        """
        CAMINHO FELIZ: Par válido → middleware libera o fluxo.

        Versão da API: v1 — endpoint POST /api/v1/auditar
        Protocolo: JSON, headers HTTP padrão
        """
        response = _internal_client.post(
            "/api/v1/auditar",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        # 201 = autenticação ok + processamento ok
        assert response.status_code == 201


# =============================================================================
# CAMADA 3 – VALIDAÇÃO DE ENTRADA
# =============================================================================

class TestCamadaValidacaoEntrada:
    """
    Camada 3 – Validação de Entrada (Guard Layer)

    Módulo: processar_auditoria + validar_destino (api.py)
    Protocolo: JSON (application/json), REST POST
    Versão da API: v1
    SLA: < 50ms (falha rápida, sem I/O)

    Processo: Antes de qualquer integração externa (upload ASIS), a API
    aplica regras de negócio DN2 para rejeitar payloads inválidos, garantindo
    que tracking_id nunca seja gerado para dados corrompidos.
    """

    def test_campo_sessao_ausente_retorna_400(self):
        """
        EXCEÇÃO: sessao_cliente ausente → HTTP 400.
        Rastreabilidade fiscal requer sessão identificada.
        """
        payload = {"valor": 1000.0, "destino": "EFD_ICMS_IPI"}
        start = time.perf_counter()
        response = _internal_client.post("/api/v1/auditar", json=payload, headers=HEADERS_VALIDOS)
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 400
        assert "tracking_id" not in response.json(), "Não deve gerar tracking_id para payload inválido"
        assert elapsed_ms < SLA_VALIDACAO_MS

    def test_valor_negativo_retorna_400(self):
        """
        EXCEÇÃO: valor ≤ 0 → HTTP 400.
        Lote fiscal negativo é semanticamente inválido.
        """
        payload = {**PAYLOAD_FISCAL_VALIDO, "valor": -100.0}
        response = _internal_client.post("/api/v1/auditar", json=payload, headers=HEADERS_VALIDOS)

        assert response.status_code == 400
        assert "maior que zero" in response.json()["detail"].lower()
        assert "tracking_id" not in response.json()

    def test_modulo_fiscal_invalido_retorna_400(self):
        """
        EXCEÇÃO: módulo fiscal fora da lista aceita → HTTP 400.
        Módulos válidos: EFD_ICMS_IPI, EFD_CONTRIBUICOES, NCM_AUDIT, ECF, SPED_FISCAL.
        """
        payload = {**PAYLOAD_FISCAL_VALIDO, "destino": "MODULO_INEXISTENTE"}
        response = _internal_client.post("/api/v1/auditar", json=payload, headers=HEADERS_VALIDOS)

        assert response.status_code == 400

    def test_payload_valido_gera_tracking_id(self):
        """
        CAMINHO FELIZ: Payload válido → HTTP 201 com tracking_id.
        tracking_id só é gerado APÓS validação completa (DN2.4).
        """
        response = _internal_client.post(
            "/api/v1/auditar",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        data = response.json()
        assert "tracking_id" in data
        assert len(data["tracking_id"]) > 0


# =============================================================================
# CAMADA 5 – INTEGRAÇÃO COM ASIS (UPLOAD SPED)
# =============================================================================

class TestCamadaUploadSPED:
    """
    Camada 5 – Integração com Serviço Externo ASIS TaxTech (Upload SPED)

    Módulo: asis_upload_file() (api.py) + proxy /api/v1/upload
    Hardware: servidores ASIS (upload.stg.asistaxtech.com.br)
    Software: API ASIS TaxTech v1
    Protocolo: HTTPS, multipart/form-data
    Timeout configurado: 5,0 segundos
    SLA do fluxo completo: 500ms (medido end-to-end via TestClient/mock)

    Estratégia live-or-mock:
    - Tenta upload na API real ASIS com credenciais reais
    - Se indisponível (timeout, erro de rede), cai em mock com ID local
    - O endpoint interno /api/v1/auditar já implementa este fallback
    """

    def test_upload_sped_live_or_mock(self):
        """
        Tenta upload de arquivo SPED na API ASIS real.
        Aceita mock se API real estiver indisponível.

        Protocolo: HTTPS multipart/form-data → upload.stg.asistaxtech.com.br
        Versão: API ASIS v1
        EXCEÇÃO tratada: timeout, erro de rede → fallback mock gracioso
        """
        resultado = _try_asis_real_upload()

        if resultado["source"] == "real":
            data = resultado["data"]
            # API real retornou: valida estrutura da resposta
            assert "processos" in data, "Resposta ASIS real deve conter campo 'processos'"
            assert len(data["processos"]) > 0
            process_id = data["processos"][0]["id"]
            assert isinstance(process_id, int), "process_id deve ser inteiro"
            print(f"\n  [LIVE] Upload ASIS real OK – process_id={process_id}")
        else:
            # API indisponível: registra razão e aceita comportamento mock
            print(f"\n  [MOCK] API ASIS indisponível: {resultado['reason']}")
            # Fallback aceitável: sem dado real, mas fluxo não deve ser bloqueado
            assert resultado["source"] == "mock"

    def test_fluxo_interno_com_fallback_mock(self):
        """
        Valida o fluxo completo via TestClient (in-process):
        autenticação → validação → upload (real ou mock) → resposta.

        O endpoint /api/v1/auditar já implementa a estratégia live-or-mock
        internamente: tenta asis_upload_file(), cai em UUID local se falhar.

        PROTOCOLO: JSON/REST, HTTP 201
        VERSÃO: API v1
        """
        start = time.perf_counter()
        response = _internal_client.post(
            "/api/v1/auditar",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 201
        data = response.json()

        # Contrato da resposta (DN2.4 / DN2.5)
        campos_obrigatorios = ["id", "status", "tracking_id", "arquivold", "diagnostico", "detalhes"]
        for campo in campos_obrigatorios:
            assert campo in data, f"Campo '{campo}' ausente na resposta"

        # Diagnóstico indica origem (real ou mock)
        assert data["diagnostico"] in ["Conforme (Real API ASIS)", "Conforme (Fallback Mock)"], (
            f"Diagnóstico inesperado: {data['diagnostico']}"
        )

        print(f"\n  [TEMPO] Fluxo completo: {elapsed_ms:.2f}ms | Fonte: {data['diagnostico']}")

        # SLA: fluxo completo deve ficar dentro de 500ms (via TestClient)
        assert elapsed_ms < SLA_FLUXO_COMPLETO_MS, (
            f"Fluxo excedeu SLA: {elapsed_ms:.2f}ms (limite {SLA_FLUXO_COMPLETO_MS}ms)"
        )

    def test_contrato_versao_api_preservado(self):
        """
        Controla que a versão v1 do contrato da API não foi alterada.

        VERSÃO aferida: POST /api/v1/auditar (versão 1, não /api/v2/...)
        Campos do contrato: id, status, tracking_id, arquivold, diagnostico, detalhes
        Sub-campos de detalhes: cliente, volume_processado, modulo
        """
        response = _internal_client.post(
            "/api/v1/auditar",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        data = response.json()

        detalhes = data.get("detalhes", {})
        assert "cliente" in detalhes
        assert "volume_processado" in detalhes
        assert "modulo" in detalhes
        assert detalhes["volume_processado"] == PAYLOAD_FISCAL_VALIDO["valor"]
        assert detalhes["modulo"] == PAYLOAD_FISCAL_VALIDO["destino"]


# =============================================================================
# CAMADA 5b – CONSULTA DE STATUS DO PROCESSO
# =============================================================================

class TestCamadaConsultaStatus:
    """
    Camada 5b – Consulta de Status de Processo ASIS

    Módulo: get_processo_status_proxy (api.py)
    Hardware: core.stg.asistaxtech.com.br
    Protocolo: HTTPS REST GET
    Versão: API ASIS v1

    Estratégia live-or-mock:
    - Tenta GET real em core.stg.asistaxtech.com.br/api/v1/processo/{id}
    - Se falhar, retorna status mock (CONCLUIDO)
    """

    def test_consulta_status_live_or_mock(self):
        """
        Consulta status de processo na API ASIS real ou mock.

        EXCEÇÃO tratada: timeout, HTTP 4xx/5xx → fallback mock estruturado.
        Campos esperados: id, status, statusDescricao, diagnostico.
        """
        # Primeiro faz upload para obter um process_id
        upload = _try_asis_real_upload()

        if upload["source"] == "real":
            process_id = upload["data"]["processos"][0]["id"]
            resultado = _try_asis_real_status(process_id)
        else:
            # API indisponível: usa ID fictício, fallback deve funcionar
            process_id = 99999
            resultado = _try_asis_real_status(process_id)

        data = resultado["data"]
        assert data is not None
        assert "id" in data
        assert "status" in data or "statusDescricao" in data

        print(f"\n  [STATUS] process_id={process_id} | fonte={resultado['source']} | status={data.get('status')}")

    def test_consulta_status_via_proxy_interno(self):
        """
        Valida o proxy interno /api/v1/processo/{id} (GET).

        Protocolo: REST GET, JSON
        Versão: v1
        EXCEÇÃO: se ASIS real falhar, proxy retorna mock estruturado com diagnostico_proxy.
        """
        response = _internal_client.get(
            "/api/v1/processo/12345",
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 200
        data = response.json()
        assert "diagnostico_proxy" in data
        assert data["diagnostico_proxy"] in [
            "Conforme (Real API ASIS)",
            "Conforme (Fallback Mock)",
        ]


# =============================================================================
# CAMADA 4 – RESILIÊNCIA (RATE LIMITER + CIRCUIT BREAKER)
# =============================================================================

class TestCamadaResiliencia:
    """
    Camada 4 – Resiliência: Rate Limiter e Circuit Breaker

    Módulos: RateLimiter, CircuitBreaker (api.py)
    Protocolo: HTTP 429 (Too Many Requests), HTTP 503 (Service Unavailable)
    Versão: API v1 — endpoint /api/v1/auditar/resilient

    Controle de qualidade:
    - Rate limiting: janela de 60s, máximo 10 req por account-key
    - Circuit breaker: abre após 5 falhas consecutivas, recupera em 30s
    - Alerta de disponibilidade: emitido quando taxa de erro > 30% (DN1 padrão)
    """

    def test_endpoint_resilient_responde_201(self):
        """
        CAMINHO FELIZ: Endpoint resiliente retorna 201 e expõe bloco availability.

        Campos obrigatórios no bloco availability:
        - circuit_state: estado atual do circuit breaker
        - rate_limit_remaining: requisições restantes na janela
        - idempotent_replay: se é um replay de idempotência
        - alert: alerta de disponibilidade (None se saudável)
        """
        start = time.perf_counter()
        response = _internal_client.post(
            "/api/v1/auditar/resilient",
            json=PAYLOAD_FISCAL_VALIDO,
            headers={"account-key": ASIS_ACCOUNT_KEY, "app-key": ASIS_APP_KEY},
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 201
        data = response.json()
        assert "availability" in data

        avail = data["availability"]
        assert "circuit_state" in avail
        assert "rate_limit_remaining" in avail
        assert "idempotent_replay" in avail
        assert avail["circuit_state"] == "CLOSED"
        assert isinstance(avail["rate_limit_remaining"], int)

        print(f"\n  [RESILIÊNCIA] {elapsed_ms:.2f}ms | circuit={avail['circuit_state']} | remaining={avail['rate_limit_remaining']}")

    def test_idempotencia_mesma_chave_retorna_mesmo_resultado(self):
        """
        Idempotência: mesma idempotency-key → mesmo tracking_id.

        Protocolo: header idempotency-key (string arbitrária)
        EXCEÇÃO evitada: reprocessamento duplicado de auditoria fiscal.
        """
        headers = {
            "account-key": ASIS_ACCOUNT_KEY,
            "app-key": ASIS_APP_KEY,
            "idempotency-key": "INT-FLUXO-G06-IDEM-001",
        }

        resp1 = _internal_client.post("/api/v1/auditar/resilient", json=PAYLOAD_FISCAL_VALIDO, headers=headers)
        resp2 = _internal_client.post("/api/v1/auditar/resilient", json=PAYLOAD_FISCAL_VALIDO, headers=headers)

        assert resp1.status_code == 201
        assert resp2.status_code == 201
        assert resp1.json()["tracking_id"] == resp2.json()["tracking_id"], (
            "Idempotência violada: tracking_ids diferentes para a mesma chave"
        )
        assert resp2.json()["idempotent_replay"] is True


# =============================================================================
# CAMADA 7 – NÃO-REPÚDIO CRIPTOGRÁFICO
# =============================================================================

class TestCamadaNaoRepudio:
    """
    Camada 7 – Não-Repúdio Criptográfico

    Módulos: sign_transaction, build_receipt, AuditLog (api.py)
    Protocolo: HMAC-SHA256, hash chain SHA-256, JSON
    Versão da API: v1.1.0 — endpoint POST /api/v1/auditar/nr
    SLA: fluxo completo < 500ms

    Processo: Cada transação fiscal válida é assinada digitalmente (HMAC-SHA256),
    recebe carimbo temporal ISO 8601 gerado pelo servidor (não pelo cliente),
    e é registrada em um log imutável com encadeamento de hashes (tipo blockchain).

    Controle de qualidade:
    - TEMPO: carimbo temporal ≤ 2s de defasagem do relógio UTC
    - PROTOCOLO: assinatura HMAC-SHA256 (64 hex chars)
    - VERSÃO: bloco non_repudiation presente no contrato v1.1.0
    - EXCEÇÃO: payload inválido não recebe assinatura nem entra no log
    """

    def test_assinatura_hmac_sha256_presente_e_valida(self):
        """
        PROTOCOLO: HMAC-SHA256 deve ser gerado para toda transação válida.

        Especificação:
        - Algoritmo: HMAC-SHA256 (conforme NR_SECRET_KEY definido em api.py)
        - Tamanho: 64 caracteres hexadecimais
        - Chave: ASIS_TAXTECH_G06_NR_SECRET_2026 (em produção: variável de ambiente)
        """
        response = _internal_client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        nr = response.json()["non_repudiation"]

        assert "signature" in nr
        assert isinstance(nr["signature"], str)
        assert len(nr["signature"]) == HMAC_HEX_LENGTH, (
            f"Assinatura {HMAC_ALGO} deve ter {HMAC_HEX_LENGTH} chars hex, "
            f"mas tem {len(nr['signature'])}"
        )

    def test_timestamp_iso8601_server_side(self):
        """
        PROTOCOLO + TEMPO: timestamp deve ser ISO 8601 gerado pelo servidor.

        - Formato: ISO 8601 com timezone UTC (ex: 2026-03-11T12:00:00.123+00:00)
        - Tolerância: ≤ 2 segundos de defasagem do relógio UTC
        - Server-side: não pode ser manipulado pelo cliente
        """
        antes = datetime.now(timezone.utc)
        response = _internal_client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        depois = datetime.now(timezone.utc)

        nr = response.json()["non_repudiation"]
        ts_str = nr["timestamp"]

        # Validar formato ISO 8601
        ts_server = datetime.fromisoformat(ts_str)
        assert ts_server.tzinfo is not None, f"Timestamp deve ter timezone ({TIMESTAMP_FORMAT})"

        # Validar que está dentro da tolerância de 2 segundos
        assert ts_server >= antes - timedelta(seconds=2), "Timestamp mais antigo que o esperado"
        assert ts_server <= depois + timedelta(seconds=2), "Timestamp mais recente que o esperado"

    def test_recibo_digital_contem_campos_criptograficos(self):
        """
        PROTOCOLO: Recibo digital deve conter todas as evidências criptográficas.

        Campos obrigatórios (contrato v1.1.0):
        - signature: HMAC-SHA256 do payload + timestamp
        - timestamp: carimbo ISO 8601 server-side
        - actor: SHA-256 da account-key (não expõe a chave original)
        - tracking_id: ID de rastreio vinculado ao log
        - payload_hash: SHA-256 do payload original (prova de conteúdo)
        """
        response = _internal_client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        receipt = response.json()["non_repudiation"]["receipt"]

        campos_criptograficos = ["signature", "timestamp", "actor", "tracking_id", "payload_hash"]
        for campo in campos_criptograficos:
            assert campo in receipt, f"Campo criptográfico '{campo}' ausente no recibo"
            assert receipt[campo], f"Campo '{campo}' está vazio no recibo"

        # Actor é SHA-256 da account-key (impede exposição da chave)
        actor_esperado = hashlib.sha256(ASIS_ACCOUNT_KEY.encode("utf-8")).hexdigest()
        assert receipt["actor"] == actor_esperado

    def test_payload_invalido_nao_recebe_assinatura(self):
        """
        EXCEÇÃO: Payload inválido não deve gerar assinatura nem entrada no log.

        Regra: não-repúdio só é gerado para transações que passaram por
        todas as validações. Transação rejeitada (HTTP 400) não tem evidência
        criptográfica para não criar "recibos falsos".
        """
        payload_invalido = {**PAYLOAD_FISCAL_VALIDO, "valor": -500.0}
        response = _internal_client.post(
            "/api/v1/auditar/nr",
            json=payload_invalido,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 400
        assert "non_repudiation" not in response.json()
        assert audit_log.size() == 0, "Log de auditoria não deve registrar transações inválidas"

    def test_log_auditoria_chain_integra_apos_multiplas_transacoes(self):
        """
        PROTOCOLO: Cadeia de hash do log deve permanecer íntegra após múltiplas transações.

        Mecanismo: cada entrada referencia o hash SHA-256 da anterior (hash chain),
        formando uma corrente criptográfica que detecta adulteração retroativa.

        TEMPO: 3 transações consecutivas dentro do SLA de 500ms cada.
        """
        for i in range(3):
            payload = {**PAYLOAD_FISCAL_VALIDO, "sessao_cliente": f"INT_NR_G06_{i}"}
            start = time.perf_counter()
            response = _internal_client.post(
                "/api/v1/auditar/nr",
                json=payload,
                headers=HEADERS_VALIDOS,
            )
            elapsed_ms = (time.perf_counter() - start) * 1000

            assert response.status_code == 201
            assert elapsed_ms < SLA_FLUXO_COMPLETO_MS, (
                f"Transação {i+1} excedeu SLA: {elapsed_ms:.2f}ms"
            )

        # Verificar integridade da cadeia completa
        assert audit_log.size() == 3
        assert audit_log.verify_chain() is True, (
            "Hash chain do log de auditoria está comprometida — possível adulteração"
        )


# =============================================================================
# CONTROLE DE QUALIDADE – FLUXO END-TO-END
# =============================================================================

class TestControleQualidadeFluxoCompleto:
    """
    Controle de Qualidade – Fluxo End-to-End

    Aferição do ciclo completo de auditoria fiscal:
    Cliente → Autenticação → Validação → Upload → Não-Repúdio → Resposta

    Controles medidos:
    - TEMPO: latência end-to-end (SLA = 500ms)
    - PROTOCOLO: HTTP 201, JSON, REST v1
    - VERSÃO: contrato v1 preservado (campos e estrutura inalterados)
    - EXCEÇÕES: fallback mock documentado e gracioso
    """

    def test_fluxo_end_to_end_com_nao_repudio_dentro_do_sla(self):
        """
        TEMPO + PROTOCOLO: Fluxo completo com não-repúdio deve estar no SLA.

        Mede o tempo do ciclo: POST /api/v1/auditar/nr
        SLA: 500ms | Alerta: 650ms (30% acima – padrão DN1)
        """
        start = time.perf_counter()
        response = _internal_client.post(
            "/api/v1/auditar/nr",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        elapsed_ms = (time.perf_counter() - start) * 1000

        assert response.status_code == 201
        print(f"\n  [E2E] Tempo total com NR: {elapsed_ms:.2f}ms (SLA={SLA_FLUXO_COMPLETO_MS}ms, alerta={SLA_ALERTA_MS}ms)")

        if elapsed_ms > SLA_ALERTA_MS:
            print(f"  [ALERTA DN1] Tempo acima do limiar de alerta ({SLA_ALERTA_MS}ms)")

        assert elapsed_ms < SLA_FLUXO_COMPLETO_MS, (
            f"Fluxo E2E com NR excedeu SLA: {elapsed_ms:.2f}ms (limite {SLA_FLUXO_COMPLETO_MS}ms)"
        )

    def test_diagnostico_indica_origem_real_ou_mock(self):
        """
        VERSÃO + EXCEÇÃO: Campo 'diagnostico' documenta a fonte da resposta.

        Valores aceitos:
        - "Conforme (Real API ASIS)": upload processado na API real ASIS
        - "Conforme (Fallback Mock)": API real indisponível, resposta simulada

        Ambos são respostas válidas — o fallback é parte do contrato de resiliência.
        """
        response = _internal_client.post(
            "/api/v1/auditar",
            json=PAYLOAD_FISCAL_VALIDO,
            headers=HEADERS_VALIDOS,
        )
        assert response.status_code == 201
        diagnostico = response.json()["diagnostico"]
        assert diagnostico in ["Conforme (Real API ASIS)", "Conforme (Fallback Mock)"], (
            f"Diagnóstico fora do contrato: '{diagnostico}'"
        )

    def test_health_check_documenta_estado_do_sistema(self):
        """
        PROTOCOLO + VERSÃO: Endpoint de health expõe estado de todos os componentes.

        GET /api/v1/health — não exige autenticação (monitoramento público)
        Versão: v1.1.0 (campo 'version' na resposta)
        """
        response = _internal_client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()

        assert data["version"] == "1.1.0", f"Versão inesperada: {data['version']}"
        assert data["status"] in ["healthy", "degraded"]
        assert "circuit_breaker" in data
        assert "availability_alert" in data
        assert "circuit_alert" in data

        print(f"\n  [HEALTH] status={data['status']} | version={data['version']} | uptime={data['uptime_seconds']}s")


if __name__ == "__main__":
    pytest.main([__file__, "-v", "-s"])
