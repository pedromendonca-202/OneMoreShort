"""Operator CLI. Run with: python -m app.cli <command>   (or `oms <command>` once installed)."""
from __future__ import annotations

import json
from functools import wraps
from typing import Any, Callable

import typer

from app.core.config import load_settings
from app.core.errors import HumanActionRequired, OMSError

app = typer.Typer(no_args_is_help=True, add_completion=False, help="OneMoreShort: autonomous Shorts factory with manual Flow visuals.")

# Windows consoles default to cp1252; paths and reports contain accents.
for _stream in ("stdout", "stderr"):
    try:
        getattr(__import__("sys"), _stream).reconfigure(encoding="utf-8", errors="replace")
    except (AttributeError, ValueError):  # not a real console (tests, pipes)
        pass


def _orchestrator():
    from app.pipeline.orchestrator import Orchestrator

    return Orchestrator(load_settings())


def _dump(data: Any) -> None:
    typer.echo(json.dumps(data, indent=2, default=str, ensure_ascii=False))


def guarded(fn: Callable) -> Callable:
    """Print WAITING_FOR_HUMAN_ACTION reports (exit 2) and platform errors (exit 1) instead of tracebacks."""

    @wraps(fn)
    def wrapper(*args: Any, **kwargs: Any):
        try:
            return fn(*args, **kwargs)
        except HumanActionRequired as err:
            typer.echo(err.report(), err=False)
            raise typer.Exit(code=2)
        except OMSError as err:
            typer.echo(f"ERROR: {err}")
            raise typer.Exit(code=1)
        except (ValueError, TimeoutError) as err:
            typer.echo(f"ERROR: {err}")
            raise typer.Exit(code=1)

    return wrapper


@app.command("init-db")
@guarded
def init_db() -> None:
    """Create the SQLite schema."""
    _orchestrator()
    typer.echo("Database ready.")


@app.command()
@guarded
def doctor() -> None:
    """Check configuration, ffmpeg and credentials for the selected mode."""
    settings = load_settings()
    from app.editing.ffmpeg import resolve_ffmpeg

    ffmpeg, ffprobe = resolve_ffmpeg()
    typer.echo(f"mode: {settings.mode} | generation: {settings.generation.mode} (manual = no Veo API cost) | tts: {settings.tts.provider}")
    typer.echo(f"ffmpeg: {ffmpeg}\nffprobe: {ffprobe}")
    typer.echo(f"google api key: {'present' if settings.google_api_key else 'absent'} | upload.enabled: {settings.upload.enabled}")
    missing = settings.missing_live_requirements()
    typer.echo("OK: manual video workflow ready" if not missing else "MISSING:\n- " + "\n- ".join(missing))


@app.command()
@guarded
def new(force: bool = typer.Option(False, "--force", help="Ignore limits.max_videos_per_day.")) -> None:
    """Create a production id (OMS-YYYYMMDD-NNNN)."""
    typer.echo(_orchestrator().new_production(force=force))


@app.command("export-prompts")
@guarded
def export_prompts(production_id: str) -> None:
    """Research, script, storyboard, continuity bible and the five Flow prompts."""
    package = _orchestrator().prepare(production_id)
    typer.echo(f"Prompts: {package.instructions.parent}\nHand-off: {package.instructions}\nInbox: {package.inbox}")


@app.command("collect-clips")
@guarded
def collect_clips(production_id: str) -> None:
    """Validate the five manually generated clips and build the normalized concat."""
    typer.echo(str(_orchestrator().collect(production_id).concat_path))


@app.command()
@guarded
def finish(production_id: str) -> None:
    """Narration, captions, mix, render, quality gate, metadata and (if enabled) upload."""
    orchestrator = _orchestrator()
    final = orchestrator.finish(production_id)
    typer.echo(f"{final}\nstate: {orchestrator.status(production_id)['state']}")


@app.command()
@guarded
def resume(production_id: str) -> None:
    """Continue from the persisted state; stops with an exact human action if clips are missing."""
    typer.echo(f"state: {_orchestrator().resume(production_id)}")


@app.command()
@guarded
def watch(production_id: str, poll: float = typer.Option(15.0, help="Seconds between inbox checks."),
          timeout: float | None = typer.Option(None, help="Give up after this many seconds.")) -> None:
    """Wait for the five clips, then collect and finish automatically."""
    typer.echo(f"Watching inbox for {production_id} (every {poll:g}s)...")
    typer.echo(f"state: {_orchestrator().watch(production_id, poll_s=poll, timeout_s=timeout)}")


@app.command()
@guarded
def status(production_id: str) -> None:
    """Show state, artefacts, upload id and analytics summary."""
    _dump(_orchestrator().status(production_id))


@app.command("list")
@guarded
def list_productions(limit: int = typer.Option(20, help="Most recent productions to show.")) -> None:
    """List recent productions."""
    for row in _orchestrator().list_productions(limit):
        typer.echo(f"{row['id']}  {row['state']:<20} cost=${row['cost_usd']:.4f}  yt={row['youtube_video_id'] or '-'}  {row['topic'] or ''}")


@app.command()
@guarded
def analytics() -> None:
    """Capture due analytics checkpoints for every published video."""
    collected = _orchestrator().collect_analytics()
    typer.echo(f"snapshots captured: {len(collected)}" + (f" -> {', '.join(collected)}" if collected else ""))


@app.command()
@guarded
def learn() -> None:
    """Refresh insights, strategy weights, knowledge base and per-video reports."""
    summary = _orchestrator().learn()
    typer.echo(f"videos analysed: {summary.videos} | insights: {len(summary.insights)}")
    for question, answer in summary.answers.items():
        typer.echo(f"- {question} {answer}")


@app.command()
@guarded
def report(production_id: str) -> None:
    """Print the latest performance report for a production."""
    typer.echo(_orchestrator().report(production_id))


@app.command()
@guarded
def daily() -> None:
    """The scheduled run: analytics -> learn -> advance today's production."""
    summary = _orchestrator().daily()
    _dump(summary)
    if summary.get("human_action"):
        action = summary["human_action"]
        typer.echo("\nWAITING_FOR_HUMAN_ACTION\nPROBLEM: " + action["problem"] + "\nEXACT HUMAN ACTION REQUIRED: " + action["action"]
                   + "\nNEXT AUTOMATIC STEP: " + action["next_step"])


@app.command()
@guarded
def metrics() -> None:
    """Operational metrics: generated, published, success/failure rates, cost, API errors."""
    _dump(_orchestrator().metrics())


@app.command()
@guarded
def costs(days: int = typer.Option(30, help="Window in days.")) -> None:
    """Spend today, over the window, and per API."""
    _dump(_orchestrator().costs(days))


@app.command("youtube-auth")
@guarded
def youtube_auth() -> None:
    """One-time OAuth consent (upload + read-only + analytics scopes)."""
    from app.youtube.auth import get_credentials

    settings = load_settings()
    get_credentials(settings.resolve(settings.youtube_client_secret_path), settings.resolve(settings.youtube_token_path))
    typer.echo("YouTube OAuth complete. Token saved; analytics and uploads will reuse it.")


if __name__ == "__main__":
    app()
