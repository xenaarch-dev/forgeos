#!/usr/bin/env python3
"""ProspectAgent — researches Indian freelancers and drafts personalized DMs.

CLI:
    python3 agents/distribution/prospect_agent.py \
        --handle "testhandle" \
        --platform "x" \
        --context "replied to tweet about contracts"
"""
import argparse
import json
import os
import subprocess
import sys

SYSTEM_PROMPT = """You are drafting personalized DMs for Xena, founder of ContractForge.

ContractForge: AI contract generator for Indian freelancers and consultants.
- GST-compliant service agreements, NDA templates, SOW generation
- PDF export with rupee amounts and Indian jurisdiction clauses
- Free first contract, no credit card required
- ₹1,499 per contract or ₹2,499/month subscription

DM rules (enforce strictly):
- Reference something specific from the context provided — never generic
- Under 150 words total
- Offer the free first contract with no card required
- End with a yes/no question
- NEVER use: "game-changer", "I think you'd love", "revolutionize", "disruptive", "powerful"
- Sound like a founder reaching out directly, not a marketing team
- Be direct. Freelancer-to-freelancer tone.
- Do not mention AI unless they brought it up

Return valid JSON only. No markdown code fences. Exact schema:
{
  "prospect_summary": "who they are, 1 sentence",
  "pain": "inferred pain point based on context",
  "fit": "High|Medium|Low",
  "dm": "the DM text, under 150 words"
}"""


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


def research_prospect(handle: str, platform: str, context: str) -> dict:
    import anthropic
    client = anthropic.Anthropic()
    msg = client.messages.create(
        model="claude-sonnet-4-6",
        max_tokens=400,
        temperature=0.5,
        system=SYSTEM_PROMPT,
        messages=[{
            "role": "user",
            "content": (
                f"Prospect:\n"
                f"Handle: @{handle}\n"
                f"Platform: {platform}\n"
                f"Context: {context}\n\n"
                "Assess fit and draft a personalized DM from Xena."
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


def _display(handle: str, data: dict) -> None:
    bar = "═" * 34
    print(f"\n{bar}")
    print(f"PROSPECT: @{handle} — {data['prospect_summary']}")
    print(f"PAIN: {data['pain']}")
    print(f"FIT: {data['fit']}")
    print()
    print("DRAFT DM:")
    print(data["dm"])
    print()
    print("[C]opy  [E]dit  [S]kip")
    print(bar)


def interactive_review(handle: str, data: dict) -> dict:
    _display(handle, data)
    while True:
        try:
            choice = input("\nChoice: ").strip().upper()
        except (KeyboardInterrupt, EOFError):
            print("\nSkipped.")
            return data
        if choice == "C":
            if _copy_to_clipboard(data["dm"]):
                print("DM copied to clipboard.")
            else:
                print("Clipboard unavailable. DM:\n")
                print(data["dm"])
            return data
        elif choice == "E":
            print("Edit DM (blank line to finish):")
            lines = []
            while True:
                line = input()
                if not line and lines:
                    break
                lines.append(line)
            if lines:
                data["dm"] = "\n".join(lines)
            _display(handle, data)
        elif choice == "S":
            print("Skipped.")
            return data
        else:
            print("Enter C, E, or S.")


def main() -> None:
    parser = argparse.ArgumentParser(description="Research prospects and draft DMs")
    parser.add_argument("--handle", required=True, help="Target handle (without @)")
    parser.add_argument("--platform", required=True, help="Platform: x, linkedin, instagram")
    parser.add_argument("--context", required=True, help="Context: what you know about them")
    args = parser.parse_args()

    _load_env()
    if not os.environ.get("ANTHROPIC_API_KEY"):
        print("Error: ANTHROPIC_API_KEY not set. Add to .env or export it.")
        sys.exit(1)

    print(f"Researching @{args.handle} on {args.platform}...")
    data = research_prospect(args.handle, args.platform, args.context)
    interactive_review(args.handle, data)


if __name__ == "__main__":
    main()
