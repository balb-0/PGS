"""
Testes automatizados para DN2 - Integridade dos Dados Fiscais na Ingestão
Projeto ASIS TaxTech - Abordagem Test Data Driven (TDD)

Este módulo testa as regras de negócio que garantem a validação rigorosa
de payloads fiscais antes do processamento, evitando erros de integridade
de dados na ingestão de documentos fiscais.
"""

import pytest
from fastapi.testclient import TestClient
import sys
from pathlib import Path

# Adicionar o caminho ao src para importar a api
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from core.api import app

# Cliente de teste para a API
client = TestClient(app)

# Headers obrigatórios para todas as requisições
# Nota: FastAPI converte underscores em hyphens para headers HTTP
HEADERS_VALIDOS = {
    "account-key": "conta-teste-123",
    "app-key": "app-teste-456"
}


class TestDN2IntegrityValidation:
    """
    Testes para DN2 - Integridade dos Dados Fiscais na Ingestão
    
    Objetivo: Validar que a API rejeita payloads inválidos ANTES de iniciar
    processamento assíncrono ou gerar tracking_id, garantindo integridade dos dados.
    """

    # ========== DN2.1: Campos Obrigatórios Ausentes ==========
    
    def test_rejeita_payload_sem_sessao_cliente(self):
        """
        DN2.1: A API deve rejeitar requisições com "sessao_cliente" ausente.
        
        Regra de negócio: Toda auditoria fiscal deve estar vinculada a uma sessão
        de cliente válida para rastreabilidade.
        
        Resultado esperado: HTTP 400 sem processing iniciado
        """
        payload = {
            # "sessao_cliente": ausente propositalmente
            "valor": 1500.00,
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "obrigatórios" in response.json()["detail"].lower()
        assert "tracking_id" not in response.json()  # Não deve gerar ID
    
    def test_rejeita_payload_sem_valor(self):
        """
        DN2.1: A API deve rejeitar requisições com "valor" ausente.
        
        Regra de negócio: O volume fiscal (valor) é essencial para auditoria,
        pois determina o escopo de análise e alocação de recursos.
        
        Resultado esperado: HTTP 400 sem processing iniciado
        """
        payload = {
            "sessao_cliente": "cliente_001",
            # "valor": ausente propositalmente
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "obrigatórios" in response.json()["detail"].lower()
        assert "tracking_id" not in response.json()
    
    def test_rejeita_payload_sem_destino(self):
        """
        DN2.1: A API deve rejeitar requisições com "destino" (módulo fiscal) ausente.
        
        Regra de negócio: O destino define qual módulo fiscal será auditado
        (ICMS, IPI, PIS, etc), sendo informação crítica para roteamento interno.
        
        Resultado esperado: HTTP 400 sem processing iniciado
        """
        payload = {
            "sessao_cliente": "cliente_001",
            "valor": 1500.00,
            # "destino": ausente propositalmente
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "obrigatórios" in response.json()["detail"].lower()
        assert "tracking_id" not in response.json()

    # ========== DN2.2: Validação de Valor > Zero ==========
    
    def test_rejeita_valor_negativo(self):
        """
        DN2.2: A API deve rejeitar requisições onde "valor" é negativo.
        
        Regra de negócio: Um lote fiscal com volume negativo é contraditório
        e indica erro na origem dos dados. Deve ser rejeitado imediatamente.
        
        Resultado esperado: HTTP 400, sem gerar tracking_id
        """
        payload = {
            "sessao_cliente": "cliente_001",
            "valor": -100.00,  # Valor negativo
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "maior que zero" in response.json()["detail"].lower()
        assert "tracking_id" not in response.json()
    
    def test_rejeita_valor_zero(self):
        """
        DN2.2: A API deve rejeitar requisições onde "valor" é zero.
        
        Regra de negócio: Um lote com volume zero é inválido. Auditorias
        de lotes vazios consomem recursos sem benefício e devem ser bloqueadas.
        
        Resultado esperado: HTTP 400, sem gerar tracking_id
        """
        payload = {
            "sessao_cliente": "cliente_001",
            "valor": 0,  # Valor zero
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "maior que zero" in response.json()["detail"].lower()
        assert "tracking_id" not in response.json()
    
    def test_rejeita_valor_zero_ponto_zero(self):
        """
        DN2.2: A API deve rejeitar "valor" com 0.0 (formato decimal).
        
        Regra de negócio: Validação de tipo e magnitude numérica.
        
        Resultado esperado: HTTP 400
        """
        payload = {
            "sessao_cliente": "cliente_001",
            "valor": 0.0,  # Zero em formato decimal
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "maior que zero" in response.json()["detail"].lower()
    
    def test_rejeita_valor_tipo_invalido_string(self):
        """
        DN2.2: A API deve rejeitar "valor" se não for numérico (ex: string).
        
        Regra de negócio: O valor deve ser passível de operações aritméticas
        para cálculos de integridade fiscal.
        
        Resultado esperado: HTTP 400
        """
        payload = {
            "sessao_cliente": "cliente_001",
            "valor": "abc",  # String inválida
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "maior que zero" in response.json()["detail"].lower()

    # ========== DN2.3 & DN2.4: Payloads Válidos ==========
    
    def test_aceita_payload_valido_inteiro(self):
        """
        DN2.5: A API deve manter o comportamento atual para payloads VÁLIDOS.
        
        Regra de negócio: Payloads válidos devem ser processados normalmente
        e retornar HTTP 201 com tracking_id e demais informações.
        
        Cenário: Valor inteiro positivo
        Resultado esperado: HTTP 201, com tracking_id presente
        """
        payload = {
            "sessao_cliente": "cliente_001",
            "valor": 1500,  # Valor inteiro positivo
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Validar estrutura de resposta (contrato da API)
        assert "id" in data
        assert "status" in data
        assert data["status"] == 201
        assert "tracking_id" in data  # DN2.4: tracking_id gerado apenas para válidos
        assert "diagnostico" in data
        assert "detalhes" in data
        
        # Validar conteúdo dos detalhes
        assert data["detalhes"]["cliente"] == "cliente_001"
        assert data["detalhes"]["volume_processado"] == 1500
        assert data["detalhes"]["modulo"] == "modulo_icms"
    
    def test_aceita_payload_valido_decimal(self):
        """
        DN2.5: A API deve processar valores decimais válidos.
        
        Cenário: Valor decimal positivo (simulando centavos em reais)
        Resultado esperado: HTTP 201, com tracking_id presente
        """
        payload = {
            "sessao_cliente": "cliente_fiscal_456",
            "valor": 2500.50,  # Valor decimal positivo
            "destino": "modulo_ipi"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "tracking_id" in data
        assert data["detalhes"]["volume_processado"] == 2500.50
    
    def test_aceita_payload_valido_valor_minimo(self):
        """
        DN2.5: A API deve processar o menor valor válido (qualquer número > 0).
        
        Cenário: Valor muito pequeno mas positivo
        Resultado esperado: HTTP 201
        """
        payload = {
            "sessao_cliente": "cliente_pequeno",
            "valor": 0.01,  # Menor quantidade possível
            "destino": "modulo_pis"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "tracking_id" in data
    
    def test_aceita_payload_valido_valor_grande(self):
        """
        DN2.5: A API deve processar valores grandes (lotes volumosos).
        
        Cenário: Valor grande representando grande volume fiscal
        Resultado esperado: HTTP 201
        """
        payload = {
            "sessao_cliente": "cliente_grande",
            "valor": 999999.99,  # Valor grande
            "destino": "modulo_icms"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 201
        data = response.json()
        assert "tracking_id" in data
        assert isinstance(data["tracking_id"], str)
        assert len(data["tracking_id"]) > 0

    # ========== Testes de Edge Cases ==========
    
    def test_payload_multiplos_campos_ausentes(self):
        """
        Teste de robustez: Quando múltiplos campos estão ausentes,
        a API deve rejeitar com mensagem clara.
        """
        payload = {
            # Apenas "valor" presente
            "valor": 100
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "tracking_id" not in response.json()
    
    def test_payload_vazio(self):
        """
        Teste de robustez: Payload completamente vazio deve ser rejeitado.
        """
        payload = {}
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 400
        assert "tracking_id" not in response.json()
    
    def test_payload_com_campos_extras(self):
        """
        DN2.5: A API deve ignorar campos extras e processar normalmente.
        
        Regra: O contrato da API define campos obrigatórios, campos extras
        não devem invalidar a requisição.
        """
        payload = {
            "sessao_cliente": "cliente_001",
            "valor": 1000.00,
            "destino": "modulo_icms",
            "campo_extra_1": "valor_irrelevante",
            "campo_extra_2": 12345
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 201
        assert "tracking_id" in response.json()


class TestDN2ContractValidation:
    """
    Testes para garantir que o contrato da API não foi alterado.
    
    Requisito: "Não alterar o contrato da API (endpoint, headers ou estrutura de resposta)"
    """
    
    def test_endpoint_existe_e_retorna_201_valido(self):
        """Validar que POST /api/v1/auditar existe e retorna 201 para payload válido."""
        payload = {
            "sessao_cliente": "test",
            "valor": 100,
            "destino": "test"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 201
    
    def test_headers_obrigatorios_ainda_sao_validados(self):
        """Validar que headers account_key e app_key ainda são obrigatórios."""
        payload = {
            "sessao_cliente": "test",
            "valor": 100,
            "destino": "test"
        }
        
        # Requisição sem headers
        response = client.post("/api/v1/auditar", json=payload)
        
        assert response.status_code == 422  # Validation Error (FastAPI default)
    
    def test_estrutura_resposta_completa(self):
        """Validar que a estrutura de resposta contém todos os campos esperados."""
        payload = {
            "sessao_cliente": "teste_contrato",
            "valor": 5000.00,
            "destino": "modulo_test"
        }
        
        response = client.post(
            "/api/v1/auditar",
            json=payload,
            headers=HEADERS_VALIDOS
        )
        
        assert response.status_code == 201
        data = response.json()
        
        # Campos que devem estar presentes (contrato da API)
        required_fields = ["id", "status", "tracking_id", "arquivold", "diagnostico", "detalhes"]
        for field in required_fields:
            assert field in data, f"Campo obrigatório '{field}' ausente na resposta"
        
        # Campos dentro de "detalhes"
        detalhes_fields = ["cliente", "volume_processado", "modulo"]
        for field in detalhes_fields:
            assert field in data["detalhes"], f"Campo obrigatório 'detalhes.{field}' ausente"


if __name__ == "__main__":
    # Executar testes com: pytest src/tests/blue_team/validation.py -v
    pytest.main([__file__, "-v"])
