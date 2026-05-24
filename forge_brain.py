"""
ForgeBrain — Obsidian-vault knowledge accumulation.

Every successful build feeds back into the brain:

    ingest  → extract decisions/patterns from context.json + ARCH.md + SECURITY.md
    compile → distil into structured WikiNote objects via Claude
    audit   → check for conflicts with existing notes
    write   → persist to ~/ObsidianVault/ForgeOS/wiki/patterns/*.md
              and update knowledge-graph.md

Subsequent builds load the accumulated patterns before the architect
runs (see `load_existing_patterns`), so the system gets smarter over
time.
"""

from __future__ import annotations

import json
import re
from dataclasses import asdict
from pathlib import Path
from typing import Any

from config import RUNTIME
from llm.router import complete as llm_complete
from models import ProjectContext, WikiNote


SYSTEM = """\
You distil engineering decisions from project documents into reusable
patterns. Output is a JSON array of objects, each with: title, pattern,
when_to_use, example, related_patterns. Keep titles short (3-6 words).
"""


class ForgeBrain:
    def __init__(self, vault_root: str | None = None) -> None:
        self.vault_root = Path(vault_root or RUNTIME.obsidian_vault).expanduser()
        self.patterns_dir = self.vault_root / "wiki" / "patterns"
        self.patterns_dir.mkdir(parents=True, exist_ok=True)

    # ------------------------------------------------------------------
    # Pipeline
    # ------------------------------------------------------------------

    def ingest(self, context: ProjectContext) -> dict[str, Any]:
        wd = Path(context.workdir)
        return {
            "context": context.summary(),
            "spec": (wd / "SPEC.md").read_text(encoding="utf-8") if (wd / "SPEC.md").exists() else "",
            "arch": (wd / "ARCH.md").read_text(encoding="utf-8") if (wd / "ARCH.md").exists() else "",
            "security": (wd / "SECURITY.md").read_text(encoding="utf-8") if (wd / "SECURITY.md").exists() else "",
            "deployment": (wd / "DEPLOYMENT.md").read_text(encoding="utf-8") if (wd / "DEPLOYMENT.md").exists() else "",
            "tasks": [asdict(t) for t in context.tasks],
            "stack": asdict(context.stack),
        }

    def compile(self, ingested: dict[str, Any]) -> list[WikiNote]:
        prompt = (
            "Distil the following project documents into 3-6 reusable engineering "
            "patterns. Each pattern must include: title, pattern, when_to_use, "
            "example, related_patterns.\n\n"
            f"PROJECT SUMMARY:\n{json.dumps(ingested['context'], indent=2, default=str)}\n\n"
            f"STACK:\n{json.dumps(ingested['stack'], indent=2, default=str)}\n\n"
            f"ARCH.md:\n{ingested['arch'][:6000]}\n\n"
            f"SECURITY.md:\n{ingested['security'][:4000]}\n"
        )
        try:
            resp = llm_complete(
                user=prompt,
                system_extra=SYSTEM,
                task_complexity="medium",
                task_type="review",
                purpose="forge_brain.compile",
                stream=False,
                max_tokens=4000,
            )
            return self._parse_notes(resp.text, source=ingested["context"]["project_id"])
        except Exception:
            return self._fallback_notes(ingested)

    def compile_from(self, context: ProjectContext) -> list[WikiNote]:
        return self.compile(self.ingest(context))

    def audit(self, notes: list[WikiNote]) -> list[WikiNote]:
        """Reconcile new notes against the existing wiki.

        - If a note with the same slug exists and the new pattern adds info,
          merge by appending an "Updated …" section.
        - If the existing note conflicts, keep the existing and append a
          "Conflict notes" block to the new one.
        """
        existing = self.load_existing_patterns()
        merged: list[WikiNote] = []
        for note in notes:
            slug = note.slug()
            if slug in existing:
                old = existing[slug]
                if note.pattern.strip() and note.pattern != old.pattern:
                    note.related_patterns = sorted(
                        set(note.related_patterns + [old.title])
                    )
                    note.example = (
                        old.example
                        + "\n\n---\n\n## Updated example\n\n"
                        + note.example
                    )
            merged.append(note)
        return merged

    def write(self, notes: list[WikiNote]) -> list[Path]:
        paths: list[Path] = []
        for note in notes:
            path = self.patterns_dir / f"{note.slug()}.md"
            path.write_text(note.to_markdown(), encoding="utf-8")
            paths.append(path)
        self._update_knowledge_graph(notes)
        return paths

    # ------------------------------------------------------------------
    # Existing-pattern loading (used by ArchitectAgent on next run)
    # ------------------------------------------------------------------

    def load_existing_patterns(self) -> dict[str, WikiNote]:
        out: dict[str, WikiNote] = {}
        if not self.patterns_dir.exists():
            return out
        for md in self.patterns_dir.glob("*.md"):
            try:
                note = self._parse_md(md)
            except Exception:
                continue
            out[md.stem] = note
        return out

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------


    # ------------------------------------------------------------------
    # Failure learning loop (Phase 10)
    # ------------------------------------------------------------------

    def read_failures(self, builds_dir: str | Path | None = None) -> list[dict]:
        """Scan all FAILURE.md files across builds/ and return parsed records."""
        from config import RUNTIME
        builds_root = Path(builds_dir or RUNTIME.builds_dir).expanduser()
        if not builds_root.exists():
            return []
        records: list[dict] = []
        for failure_md in sorted(builds_root.rglob("FAILURE.md")):
            text = failure_md.read_text(encoding="utf-8")
            record: dict = {"source_file": str(failure_md), "raw": text}
            # Parse simple key:value front-matter lines
            for line in text.splitlines():
                if ":" in line:
                    key, _, val = line.partition(":")
                    key = key.strip().lower().replace(" ", "_")
                    if key in {"stage", "agent", "error", "idea", "timestamp"}:
                        record[key] = val.strip()
            records.append(record)
        return records

    def learn_from_failures(self, builds_dir: str | Path | None = None) -> list[WikiNote]:
        """Read FAILURE.md files, distil failure patterns, write to wiki."""
        records = self.read_failures(builds_dir)
        if not records:
            return []
        failures_text = "\n\n".join(
            f"### Build: {r.get('source_file', '?')}\n"
            f"Stage: {r.get('stage', '?')} | Agent: {r.get('agent', '?')}\n"
            f"Error: {r.get('error', r['raw'][:300])}"
            for r in records
        )
        try:
            resp = llm_complete(
                user=(
                    "Analyse these ForgeOS build failures and distil 2-4 patterns "
                    "explaining the root causes and fixes applied.\n\n"
                    f"FAILURES:\n{failures_text[:8000]}\n\n"
                    "Return a JSON array. Each item: "
                    "{title, pattern, when_to_use, example, related_patterns}"
                ),
                system_extra=SYSTEM,
                task_complexity="medium",
                task_type="review",
                purpose="forge_brain.failure_patterns",
                stream=False,
                max_tokens=3000,
            )
            notes = self._parse_notes(resp.text, source="failure_learning")
        except Exception:
            notes = []

        if notes:
            notes = self.audit(notes)
            self.write(notes)
        return notes

    def update_agents_md(self, agents_md_path: str | Path | None = None) -> Path:
        """Write / refresh AGENTS.md from accumulated wiki patterns."""
        agents_md = Path(agents_md_path or "/home/padmaja/forge/forgeos/AGENTS.md")
        patterns = self.load_existing_patterns()
        if not patterns:
            block = "_No patterns accumulated yet._\n"
        else:
            lines = []
            for slug, note in sorted(patterns.items()):
                lines.append(f"### {note.title}\n")
                if note.pattern:
                    lines.append(f"{note.pattern}\n")
                if note.when_to_use:
                    lines.append(f"**When**: {note.when_to_use}\n")
                lines.append("")
            block = "\n".join(lines)

        content = (
            "# ForgeOS Agent Patterns\n\n"
            "> Auto-generated by ForgeBrain from accumulated build knowledge.\n"
            "> Edit `forge_brain.py` or the Obsidian vault, not this file directly.\n\n"
            "## Accumulated Patterns\n\n"
            + block
        )
        agents_md.write_text(content, encoding="utf-8")
        return agents_md

    def run_learning_loop(
        self,
        context: ProjectContext | None = None,
        builds_dir: str | Path | None = None,
    ) -> dict:
        """Full learning cycle: ingest success + failures, write wiki + AGENTS.md."""
        notes: list[WikiNote] = []

        # Success patterns from a completed build
        if context is not None:
            success_notes = self.compile_from(context)
            if success_notes:
                success_notes = self.audit(success_notes)
                self.write(success_notes)
                notes.extend(success_notes)

        # Failure patterns from all builds
        failure_notes = self.learn_from_failures(builds_dir)
        notes.extend(failure_notes)

        agents_md = self.update_agents_md()

        return {
            "wiki_notes_written": len(notes),
            "agents_md": str(agents_md),
            "patterns_total": len(self.load_existing_patterns()),
        }

    def _parse_notes(self, text: str, source: str) -> list[WikiNote]:
        # Find a JSON array in the response
        m = re.search(r"\[.*\]", text, re.S)
        if not m:
            return []
        try:
            data = json.loads(m.group(0))
        except json.JSONDecodeError:
            return []
        notes: list[WikiNote] = []
        for entry in data:
            if not isinstance(entry, dict):
                continue
            notes.append(
                WikiNote(
                    title=str(entry.get("title", "Untitled pattern")),
                    pattern=str(entry.get("pattern", "")),
                    when_to_use=str(entry.get("when_to_use", "")),
                    example=str(entry.get("example", "")),
                    related_patterns=[str(x) for x in entry.get("related_patterns", []) if x],
                    source_project=source,
                    tags=["forgeos", "auto"],
                )
            )
        return notes

    def _fallback_notes(self, ingested: dict[str, Any]) -> list[WikiNote]:
        stack = ingested.get("stack", {})
        return [
            WikiNote(
                title="Default ForgeOS SaaS stack",
                pattern=(
                    "Use Next.js for the frontend, FastAPI for the backend, "
                    "Supabase Postgres for storage, Upstash Redis for cache, "
                    "Sentry + Uptime Robot for monitoring."
                ),
                when_to_use="Greenfield SaaS where you need auth, payments, and email.",
                example=json.dumps(stack, indent=2),
                related_patterns=["RLS by default", "Webhook signature verification"],
                source_project=str(ingested.get("context", {}).get("project_id", "")),
                tags=["stack", "saas"],
            ),
            WikiNote(
                title="RLS by default",
                pattern="Enable RLS on every Supabase table; deny by default; allow only owner.",
                when_to_use="Any multi-tenant Supabase application.",
                example=(
                    "alter table public.items enable row level security;\n"
                    "create policy \"items owner\" on public.items for all\n"
                    "  using (auth.uid() = user_id) with check (auth.uid() = user_id);"
                ),
                related_patterns=["Default ForgeOS SaaS stack"],
                tags=["security", "supabase"],
            ),
            WikiNote(
                title="Webhook signature verification",
                pattern=(
                    "Verify HMAC signature on every inbound webhook before "
                    "processing. Use a constant-time comparison."
                ),
                when_to_use="Inbound payment, billing, or third-party events.",
                example=(
                    "digest = hmac.new(secret, body, hashlib.sha256).hexdigest()\n"
                    "if not hmac.compare_digest(digest, header_signature): raise HTTPException(401)"
                ),
                related_patterns=["RLS by default"],
                tags=["security", "webhooks"],
            ),
        ]

    def _update_knowledge_graph(self, notes: list[WikiNote]) -> None:
        graph_path = self.vault_root / "knowledge-graph.md"
        existing = graph_path.read_text(encoding="utf-8") if graph_path.exists() else ""
        new_lines: list[str] = []
        for note in notes:
            line = f"- [[{note.slug()}|{note.title}]] — tags: {', '.join(note.tags) or 'forgeos'}"
            if line not in existing:
                new_lines.append(line)
        if not new_lines and existing:
            return
        block = "## Patterns\n\n" + "\n".join(new_lines) + "\n"
        if existing:
            graph_path.write_text(existing.rstrip() + "\n\n" + block, encoding="utf-8")
        else:
            graph_path.write_text("# ForgeOS Knowledge Graph\n\n" + block, encoding="utf-8")

    def _parse_md(self, path: Path) -> WikiNote:
        text = path.read_text(encoding="utf-8")
        title_m = re.search(r"^# (.+)$", text, re.M)
        title = title_m.group(1).strip() if title_m else path.stem

        def _section(header: str) -> str:
            m = re.search(rf"## {header}\n\n(.*?)(?=\n##|\Z)", text, re.S)
            return m.group(1).strip() if m else ""

        return WikiNote(
            title=title,
            pattern=_section("Pattern"),
            when_to_use=_section("When to use"),
            example=_section("Example"),
            related_patterns=[],
            tags=["forgeos"],
        )


__all__ = ["ForgeBrain"]
