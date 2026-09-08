"""Operator CLI. Run with: python -m app.cli <command>."""
from __future__ import annotations
import typer
from app.core.config import load_settings
from app.pipeline.orchestrator import Orchestrator
from app.youtube.auth import get_credentials
app=typer.Typer(no_args_is_help=True)
def orch(): return Orchestrator(load_settings())
@app.command("init-db")
def init_db(): orch();typer.echo("Database ready.")
@app.command("new")
def new(): typer.echo(orch().new_production())
@app.command("export-prompts")
def export_prompts(production_id:str):
 p=orch().prepare(production_id);typer.echo(f"Prompts: {p.instructions}\nInbox: {p.inbox}")
@app.command("collect-clips")
def collect_clips(production_id:str): typer.echo(orch().collect(production_id).concat_path)
@app.command()
def finish(production_id:str): typer.echo(orch().finish(production_id))
@app.command()
def status(production_id:str): typer.echo(orch().status(production_id))
@app.command()
def doctor():
 s=load_settings();missing=s.missing_live_requirements();typer.echo("OK: manual video workflow" if not missing else "MISSING:\n"+"\n".join(missing))
@app.command("youtube-auth")
def youtube_auth():
 s=load_settings();get_credentials(s.resolve(s.youtube_client_secret_path),s.resolve(s.youtube_token_path),["https://www.googleapis.com/auth/youtube.upload"]);typer.echo("YouTube OAuth complete.")
if __name__=="__main__":app()
