"""
ForgeOS drainer — process the build queue and check Telegram in one pass.

Invoked by Windows Task Scheduler (see schtasks command in STATE.md):
  wsl.exe -d Ubuntu-22.04 -e bash -lc
    "cd /home/padmaja/forge/forgeos && PYTHONPATH=. python3 -m daemon.drainer"

Each invocation:
  1. Polls Telegram for new messages (no-ops silently if credentials missing).
     Any text message from the configured chat is treated as a build idea and
     added to the queue.
  2. Pops the oldest pending job (FIFO).
  3. Runs the full HermesOrchestrator pipeline.
  4. Archives the job with status=success or status=failed.

Only ONE job is processed per invocation — the Task Scheduler trigger frequency
controls the build cadence. The queue absorbs bursts (e.g. multiple Telegram
messages before the scheduler fires again).

Environment variables:
  FORGEOS_AUTO_DEPLOY=1    — enable GitHub/Railway/Vercel deploy inside the build
  TELEGRAM_BOT_TOKEN=...   — Telegram bot token; omit to skip Telegram polling
  TELEGRAM_CHAT_ID=...     — numeric chat ID where ideas arrive
"""

from __future__ import annotations

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

from agents.hermes import HermesOrchestrator
from daemon.queue import BuildQueue

# Telegram offset persists across invocations so we never re-process a message.
_STATE_DIR = Path("daemon/state")
_TG_OFFSET_FILE = _STATE_DIR / "telegram_offset.txt"


def _tg_poll(queue: BuildQueue) -> int:
    """
    Poll Telegram for new messages. Enqueues each as a build idea.
    Returns the number of new ideas enqueued. No-ops silently without credentials.
    """
    token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = os.environ.get("TELEGRAM_CHAT_ID", "")
    if not token or not chat_id:
        return 0

    offset = _read_offset()
    updates = _fetch_updates(token, offset)
    if updates is None:
        return 0

    enqueued = 0
    max_update_id = offset - 1

    for update in updates:
        update_id: int = update.get("update_id", 0)
        if update_id > max_update_id:
            max_update_id = update_id

        msg: dict[str, Any] = update.get("message") or {}
        from_chat_id = str((msg.get("chat") or {}).get("id", ""))
        text = (msg.get("text") or "").strip()

        if from_chat_id != str(chat_id):
            continue
        if not text:
            continue

        queue.enqueue(text, source="telegram")
        enqueued += 1

    # Advance offset so the next poll skips these updates.
    if max_update_id >= offset:
        _write_offset(max_update_id + 1)

    return enqueued


def _read_offset() -> int:
    if _TG_OFFSET_FILE.exists():
        try:
            return int(_TG_OFFSET_FILE.read_text(encoding="utf-8").strip())
        except ValueError:
            pass
    return 0


def _write_offset(offset: int) -> None:
    _STATE_DIR.mkdir(parents=True, exist_ok=True)
    _TG_OFFSET_FILE.write_text(str(offset), encoding="utf-8")


def _fetch_updates(token: str, offset: int) -> list[dict[str, Any]] | None:
    url = (
        f"https://api.telegram.org/bot{token}/getUpdates"
        f"?offset={offset}&limit=20&timeout=5"
    )
    try:
        with urllib.request.urlopen(url, timeout=10) as resp:
            data: dict[str, Any] = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError) as exc:
        sys.stderr.write(f"[drainer/tg] poll failed: {exc}\n")
        return None
    if not data.get("ok"):
        sys.stderr.write(f"[drainer/tg] API returned not-ok: {data}\n")
        return None
    return data.get("result", [])


def drain_once(queue: BuildQueue | None = None) -> bool:
    """
    Process one pending job from the queue.

    Returns True if a job was processed, False if the queue was empty.
    Exceptions raised by the build are caught, archived as failed, and
    re-raised so the caller (or Task Scheduler) can detect failure.
    """
    if queue is None:
        queue = BuildQueue()

    job = queue.pop_next()
    if job is None:
        return False

    idea: str = job["idea"]
    _print(f"starting build: {idea!r}")

    try:
        ctx = HermesOrchestrator(idea=idea).run()
        queue.archive(job, status="success")
        _print(f"build complete: {ctx.project_id}")
    except Exception as exc:
        err = str(exc)
        queue.archive(job, status="failed", error=err)
        _print(f"build FAILED: {err[:200]}")
        raise

    return True


def main() -> None:
    queue = BuildQueue()

    enqueued = _tg_poll(queue)
    if enqueued:
        _print(f"{enqueued} idea(s) added from Telegram")
    elif not os.environ.get("TELEGRAM_BOT_TOKEN"):
        _print("Telegram not configured (TELEGRAM_BOT_TOKEN missing) — skipping poll")

    pending = queue.pending_count()
    _print(f"queue depth: {pending} pending job(s)")

    try:
        processed = drain_once(queue)
    except Exception:
        sys.exit(1)

    if not processed:
        _print("queue empty — nothing to build")


def _print(msg: str) -> None:
    print(f"[drainer] {msg}", flush=True)


if __name__ == "__main__":
    main()
