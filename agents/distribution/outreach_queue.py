#!/usr/bin/env python3
"""OutreachQueue — manages outreach DM queue stored in queue.jsonl.

CLI:
    python3 agents/distribution/outreach_queue.py add --handle "designerpriya" --platform "x"
    python3 agents/distribution/outreach_queue.py review
    python3 agents/distribution/outreach_queue.py stats
"""
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

QUEUE_PATH = Path(__file__).parent / "queue.jsonl"


def _load_queue() -> list:
    if not QUEUE_PATH.exists():
        return []
    entries = []
    with open(QUEUE_PATH) as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    return entries


def _save_queue(entries: list) -> None:
    with open(QUEUE_PATH, "w") as f:
        for entry in entries:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def _copy_to_clipboard(text: str) -> bool:
    for cmd in [["clip.exe"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return False


def cmd_add(handle: str, platform: str) -> None:
    entries = _load_queue()
    existing = [e for e in entries if e["handle"] == handle and e["platform"] == platform]
    if existing:
        print(f"@{handle} on {platform} already in queue (status: {existing[0]['status']}).")
        return

    draft_dm = ""
    prospect_summary = ""

    try:
        context = input(f"Context for @{handle} (Enter to skip DM draft): ").strip()
    except (KeyboardInterrupt, EOFError):
        context = ""

    if context:
        try:
            sys.path.insert(0, str(Path(__file__).parent.parent.parent))
            from agents.distribution.prospect_agent import research_prospect, interactive_review, _load_env
            _load_env()
            if os.environ.get("ANTHROPIC_API_KEY"):
                print(f"Drafting DM for @{handle}...")
                data = research_prospect(handle, platform, context)
                data = interactive_review(handle, data)
                draft_dm = data.get("dm", "")
                prospect_summary = data.get("prospect_summary", "")
        except Exception as e:
            print(f"DM draft skipped: {e}")

    entry = {
        "handle": handle,
        "platform": platform,
        "status": "pending",
        "draft_dm": draft_dm,
        "prospect_summary": prospect_summary,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "sent_at": None,
    }
    entries.append(entry)
    _save_queue(entries)
    pending = sum(1 for e in entries if e["status"] == "pending")
    print(f"Added @{handle} ({platform}). Pending total: {pending}")


def cmd_review() -> None:
    entries = _load_queue()
    pending = [e for e in entries if e["status"] == "pending"]
    if not pending:
        print("No pending entries.")
        return

    batch = pending[:3]
    bar = "═" * 34

    for i, entry in enumerate(batch, 1):
        print(f"\n{bar}")
        print(f"[{i}/{len(batch)}] @{entry['handle']} on {entry['platform']}")
        if entry.get("prospect_summary"):
            print(f"WHO: {entry['prospect_summary']}")
        if entry.get("draft_dm"):
            print(f"\nDRAFT DM:\n{entry['draft_dm']}")
        else:
            print("(no DM draft — run prospect_agent.py to generate one)")
        print(f"\n[S]ent  [E]dit DM  [K]eep pending  [X]skip")
        print(bar)

        while True:
            try:
                choice = input("\nChoice: ").strip().upper()
            except (KeyboardInterrupt, EOFError):
                print("\nReview ended.")
                _save_queue(entries)
                return

            if choice == "S":
                entry["status"] = "sent"
                entry["sent_at"] = datetime.now(timezone.utc).isoformat()
                print("Marked as sent.")
                break
            elif choice == "E":
                print("Edit DM (blank line to finish):")
                lines = []
                while True:
                    line = input()
                    if not line and lines:
                        break
                    lines.append(line)
                if lines:
                    entry["draft_dm"] = "\n".join(lines)
                    if _copy_to_clipboard(entry["draft_dm"]):
                        print("DM updated and copied to clipboard.")
                    else:
                        print("DM updated.")
                break
            elif choice == "K":
                print("Kept pending.")
                break
            elif choice == "X":
                entry["status"] = "skip"
                print("Skipped.")
                break
            else:
                print("Enter S, E, K, or X.")

    _save_queue(entries)


def cmd_stats() -> None:
    entries = _load_queue()
    if not entries:
        print("Queue is empty.")
        return

    counts: dict = {}
    for e in entries:
        s = e.get("status", "pending")
        counts[s] = counts.get(s, 0) + 1

    print("\nOutreach Queue Stats")
    print("════════════════════")
    print(f"Total:    {len(entries)}")
    for status in ("pending", "sent", "replied", "skip"):
        if counts.get(status, 0) > 0:
            print(f"{status.capitalize():<10} {counts[status]}")

    sent = [e for e in entries if e.get("status") == "sent" and e.get("sent_at")]
    if sent:
        sent.sort(key=lambda e: e["sent_at"], reverse=True)
        print(f"\nLast sent: @{sent[0]['handle']} ({sent[0]['sent_at'][:10]})")


def main() -> None:
    parser = argparse.ArgumentParser(description="Outreach DM queue manager")
    sub = parser.add_subparsers(dest="cmd", required=True)

    add_p = sub.add_parser("add", help="Add a prospect to the queue")
    add_p.add_argument("--handle", required=True, help="Handle without @")
    add_p.add_argument("--platform", required=True, help="x, linkedin, instagram")

    sub.add_parser("review", help="Review next 3 pending entries")
    sub.add_parser("stats", help="Show queue statistics")

    args = parser.parse_args()

    if args.cmd == "add":
        cmd_add(args.handle, args.platform)
    elif args.cmd == "review":
        cmd_review()
    elif args.cmd == "stats":
        cmd_stats()


if __name__ == "__main__":
    main()
