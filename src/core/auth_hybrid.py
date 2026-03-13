import hashlib
from typing import Dict, Any, Optional

from fastapi import Header, HTTPException

from core.auth_clerk import verify_clerk_token, extract_clerk_identity


# =============================================================================
# INT3 — Autenticação Híbrida: Clerk JWT + API Keys (account-key/app-key)
# Garante retrocompatibilidade com sistemas legados e suporte a novos
# clientes autenticados via Clerk OpenID Connect / OAuth 2.0.
# =============================================================================

# Importação circular evitada: VALID_CREDENTIAL_PAIRS e authenticate_request
# são importados localmente dentro de authenticate_hybrid para não criar
# dependência circular entre auth_hybrid.py e api.py.


def _build_api_key_identity(account_key: str) -> Dict[str, Any]:
    """
    INT3 — Constrói a identidade normalizada para autenticação via API key.

    Mapeia o sistema legado (account-key/app-key) para o formato unificado
    de identidade, garantindo que DN4 (não-repúdio) funcione de forma
    transparente independentemente do método de autenticação.

    Args:
        account_key: Chave de conta autenticada.

    Returns:
        Dicionário de identidade normalizado no formato unificado:
        {
            "auth_type": "api_key",
            "user_id": str (account_key),
            "org_id": str (derivado do account_key),
            "actor": str (SHA-256 do account_key — compatível com DN4),
            "tenant_id": str (account_key como tenant isolado),
            "email_hash": "",
        }
    """
    actor = hashlib.sha256(account_key.encode("utf-8")).hexdigest()
    return {
        "auth_type": "api_key",
        "user_id": account_key,
        "org_id": account_key,
        "actor": actor,
        "tenant_id": account_key,
        "email_hash": "",
    }


def authenticate_hybrid(
    authorization: Optional[str] = Header(default=None),
    account_key: Optional[str] = Header(default=None),
    app_key: Optional[str] = Header(default=None),
) -> Dict[str, Any]:
    """
    INT3 — Orquestrador de autenticação híbrida.

    Detecta automaticamente o método de autenticação pelo cabeçalho presente:
    - `Authorization: Bearer <token>` → Clerk JWT (OpenID Connect / OAuth 2.0)
    - `account-key` + `app-key` → API Keys legadas (retrocompatibilidade)

    Retorna identidade normalizada no formato unificado, garantindo que
    os demais componentes (DN4, rate limiter, histórico de transações)
    funcionem de forma transparente independentemente do método usado.

    Raises:
        HTTPException 401: nenhum método de autenticação fornecido.
        HTTPException 401/403: credenciais inválidas (delegado ao método detectado).
    """
    # Tenta autenticação via Clerk JWT (header Authorization: Bearer ...)
    if authorization and authorization.startswith("Bearer "):
        token = authorization.removeprefix("Bearer ").strip()
        claims = verify_clerk_token(token)
        return extract_clerk_identity(claims)

    # Tenta autenticação via API Keys legadas
    if account_key or app_key:
        # Importação local para evitar circularidade com api.py
        from core.api import VALID_CREDENTIAL_PAIRS

        if not account_key or not app_key:
            raise HTTPException(
                status_code=401,
                detail="INT3: Credenciais de autenticação ausentes (account-key e app-key obrigatórios)",
            )
        if (account_key, app_key) not in VALID_CREDENTIAL_PAIRS:
            raise HTTPException(
                status_code=403,
                detail="INT3: Credenciais inválidas",
            )
        return _build_api_key_identity(account_key)

    # Nenhum método detectado
    raise HTTPException(
        status_code=401,
        detail=(
            "INT3: Autenticação obrigatória. "
            "Forneça 'Authorization: Bearer <token>' (Clerk) "
            "ou os headers 'account-key' e 'app-key' (API Keys)."
        ),
    )
