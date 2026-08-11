"""
Request admission for the mesh HTTP surface — SPEC_AgentMesh.md §6c and §6e.

Three concerns, all about whether a request is allowed to proceed:

  verify_bearer()        Supabase user JWT, verified against the project's
                         JWKS — the same identity web/middleware.ts trusts.
  issue/verify_stream_token()
                         A one-time, 5-minute, single-command token for
                         EventSource, which cannot send an Authorization
                         header. §6c left the signing mechanism open; the
                         choice made here is HMAC-SHA256 (see below).
  RateLimiter            10 commands/minute, 100/day per user (§6e), enforced
                         here because the UI is not a trust boundary.

Why HMAC and not a second JWT: the token is read only by the process that
minted it, so there is nothing to gain from asymmetric signing or from a
parseable standard envelope, and PyJWT's own defaults (no audience, no
issuer) would have to be tightened back up by hand. hmac + compare_digest is
~20 lines, has no key distribution story to get wrong, and matches the
signature-verification idiom this repo already generates in
agents/scaffold.py. The secret lives in MESH_STREAM_SECRET.

Auth is REQUIRED BY DEFAULT. Disabling it takes an explicit
MESH_ALLOW_UNAUTH=true, which is for localhost development only. This is
deliberately the opposite of api.py's older FORGEOS_API_KEY flag: a missing
or misspelled environment variable should fail closed, not quietly serve an
unauthenticated public endpoint.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import threading
import time
from typing import Any

#: §6c — signed, 5-minute TTL, scoped to one command_id and one user.
STREAM_TOKEN_TTL_SECONDS = 300

#: §6e
RATE_LIMIT_PER_MINUTE = 10
RATE_LIMIT_PER_DAY = 100

_AUDIENCE = "authenticated"


class AuthError(Exception):
    """Raised when a request must not proceed. Carries an HTTP status."""

    def __init__(self, detail: str, status: int = 401) -> None:
        super().__init__(detail)
        self.detail = detail
        self.status = status


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------


def auth_required() -> bool:
    """True unless auth has been explicitly waived for local development.

    Fails closed: anything other than an affirmative MESH_ALLOW_UNAUTH — unset,
    empty, misspelled, "false" — leaves Supabase JWT verification enforced.
    """
    return os.environ.get("MESH_ALLOW_UNAUTH", "").lower() not in {
        "1",
        "true",
        "yes",
        "on",
    }


def _supabase_url() -> str:
    return os.environ.get("SUPABASE_URL", "").rstrip("/")


def _stream_secret() -> str:
    secret = os.environ.get("MESH_STREAM_SECRET", "")
    if not secret:
        raise AuthError("MESH_STREAM_SECRET not configured", status=500)
    return secret


# ---------------------------------------------------------------------------
# Supabase JWT (§6c)
# ---------------------------------------------------------------------------

_jwks_lock = threading.Lock()
_jwks_client: Any = None


def _jwks() -> Any:
    """Cached PyJWKClient. It caches keys itself, so this is built once."""
    global _jwks_client
    with _jwks_lock:
        if _jwks_client is None:
            from jwt import PyJWKClient

            url = _supabase_url()
            if not url:
                raise AuthError("SUPABASE_URL not configured", status=500)
            _jwks_client = PyJWKClient(f"{url}/auth/v1/.well-known/jwks.json")
        return _jwks_client


def reset_jwks_cache() -> None:
    """Drop the cached client — used by tests, and after a key rotation."""
    global _jwks_client
    with _jwks_lock:
        _jwks_client = None


def verify_bearer(authorization: str | None) -> dict[str, Any]:
    """Verify an `Authorization: Bearer <supabase_access_token>` header.

    Returns the token claims. Raises AuthError on anything else.
    """
    if not authorization or not authorization.startswith("Bearer "):
        raise AuthError("Missing bearer token")
    token = authorization[7:].strip()
    if not token:
        raise AuthError("Missing bearer token")

    import jwt

    try:
        signing_key = _jwks().get_signing_key_from_jwt(token)
        return jwt.decode(
            token,
            signing_key.key,
            algorithms=["ES256", "RS256"],
            audience=_AUDIENCE,
            issuer=f"{_supabase_url()}/auth/v1",
            options={"require": ["exp", "sub"]},
        )
    except AuthError:
        raise
    except jwt.ExpiredSignatureError as exc:
        raise AuthError("Token expired") from exc
    except Exception as exc:
        raise AuthError(f"Invalid token: {type(exc).__name__}") from exc


def user_id_from_claims(claims: dict[str, Any]) -> str:
    user_id = str(claims.get("sub") or "")
    if not user_id:
        raise AuthError("Token has no subject")
    return user_id


# ---------------------------------------------------------------------------
# One-time stream token (§6c)
# ---------------------------------------------------------------------------


def _b64e(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode().rstrip("=")


def _b64d(text: str) -> bytes:
    return base64.urlsafe_b64decode(text + "=" * (-len(text) % 4))


def _sign(payload_b64: str) -> str:
    digest = hmac.new(
        _stream_secret().encode(), payload_b64.encode(), hashlib.sha256
    ).digest()
    return _b64e(digest)


def issue_stream_token(command_id: str, user_id: str, *, now: float | None = None) -> str:
    """Mint a token good for one command, one user, five minutes, one use."""
    issued = int(now if now is not None else time.time())
    payload = {
        "cid": command_id,
        "uid": user_id,
        "exp": issued + STREAM_TOKEN_TTL_SECONDS,
        "jti": secrets.token_urlsafe(8),
    }
    payload_b64 = _b64e(json.dumps(payload, separators=(",", ":")).encode())
    return f"{payload_b64}.{_sign(payload_b64)}"


class _UsedTokens:
    """Single-use enforcement. In-memory, so single-instance only (§6a)."""

    def __init__(self) -> None:
        self._seen: dict[str, float] = {}
        self._lock = threading.Lock()

    def claim(self, jti: str, expires_at: float) -> bool:
        """True the first time a jti is presented, False every time after."""
        now = time.time()
        with self._lock:
            for key, exp in [(k, v) for k, v in self._seen.items() if v < now]:
                self._seen.pop(key, None)
            if jti in self._seen:
                return False
            self._seen[jti] = expires_at
            return True

    def clear(self) -> None:
        with self._lock:
            self._seen.clear()


_used_tokens = _UsedTokens()


def verify_stream_token(
    token: str | None, command_id: str, *, now: float | None = None
) -> str:
    """Verify a `?t=` stream token. Returns the user id it was minted for."""
    if not token:
        raise AuthError("Missing stream token")

    try:
        payload_b64, signature = token.split(".", 1)
    except ValueError as exc:
        raise AuthError("Malformed stream token") from exc

    if not hmac.compare_digest(_sign(payload_b64), signature):
        raise AuthError("Bad stream token signature")

    try:
        payload = json.loads(_b64d(payload_b64))
    except Exception as exc:
        raise AuthError("Malformed stream token") from exc

    current = now if now is not None else time.time()
    if float(payload.get("exp", 0)) < current:
        raise AuthError("Stream token expired")
    if payload.get("cid") != command_id:
        raise AuthError("Stream token is for a different command", status=403)
    if not _used_tokens.claim(str(payload.get("jti", "")), float(payload["exp"])):
        raise AuthError("Stream token already used", status=403)

    return str(payload.get("uid", ""))


# ---------------------------------------------------------------------------
# Rate limiting (§6e)
# ---------------------------------------------------------------------------


class RateLimiter:
    """Per-user sliding windows. Server-side: the UI is not a trust boundary."""

    def __init__(
        self,
        per_minute: int = RATE_LIMIT_PER_MINUTE,
        per_day: int = RATE_LIMIT_PER_DAY,
    ) -> None:
        self.per_minute = per_minute
        self.per_day = per_day
        self._hits: dict[str, list[float]] = {}
        self._lock = threading.Lock()

    def check(self, user_id: str, *, now: float | None = None) -> None:
        """Record one command for this user, or raise AuthError(429)."""
        current = now if now is not None else time.time()
        with self._lock:
            hits = [t for t in self._hits.get(user_id, []) if current - t < 86_400]
            if len([t for t in hits if current - t < 60]) >= self.per_minute:
                raise AuthError(
                    f"Rate limit: {self.per_minute} commands per minute. "
                    "Wait a moment and try again.",
                    status=429,
                )
            if len(hits) >= self.per_day:
                raise AuthError(
                    f"Rate limit: {self.per_day} commands per day. "
                    "This resets 24 hours after your first command today.",
                    status=429,
                )
            hits.append(current)
            self._hits[user_id] = hits

    def reset(self) -> None:
        with self._lock:
            self._hits.clear()


__all__ = [
    "RATE_LIMIT_PER_DAY",
    "RATE_LIMIT_PER_MINUTE",
    "STREAM_TOKEN_TTL_SECONDS",
    "AuthError",
    "RateLimiter",
    "auth_required",
    "issue_stream_token",
    "reset_jwks_cache",
    "user_id_from_claims",
    "verify_bearer",
    "verify_stream_token",
]
