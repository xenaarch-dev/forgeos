"""
Flat-file store for custom agent specs, one JSON file per agent per owner.

Same philosophy as the Daemon Mode queue (builds/queue/): plain files that a
founder can read, diff and back up. Layout:

    <root>/<owner>/<slug>.json

Owner ids come from the authenticated user (or "anonymous" in local dev) and
are reduced to a safe path segment, so one user can never read or write
another user's directory and no path from a request reaches the filesystem.
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from pathlib import Path

from agent_builder.spec import SLUG_RE, AgentSpec

MAX_AGENTS_PER_OWNER = 50


class AgentStoreError(Exception):
    pass


def _owner_dir_name(owner: str) -> str:
    if re.fullmatch(r"[A-Za-z0-9_-]{1,64}", owner):
        return owner
    # Anything else (emails, odd JWT subs) becomes a stable opaque name.
    return "u_" + hashlib.sha256(owner.encode("utf-8")).hexdigest()[:24]


class AgentStore:
    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def _dir(self, owner: str) -> Path:
        return self.root / _owner_dir_name(owner)

    def _path(self, owner: str, slug: str) -> Path:
        if not SLUG_RE.match(slug):
            raise AgentStoreError("invalid slug")
        return self._dir(owner) / f"{slug}.json"

    def list(self, owner: str) -> list[AgentSpec]:
        folder = self._dir(owner)
        if not folder.is_dir():
            return []
        specs: list[AgentSpec] = []
        for path in sorted(folder.glob("*.json")):
            try:
                specs.append(AgentSpec.model_validate_json(path.read_text(encoding="utf-8")))
            except (OSError, ValueError):
                continue  # a hand-edited broken file never takes the list down
        return specs

    def get(self, owner: str, slug: str) -> AgentSpec | None:
        path = self._path(owner, slug)
        if not path.exists():
            return None
        return AgentSpec.model_validate_json(path.read_text(encoding="utf-8"))

    def save(self, owner: str, spec: AgentSpec, *, create: bool) -> AgentSpec:
        path = self._path(owner, spec.slug)
        if create and path.exists():
            raise AgentStoreError(f"an agent called {spec.slug!r} already exists")
        if not create and not path.exists():
            raise AgentStoreError(f"no agent called {spec.slug!r}")
        if create and len(self.list(owner)) >= MAX_AGENTS_PER_OWNER:
            raise AgentStoreError(f"limit of {MAX_AGENTS_PER_OWNER} custom agents reached")
        path.parent.mkdir(parents=True, exist_ok=True)
        # Atomic replace: a crash mid-write never leaves a half-written spec.
        fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
        with os.fdopen(fd, "w", encoding="utf-8") as fh:
            json.dump(spec.model_dump(mode="json"), fh, indent=2)
        os.replace(tmp, path)
        return spec

    def delete(self, owner: str, slug: str) -> bool:
        path = self._path(owner, slug)
        if not path.exists():
            return False
        path.unlink()
        return True


__all__ = ["AgentStore", "AgentStoreError", "MAX_AGENTS_PER_OWNER"]
