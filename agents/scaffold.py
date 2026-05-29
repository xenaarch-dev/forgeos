"""
ScaffoldAgent.

Generates the full project directory tree and all boilerplate config
files based on `STACK.json`. Output goes under `<workdir>/project/`.
"""

from __future__ import annotations

import json
from pathlib import Path
from textwrap import dedent
from typing import Any

from models import ProjectContext, TaskStatus
from models.outputs.scaffold_output import ScaffoldOutput
from .base import BaseAgent


class ScaffoldAgent(BaseAgent):
    name = "scaffold"
    phase = "scaffold"

    def _execute(self, context: ProjectContext) -> dict[str, Any]:
        project_root = Path(context.workdir) / "project"
        project_root.mkdir(parents=True, exist_ok=True)

        produced: list[str] = []
        produced += self._write_root_configs(project_root, context)
        produced += self._write_backend(project_root, context)
        produced += self._write_frontend(project_root, context)
        produced += self._write_supabase(project_root, context)
        produced += self._write_docker(project_root, context)
        produced += self._write_github_actions(project_root, context)
        produced += self._write_doppler(project_root, context)
        produced += self._write_payments(project_root, context)
        produced += self._write_monitoring(project_root, context)
        produced += self._write_readme(project_root, context)
        if "ml_service" in context.stack.extras:
            produced += self._write_ml_service(project_root, context)

        # Mark scaffold tasks done
        for t in context.tasks:
            if t.agent == "scaffold":
                t.status = TaskStatus.DONE.value

        # Build validated ScaffoldOutput from generated artifacts
        output = ScaffoldOutput(
            project_root=str(project_root.relative_to(context.workdir)),
            files_created=produced,
            has_backend=(project_root / "backend/app/main.py").exists(),
            has_frontend=(project_root / "frontend/package.json").exists(),
            has_supabase=(project_root / "supabase/schema.sql").exists(),
            has_docker=(project_root / "docker-compose.yml").exists(),
            has_github_actions=(project_root / ".github/workflows/ci.yml").exists(),
            backend_framework=getattr(context.stack, "backend", "FastAPI") or "FastAPI",
            frontend_framework=getattr(context.stack, "frontend", "Next.js 14") or "Next.js 14",
            file_count=len(produced),
        )

        return {
            **output.model_dump(),
            "files": produced,  # legacy key kept for backward compat
        }

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _write_file(self, root: Path, relpath: str, content: str) -> str:
        path = root / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(dedent(content), encoding="utf-8")
        return str(path.relative_to(root))

    # ------------------------------------------------------------------
    # Root configs
    # ------------------------------------------------------------------

    def _write_root_configs(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, ".gitignore", _GITIGNORE))
        files.append(
            self._write_file(
                root,
                ".env.example",
                _ENV_EXAMPLE.format(project=ctx.project_id),
            )
        )
        files.append(self._write_file(root, "pyproject.toml", _PYPROJECT))
        files.append(self._write_file(root, "package.json", _PACKAGE_JSON))
        return files

    # ------------------------------------------------------------------
    # Backend
    # ------------------------------------------------------------------

    def _write_backend(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, "backend/__init__.py", ""))
        files.append(self._write_file(root, "backend/app/__init__.py", ""))
        files.append(self._write_file(root, "backend/app/main.py", _BE_MAIN))
        files.append(self._write_file(root, "backend/app/config.py", _BE_CONFIG))
        files.append(self._write_file(root, "backend/app/db.py", _BE_DB))
        files.append(self._write_file(root, "backend/app/auth.py", _BE_AUTH))
        files.append(self._write_file(root, "backend/app/rate_limit.py", _BE_RATE_LIMIT))
        files.append(self._write_file(root, "backend/app/models.py", _BE_MODELS))
        files.append(self._write_file(root, "backend/app/schemas.py", _BE_SCHEMAS))
        files.append(self._write_file(root, "backend/app/routers/__init__.py", ""))
        files.append(self._write_file(root, "backend/app/routers/health.py", _BE_R_HEALTH))
        files.append(self._write_file(root, "backend/app/routers/items.py", _BE_R_ITEMS))
        files.append(self._write_file(root, "backend/app/routers/billing.py", _BE_R_BILLING))
        files.append(self._write_file(root, "backend/app/sentry.py", _BE_SENTRY))
        files.append(self._write_file(root, "backend/alembic.ini", _ALEMBIC_INI))
        files.append(self._write_file(root, "backend/migrations/env.py", _ALEMBIC_ENV))
        files.append(
            self._write_file(
                root,
                "backend/migrations/versions/0001_baseline.py",
                _ALEMBIC_BASELINE,
            )
        )
        files.append(self._write_file(root, "backend/tests/__init__.py", ""))
        files.append(self._write_file(root, "backend/tests/conftest.py", _BE_CONFTEST))
        files.append(self._write_file(root, "backend/tests/test_health.py", _BE_TEST_HEALTH))
        files.append(self._write_file(root, "backend/tests/test_items.py", _BE_TEST_ITEMS))
        return files

    # ------------------------------------------------------------------
    # Frontend
    # ------------------------------------------------------------------

    def _write_frontend(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, "frontend/package.json", _FE_PACKAGE_JSON))
        files.append(self._write_file(root, "frontend/next.config.mjs", _FE_NEXT_CONFIG))
        files.append(self._write_file(root, "frontend/tsconfig.json", _FE_TSCONFIG))
        files.append(self._write_file(root, "frontend/tailwind.config.ts", _FE_TAILWIND))
        files.append(self._write_file(root, "frontend/postcss.config.js", _FE_POSTCSS))
        files.append(self._write_file(root, "frontend/app/globals.css", _FE_GLOBALS))
        files.append(self._write_file(root, "frontend/app/layout.tsx", _FE_LAYOUT))
        files.append(self._write_file(root, "frontend/app/page.tsx", _FE_PAGE))
        files.append(self._write_file(root, "frontend/app/dashboard/page.tsx", _FE_DASHBOARD))
        files.append(self._write_file(root, "frontend/lib/supabase.ts", _FE_SUPABASE))
        files.append(self._write_file(root, "frontend/lib/api.ts", _FE_API))
        files.append(self._write_file(root, "frontend/lib/sentry.ts", _FE_SENTRY))
        files.append(self._write_file(root, "frontend/components/ItemForm.tsx", _FE_ITEMFORM))
        files.append(self._write_file(root, "frontend/components/ItemList.tsx", _FE_ITEMLIST))
        files.append(self._write_file(root, "frontend/vitest.config.ts", _FE_VITEST))
        files.append(self._write_file(root, "frontend/tests/setup.ts", _FE_VITEST_SETUP))
        files.append(self._write_file(root, "frontend/tests/items.test.tsx", _FE_VITEST_ITEMS))
        return files

    # ------------------------------------------------------------------
    # Supabase
    # ------------------------------------------------------------------

    def _write_supabase(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, "supabase/schema.sql", _SUPABASE_SCHEMA))
        files.append(self._write_file(root, "supabase/policies.sql", _SUPABASE_POLICIES))
        return files

    # ------------------------------------------------------------------
    # Docker / CI / monitoring etc
    # ------------------------------------------------------------------

    def _write_docker(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, "docker-compose.yml", _DOCKER_COMPOSE))
        files.append(self._write_file(root, "backend/Dockerfile", _BACKEND_DOCKERFILE))
        files.append(self._write_file(root, "frontend/Dockerfile", _FRONTEND_DOCKERFILE))
        files.append(self._write_file(root, ".dockerignore", _DOCKERIGNORE))
        return files

    def _write_github_actions(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, ".github/workflows/ci.yml", _CI_YAML))
        files.append(self._write_file(root, ".github/workflows/deploy.yml", _DEPLOY_YAML))
        return files

    def _write_doppler(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, "doppler.yaml", _DOPPLER_YAML))
        return files

    def _write_payments(self, root: Path, ctx: ProjectContext) -> list[str]:
        return [self._write_file(root, "backend/app/lemon.py", _BE_LEMON)]

    def _write_monitoring(self, root: Path, ctx: ProjectContext) -> list[str]:
        return [self._write_file(root, "monitoring/sentry.md", _SENTRY_NOTES)]

    def _write_readme(self, root: Path, ctx: ProjectContext) -> list[str]:
        readme = _README.format(
            idea=ctx.idea.replace("`", "'"),
            stack_md="\n".join(
                f"- **{k}**: {v}"
                for k, v in {
                    "frontend": ctx.stack.frontend,
                    "backend": ctx.stack.backend,
                    "database": ctx.stack.database,
                    "cache": ctx.stack.cache,
                    "queue": ctx.stack.queue,
                    "auth": ctx.stack.auth,
                    "payments": ctx.stack.payments,
                    "email": ctx.stack.email,
                    "monitoring": ctx.stack.monitoring,
                    "ci_cd": ctx.stack.ci_cd,
                    "deployment": ctx.stack.deployment,
                }.items()
                if v
            ),
        )
        return [self._write_file(root, "README.md", readme)]

    def _write_ml_service(self, root: Path, ctx: ProjectContext) -> list[str]:
        files: list[str] = []
        files.append(self._write_file(root, "ml/train.py", _ML_TRAIN))
        files.append(self._write_file(root, "ml/inference.py", _ML_INFERENCE))
        files.append(self._write_file(root, "ml/data_validation.py", _ML_VALIDATION))
        return files


# ---------------------------------------------------------------------------
# Boilerplate templates
# ---------------------------------------------------------------------------

_GITIGNORE = """\
# Python
__pycache__/
*.pyc
.venv/
venv/
.pytest_cache/
.coverage
htmlcov/

# Node
node_modules/
.next/
dist/
build/

# Env
.env
.env.local
.env.production
.env.development
.env.example.bak

# Misc
.DS_Store
.idea/
.vscode/
*.log
"""

_ENV_EXAMPLE = """\
# Project: {project}
# Copy to .env and fill in real values.
# These are PLACEHOLDERS — never commit real secrets.

# --- Backend ---
DATABASE_URL=postgresql+asyncpg://user:password@localhost:5432/app
SUPABASE_URL=
SUPABASE_ANON_KEY=
SUPABASE_SERVICE_ROLE_KEY=
SUPABASE_JWT_SECRET=
APP_SECRET=replace-with-random-32-bytes
LOG_LEVEL=INFO
PORT=8000

# --- Cache / Queue ---
UPSTASH_REDIS_URL=
UPSTASH_REDIS_TOKEN=

# --- Frontend ---
NEXT_PUBLIC_SUPABASE_URL=
NEXT_PUBLIC_SUPABASE_ANON_KEY=
NEXT_PUBLIC_API_URL=http://localhost:8000

# --- Payments ---
LEMONSQUEEZY_API_KEY=
LEMONSQUEEZY_WEBHOOK_SECRET=
LEMONSQUEEZY_STORE_ID=

# --- Email ---
RESEND_API_KEY=

# --- Monitoring ---
SENTRY_DSN_BACKEND=
NEXT_PUBLIC_SENTRY_DSN_FRONTEND=
"""

_PYPROJECT = """\
[project]
name = "app-backend"
version = "0.1.0"
description = "Backend service"
requires-python = ">=3.11"
dependencies = [
  "fastapi>=0.115",
  "uvicorn[standard]>=0.30",
  "pydantic>=2.7",
  "pydantic-settings>=2.4",
  "sqlalchemy[asyncio]>=2.0",
  "asyncpg>=0.29",
  "alembic>=1.13",
  "httpx>=0.27",
  "python-jose[cryptography]>=3.3",
  "passlib[bcrypt]>=1.7",
  "redis>=5.0",
  "sentry-sdk>=2.10",
  "structlog>=24.1",
  "python-multipart>=0.0.9",
]

[project.optional-dependencies]
dev = [
  "pytest>=8.2",
  "pytest-asyncio>=0.23",
  "pytest-cov>=5.0",
  "httpx[testing]>=0.27",
  "respx>=0.21",
  "ruff>=0.5",
  "mypy>=1.10",
]

[tool.pytest.ini_options]
asyncio_mode = "auto"
addopts = "-q --cov=backend --cov-report=term-missing --cov-fail-under=80"

[tool.ruff]
line-length = 100
target-version = "py311"
"""

_PACKAGE_JSON = """\
{
  "name": "app-monorepo",
  "private": true,
  "workspaces": ["frontend"]
}
"""

_BE_MAIN = """\
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import settings
from .routers import billing, health, items
from .sentry import init_sentry

logging.basicConfig(level=settings.log_level)
init_sentry()

app = FastAPI(
    title="App API",
    version="0.1.0",
    docs_url="/api/docs",
    redoc_url=None,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health.router)
app.include_router(items.router, prefix="/api")
app.include_router(billing.router, prefix="/api")
"""

_BE_CONFIG = """\
from __future__ import annotations

from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str = Field("postgresql+asyncpg://app:app@localhost:5432/app")
    supabase_url: str = ""
    supabase_anon_key: str = ""
    supabase_service_role_key: str = ""
    supabase_jwt_secret: str = ""

    app_secret: str = "change-me"
    log_level: str = "INFO"
    cors_origins: list[str] = ["*"]

    upstash_redis_url: str = ""
    upstash_redis_token: str = ""

    lemonsqueezy_api_key: str = ""
    lemonsqueezy_webhook_secret: str = ""

    sentry_dsn_backend: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
"""

_BE_DB = """\
from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from .config import settings

engine = create_async_engine(settings.database_url, pool_pre_ping=True, future=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False, class_=AsyncSession)


async def get_session() -> AsyncSession:
    async with SessionLocal() as session:
        yield session
"""

_BE_AUTH = """\
from __future__ import annotations

from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from jose import JWTError, jwt

from .config import settings


class CurrentUser:
    def __init__(self, sub: str, email: str | None = None) -> None:
        self.sub = sub
        self.email = email


def _decode(token: str) -> dict:
    if not settings.supabase_jwt_secret:
        raise HTTPException(status_code=503, detail="Auth not configured")
    try:
        return jwt.decode(
            token,
            settings.supabase_jwt_secret,
            algorithms=["HS256"],
            audience="authenticated",
        )
    except JWTError as e:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e)) from e


async def require_user(
    authorization: Annotated[str | None, Header()] = None,
) -> CurrentUser:
    if not authorization or not authorization.lower().startswith("bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.split(" ", 1)[1].strip()
    claims = _decode(token)
    sub = claims.get("sub")
    if not sub:
        raise HTTPException(status_code=401, detail="Invalid token: missing sub")
    return CurrentUser(sub=sub, email=claims.get("email"))


CurrentUserDep = Annotated[CurrentUser, Depends(require_user)]
"""

_BE_RATE_LIMIT = """\
from __future__ import annotations

import time
from collections import defaultdict, deque
from typing import Annotated

from fastapi import Depends, HTTPException, Request

from .config import settings


class _InMemoryLimiter:
    def __init__(self, capacity: int = 60, window: float = 60.0) -> None:
        self.capacity = capacity
        self.window = window
        self._buckets: dict[str, deque[float]] = defaultdict(deque)

    def check(self, key: str) -> None:
        now = time.monotonic()
        bucket = self._buckets[key]
        while bucket and now - bucket[0] > self.window:
            bucket.popleft()
        if len(bucket) >= self.capacity:
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        bucket.append(now)


_limiter = _InMemoryLimiter()


async def rate_limit(request: Request) -> None:
    key = request.client.host if request.client else "anonymous"
    _limiter.check(key)


RateLimitDep = Annotated[None, Depends(rate_limit)]
"""

_BE_MODELS = """\
from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, func
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    email: Mapped[str] = mapped_column(String(320), unique=True, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    items: Mapped[list["Item"]] = relationship(back_populates="user")


class Item(Base):
    __tablename__ = "items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(200), nullable=False)
    data: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user: Mapped[User] = relationship(back_populates="items")
"""

_BE_SCHEMAS = """\
from __future__ import annotations

import uuid
from datetime import datetime
from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class ItemCreate(BaseModel):
    title: str = Field(min_length=1, max_length=200)
    data: dict[str, Any] = Field(default_factory=dict)


class ItemUpdate(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=200)
    data: dict[str, Any] | None = None


class ItemRead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: uuid.UUID
    title: str
    data: dict[str, Any]
    created_at: datetime
"""

_BE_R_HEALTH = """\
from __future__ import annotations

from fastapi import APIRouter

router = APIRouter()


@router.get("/healthz", tags=["meta"])
async def healthz() -> dict[str, str]:
    return {"status": "ok"}
"""

_BE_R_ITEMS = """\
from __future__ import annotations

import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from ..auth import CurrentUserDep
from ..db import get_session
from ..models import Item
from ..rate_limit import RateLimitDep
from ..schemas import ItemCreate, ItemRead, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.get("", response_model=list[ItemRead])
async def list_items(
    user: CurrentUserDep,
    session: AsyncSession = Depends(get_session),
) -> list[ItemRead]:
    rows = await session.scalars(
        select(Item).where(Item.user_id == uuid.UUID(user.sub)).order_by(Item.created_at.desc())
    )
    return [ItemRead.model_validate(r) for r in rows]


@router.post("", response_model=ItemRead, status_code=status.HTTP_201_CREATED)
async def create_item(
    payload: ItemCreate,
    user: CurrentUserDep,
    _: RateLimitDep,
    session: AsyncSession = Depends(get_session),
) -> ItemRead:
    item = Item(user_id=uuid.UUID(user.sub), title=payload.title, data=payload.data)
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return ItemRead.model_validate(item)


@router.patch("/{item_id}", response_model=ItemRead)
async def update_item(
    item_id: uuid.UUID,
    payload: ItemUpdate,
    user: CurrentUserDep,
    _: RateLimitDep,
    session: AsyncSession = Depends(get_session),
) -> ItemRead:
    item = await session.get(Item, item_id)
    if not item or item.user_id != uuid.UUID(user.sub):
        raise HTTPException(status_code=404, detail="Item not found")
    if payload.title is not None:
        item.title = payload.title
    if payload.data is not None:
        item.data = payload.data
    await session.commit()
    await session.refresh(item)
    return ItemRead.model_validate(item)


@router.delete("/{item_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_item(
    item_id: uuid.UUID,
    user: CurrentUserDep,
    _: RateLimitDep,
    session: AsyncSession = Depends(get_session),
) -> None:
    item = await session.get(Item, item_id)
    if not item or item.user_id != uuid.UUID(user.sub):
        raise HTTPException(status_code=404, detail="Item not found")
    await session.delete(item)
    await session.commit()
"""

_BE_R_BILLING = """\
from __future__ import annotations

import hashlib
import hmac
import json

from fastapi import APIRouter, Header, HTTPException, Request

from ..config import settings

router = APIRouter(prefix="/billing", tags=["billing"])


def _verify(signature: str, body: bytes, secret: str) -> bool:
    if not signature or not secret:
        return False
    digest = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(digest, signature)


@router.post("/webhook")
async def lemonsqueezy_webhook(
    request: Request,
    x_signature: str = Header(default=""),
) -> dict[str, str]:
    body = await request.body()
    if not _verify(x_signature, body, settings.lemonsqueezy_webhook_secret):
        raise HTTPException(status_code=401, detail="Bad signature")
    try:
        payload = json.loads(body.decode("utf-8") or "{}")
    except json.JSONDecodeError as e:
        raise HTTPException(status_code=400, detail="Invalid JSON") from e
    event = payload.get("meta", {}).get("event_name")
    # In production, route on event and update subscription state.
    return {"status": "received", "event": event or "unknown"}
"""

_BE_SENTRY = """\
from __future__ import annotations

import sentry_sdk

from .config import settings


def init_sentry() -> None:
    if not settings.sentry_dsn_backend:
        return
    sentry_sdk.init(
        dsn=settings.sentry_dsn_backend,
        traces_sample_rate=0.1,
        profiles_sample_rate=0.1,
        send_default_pii=False,
    )
"""

_BE_LEMON = """\
from __future__ import annotations

import httpx

from .config import settings


async def create_checkout(variant_id: str, customer_email: str) -> str:
    if not settings.lemonsqueezy_api_key:
        raise RuntimeError("Lemon Squeezy is not configured")
    headers = {
        "Authorization": f"Bearer {settings.lemonsqueezy_api_key}",
        "Accept": "application/vnd.api+json",
        "Content-Type": "application/vnd.api+json",
    }
    payload = {
        "data": {
            "type": "checkouts",
            "attributes": {"checkout_data": {"email": customer_email}},
            "relationships": {
                "variant": {"data": {"type": "variants", "id": variant_id}},
            },
        }
    }
    async with httpx.AsyncClient(timeout=30) as client:
        resp = await client.post(
            "https://api.lemonsqueezy.com/v1/checkouts",
            headers=headers,
            json=payload,
        )
        resp.raise_for_status()
        return resp.json()["data"]["attributes"]["url"]
"""

_ALEMBIC_INI = """\
[alembic]
script_location = migrations
sqlalchemy.url = driver://user:pass@host/db

[loggers]
keys = root,alembic
[handlers]
keys = console
[formatters]
keys = generic

[logger_root]
level = WARN
handlers = console
qualname =

[logger_alembic]
level = INFO
handlers =
qualname = alembic

[handler_console]
class = StreamHandler
args = (sys.stderr,)
level = NOTSET
formatter = generic

[formatter_generic]
format = %(levelname)-5.5s [%(name)s] %(message)s
"""

_ALEMBIC_ENV = """\
from __future__ import annotations

import asyncio
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from backend.app.config import settings
from backend.app.models import Base

config = context.config
if config.config_file_name:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    cfg = config.get_section(config.config_ini_section) or {}
    cfg["sqlalchemy.url"] = settings.database_url
    engine = async_engine_from_config(cfg, prefix="sqlalchemy.")
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_migrations_offline() -> None:
    context.configure(
        url=settings.database_url,
        target_metadata=target_metadata,
        literal_binds=True,
    )
    with context.begin_transaction():
        context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
"""

_ALEMBIC_BASELINE = """\
\"\"\"baseline schema\"\"\"

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects.postgresql import JSONB, UUID

revision = "0001_baseline"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(320), nullable=False, unique=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_table(
        "items",
        sa.Column("id", UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("data", JSONB, server_default="{}"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_items_user_id", "items", ["user_id"])


def downgrade() -> None:
    op.drop_index("ix_items_user_id", table_name="items")
    op.drop_table("items")
    op.drop_table("users")
"""

_BE_CONFTEST = """\
from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)
"""

_BE_TEST_HEALTH = """\
from __future__ import annotations


def test_healthz(client) -> None:
    resp = client.get("/healthz")
    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
"""

_BE_TEST_ITEMS = """\
from __future__ import annotations


def test_items_requires_auth(client) -> None:
    resp = client.get("/api/items")
    assert resp.status_code == 401
"""

_FE_PACKAGE_JSON = """\
{
  "name": "frontend",
  "private": true,
  "version": "0.1.0",
  "scripts": {
    "dev": "next dev",
    "build": "next build",
    "start": "next start",
    "lint": "next lint",
    "test": "vitest run --coverage",
    "test:watch": "vitest"
  },
  "dependencies": {
    "@hookform/resolvers": "^3.9.0",
    "@supabase/supabase-js": "^2.45.0",
    "@tanstack/react-query": "^5.51.0",
    "@sentry/nextjs": "^8.20.0",
    "next": "14.2.5",
    "react": "18.3.1",
    "react-dom": "18.3.1",
    "react-hook-form": "^7.52.0",
    "zod": "^3.23.8"
  },
  "devDependencies": {
    "@testing-library/react": "^16.0.0",
    "@types/node": "^20.14.0",
    "@types/react": "^18.3.0",
    "@types/react-dom": "^18.3.0",
    "@vitest/coverage-v8": "^2.0.0",
    "autoprefixer": "^10.4.19",
    "jsdom": "^24.1.0",
    "postcss": "^8.4.39",
    "tailwindcss": "^3.4.6",
    "typescript": "^5.5.0",
    "vitest": "^2.0.0"
  }
}
"""

_FE_NEXT_CONFIG = """\
/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  experimental: { typedRoutes: true },
};
export default nextConfig;
"""

_FE_TSCONFIG = """\
{
  "compilerOptions": {
    "target": "ES2022",
    "lib": ["dom", "dom.iterable", "esnext"],
    "allowJs": false,
    "skipLibCheck": true,
    "strict": true,
    "noEmit": true,
    "esModuleInterop": true,
    "module": "esnext",
    "moduleResolution": "bundler",
    "resolveJsonModule": true,
    "isolatedModules": true,
    "jsx": "preserve",
    "incremental": true,
    "baseUrl": ".",
    "paths": { "@/*": ["./*"] }
  },
  "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
  "exclude": ["node_modules"]
}
"""

_FE_TAILWIND = """\
import type { Config } from "tailwindcss";

const config: Config = {
  content: ["./app/**/*.{ts,tsx}", "./components/**/*.{ts,tsx}"],
  theme: { extend: {} },
  plugins: [],
};
export default config;
"""

_FE_POSTCSS = """\
module.exports = { plugins: { tailwindcss: {}, autoprefixer: {} } };
"""

_FE_GLOBALS = """\
@tailwind base;
@tailwind components;
@tailwind utilities;

:root { color-scheme: light dark; }
body { @apply bg-white text-slate-900 dark:bg-slate-950 dark:text-slate-100; }
"""

_FE_LAYOUT = """\
import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "App",
  description: "Built with ForgeOS",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
"""

_FE_PAGE = """\
export default function Home() {
  return (
    <main className="mx-auto max-w-3xl p-12">
      <h1 className="text-3xl font-semibold">Welcome</h1>
      <p className="mt-4 text-slate-600">
        Sign in and head to the dashboard to start.
      </p>
      <a
        className="mt-6 inline-block rounded bg-slate-900 px-4 py-2 text-white"
        href="/dashboard"
      >
        Go to dashboard
      </a>
    </main>
  );
}
"""

_FE_DASHBOARD = """\
"use client";

import { useEffect, useState } from "react";

import { ItemForm } from "@/components/ItemForm";
import { ItemList } from "@/components/ItemList";
import { listItems, type Item } from "@/lib/api";

export default function DashboardPage() {
  const [items, setItems] = useState<Item[]>([]);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    listItems()
      .then(setItems)
      .catch((e) => setError(String(e)));
  }, []);

  return (
    <main className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Your items</h1>
      {error && <p className="mt-2 text-sm text-red-600">{error}</p>}
      <div className="mt-6">
        <ItemForm onCreated={(i) => setItems((prev) => [i, ...prev])} />
      </div>
      <div className="mt-8">
        <ItemList items={items} />
      </div>
    </main>
  );
}
"""

_FE_SUPABASE = """\
import { createClient } from "@supabase/supabase-js";

const url = process.env.NEXT_PUBLIC_SUPABASE_URL ?? "";
const key = process.env.NEXT_PUBLIC_SUPABASE_ANON_KEY ?? "";

export const supabase = createClient(url, key, {
  auth: { persistSession: true, detectSessionInUrl: true },
});
"""

_FE_API = """\
import { supabase } from "./supabase";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "";

export type Item = {
  id: string;
  title: string;
  data: Record<string, unknown>;
  created_at: string;
};

async function authedFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const { data } = await supabase.auth.getSession();
  const token = data.session?.access_token;
  const headers = new Headers(init.headers);
  headers.set("Content-Type", "application/json");
  if (token) headers.set("Authorization", `Bearer ${token}`);
  return fetch(`${BASE}${path}`, { ...init, headers });
}

export async function listItems(): Promise<Item[]> {
  const r = await authedFetch("/api/items");
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function createItem(input: { title: string; data?: Record<string, unknown> }): Promise<Item> {
  const r = await authedFetch("/api/items", {
    method: "POST",
    body: JSON.stringify({ title: input.title, data: input.data ?? {} }),
  });
  if (!r.ok) throw new Error(`HTTP ${r.status}`);
  return r.json();
}

export async function deleteItem(id: string): Promise<void> {
  const r = await authedFetch(`/api/items/${id}`, { method: "DELETE" });
  if (!r.ok && r.status !== 204) throw new Error(`HTTP ${r.status}`);
}
"""

_FE_SENTRY = """\
import * as Sentry from "@sentry/nextjs";

const dsn = process.env.NEXT_PUBLIC_SENTRY_DSN_FRONTEND;
if (dsn) {
  Sentry.init({ dsn, tracesSampleRate: 0.1, replaysSessionSampleRate: 0 });
}
"""

_FE_ITEMFORM = """\
"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { createItem, type Item } from "@/lib/api";

const Schema = z.object({ title: z.string().min(1).max(200) });
type FormValues = z.infer<typeof Schema>;

export function ItemForm({ onCreated }: { onCreated: (i: Item) => void }) {
  const { register, handleSubmit, reset, formState } = useForm<FormValues>({
    resolver: zodResolver(Schema),
  });

  const onSubmit = handleSubmit(async (values) => {
    const item = await createItem({ title: values.title });
    onCreated(item);
    reset();
  });

  return (
    <form onSubmit={onSubmit} className="flex gap-2">
      <input
        {...register("title")}
        placeholder="What needs doing?"
        className="flex-1 rounded border px-3 py-2"
      />
      <button
        disabled={formState.isSubmitting}
        className="rounded bg-slate-900 px-4 py-2 text-white"
      >
        Add
      </button>
    </form>
  );
}
"""

_FE_ITEMLIST = """\
"use client";

import type { Item } from "@/lib/api";

export function ItemList({ items }: { items: Item[] }) {
  if (items.length === 0) {
    return <p className="text-sm text-slate-500">No items yet.</p>;
  }
  return (
    <ul className="divide-y rounded border">
      {items.map((i) => (
        <li key={i.id} className="px-4 py-3">
          <p className="font-medium">{i.title}</p>
          <p className="text-xs text-slate-500">{i.created_at}</p>
        </li>
      ))}
    </ul>
  );
}
"""

_FE_VITEST = """\
import { defineConfig } from "vitest/config";

export default defineConfig({
  test: {
    environment: "jsdom",
    setupFiles: ["./tests/setup.ts"],
    coverage: { reporter: ["text"], thresholds: { lines: 80, functions: 80, branches: 70 } },
  },
});
"""

_FE_VITEST_SETUP = """\
import "@testing-library/react";
"""

_FE_VITEST_ITEMS = """\
import { render, screen } from "@testing-library/react";
import { describe, it, expect } from "vitest";

import { ItemList } from "@/components/ItemList";

describe("ItemList", () => {
  it("renders empty state", () => {
    render(<ItemList items={[]} />);
    expect(screen.getByText(/no items yet/i)).toBeTruthy();
  });
});
"""

_SUPABASE_SCHEMA = """\
-- Baseline schema for the application.
create extension if not exists "pgcrypto";

create table if not exists public.users (
  id uuid primary key default gen_random_uuid(),
  email text unique not null,
  created_at timestamptz not null default now()
);

create table if not exists public.items (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references public.users(id) on delete cascade,
  title text not null,
  data jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now()
);

create index if not exists ix_items_user_id on public.items(user_id);
"""

_SUPABASE_POLICIES = """\
-- Row-level security policies. SecurityAgent will refine these.
alter table public.users enable row level security;
alter table public.items enable row level security;

create policy "users can read self" on public.users
  for select using (auth.uid() = id);

create policy "items owner select" on public.items
  for select using (auth.uid() = user_id);

create policy "items owner write" on public.items
  for all using (auth.uid() = user_id) with check (auth.uid() = user_id);
"""

_DOCKER_COMPOSE = """\
version: "3.9"
services:
  db:
    image: postgres:16-alpine
    environment:
      POSTGRES_USER: app
      POSTGRES_PASSWORD: app
      POSTGRES_DB: app
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD", "pg_isready", "-U", "app"]
      interval: 5s
      timeout: 5s
      retries: 10

  backend:
    build:
      context: .
      dockerfile: backend/Dockerfile
    env_file: .env
    environment:
      DATABASE_URL: postgresql+asyncpg://app:app@db:5432/app
    ports:
      - "8000:8000"
    depends_on:
      db:
        condition: service_healthy

  frontend:
    build:
      context: ./frontend
    env_file: .env
    ports:
      - "3000:3000"
    depends_on:
      - backend
"""

_BACKEND_DOCKERFILE = """\
FROM python:3.11-slim
WORKDIR /app
ENV PIP_NO_CACHE_DIR=1 PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1
COPY pyproject.toml ./
RUN pip install --upgrade pip && pip install .
COPY backend ./backend
EXPOSE 8000
CMD ["uvicorn", "backend.app.main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

_FRONTEND_DOCKERFILE = """\
FROM node:20-alpine AS deps
WORKDIR /app
COPY package.json ./
RUN npm install --legacy-peer-deps

FROM node:20-alpine AS build
WORKDIR /app
COPY --from=deps /app/node_modules ./node_modules
COPY . .
RUN npm run build

FROM node:20-alpine AS run
WORKDIR /app
ENV NODE_ENV=production
COPY --from=build /app ./
EXPOSE 3000
CMD ["npm", "run", "start"]
"""

_DOCKERIGNORE = """\
.git
.venv
node_modules
.next
__pycache__
.env
"""

_CI_YAML = """\
name: CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  backend:
    runs-on: ubuntu-latest
    services:
      postgres:
        image: postgres:16-alpine
        env:
          POSTGRES_USER: app
          POSTGRES_PASSWORD: app
          POSTGRES_DB: app
        ports: ["5432:5432"]
        options: >-
          --health-cmd "pg_isready -U app" --health-interval 5s
          --health-timeout 5s --health-retries 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with: { python-version: "3.11" }
      - run: pip install -e .[dev]
      - run: alembic -c backend/alembic.ini upgrade head
        env:
          DATABASE_URL: postgresql+asyncpg://app:app@localhost:5432/app
      - run: pytest

  frontend:
    runs-on: ubuntu-latest
    defaults:
      run: { working-directory: frontend }
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: "20" }
      - run: npm install --legacy-peer-deps
      - run: npm run build
      - run: npm test

  security:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Run Trivy
        uses: aquasecurity/trivy-action@master
        with:
          scan-type: fs
          ignore-unfixed: true
          severity: HIGH,CRITICAL
"""

_DEPLOY_YAML = """\
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-backend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trigger Railway deploy
        run: |
          curl -fsSL -X POST -H "Authorization: Bearer $RAILWAY_TOKEN" \\
            https://backboard.railway.app/graphql/v2 \\
            -H "Content-Type: application/json" \\
            -d '{"query":"mutation { serviceInstanceRedeploy(serviceId: \\"$RAILWAY_SERVICE_ID\\", environmentId: \\"$RAILWAY_ENV_ID\\") }"}'
        env:
          RAILWAY_TOKEN: ${{ secrets.RAILWAY_TOKEN }}
          RAILWAY_SERVICE_ID: ${{ secrets.RAILWAY_SERVICE_ID }}
          RAILWAY_ENV_ID: ${{ secrets.RAILWAY_ENV_ID }}

  deploy-frontend:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - name: Trigger Vercel deploy
        run: |
          curl -fsSL -X POST -H "Authorization: Bearer $VERCEL_TOKEN" \\
            https://api.vercel.com/v13/deployments \\
            -H "Content-Type: application/json" \\
            -d "{\\"name\\":\\"frontend\\",\\"target\\":\\"production\\",\\"gitSource\\":{\\"type\\":\\"github\\",\\"ref\\":\\"main\\"}}"
        env:
          VERCEL_TOKEN: ${{ secrets.VERCEL_TOKEN }}
"""

_DOPPLER_YAML = """\
setup:
  - project: app
    config: dev
"""

_SENTRY_NOTES = """\
# Sentry

The backend initialises Sentry from `SENTRY_DSN_BACKEND`.
The frontend initialises Sentry from `NEXT_PUBLIC_SENTRY_DSN_FRONTEND`.

Use `forge healer` to auto-open PRs for new unresolved issues.
"""

_README = """\
# {idea}

## Stack

{stack_md}

## Architecture

```mermaid
graph TD
  user([User]) --> fe[Frontend]
  fe --> be[Backend API]
  be --> db[(Database)]
  be --> cache[(Cache)]
  be --> queue[(Queue)]
  be --> obs[Sentry/Uptime Robot]
```

## Local development

```bash
cp .env.example .env
docker compose up --build
```

Backend → http://localhost:8000
Frontend → http://localhost:3000

## Tests

```bash
pip install -e .[dev]
pytest
cd frontend && npm test
```
"""

_ML_TRAIN = """\
from __future__ import annotations

import argparse
import json
import os
from pathlib import Path

import mlflow


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True)
    parser.add_argument("--out", type=str, default="artifacts")
    args = parser.parse_args()

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)

    mlflow.set_tracking_uri(os.environ.get("MLFLOW_TRACKING_URI", str(out / "mlruns")))
    with mlflow.start_run(run_name="baseline"):
        # Replace with real training; this baseline just logs counts.
        rows = sum(1 for _ in open(args.data))
        mlflow.log_param("rows", rows)
        mlflow.log_metric("placeholder_score", 0.5)
        (out / "model.json").write_text(json.dumps({"version": "0.1"}))
        mlflow.log_artifact(str(out / "model.json"))


if __name__ == "__main__":
    main()
"""

_ML_INFERENCE = """\
from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(prefix="/ml", tags=["ml"])


class InferRequest(BaseModel):
    features: list[float]


class InferResponse(BaseModel):
    score: float


@router.post("/predict", response_model=InferResponse)
async def predict(payload: InferRequest) -> InferResponse:
    # Placeholder model — replace with a real loaded artifact.
    score = sum(payload.features) / max(1, len(payload.features))
    return InferResponse(score=score)
"""

_ML_VALIDATION = """\
from __future__ import annotations

from pathlib import Path

import great_expectations as gx


def validate(csv_path: str) -> bool:
    ctx = gx.get_context()
    suite = ctx.add_or_update_expectation_suite("baseline")
    batch = ctx.sources.add_or_update_pandas("ds").read_csv(csv_path)
    validator = ctx.get_validator(batch_request=batch.build_batch_request(), expectation_suite=suite)
    validator.expect_column_values_to_not_be_null("id")
    return validator.validate()["success"]
"""


__all__ = ["ScaffoldAgent"]
