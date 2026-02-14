"""
Módulo de Não-Repúdio (Non-Repudiation) - DN4
Projeto ASIS TaxTech - Grupo 06

Este módulo implementa mecanismos criptográficos de não-repúdio para transações
de auditoria fiscal, garantindo que nenhuma das partes possa negar a realização
de uma transação. Subsidia as áreas de segurança e suporte aos clientes.

Mecanismos implementados:
- DN4.1: Assinatura digital via HMAC-SHA256
- DN4.2: Carimbo temporal imutável (ISO 8601)
- DN4.3: Cadeia de autenticação (hash do ator)
- DN4.4: Recibo digital completo
- DN4.5: Log de auditoria com cadeia de hash (hash chain)
- DN4.6: Alertas de violação de não-repúdio
"""

import hmac
import hashlib
import json
import threading
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


# Chave secreta para HMAC — em produção, viria de variável de ambiente
NR_SECRET_KEY = "ASIS_TAXTECH_G06_NR_SECRET_2026"

# Limiar de alerta: 30% acima do esperado (padrão DN1)
ALERTA_THRESHOLD = 0.30


# ---------------------------------------------------------------------------
# DN4.1 — Assinatura Digital (HMAC-SHA256)
# ---------------------------------------------------------------------------

def sign_transaction(payload: Dict[str, Any], timestamp: str, secret: str = NR_SECRET_KEY) -> str:
    """
    Gera uma assinatura HMAC-SHA256 sobre o payload serializado + timestamp.

    A assinatura vincula o conteúdo da transação ao momento em que foi processada,
    impedindo adulteração posterior (não-repúdio de conteúdo).

    Args:
        payload: Dicionário com os dados da transação fiscal.
        timestamp: Carimbo temporal ISO 8601 da transação.
        secret: Chave secreta HMAC.

    Returns:
        String hexadecimal da assinatura HMAC-SHA256.
    """
    # Serialização determinística (sort_keys garante ordem consistente)
    message = json.dumps(payload, sort_keys=True, ensure_ascii=False) + "|" + timestamp
    return hmac.new(
        secret.encode("utf-8"),
        message.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()


def verify_signature(payload: Dict[str, Any], timestamp: str, signature: str, secret: str = NR_SECRET_KEY) -> bool:
    """
    Verifica se a assinatura HMAC-SHA256 corresponde ao payload + timestamp.

    Returns:
        True se a assinatura é válida, False caso contrário.
    """
    expected = sign_transaction(payload, timestamp, secret)
    return hmac.compare_digest(expected, signature)


# ---------------------------------------------------------------------------
# DN4.2 — Carimbo Temporal Imutável
# ---------------------------------------------------------------------------

def generate_timestamp() -> str:
    """
    Gera um carimbo temporal ISO 8601 em UTC (server-side).

    O timestamp é gerado exclusivamente pelo servidor para impedir que o
    cliente manipule o momento registrado da transação.

    Returns:
        String ISO 8601 com timezone UTC (ex: '2026-02-12T12:00:00.123456+00:00').
    """
    return datetime.now(timezone.utc).isoformat()


# ---------------------------------------------------------------------------
# DN4.3 — Cadeia de Autenticação
# ---------------------------------------------------------------------------

def hash_actor(account_key: str) -> str:
    """
    Gera um hash SHA-256 da account-key do ator autenticado.

    Registra a identidade do ator de forma irreversível, vinculando a transação
    a uma conta específica sem expor a chave original.

    Args:
        account_key: Chave de conta do ator autenticado.

    Returns:
        String hexadecimal do hash SHA-256 da account-key.
    """
    return hashlib.sha256(account_key.encode("utf-8")).hexdigest()


# ---------------------------------------------------------------------------
# DN4.4 — Recibo Digital
# ---------------------------------------------------------------------------

def hash_payload(payload: Dict[str, Any]) -> str:
    """
    Gera um hash SHA-256 do payload da transação.

    Returns:
        String hexadecimal do hash do payload.
    """
    serialized = json.dumps(payload, sort_keys=True, ensure_ascii=False)
    return hashlib.sha256(serialized.encode("utf-8")).hexdigest()


def build_receipt(
    signature: str,
    timestamp: str,
    actor: str,
    tracking_id: str,
    payload: Dict[str, Any]
) -> Dict[str, str]:
    """
    Constrói o recibo digital completo de não-repúdio.

    O recibo contém todas as evidências criptográficas necessárias para provar
    que a transação ocorreu, por quem, quando, e com qual conteúdo.

    Args:
        signature: Assinatura HMAC-SHA256 da transação.
        timestamp: Carimbo temporal ISO 8601.
        actor: Hash SHA-256 do ator autenticado.
        tracking_id: ID de rastreio da transação.
        payload: Dados originais da transação.

    Returns:
        Dicionário com todos os campos do recibo digital.
    """
    return {
        "signature": signature,
        "timestamp": timestamp,
        "actor": actor,
        "tracking_id": tracking_id,
        "payload_hash": hash_payload(payload)
    }


# ---------------------------------------------------------------------------
# DN4.5 — Log de Auditoria com Cadeia de Hash
# ---------------------------------------------------------------------------

class AuditLog:
    """
    Log de auditoria imutável com cadeia de hash (hash chain).

    Cada entrada referencia o hash da entrada anterior, formando uma corrente
    criptográfica que impede a adulteração retroativa de registros.

    Thread-safe para uso em ambiente assíncrono (FastAPI).
    """

    def __init__(self):
        self._log: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def append(self, receipt: Dict[str, str]) -> Dict[str, Any]:
        """
        Adiciona uma entrada ao log de auditoria com encadeamento de hash.

        Args:
            receipt: Recibo digital da transação (DN4.4).

        Returns:
            Entrada completa do log incluindo posição e hash de encadeamento.
        """
        with self._lock:
            position = len(self._log)
            prev_hash = self._log[-1]["entry_hash"] if self._log else "GENESIS"

            # Conteúdo da entrada: recibo + metadados de encadeamento
            entry_content = json.dumps(receipt, sort_keys=True) + "|" + prev_hash
            entry_hash = hashlib.sha256(entry_content.encode("utf-8")).hexdigest()

            entry = {
                "position": position,
                "prev_hash": prev_hash,
                "entry_hash": entry_hash,
                "receipt": receipt,
            }

            self._log.append(entry)
            return entry

    def verify_chain(self) -> bool:
        """
        Verifica a integridade da cadeia de hash do log completo.

        Returns:
            True se toda a cadeia é íntegra, False se houve adulteração.
        """
        with self._lock:
            for i, entry in enumerate(self._log):
                # Verificar prev_hash
                expected_prev = self._log[i - 1]["entry_hash"] if i > 0 else "GENESIS"
                if entry["prev_hash"] != expected_prev:
                    return False

                # Verificar entry_hash
                entry_content = json.dumps(entry["receipt"], sort_keys=True) + "|" + entry["prev_hash"]
                expected_hash = hashlib.sha256(entry_content.encode("utf-8")).hexdigest()
                if entry["entry_hash"] != expected_hash:
                    return False

            return True

    def get_log(self) -> List[Dict[str, Any]]:
        """Retorna cópia do log de auditoria completo."""
        with self._lock:
            return list(self._log)

    def get_entry(self, position: int) -> Optional[Dict[str, Any]]:
        """Retorna uma entrada específica do log pelo índice."""
        with self._lock:
            if 0 <= position < len(self._log):
                return self._log[position]
            return None

    def size(self) -> int:
        """Retorna o número de entradas no log."""
        with self._lock:
            return len(self._log)

    def clear(self):
        """Limpa o log (apenas para testes)."""
        with self._lock:
            self._log.clear()


# Instância global do log de auditoria (singleton para o ciclo de vida da API)
audit_log = AuditLog()


# ---------------------------------------------------------------------------
# DN4.6 — Alertas de Violação de Não-Repúdio
# ---------------------------------------------------------------------------

def check_alert(receipt: Optional[Dict[str, str]]) -> Optional[str]:
    """
    Verifica se o recibo digital possui todos os campos obrigatórios de não-repúdio.

    Emite alerta quando campos essenciais estão ausentes ou vazios, indicando
    possível falha nos mecanismos de não-repúdio.

    Args:
        receipt: Recibo digital da transação ou None.

    Returns:
        Mensagem de alerta se houver violação, None se tudo estiver correto.
    """
    if receipt is None:
        return "ALERTA NÃO-REPÚDIO: Recibo digital ausente — transação sem evidência criptográfica"

    required_fields = ["signature", "timestamp", "actor", "tracking_id", "payload_hash"]
    missing = [f for f in required_fields if not receipt.get(f)]

    if missing:
        return f"ALERTA NÃO-REPÚDIO: Campos ausentes no recibo: {', '.join(missing)}"

    return None


def check_chain_alert(log: AuditLog) -> Optional[str]:
    """
    Verifica a integridade da cadeia de hash do log de auditoria.

    Emite alerta quando a cadeia está quebrada, indicando possível adulteração.

    Args:
        log: Instância do AuditLog.

    Returns:
        Mensagem de alerta se a cadeia estiver comprometida, None se íntegra.
    """
    if not log.verify_chain():
        return "ALERTA NÃO-REPÚDIO: Cadeia de hash do log de auditoria comprometida — possível adulteração detectada"
    return None
