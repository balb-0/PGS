import os
import hashlib
import threading
import time
from typing import Dict, Any, Optional

import httpx
from fastapi import HTTPException
from jose import jwt, JWTError
from jose.exceptions import ExpiredSignatureError


# =============================================================================
# INT3 — Clerk Identity Provider (OpenID Connect / OAuth 2.0)
# Garante isolamento de contas (DN4) e conformidade LGPD.
# =============================================================================

# Variáveis de ambiente para configuração do Clerk
CLERK_PUBLISHABLE_KEY = os.getenv("CLERK_PUBLISHABLE_KEY", "")
CLERK_SECRET_KEY = os.getenv("CLERK_SECRET_KEY", "")
CLERK_JWKS_URL = os.getenv(
    "CLERK_JWKS_URL",
    "https://clerk.accounts.dev/.well-known/jwks.json",
)

# Algoritmos aceitos pelo Clerk (RS256 é o padrão)
CLERK_ALGORITHMS = ["RS256"]

# TTL do cache de JWKS em segundos (1 hora)
JWKS_CACHE_TTL = 3600.0


# =============================================================================
# INT3.1 — Cache de JWKS (JSON Web Key Set)
# Minimiza chamadas externas e garante SLA de latência (DN1/RNF3).
# =============================================================================

class JWKSCache:
    """
    Cache thread-safe das chaves públicas do Clerk (JWKS).

    Revalida automaticamente o cache após JWKS_CACHE_TTL segundos,
    evitando chamadas externas desnecessárias e mantendo a latência
    dentro do SLA de 500ms (DN1/RNF3).
    """

    def __init__(self, jwks_url: str, ttl: float = JWKS_CACHE_TTL):
        self._jwks_url = jwks_url
        self._ttl = ttl
        self._keys: Optional[Dict[str, Any]] = None
        self._last_fetch: float = 0.0
        self._lock = threading.Lock()

    def _is_stale(self) -> bool:
        return self._keys is None or (time.time() - self._last_fetch) > self._ttl

    def get_keys(self) -> Dict[str, Any]:
        """
        Retorna as chaves JWKS do Clerk, buscando remotamente se necessário.

        Raises:
            HTTPException 503: quando não for possível obter as chaves.
        """
        with self._lock:
            if self._is_stale():
                self._fetch()
            return self._keys  # type: ignore[return-value]

    def _fetch(self) -> None:
        """Busca as chaves JWKS do endpoint público do Clerk."""
        try:
            response = httpx.get(self._jwks_url, timeout=5.0)
            response.raise_for_status()
            self._keys = response.json()
            self._last_fetch = time.time()
        except Exception as exc:
            raise HTTPException(
                status_code=503,
                detail=f"INT3: Falha ao obter chaves JWKS do Clerk: {exc}",
            )

    def invalidate(self) -> None:
        """Invalida o cache (usado em testes e rotação de chaves)."""
        with self._lock:
            self._keys = None
            self._last_fetch = 0.0


# Instância global do cache de JWKS (singleton)
_jwks_cache = JWKSCache(CLERK_JWKS_URL)


# =============================================================================
# INT3.2 — Validação de Token JWT Clerk
# =============================================================================

def verify_clerk_token(token: str) -> Dict[str, Any]:
    """
    INT3 — Valida um Bearer token JWT emitido pelo Clerk.

    Verifica assinatura (RS256), expiração e extrai claims relevantes.
    Garante que apenas tokens legítimos do IDP configurado são aceitos.

    Args:
        token: Token JWT no formato Bearer (sem o prefixo 'Bearer ').

    Returns:
        Dicionário com os claims do JWT: sub, org_id, email, metadata.

    Raises:
        HTTPException 401: token ausente, expirado ou com assinatura inválida.
    """
    if not token:
        raise HTTPException(
            status_code=401,
            detail="INT3: Token de autenticação ausente",
        )

    jwks = _jwks_cache.get_keys()

    try:
        payload = jwt.decode(
            token,
            jwks,
            algorithms=CLERK_ALGORITHMS,
            options={"verify_aud": False},
        )
    except ExpiredSignatureError:
        raise HTTPException(
            status_code=401,
            detail="INT3: Token JWT expirado",
        )
    except JWTError as exc:
        raise HTTPException(
            status_code=401,
            detail=f"INT3: Token JWT inválido — {exc}",
        )

    return payload


# =============================================================================
# INT3.3 — Extração e Normalização de Claims Clerk
# Pseudonimização conforme LGPD: dados sensíveis são hasheados (SHA-256).
# =============================================================================

def extract_clerk_identity(claims: Dict[str, Any]) -> Dict[str, Any]:
    """
    INT3 — Extrai e normaliza a identidade do usuário a partir dos claims JWT.

    Aplica pseudonimização conforme LGPD:
    - user_id (`sub`) e org_id são hasheados para geração do `actor`
    - Email não é armazenado em logs de auditoria
    - Apenas identificadores hasheados são persistidos

    Args:
        claims: Payload decodificado do JWT Clerk.

    Returns:
        Dicionário normalizado com identidade do usuário:
        {
            "auth_type": "clerk",
            "user_id": str (sub do JWT),
            "org_id": str (organização Clerk ou "default"),
            "actor": str (SHA-256 de user_id + org_id — para DN4/não-repúdio),
            "tenant_id": str (equivalente a org_id para isolamento DN4),
            "email_hash": str (SHA-256 do email, se presente),
        }
    """
    user_id: str = claims.get("sub", "")
    org_id: str = claims.get("org_id", "") or claims.get("azp", "") or "default"
    email: str = claims.get("email", "") or ""

    # DN4: actor gerado como hash irreversível (user_id + org_id)
    # Garante rastreabilidade sem expor identificadores originais (LGPD)
    actor = hashlib.sha256(f"{user_id}:{org_id}".encode("utf-8")).hexdigest()
    email_hash = hashlib.sha256(email.encode("utf-8")).hexdigest() if email else ""

    return {
        "auth_type": "clerk",
        "user_id": user_id,
        "org_id": org_id,
        "actor": actor,
        "tenant_id": org_id,
        "email_hash": email_hash,
    }


def hash_clerk_actor(user_id: str, org_id: str) -> str:
    """
    INT3/DN4 — Gera o hash do ator para uso no recibo digital de não-repúdio.

    Equivalente ao `hash_actor(account_key)` para autenticação via API key,
    porém derivado da identidade Clerk (user_id + org_id).

    Args:
        user_id: Identificador único do usuário no Clerk (claim `sub`).
        org_id: Identificador da organização no Clerk (claim `org_id`).

    Returns:
        String hexadecimal SHA-256 do ator Clerk.
    """
    return hashlib.sha256(f"{user_id}:{org_id}".encode("utf-8")).hexdigest()


# =============================================================================
# INT3.4 — Utilitário de Injeção para Testes
# Permite substituir o cache de JWKS em testes sem chamadas de rede.
# =============================================================================

def get_jwks_cache() -> JWKSCache:
    """Retorna a instância global do cache de JWKS (para injeção em testes)."""
    return _jwks_cache


def override_jwks_cache(cache: JWKSCache) -> None:
    """
    Substitui a instância global do cache de JWKS.
    Usado exclusivamente em testes para evitar chamadas de rede reais.
    """
    global _jwks_cache
    _jwks_cache = cache
