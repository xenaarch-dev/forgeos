"""
ForgeOS — runtime configuration.

All secrets are loaded from environment variables. A `.env` file is loaded
at import time when present (no third-party dependency required).
Hard-coded fallbacks exist *only* for non-secret defaults like model names
and timeouts; never for credentials.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path


# ---------------------------------------------------------------------------
# .env loader (zero-dependency)
# ---------------------------------------------------------------------------


def _load_dotenv(path: str | os.PathLike[str] = ".env") -> None:
    p = Path(path)
    if not p.exists():
        return
    for raw in p.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, val = line.partition("=")
        key = key.strip()
        val = val.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = val


_load_dotenv()
_load_dotenv(Path(__file__).resolve().parent.parent / ".env")


def _get(name: str, default: str = "") -> str:
    return os.environ.get(name, default)


def _get_int(name: str, default: int) -> int:
    v = os.environ.get(name)
    try:
        return int(v) if v is not None else default
    except ValueError:
        return default


def _get_float(name: str, default: float) -> float:
    v = os.environ.get(name)
    try:
        return float(v) if v is not None else default
    except ValueError:
        return default


def _get_bool(name: str, default: bool) -> bool:
    v = os.environ.get(name)
    if v is None:
        return default
    return v.lower() in {"1", "true", "yes", "on"}


# ---------------------------------------------------------------------------
# LLM configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class LLMConfig:
    anthropic_api_key: str = field(default_factory=lambda: _get("ANTHROPIC_API_KEY"))
    anthropic_model: str = field(
        default_factory=lambda: _get("ANTHROPIC_MODEL", "claude-haiku-4-5")
    )
    openrouter_api_key: str = field(default_factory=lambda: _get("OPENROUTER_API_KEY"))
    openrouter_base_url: str = field(
        default_factory=lambda: _get(
            "OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1"
        )
    )
    deepseek_model: str = field(
        default_factory=lambda: _get("DEEPSEEK_MODEL", "deepseek/deepseek-chat")
    )
    ollama_base_url: str = field(
        default_factory=lambda: _get("OLLAMA_BASE_URL", "http://localhost:11434")
    )
    ollama_model: str = field(
        default_factory=lambda: _get("OLLAMA_MODEL", "qwen2.5-coder:latest")
    )
    request_timeout: float = field(default_factory=lambda: _get_float("LLM_TIMEOUT", 120.0))
    max_retries: int = field(default_factory=lambda: _get_int("LLM_MAX_RETRIES", 5))
    retry_initial_delay: float = field(
        default_factory=lambda: _get_float("LLM_RETRY_DELAY", 1.5)
    )


# ---------------------------------------------------------------------------
# Tool / API configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ToolConfig:
    github_token: str = field(default_factory=lambda: _get("GITHUB_TOKEN"))
    github_owner: str = field(default_factory=lambda: _get("GITHUB_OWNER"))
    github_api: str = field(
        default_factory=lambda: _get("GITHUB_API", "https://api.github.com")
    )

    railway_token: str = field(default_factory=lambda: _get("RAILWAY_TOKEN"))
    railway_api: str = field(
        default_factory=lambda: _get("RAILWAY_API", "https://backboard.railway.app/graphql/v2")
    )

    vercel_token: str = field(default_factory=lambda: _get("VERCEL_TOKEN"))
    vercel_api: str = field(
        default_factory=lambda: _get("VERCEL_API", "https://api.vercel.com")
    )
    vercel_team_id: str = field(default_factory=lambda: _get("VERCEL_TEAM_ID"))

    render_api_key: str = field(default_factory=lambda: _get("RENDER_API_KEY"))
    render_owner_id: str = field(default_factory=lambda: _get("RENDER_OWNER_ID"))

    supabase_access_token: str = field(default_factory=lambda: _get("SUPABASE_ACCESS_TOKEN"))
    supabase_project_ref: str = field(default_factory=lambda: _get("SUPABASE_PROJECT_REF"))
    supabase_api: str = field(
        default_factory=lambda: _get("SUPABASE_API", "https://api.supabase.com")
    )

    sentry_token: str = field(default_factory=lambda: _get("SENTRY_AUTH_TOKEN"))
    sentry_org: str = field(default_factory=lambda: _get("SENTRY_ORG"))
    sentry_api: str = field(
        default_factory=lambda: _get("SENTRY_API", "https://sentry.io/api/0")
    )

    uptimerobot_api_key: str = field(default_factory=lambda: _get("UPTIMEROBOT_API_KEY"))
    uptimerobot_api: str = field(
        default_factory=lambda: _get("UPTIMEROBOT_API", "https://api.uptimerobot.com/v2")
    )

    upstash_redis_url: str = field(default_factory=lambda: _get("UPSTASH_REDIS_URL"))
    upstash_redis_token: str = field(default_factory=lambda: _get("UPSTASH_REDIS_TOKEN"))

    # V3 additions
    e2b_api_key: str = field(default_factory=lambda: _get("E2B_API_KEY"))
    composio_api_key: str = field(default_factory=lambda: _get("COMPOSIO_API_KEY"))
    redis_url: str = field(default_factory=lambda: _get("REDIS_URL", "redis://localhost:6379"))
    supabase_url: str = field(default_factory=lambda: _get("SUPABASE_URL"))
    supabase_service_key: str = field(default_factory=lambda: _get("SUPABASE_SERVICE_KEY"))

    lemonsqueezy_api_key: str = field(default_factory=lambda: _get("LEMONSQUEEZY_API_KEY"))


# ---------------------------------------------------------------------------
# Runtime / orchestration configuration
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class RuntimeConfig:
    workdir_root: str = field(
        default_factory=lambda: _get("FORGEOS_WORKDIR", str(Path.cwd() / ".forgeos"))
    )
    obsidian_vault: str = field(
        default_factory=lambda: _get(
            "OBSIDIAN_VAULT",
            str(Path.home() / "ObsidianVault" / "ForgeOS"),
        )
    )
    log_level: str = field(default_factory=lambda: _get("FORGEOS_LOG_LEVEL", "INFO"))
    max_agent_retries: int = field(
        default_factory=lambda: _get_int("FORGEOS_MAX_AGENT_RETRIES", 3)
    )
    retry_backoff_base: float = field(
        default_factory=lambda: _get_float("FORGEOS_RETRY_BACKOFF", 2.0)
    )
    healer_sentry_interval: int = field(
        default_factory=lambda: _get_int("HEALER_SENTRY_INTERVAL", 300)
    )
    healer_uptime_interval: int = field(
        default_factory=lambda: _get_int("HEALER_UPTIME_INTERVAL", 60)
    )
    enable_obsidian: bool = field(
        default_factory=lambda: _get_bool("FORGEOS_ENABLE_OBSIDIAN", True)
    )
    dry_run: bool = field(default_factory=lambda: _get_bool("FORGEOS_DRY_RUN", False))
    api_key: str = field(
        default_factory=lambda: _get("FORGEOS_API_KEY")
    )  # Optional Bearer token for the FastAPI server; empty = no auth (dev only)

    # Telegram notifications (Hermes)
    telegram_bot_token: str = field(
        default_factory=lambda: _get("TELEGRAM_BOT_TOKEN")
    )
    telegram_chat_id: str = field(
        default_factory=lambda: _get("TELEGRAM_CHAT_ID")
    )

    builds_dir: str = field(
        default_factory=lambda: _get(
            "FORGEOS_BUILDS_DIR",
            str(Path.cwd() / "builds"),
        )
    )

    # Mission system
    mission_max_features: int = field(
        default_factory=lambda: _get_int("MISSION_MAX_FEATURES", 12)
    )
    gstack_min_score: float = field(
        default_factory=lambda: _get_float("GSTACK_MIN_SCORE", 7.0)
    )


# ---------------------------------------------------------------------------
# Costs (rough $/1K tokens — used for ledger; update as needed)
# ---------------------------------------------------------------------------


MODEL_COST_PER_1K_TOKENS: dict[str, tuple[float, float]] = {
    # (input $/1K, output $/1K)
    "claude-haiku-4-5":        (0.00080, 0.00400),   # validation / security
    "claude-sonnet-4-20250514": (0.003,   0.015),    # planning / architecture
    "claude-opus-4-6":          (0.015,   0.075),
    "deepseek/deepseek-chat":   (0.00027, 0.0011),
    "deepseek-v3":              (0.00027, 0.0011),
    # Local Ollama models — free
    "qwen2.5-coder:7b":    (0.0, 0.0),
    "qwen2.5-coder:latest": (0.0, 0.0),
    "qwen3-coder-next":     (0.0, 0.0),
}


def estimate_cost(model: str, prompt_tokens: int, completion_tokens: int) -> float:
    rates = MODEL_COST_PER_1K_TOKENS.get(model, (0.0, 0.0))
    return round(
        (prompt_tokens / 1000.0) * rates[0] + (completion_tokens / 1000.0) * rates[1],
        6,
    )


# ---------------------------------------------------------------------------
# Singletons
# ---------------------------------------------------------------------------


LLM = LLMConfig()
TOOLS = ToolConfig()
RUNTIME = RuntimeConfig()


def required(key: str, value: str) -> str:
    """Validate that a required env-derived setting is non-empty."""
    if not value:
        raise EnvironmentError(
            f"Required configuration '{key}' is not set. "
            "Set it in your environment or .env file."
        )
    return value


__all__ = [
    "LLM",
    "LLMConfig",
    "MODEL_COST_PER_1K_TOKENS",
    "RUNTIME",
    "RuntimeConfig",
    "TOOLS",
    "ToolConfig",
    "estimate_cost",
    "required",
]
