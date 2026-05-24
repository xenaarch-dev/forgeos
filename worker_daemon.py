"""
ForgeOS worker daemon.

Starts an rq worker that drains the "forgeos" queue.
Restarts automatically on crash (via systemd or manual re-run).

Usage:
    PYTHONPATH=. python3 worker_daemon.py
    # or with god-mode enabled:
    PYTHONPATH=. python3 worker_daemon.py --god-mode
"""

from __future__ import annotations

import argparse
import logging
import os
import sys
import time
from pathlib import Path

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger("forgeos.worker")


def _parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(description="ForgeOS rq worker daemon")
    p.add_argument("--god-mode", action="store_true", help="Enable god-mode (autonomous healing)")
    p.add_argument("--queues", default="forgeos", help="Comma-separated queue names")
    p.add_argument("--burst", action="store_true", help="Exit after draining current queue")
    return p.parse_args()


def main() -> None:
    args = _parse_args()
    if args.god_mode:
        os.environ["FORGEOS_GOD_MODE"] = "1"
        log.info("God-mode ENABLED — autonomous healing and continuous learning active")

    queues = [q.strip() for q in args.queues.split(",")]

    try:
        from redis import Redis
        from rq import Worker, Queue as RQQueue
        from config import RUNTIME

        redis_url = getattr(RUNTIME, "redis_url", None) or os.environ.get("REDIS_URL", "redis://localhost:6379")
        conn = Redis.from_url(redis_url)
        conn.ping()
    except Exception as e:
        log.error(f"Redis unavailable ({e}) — worker cannot start")
        sys.exit(1)

    log.info(f"Connecting to Redis at {redis_url}, watching queues: {queues}")
    rq_queues = [RQQueue(q, connection=conn) for q in queues]

    worker = Worker(rq_queues, connection=conn)
    log.info(f"Worker {worker.name} starting (burst={args.burst})")

    try:
        worker.work(burst=args.burst, with_scheduler=True)
    except KeyboardInterrupt:
        log.info("Worker stopped by user")
    except Exception as e:
        log.error(f"Worker crashed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
