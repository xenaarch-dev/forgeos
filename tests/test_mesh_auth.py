"""
TDD: mesh auth, CORS and rate limiting — Phase 5 of SPEC_AgentMesh.md §6.

No network. Supabase JWT verification is exercised against a locally
generated ES256 keypair standing in for the project's JWKS, so the real
verification path (signature, issuer, audience, expiry, algorithm) runs
end to end without reaching the internet.
"""

from __future__ import annotations

import dataclasses
import time
from unittest.mock import MagicMock, patch

import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import ec
from fastapi.testclient import TestClient

import api
from mesh import auth as mesh_auth
from mesh.auth import (
    RATE_LIMIT_PER_DAY,
    RATE_LIMIT_PER_MINUTE,
    STREAM_TOKEN_TTL_SECONDS,
    AuthError,
    RateLimiter,
    issue_stream_token,
    verify_bearer,
    verify_stream_token,
)
from mesh.registry import CapabilityRegistry

SUPABASE_URL = "https://vcjicrqfnwdegggkrlpd.supabase.co"
USER_ID = "11111111-2222-3333-4444-555555555555"


# ---------------------------------------------------------------------------
# ES256 keypair standing in for the project's JWKS
# ---------------------------------------------------------------------------


@pytest.fixture(scope="module")
def keypair():
    key = ec.generate_private_key(ec.SECP256R1())
    return key, key.public_key()


def _make_token(private_key, **overrides) -> str:
    now = int(time.time())
    claims = {
        "sub": USER_ID,
        "aud": "authenticated",
        "iss": f"{SUPABASE_URL}/auth/v1",
        "iat": now,
        "exp": now + 3600,
        "role": "authenticated",
    }
    claims.update(overrides)
    return jwt.encode(claims, private_key, algorithm="ES256")


@pytest.fixture(autouse=True)
def base_env(monkeypatch):
    monkeypatch.setenv("SUPABASE_URL", SUPABASE_URL)
    monkeypatch.setenv("MESH_STREAM_SECRET", "test-secret-not-a-real-one")
    monkeypatch.delenv("MESH_REQUIRE_AUTH", raising=False)
    mesh_auth.reset_jwks_cache()
    mesh_auth._used_tokens.clear()
    yield
    mesh_auth.reset_jwks_cache()
    mesh_auth._used_tokens.clear()


@pytest.fixture
def jwks(monkeypatch, keypair):
    """Point the verifier at the local public key instead of the network."""
    _, public_key = keypair
    signing_key = MagicMock()
    signing_key.key = public_key
    client = MagicMock()
    client.get_signing_key_from_jwt.return_value = signing_key
    monkeypatch.setattr(mesh_auth, "_jwks", lambda: client)
    return client


# ---------------------------------------------------------------------------
# §6c — Supabase JWT
# ---------------------------------------------------------------------------


class TestVerifyBearer:
    def test_valid_token_returns_claims(self, jwks, keypair):
        private, _ = keypair
        claims = verify_bearer(f"Bearer {_make_token(private)}")
        assert claims["sub"] == USER_ID

    def test_missing_header_is_401(self):
        with pytest.raises(AuthError) as e:
            verify_bearer(None)
        assert e.value.status == 401

    def test_non_bearer_scheme_rejected(self):
        with pytest.raises(AuthError):
            verify_bearer("Basic abc123")

    def test_empty_token_rejected(self):
        with pytest.raises(AuthError):
            verify_bearer("Bearer    ")

    def test_expired_token_rejected(self, jwks, keypair):
        private, _ = keypair
        stale = _make_token(private, exp=int(time.time()) - 60)
        with pytest.raises(AuthError, match="expired"):
            verify_bearer(f"Bearer {stale}")

    def test_wrong_issuer_rejected(self, jwks, keypair):
        private, _ = keypair
        token = _make_token(private, iss="https://evil.supabase.co/auth/v1")
        with pytest.raises(AuthError):
            verify_bearer(f"Bearer {token}")

    def test_wrong_audience_rejected(self, jwks, keypair):
        private, _ = keypair
        with pytest.raises(AuthError):
            verify_bearer(f"Bearer {_make_token(private, aud='anon')}")

    def test_token_signed_by_another_key_rejected(self, jwks):
        other = ec.generate_private_key(ec.SECP256R1())
        with pytest.raises(AuthError):
            verify_bearer(f"Bearer {_make_token(other)}")

    def test_garbage_token_rejected(self, jwks):
        with pytest.raises(AuthError):
            verify_bearer("Bearer not-a-jwt")

    def test_unsigned_alg_none_token_rejected(self, jwks):
        """alg=none is the classic JWT bypass; it must never verify."""
        forged = jwt.encode({"sub": USER_ID, "aud": "authenticated"}, None, algorithm="none")
        with pytest.raises(AuthError):
            verify_bearer(f"Bearer {forged}")


# ---------------------------------------------------------------------------
# §6c — one-time stream token
# ---------------------------------------------------------------------------


class TestStreamToken:
    def test_round_trip_returns_the_user(self):
        token = issue_stream_token("cmd123", USER_ID)
        assert verify_stream_token(token, "cmd123") == USER_ID

    def test_ttl_is_five_minutes(self):
        assert STREAM_TOKEN_TTL_SECONDS == 300

    def test_expired_token_rejected(self):
        token = issue_stream_token("cmd123", USER_ID, now=time.time() - 400)
        with pytest.raises(AuthError, match="expired"):
            verify_stream_token(token, "cmd123")

    def test_still_valid_just_inside_the_window(self):
        token = issue_stream_token("cmd123", USER_ID, now=time.time() - 290)
        assert verify_stream_token(token, "cmd123") == USER_ID

    def test_scoped_to_one_command(self):
        token = issue_stream_token("cmd123", USER_ID)
        with pytest.raises(AuthError) as e:
            verify_stream_token(token, "cmd999")
        assert e.value.status == 403

    def test_single_use(self):
        token = issue_stream_token("cmd123", USER_ID)
        assert verify_stream_token(token, "cmd123") == USER_ID
        with pytest.raises(AuthError, match="already used"):
            verify_stream_token(token, "cmd123")

    def test_tampered_payload_rejected(self):
        token = issue_stream_token("cmd123", USER_ID)
        payload, sig = token.split(".", 1)
        forged = payload[:-2] + ("AA" if not payload.endswith("AA") else "BB")
        with pytest.raises(AuthError, match="signature"):
            verify_stream_token(f"{forged}.{sig}", "cmd123")

    def test_token_from_a_different_secret_rejected(self, monkeypatch):
        token = issue_stream_token("cmd123", USER_ID)
        monkeypatch.setenv("MESH_STREAM_SECRET", "a-completely-different-secret")
        with pytest.raises(AuthError, match="signature"):
            verify_stream_token(token, "cmd123")

    def test_missing_token_rejected(self):
        with pytest.raises(AuthError):
            verify_stream_token(None, "cmd123")

    def test_malformed_token_rejected(self):
        with pytest.raises(AuthError):
            verify_stream_token("no-dot-here", "cmd123")

    def test_secret_is_required(self, monkeypatch):
        monkeypatch.delenv("MESH_STREAM_SECRET", raising=False)
        with pytest.raises(AuthError) as e:
            issue_stream_token("cmd123", USER_ID)
        assert e.value.status == 500


# ---------------------------------------------------------------------------
# §6e — rate limiting
# ---------------------------------------------------------------------------


class TestRateLimiter:
    def test_spec_limits(self):
        assert RATE_LIMIT_PER_MINUTE == 10
        assert RATE_LIMIT_PER_DAY == 100

    def test_allows_up_to_the_minute_limit(self):
        limiter = RateLimiter()
        for _ in range(RATE_LIMIT_PER_MINUTE):
            limiter.check("u1")

    def test_blocks_past_the_minute_limit_with_429(self):
        limiter = RateLimiter()
        for _ in range(RATE_LIMIT_PER_MINUTE):
            limiter.check("u1")
        with pytest.raises(AuthError) as e:
            limiter.check("u1")
        assert e.value.status == 429
        assert "per minute" in e.value.detail

    def test_message_is_renderable_in_a_transcript(self):
        limiter = RateLimiter(per_minute=1)
        limiter.check("u1")
        with pytest.raises(AuthError) as e:
            limiter.check("u1")
        assert e.value.detail.strip()
        assert "\n" not in e.value.detail

    def test_window_slides(self):
        limiter = RateLimiter()
        base = time.time()
        for i in range(RATE_LIMIT_PER_MINUTE):
            limiter.check("u1", now=base + i * 0.1)
        limiter.check("u1", now=base + 61)

    def test_daily_limit_enforced(self):
        limiter = RateLimiter(per_minute=10_000, per_day=RATE_LIMIT_PER_DAY)
        base = time.time()
        for i in range(RATE_LIMIT_PER_DAY):
            limiter.check("u1", now=base + i)
        with pytest.raises(AuthError) as e:
            limiter.check("u1", now=base + RATE_LIMIT_PER_DAY)
        assert "per day" in e.value.detail

    def test_limits_are_per_user(self):
        limiter = RateLimiter()
        for _ in range(RATE_LIMIT_PER_MINUTE):
            limiter.check("u1")
        limiter.check("u2")


# ---------------------------------------------------------------------------
# Over HTTP
# ---------------------------------------------------------------------------


@pytest.fixture
def client(monkeypatch, tmp_path):
    api._commands.clear()
    api._rate_limiter.reset()
    monkeypatch.setattr(
        api, "RUNTIME", dataclasses.replace(api.RUNTIME, workdir_root=str(tmp_path))
    )
    monkeypatch.setattr(api, "default_registry", lambda: CapabilityRegistry())
    disabled = MagicMock()
    disabled.enabled = False
    disabled.get_thread.return_value = None
    monkeypatch.setattr(api, "_store", disabled)
    with TestClient(api.app) as c:
        c.timeout = 10.0
        yield c
    api._commands.clear()


class TestAuthEnforcedOverHttp:
    @pytest.fixture(autouse=True)
    def require_auth(self, monkeypatch):
        monkeypatch.setenv("MESH_REQUIRE_AUTH", "true")

    def test_post_command_without_a_token_is_401(self, client):
        r = client.post("/command", json={"text": "RUN MORNING METRICS"})
        assert r.status_code == 401
        assert "detail" in r.json()

    def test_get_command_without_a_token_is_401(self, client):
        assert client.get("/command/abc123def456").status_code == 401

    def test_bad_token_is_401(self, client):
        r = client.post(
            "/command",
            json={"text": "RUN MORNING METRICS"},
            headers={"Authorization": "Bearer garbage"},
        )
        assert r.status_code == 401

    def test_valid_token_is_accepted(self, client, jwks, keypair):
        private, _ = keypair
        r = client.post(
            "/command",
            json={"text": "RUN MORNING METRICS"},
            headers={"Authorization": f"Bearer {_make_token(private)}"},
        )
        assert r.status_code == 201
        assert r.json()["route"]["capability"] == "unsupported"

    def test_stream_token_is_issued_for_dispatched_commands(
        self, client, jwks, keypair, monkeypatch
    ):
        from mesh.models import Capability
        from tests.test_mesh_api import _StubCapability

        reg = CapabilityRegistry()
        reg.register(Capability.CONTRACT, _StubCapability)
        monkeypatch.setattr(api, "default_registry", lambda: reg)

        private, _ = keypair
        body = client.post(
            "/command",
            json={"text": "GENERATE NDA"},
            headers={"Authorization": f"Bearer {_make_token(private)}"},
        ).json()
        assert body["dispatched"] is True
        assert body["stream_token"]

    def test_stream_without_a_token_is_401(self, client):
        assert client.get("/command/abc123def456/stream").status_code == 401

    def test_stream_with_a_bad_token_is_401(self, client):
        r = client.get("/command/abc123def456/stream?t=nonsense")
        assert r.status_code == 401

    def test_healthz_stays_public(self, client):
        assert client.get("/healthz").status_code == 200

    def test_rate_limit_returns_429(self, client, jwks, keypair):
        private, _ = keypair
        headers = {"Authorization": f"Bearer {_make_token(private)}"}
        codes = [
            client.post("/command", json={"text": "RUN MORNING METRICS"}, headers=headers).status_code
            for _ in range(RATE_LIMIT_PER_MINUTE + 2)
        ]
        assert codes.count(201) == RATE_LIMIT_PER_MINUTE
        assert 429 in codes

    def test_rate_limit_body_is_renderable(self, client, jwks, keypair):
        private, _ = keypair
        headers = {"Authorization": f"Bearer {_make_token(private)}"}
        last = None
        for _ in range(RATE_LIMIT_PER_MINUTE + 1):
            last = client.post("/command", json={"text": "RUN MORNING METRICS"}, headers=headers)
        assert last.status_code == 429
        assert "per minute" in last.json()["detail"]


class TestOpenModeForLocalDevelopment:
    def test_no_token_needed_when_auth_is_off(self, client):
        r = client.post("/command", json={"text": "RUN MORNING METRICS"})
        assert r.status_code == 201

    def test_no_stream_token_minted_in_open_mode(self, client, monkeypatch):
        from mesh.models import Capability
        from tests.test_mesh_api import _StubCapability

        reg = CapabilityRegistry()
        reg.register(Capability.CONTRACT, _StubCapability)
        monkeypatch.setattr(api, "default_registry", lambda: reg)
        body = client.post("/command", json={"text": "GENERATE NDA"}).json()
        assert body["dispatched"] is True
        assert body["stream_token"] is None


# ---------------------------------------------------------------------------
# §6d — CORS allowlist
# ---------------------------------------------------------------------------


class TestCorsAllowlist:
    def _preflight(self, client, origin: str):
        return client.options(
            "/command",
            headers={
                "Origin": origin,
                "Access-Control-Request-Method": "POST",
                "Access-Control-Request-Headers": "authorization,content-type",
            },
        )

    @pytest.mark.parametrize(
        "origin",
        [
            "https://forgeos-eight.vercel.app",
            "http://localhost:3000",
            "https://forgeos-git-feature-branch.vercel.app",
            "https://forgeos-abc123.vercel.app",
        ],
    )
    def test_allowed_origins_get_the_header(self, client, origin):
        r = self._preflight(client, origin)
        assert r.headers.get("access-control-allow-origin") == origin

    @pytest.mark.parametrize(
        "origin",
        [
            "https://evil.example.com",
            "https://forgeos-eight.vercel.app.evil.com",
            "http://forgeos-eight.vercel.app",
            "https://notforgeos-abc.vercel.app",
        ],
    )
    def test_disallowed_origins_get_no_header(self, client, origin):
        r = self._preflight(client, origin)
        assert "access-control-allow-origin" not in {k.lower() for k in r.headers}

    def test_never_a_wildcard(self):
        assert "*" not in api._ALLOWED_ORIGINS

    def test_credentials_are_allowed(self, client):
        r = self._preflight(client, "https://forgeos-eight.vercel.app")
        assert r.headers.get("access-control-allow-credentials") == "true"

    def test_only_the_exposed_methods(self):
        assert set(api._ALLOWED_METHODS) == {"GET", "POST", "OPTIONS"}


# ---------------------------------------------------------------------------
# Deployment configuration
# ---------------------------------------------------------------------------


class TestRequirementsFile:
    @pytest.fixture(scope="class")
    def reqs(self) -> str:
        from pathlib import Path

        return (Path(api.__file__).parent / "requirements.txt").read_text()

    @pytest.mark.parametrize(
        "pkg", ["fastapi", "uvicorn", "pydantic", "httpx", "PyYAML", "supabase", "PyJWT"]
    )
    def test_runtime_dependency_present(self, reqs, pkg):
        assert pkg.lower() in reqs.lower()

    def test_cryptography_present_for_es256(self, reqs):
        """PyJWT cannot verify ES256 without it."""
        assert "cryptography" in reqs.lower()


class TestRenderClientSupportsThePaidSingaporeService:
    def test_defaults_unchanged_for_existing_callers(self):
        import inspect

        from tools.render import RenderClient

        sig = inspect.signature(RenderClient.create_web_service)
        assert sig.parameters["plan"].default == "free"
        assert sig.parameters["region"].default == "oregon"
        assert sig.parameters["root_dir"].default == "backend"

    def test_plan_region_health_and_env_vars_are_settable(self):
        import inspect

        from tools.render import RenderClient

        params = inspect.signature(RenderClient.create_web_service).parameters
        for name in ("plan", "region", "env_vars", "health_check_path"):
            assert name in params

    def test_env_vars_are_sent_in_render_shape(self):
        from tools.render import RenderClient

        with patch("tools.render.http_request", return_value={}) as req:
            RenderClient(api_key="k", owner_id="o").create_web_service(
                name="svc",
                repo_url="https://github.com/x/y",
                plan="starter",
                region="singapore",
                root_dir=".",
                env_vars={"B": "2", "A": "1"},
                health_check_path="/healthz",
            )
        body = req.call_args.kwargs["json_body"]
        assert body["envVars"] == [{"key": "A", "value": "1"}, {"key": "B", "value": "2"}]
        assert body["serviceDetails"]["plan"] == "starter"
        assert body["serviceDetails"]["region"] == "singapore"
        assert body["serviceDetails"]["healthCheckPath"] == "/healthz"
