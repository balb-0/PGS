"""
INT5 — Aferição da Integração RFB / SPED
Projeto ASIS TaxTech - Grupo 06 - Blue Team

Módulo autocontido: Lógica de aferição de Layout/Contrato + Testes Unitários.

Foco da Aferição:
  Garantir que os payloads gerados pelo sistema ASIS e destinados ao SPED 
  estão em rigorosa conformidade com o Layout Oficial (v2026), sem depender 
  de chamadas de rede externas ou da disponibilidade da infraestrutura da RFB.
"""

import logging
import unittest
from unittest import mock
from datetime import datetime, timezone
from typing import Any, Dict, List

# =============================================================================
# Lógica de Aferição INT5 (Validação Autocontida de Layout/Schema)
# =============================================================================

# Log sem expor dados sensíveis (LGPD)
logger = logging.getLogger("int5_sped_layout")
logger.setLevel(logging.INFO)
_handler = logging.StreamHandler()
_handler.setFormatter(logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s"))
if not logger.handlers:
    logger.addHandler(_handler)

EXPECTED_VERSION = "v2026"

class IntegracaoStatus:
    CONFORME = "CONFORME"
    LAYOUT_INVALIDO = "LAYOUT INVÁLIDO"

# =============================================================================
# Definição do Contrato / Layout Oficial (RF1 v2026)
# =============================================================================

# Tabela de regras simples de validação do layout (Schema)
# Em produção, pode ser substituído por Pydantic ou Cerberus.
LAYOUT_RF1_V2026 = {
    "versao": {"type": str, "required": True, "value": "v2026"},
    "cnpj_emissor": {"type": str, "required": True, "length": 14},
    "competencia": {"type": str, "required": True},
    "hash_lote": {"type": str, "required": True},
    "volume_transacoes": {"type": int, "required": False}, # opcional
}

def validar_layout_sped(payload: Dict[str, Any]) -> Dict[str, Any]:
    """
    Motor interno de validação. Bate o payload do ASIS contra as
    regras estáticas oficiais do Layout da Receita Federal.
    """
    erros: List[str] = []

    # 1. Verifica campos obrigatórios
    for campo, regras in LAYOUT_RF1_V2026.items():
        if regras.get("required") and campo not in payload:
            erros.append(f"Campo obrigatório ausente: '{campo}'")
            continue
        
        # 2. Verifica regras de formato se o campo existir
        if campo in payload:
            valor = payload[campo]
            tipo_esperado = regras.get("type")
            
            if not isinstance(valor, tipo_esperado):
                erros.append(f"Tipo incorreto para o campo '{campo}'. Esperado {tipo_esperado.__name__}")
                continue
                
            if "length" in regras and len(valor) != regras["length"]:
                erros.append(f"Tamanho invalido para '{campo}'. Esperado {regras['length']} caracteres")
                
            if "value" in regras and valor != regras["value"]:
                erros.append(f"Valor incorreto para '{campo}'. Esperado: '{regras['value']}'")

    if erros:
        return {"valido": False, "erros": erros}

    return {"valido": True, "erros": []}


def aferir_layout_int5(payload_recebido: Dict[str, Any]) -> Dict[str, Any]:
    """
    Programa de aferição da integração INT5 — RFB / SPED.
    Confirma se o contrato está conforme o Layout Interno.

    Retorna dicionário com status final, erros (se houver) e timestamp.
    """
    relatorio: Dict[str, Any] = {
        "integracao": "INT5_SPED_RF1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "versao_layout": EXPECTED_VERSION,
    }

    resultado_validacao = validar_layout_sped(payload_recebido)

    if resultado_validacao["valido"] is True:
        relatorio["status"] = IntegracaoStatus.CONFORME
        logger.info("Afericao INT5: Payload ASIS esta CONFORME o Layout v2026 oficial.")
    else:
        relatorio["status"] = IntegracaoStatus.LAYOUT_INVALIDO
        relatorio["detalhes_erros"] = resultado_validacao["erros"]
        logger.warning(
            f"Afericao INT5: QUEBRA DE CONTRATO DETECTADA. "
            f"Erros de Layout: {resultado_validacao['erros']}"
        )

    return relatorio


# =============================================================================
# Importação da API ASIS (Para interceptar o Contrato)
# =============================================================================
from fastapi.testclient import TestClient
from src.core.api import app, ASIS_ACCOUNT_KEY, ASIS_APP_KEY

# Cliente de Teste da nossa própria API
client = TestClient(app)

HEADERS_VALIDOS = {
    "account-key": ASIS_ACCOUNT_KEY,
    "app-key": ASIS_APP_KEY
}

# Payload base HTTP que entra no ASIS (que fará o ASIS gerar o Contrato SPED internamente)
PAYLOAD_ENTRADA_ASIS_PERFEITO = {
    "sessao_cliente": "SESSAO_TESTE_AFERICAO",
    "valor": 1500.0,
    "destino": "SPED_FISCAL"
}

# =============================================================================
# Testes Blue Team — Integrado com API
# =============================================================================

class TestINT5SpedAfericaoLayoutIntegrado(unittest.TestCase):
    """
    Blue Team — Afericao de Layout SEM dependencia da Receita.
    O teste:
      1. Bate na NOSSA API ASIS (/api/v1/auditar)
      2. Intercepta o "payload_sped_gerado" (o contrato que seria enviado à RFB)
      3. Valida se esse contrato ASIS respeita rigorosamente o Layout v2026 oficial.
    """

    def test_contrato_asis_gerado_esta_conforme_o_layout(self):
        """
        Cenario 1: Conforme
        A API processa a auditoria e gera um contrato SPED válido.
        A validação de layout pura atesta a conformidade.
        """
        # 1. Envia requisição para nossa API
        resp = client.post(
            "/api/v1/auditar", 
            json=PAYLOAD_ENTRADA_ASIS_PERFEITO,
            headers=HEADERS_VALIDOS
        )
        self.assertEqual(resp.status_code, 201)
        
        # 2. Intercepta o Contrato/Schema gerado pela API ASIS
        dados_resposta = resp.json()
        self.assertIn("payload_sped_gerado", dados_resposta, "A API não gerou/retornou o contrato SPED")
        contrato_gerado = dados_resposta["payload_sped_gerado"]

        # 3. Valida esse Contrato contra o Layout Oficial (v2026)
        resultado_afericao = aferir_layout_int5(contrato_gerado)
        
        # 4. Afirma que está CONFORME
        self.assertEqual(resultado_afericao["status"], IntegracaoStatus.CONFORME)
        self.assertNotIn("detalhes_erros", resultado_afericao)

    def test_captura_quebra_de_contrato_schema_invalido(self):
        """
        Cenario 2: Quebra de Contrato - O ASIS gera um contrato faltando campo.
        Forcamos a mudança nas regras de validação para simular que a "Receita exigiria uma chave extra".
        E provamos que o motor de layout bloqueia o contrato gerado pela API.
        """
        # Altera temporariamente as regras oficiais para EXIGIR um campo inexistente no ASIS
        LAYOUT_RF1_V2026["chave_nova_secreta_da_receita"] = {"type": str, "required": True}
        
        try:
            # 1. Envia requisição normal para nossa API
            resp = client.post("/api/v1/auditar", json=PAYLOAD_ENTRADA_ASIS_PERFEITO, headers=HEADERS_VALIDOS)
            contrato_gerado = resp.json()["payload_sped_gerado"]

            # 2. Valida o Contrato (que agora vai falhar por falta da chave secreta)
            resultado_afericao = aferir_layout_int5(contrato_gerado)
            
            # 3. Confirma o alerta
            self.assertEqual(resultado_afericao["status"], IntegracaoStatus.LAYOUT_INVALIDO)
            self.assertTrue(any("chave_nova_secreta_da_receita" in err for err in resultado_afericao["detalhes_erros"]))
        finally:
            # Restaura a regra normal
            del LAYOUT_RF1_V2026["chave_nova_secreta_da_receita"]

    def test_estrutura_relatorio_afericao(self):
        """
        Cenario 3: Valida a estrutura da aferição gerada a partir do payload ASIS.
        """
        resp = client.post("/api/v1/auditar", json=PAYLOAD_ENTRADA_ASIS_PERFEITO, headers=HEADERS_VALIDOS)
        contrato_gerado = resp.json()["payload_sped_gerado"]
        
        resultado_afericao = aferir_layout_int5(contrato_gerado)
        
        campos_obrigatorios = ["integracao", "timestamp", "versao_layout", "status"]
        for campo in campos_obrigatorios:
            self.assertIn(campo, resultado_afericao, f"Campo obrigatorio '{campo}' ausente")
        self.assertEqual(resultado_afericao["integracao"], "INT5_SPED_RF1")


if __name__ == "__main__":
    unittest.main(verbosity=2)

