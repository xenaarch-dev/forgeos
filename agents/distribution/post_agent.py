#!/usr/bin/env python3
"""PostAgent — drafts X posts in Xena's voice from build events.

CLI:
    python3 agents/distribution/post_agent.py \
        --event "feature_shipped" \
        --description "auth redirect fixed, QA green" \
        --product "ContractForge"
"""
import argparse
import json
import os
import subprocess
import sys

SYSTEM_PROMPT = """You are writing X (Twitter) posts for Xena, founder of ForgeOS and ContractForge, building in public.

Voice rules (enforce strictly):
- Direct and specific. Real numbers. Real tech. Real problems.
- Lowercase is fine. Fragments are fine.
- NEVER use: "excited to announce", "thrilled to share", "game-changer", "I'm proud"
- NEVER use 🚀 or 💡 — those two emojis are permanently banned
- No corporate language. No buzzwords.
- Short sentences. One idea per tweet.
- Talk like a builder after a long session, not a marketer.

Return valid JSON only. No markdown code fences. Exact schema:
{
  "main": "post text, max 280 chars",
  "thread": ["tweet text", "tweet text"],
  "hashtags": "#buildinpublic",
  "attach": "what screenshot to attach, or 'none'"
}

thread: 2-3 tweets only if the event warrants more detail. Use [] if not needed.
main: count characters carefully. Must be 280 or fewer."""


def _load_env() -> None:
    if os.environ.get("ANTHROPIC_API_KEY"):
        return
    env_path = os.path.join(os.path.dirname(__file__), "..", "..", ".env")
    if os.path.exists(env_path):
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("ANTHROPIC_API_KEY="):
                    os.environ["ANTHROPIC_API_KEY"] = line.split("=", 1)[1]
                    break


def generate_post(event: str, description: str, product: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=500,
        temperature=0.7,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Build event for {product}:\n\n"
                f"Event type: {event}\n"
                f"Description: {description}\n\n"
                "Write an X post in Xena's voice. Main post must be ≤280 chars. Be specific."
            ),
        }],
    )
    text = msg.content[0].text.strip()
    if text.startswith("```"):
        lines = text.splitlines()
        start = 1
        end = len(lines) - 1 if lines[-1].strip() == "```" else len(lines)
        text = "\n".join(lines[start:end])
    return json.loads(text)


def _copy_to_clipboard(text: str) -> bool:
    for cmd in [["clip.exe"], ["xclip", "-selection", "clipboard"], ["xsel", "--clipboard", "--input"]]:
        try:
            subprocess.run(cmd, input=text.encode("utf-8"), check=True, capture_output=True)
            return True
        except (FileNotFoundError, subprocess.CalledProcessError):
            continue
    return False


def _save_draft(data: dict, event: str, product: str) -> str:
    from datetime import datetime
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    drafts_dir = os.path.join(os.path.dirname(__file__), "..", "..", "drafts", "posts")
    os.makedirs(drafts_dir, exist_ok=True)
    slug = f"{ts}_{product.lower().replace(' ', '_')}_{event.lower().replace(' ', '_')}"
    path = os.path.join(drafts_dir, f"{slug}.txt")
    parts = [data["main"]]
    if data.get("thread"):
        n = len(data["thread"])
        for i, t in enumerate(data["thread"], 1):
            parts.append(f"[{i}/{n}] {t}")
    parts.append(data.get("hashtags", "#buildinpublic"))
    parts.append(f"ATTACH: {data.get('attach', 'none')}")
    with open(path, "w") as f:
        f.write("\n\n".join(parts))
    return path


def _display(data: dict) -> None:
    bar = "═" * 34
    print(f"\n{bar}")
    print("DRAFT POST — review before sending")
    print(bar)
    print()
    print(data["main"])
    print()
    if data.get("thread"):
        n = len(data["thread"])
        print("THREAD (optional):")
        for i, t in enumerate(data["thread"], 1):
            print(f"[{i}/{n}] {t}")
        print()
    print(f'HASHTAGS: {data.get("hashtags", "#buildinpublic")}')
    print(f'ATTACH: {data.get("attach", "none")}')
    print()
    print("[C]opy  [E]dit  [S]kip")
    print(bar)


def interactive_review(data: dict, event: str = "", product: str = "") -> None:
    _display(data)
    while True:
        try:
            choice = input("\nChoice: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nSkipped.")
            return
        if choice == "C":
            parts = [data["main"]]
            if data.get("thread"):
                n = len(data["thread"])
                for i, t in enumerate(data["thread"], 1):
                    parts.append(f"\n[{i}/{n}] {t}")
            parts.append(data.get("hashtags", "#buildinpublic"))
            full = "\n".join(parts)
            if _copy_to_clipboard(full):
                print("Copied to clipboard.")
            else:
                print("Clipboard unavailable. Text:\n")
                print(full)
            if event and product:
                path = _save_draft(data, event, product)
                print(f"Draft saved: {path}")
            return
        elif choice == "E":
            print("Edit main post (blank line to finish):")
            lines = []
            while True:
                line = input()
                if not line and lines:
                    break
                lines.append(line)
            if lines:
                data["main"] = "\n".join(lines)
                if len(data["main"]) > 280:
                    data["main"] = data["main"][:277] + "..."
            _display(data)
        elif choice == "S":
            print("Skipped.")
            return
        else:
            print("Enter C, E, or S.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Draft X posts in Xena's voice")
    parser.add_argument("--event", required=True, help="Event type, e.g. feature_shipped")
    parser.add_argument("--description", required=True, help="What happened")
    parser.add_argument("--product", required=True, help="Product name, e.g. ContractForge")
    args = parser.parse_args()

    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set. Add to .env or export it.")
        sys.exit(1)

    print(f"Drafting [{args.product}] — event: {args.event}")
    data = generate_post(args.event, args.description, args.product)
    if len(data["main"]) > 280:
        data["main"] = data["main"][:277] + "..."
    interactive_review(data, event=args.event, product=args.product)


if __name__ == "__main__":
    main()
