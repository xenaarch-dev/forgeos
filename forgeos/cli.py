"""
ForgeOS CLI — build, status, init.

Entry point: forgeos.cli:main
"""
from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

import click


@click.group()
@click.version_option(package_name="forgeos")
def cli() -> None:
    """ForgeOS: autonomous multi-agent product factory.

    One English sentence -> a built, tested, secured, deployed SaaS.
    """


@cli.command()
@click.argument("idea")
@click.option(
    "--workdir", "-w", default=None,
    help="Resume an interrupted build by providing its workdir path.",
)
@click.option(
    "--legacy", is_flag=True, default=False,
    help="Use V1 flat pipeline (no quality gates, faster).",
)
def build(idea: str, workdir: str | None, legacy: bool) -> None:
    """Start a ForgeOS build from a plain-language IDEA.

    \b
    Examples:
      forgeos build "Build a habit tracker SaaS at $12/mo"
      forgeos build "Build ContractForge — AI contract SaaS at $29/mo" --legacy
      forgeos build "same idea" --workdir builds/<id>
    """
    from forgeos.pipeline import run_build

    sys.exit(run_build(idea, workdir=workdir, legacy=legacy))


@cli.command()
@click.argument("build_id", required=False)
def status(build_id: str | None) -> None:
    """Show build status.

    With no argument, lists all builds. Pass BUILD_ID for a detailed view.

    \b
    Examples:
      forgeos status
      forgeos status abc123
    """
    builds_dir = Path("builds")
    if not builds_dir.exists():
        click.echo("No builds directory found. Run `forgeos build` first.")
        return

    if build_id:
        _show_build(builds_dir / build_id)
    else:
        _list_builds(builds_dir)


def _list_builds(builds_dir: Path) -> None:
    dirs = sorted(
        (d for d in builds_dir.iterdir() if d.is_dir()),
        key=lambda d: d.stat().st_mtime,
        reverse=True,
    )
    if not dirs:
        click.echo("No builds found.")
        return

    click.echo(f"\n{'ID':<36}  {'IDEA':<44}  STATUS")
    click.echo("-" * 92)
    for d in dirs:
        ctx_file = d / "context.json"
        if not ctx_file.exists():
            click.echo(f"{d.name:<36}  {'(no context.json)':<44}  unknown")
            continue
        try:
            ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
        except Exception:
            click.echo(f"{d.name:<36}  {'(unreadable)':<44}  error")
            continue
        idea = (ctx.get("idea") or "")[:43]
        phase = ctx.get("current_phase") or "—"
        agents = ctx.get("agents") or []
        ok = sum(1 for a in agents if a.get("status") == "success")
        fail = sum(1 for a in agents if a.get("status") == "failed")
        summary = f"{ok} ok / {fail} failed @ {phase}"
        click.echo(f"{d.name:<36}  {idea:<44}  {summary}")


def _show_build(build_dir: Path) -> None:
    ctx_file = build_dir / "context.json"
    if not ctx_file.exists():
        click.echo(f"Build not found: {build_dir}", err=True)
        sys.exit(1)
    try:
        ctx = json.loads(ctx_file.read_text(encoding="utf-8"))
    except Exception as e:
        click.echo(f"Could not read context.json: {e}", err=True)
        sys.exit(1)

    click.echo(f"\nProject:  {ctx.get('project_id', '?')}")
    click.echo(f"Idea:     {ctx.get('idea', '?')}")
    click.echo(f"Phase:    {ctx.get('current_phase', '?')}")
    click.echo(f"Repo:     {ctx.get('repo_url') or '(none)'}")
    click.echo(f"Backend:  {ctx.get('backend_url') or '(none)'}")
    click.echo(f"Frontend: {ctx.get('frontend_url') or '(none)'}")

    agents = ctx.get("agents") or []
    if agents:
        click.echo(f"\nAgents ({len(agents)}):")
        for a in agents:
            ok = a.get("status") == "success"
            name = a.get("name", "?")
            dur = a.get("duration_seconds")
            dur_str = f"  {dur:.1f}s" if dur else ""
            err = a.get("error")
            line = f"  {'ok  ' if ok else 'FAIL'} {name:<22}{dur_str}"
            if err:
                line += f"\n       {err[:80]}"
            click.echo(line)


@cli.command()
def init() -> None:
    """Initialize a .env file for ForgeOS.

    Copies .env.example if it exists; otherwise writes a template with all
    supported keys so you know what to fill in.
    """
    env_file = Path(".env")
    example_file = Path(".env.example")

    if env_file.exists():
        click.echo(".env already exists — not overwriting.")
        click.echo("Edit it directly to update your keys.")
        return

    if example_file.exists():
        shutil.copy(example_file, env_file)
        click.echo("Created .env from .env.example.")
    else:
        env_file.write_text(
            "# ForgeOS environment\n"
            "\n"
            "# Required — Claude fallback for quality gates\n"
            "ANTHROPIC_API_KEY=sk-ant-...\n"
            "\n"
            "# Optional — local LLM (free, GPU-accelerated)\n"
            "OLLAMA_MODEL=qwen2.5-coder:7b\n"
            "ANTHROPIC_MODEL=claude-haiku-4-5\n"
            "\n"
            "# Optional — deploy targets\n"
            "GITHUB_TOKEN=\n"
            "RAILWAY_TOKEN=\n"
            "VERCEL_TOKEN=\n"
            "\n"
            "# Optional — generated project database\n"
            "SUPABASE_URL=\n"
            "SUPABASE_ANON_KEY=\n"
            "SUPABASE_SERVICE_ROLE_KEY=\n"
            "SUPABASE_ACCESS_TOKEN=\n"
            "\n"
            "# Optional — notifications (Hermes Agent)\n"
            "TELEGRAM_BOT_TOKEN=\n"
            "TELEGRAM_CHAT_ID=\n"
            "\n"
            "# Optional — monitoring\n"
            "SENTRY_AUTH_TOKEN=\n"
            "UPTIMEROBOT_API_KEY=\n"
            "\n"
            "# Optional — pipeline tuning\n"
            "GSTACK_MIN_SCORE=7.0\n"
            "MISSION_MAX_FEATURES=12\n",
            encoding="utf-8",
        )
        click.echo("Created .env with all supported keys.")

    click.echo("\nNext steps:")
    click.echo("  1. Edit .env — add ANTHROPIC_API_KEY at minimum")
    click.echo("  2. forgeos build \"Build a habit tracker SaaS at $12/mo\"")


def main() -> None:
    cli()


if __name__ == "__main__":
    main()
