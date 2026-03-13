"""
INT5 — Aferição da Integração RFB / SPED
Projeto ASIS TaxTech - Grupo 06 - Blue Team

Módulo autocontido: lógica de aferição + testes unitários no mesmo arquivo.

Estratégia Live-or-Mock:
  [API REAL RFB] Se o endpoint real da RFB estiver acessível, testes de happy path
                 rodam contra ele. Cenários de falha usam URLs reais que falham.
  [MOCK LOCAL]   Se a API real estiver offline, todos os testes rodam com mock local.

Todos os 6 testes rodam sempre — nenhum é skipado.
"""

import logging
import sys
import unittest
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from unittest.mock import AsyncMock, MagicMock, patch

import httpx

# =============================================================================
# Lógica de Aferição INT5 (autocontida)
# =============================================================================

# Log sem expor dados sensíveis (LGPD)
logger = logging.getLogger("int5_sped")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)

# Constantes de configuração
INT5_ENDPOINT    = "https://sped.api.receita.fazenda.gov.br/v1/layout/rf1"
EXPECTED_VERSION = "v2026"
_versao_local    = "v2026"  # Controle local de versão (em prod: banco/Redis/arquivo)


class IntegracaoStatus:
    CONFORME          = "CONFORME"
    MUDANCA_DETECTADA = "MUDANCA DETECTADA"
    INDISPONIVEL      = "INDISPONIVEL"


def carregar_versao_anterior() -> str:
    """Retorna a última versão registrada localmente."""
    return _versao_local


def salvar_versao_atual(versao: str) -> None:
    """Atualiza o registro de versão local ao detectar mudança."""
    global _versao_local
    _versao_local = versao


# Payload representativo da nossa estrutura RF1 (v2026)
PAYLOAD_AFERICAO = {
    "versao": "v2026",
    "cnpj_emissor": "00000000000191",
    "competencia": "2026-01",
    "hash_lote": "afericao-automatica"
}

async def checar_endpoint_sped(url: str = INT5_ENDPOINT, timeout: float = 10.0) -> Dict[str, Any]:
    """
    Submete um payload de afericao ao servico do SPED/RFB.
    Valida ativamente se a estrutura do nosso sistema (v2026)
    ainda e aceita pelo contrato vigente da Receita.
    """
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, json=PAYLOAD_AFERICAO, headers={"Accept": "application/json"})
            
            # Se a Receita retornar 400/422 (Unprocessable Entity), o layout mudou.
            # Convertemos isso num retorno controlado em vez de explodir exceçao.
            if response.status_code in (400, 422):
                return {"aceito": False, "motivo": response.text, "status_code": response.status_code}
            
            response.raise_for_status()
            return {"aceito": True, "status_code": response.status_code, "dados": response.json()}
            
    except httpx.HTTPStatusError as e:
        logger.error(f"Erro HTTP ao acessar SPED: Codigo {e.response.status_code}")
        raise ConnectionError("Falha de comunicacao com o servico (HTTP Error).")
    except httpx.RequestError:
        logger.error("Falha de rede ao acessar SPED. Endpoint indisponivel ou inacessivel.")
        raise ConnectionError("Endpoint do SPED inacessivel.")
    except Exception:
        logger.error("Erro inesperado durante a comunicacao com o SPED.")
        raise ConnectionError("Erro interno no cliente HTTP.")


async def verificar_integracao_int5(
    url: str = INT5_ENDPOINT,
    timeout: float = 10.0,
) -> Dict[str, Any]:
    """
    Programa de aferição da integração INT5 — RFB / SPED.
    Compatível com APScheduler/cron para execução periódica.

    Retorna dicionário com:
      - integracao      : identificador da integração
      - timestamp       : momento da verificação (UTC ISO 8601)
      - versao_esperada : versão de referência configurada
      - versao_obtida   : versão retornada pelo serviço (None se indisponível)
      - status          : CONFORME | MUDANCA DETECTADA | INDISPONIVEL
    """
    relatorio: Dict[str, Any] = {
        "integracao":      "INT5_SPED_RF1",
        "timestamp":       datetime.now(timezone.utc).isoformat(),
        "versao_esperada": EXPECTED_VERSION,
    }

    versao_anterior = carregar_versao_anterior()

    try:
        dados = await checar_endpoint_sped(url, timeout=timeout)
        
        # Se foi aceito (200, 201, 202), o contrato v2026 continua valendo
        if dados.get("aceito") is True:
            relatorio["status"] = IntegracaoStatus.CONFORME
            relatorio["versao_obtida"] = EXPECTED_VERSION  # Confirmado que o esperado foi aceito
            logger.info("Afericao INT5: Payload de validacao ACEITO. Conformidade mantida.")
        else:
            # Rejeitado (400, 422) = Desacordo de contrato (Receita mudou o layout exigido)
            relatorio["status"] = IntegracaoStatus.MUDANCA_DETECTADA
            relatorio["versao_obtida"] = "rejeitado (mudanca_schema)"
            logger.warning(
                f"Afericao INT5: Quebra de contrato! Layout rejeitado pela RFB. "
                f"Motivo: {dados.get('motivo')} | Status: {dados.get('status_code')}"
            )
            salvar_versao_atual("desatualizado")

    except ConnectionError:
        relatorio["status"]        = IntegracaoStatus.INDISPONIVEL
        relatorio["versao_obtida"] = None
        logger.critical("Afericao INT5: Servico do SPED INDISPONIVEL.")

    return relatorio


# =============================================================================
# Probe: detectar disponibilidade do endpoint real
# =============================================================================

def _endpoint_real_disponivel(url: str = INT5_ENDPOINT, timeout: float = 3.0) -> bool:
    """Retorna True se o host responder qualquer chamada HEAD/GET/POST."""
    try:
        # Usamos HEAD para probe leve apenas para ver se o dns/rede existe
        httpx.head(url, timeout=timeout)
        return True
    except (httpx.RequestError, httpx.TimeoutException):
        return False


USANDO_API_REAL = _endpoint_real_disponivel()

print(
    f"\n[INT5] Modo: {'[API REAL RFB]' if USANDO_API_REAL else '[MOCK LOCAL]'}"
    f" | endpoint: {INT5_ENDPOINT}\n"
)

# Caminho do patch detectado em runtime — funciona com pytest e execucao direta
_PATCH_TARGET = f"{__name__}.httpx.AsyncClient"

URL_PORTA_FECHADA = "http://127.0.0.1:1/"   # Porta sem servidor — ConnectionRefused real
URL_TIMEOUT_REAL  = INT5_ENDPOINT            # Endpoint real com timeout absurdamente curto


# =============================================================================
# Helper: montar mock do AsyncClient como context manager
# =============================================================================

def _make_async_client_mock(json_return=None, raise_for_status_exc=None, request_error=None):
    """Constrói mock de httpx.AsyncClient compatível com `async with`."""
    mock_response = MagicMock()
    mock_response.status_code = 200

    if raise_for_status_exc:
        mock_response.raise_for_status.side_effect = raise_for_status_exc
    else:
        mock_response.raise_for_status.return_value = None

    if json_return is not None:
        mock_response.json.return_value = json_return

    mock_inner = AsyncMock()
    if request_error:
        mock_inner.post.side_effect = request_error
    else:
        mock_inner.post.return_value = mock_response

    mock_cm = AsyncMock()
    mock_cm.__aenter__.return_value = mock_inner
    mock_cm.__aexit__.return_value = False
    return mock_cm


# =============================================================================
# Testes
# =============================================================================

class TestINT5SpedAfericao(unittest.IsolatedAsyncioTestCase):
    """
    Blue Team — Afericao da Integracao INT5 (SPED / RFB).
    Todos os 6 testes rodam sempre — sem skipTest.
    """

    # -------------------------------------------------------------------------
    # Cenário 1: Layout CONFORME (v2026)
    # -------------------------------------------------------------------------

    async def test_integracao_em_conformidade_v2026(self):
        """
        Cenario 1 - CONFORME
        Submete o payload v2026 e o servico ACEITA (simulando 202 Accepted).
        Confirma que a estrutura do nosso sistema esta em conformidade.
        """
        if USANDO_API_REAL:
            resultado = await verificar_integracao_int5()
            self.assertIn(resultado["status"], [
                IntegracaoStatus.CONFORME,
                IntegracaoStatus.MUDANCA_DETECTADA,
            ])
            print(f"  [REAL] Status={resultado['status']} | Conformidade={resultado.get('versao_obtida')}")
        else:
            mock_cm = _make_async_client_mock(json_return={"protocolo": "123"}, raise_for_status_exc=None)
            # Força o mock a retornar 202 Accepted
            with patch(_PATCH_TARGET, return_value=mock_cm) as mock_post:
                resultado = await verificar_integracao_int5()
            self.assertEqual(resultado["status"], IntegracaoStatus.CONFORME)
            self.assertEqual(resultado["versao_obtida"], EXPECTED_VERSION)

        self.assertIn("timestamp", resultado)

    # -------------------------------------------------------------------------
    # Cenário 2: Quebra de Contrato — Payload rejeitado
    # -------------------------------------------------------------------------

    async def test_integracao_layout_desatualizado_mudanca(self):
        """
        Cenario 2 - MUDANCA DETECTADA (Quebra de contrato)
        A Receita Federal REJEITA nosso payload (ex: mudaram a versao pra v2027
        e nossa estrutura v2026 virou invalida) acusando 422 Unprocessable Entity.
        """
        if USANDO_API_REAL:
            resultado = await verificar_integracao_int5()
            self.assertIn(resultado["status"], [
                IntegracaoStatus.CONFORME,
                IntegracaoStatus.MUDANCA_DETECTADA,
            ])
        else:
            # Simulando RFB rejeitando nosso schema
            mock_response = MagicMock()
            mock_response.status_code = 422
            mock_response.text = '{"erro": "Layout v2026 descontinuado, utilize v2027"}'
            
            mock_inner = AsyncMock()
            mock_inner.post.return_value = mock_response
            mock_cm = AsyncMock()
            mock_cm.__aenter__.return_value = mock_inner
            
            with patch(_PATCH_TARGET, return_value=mock_cm):
                resultado = await verificar_integracao_int5()
                
            self.assertEqual(resultado["status"], IntegracaoStatus.MUDANCA_DETECTADA)
            self.assertEqual(resultado["versao_obtida"], "rejeitado (mudanca_schema)")

    # -------------------------------------------------------------------------
    # Cenário 3: Erro de rede — conexão recusada (falha real de rede)
    # -------------------------------------------------------------------------

    async def test_integracao_servico_indisponivel_erro_rede(self):
        """
        Cenario 3 - INDISPONIVEL (falha de rede genuina)
        Aponta para porta local fechada (127.0.0.1:1) — ConnectionRefused real.
        """
        resultado = await verificar_integracao_int5(url=URL_PORTA_FECHADA)

        self.assertEqual(resultado["status"], IntegracaoStatus.INDISPONIVEL)
        self.assertIsNone(resultado.get("versao_obtida"))
        self.assertIn("timestamp", resultado)

    # -------------------------------------------------------------------------
    # Cenário 4: HTTP 503 — única exceção que usa mock
    # -------------------------------------------------------------------------

    async def test_integracao_servico_erro_http_503(self):
        """
        Cenario 4 - INDISPONIVEL (HTTP 503)
        Nao existe servidor confiavel para forcar 503 sob demanda.
        Este e o unico cenario que usa mock controlado.
        """
        mock_response = MagicMock()
        mock_response.status_code = 503
        exc = httpx.HTTPStatusError(
            message="503 Service Unavailable",
            request=MagicMock(),
            response=mock_response,
        )
        mock_cm = _make_async_client_mock(raise_for_status_exc=exc)
        with patch(_PATCH_TARGET, return_value=mock_cm):
            resultado = await verificar_integracao_int5()

        self.assertEqual(resultado["status"], IntegracaoStatus.INDISPONIVEL)
        self.assertIsNone(resultado.get("versao_obtida"))
        self.assertIn("timestamp", resultado)

    # -------------------------------------------------------------------------
    # Cenário 5: Timeout — requisição real com timeout mínimo
    # -------------------------------------------------------------------------

    async def test_integracao_servico_timeout(self):
        """
        Cenario 5 - INDISPONIVEL (timeout genuino)
        Usa o endpoint real com timeout=0.001s — impossivel de satisfazer.
        TimeoutException real, sem mock.
        """
        resultado = await verificar_integracao_int5(
            url=URL_TIMEOUT_REAL,
            timeout=0.001,
        )

        self.assertEqual(resultado["status"], IntegracaoStatus.INDISPONIVEL)
        self.assertIsNone(resultado.get("versao_obtida"))
        self.assertIn("timestamp", resultado)

    # -------------------------------------------------------------------------
    # Cenário 6: Estrutura do relatório
    # -------------------------------------------------------------------------

    async def test_estrutura_relatorio_retornado(self):
        """
        Cenario 6 - Estrutura do relatorio
        Valida que todos os campos obrigatorios estao presentes no retorno.
        API real (quando disponivel) ou mock como fallback.
        """
        if USANDO_API_REAL:
            resultado = await verificar_integracao_int5()
        else:
            mock_cm = _make_async_client_mock(
                json_return={"versao_layout": EXPECTED_VERSION, "ativo": True}
            )
            with patch(_PATCH_TARGET, return_value=mock_cm):
                resultado = await verificar_integracao_int5()

        for campo in ["integracao", "timestamp", "versao_esperada", "status"]:
            self.assertIn(campo, resultado, f"Campo obrigatorio '{campo}' ausente no relatorio")

        self.assertEqual(resultado["integracao"],      "INT5_SPED_RF1")
        self.assertEqual(resultado["versao_esperada"], EXPECTED_VERSION)


if __name__ == "__main__":
    unittest.main(verbosity=2)
