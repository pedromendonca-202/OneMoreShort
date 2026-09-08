"""FastAPI application factory and the `python -m app.web` entry point (bound to 127.0.0.1 only)."""
from __future__ import annotations

from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any

from fastapi import FastAPI, Request
from fastapi.responses import FileResponse, JSONResponse
from fastapi.staticfiles import StaticFiles

from app.core.config import Settings, load_settings
from app.core.errors import HumanActionRequired, OMSError
from app.core.logging import configure_logging, get_logger
from app.web.deps import WebContext
from app.web.events import EventBus, JobRunner
from app.web.routes import all_routers
from app.web.security import CsrfMiddleware, SecurityHeadersMiddleware

STATIC_DIR = Path(__file__).resolve().parent / "static"
HOST, PORT = "127.0.0.1", 8787
log = get_logger(component="web")


def build_context(settings: Settings | None = None, orchestrator: Any | None = None) -> WebContext:
    settings = settings or load_settings()
    if orchestrator is None:
        from app.pipeline.orchestrator import Orchestrator

        orchestrator = Orchestrator(settings)
    bus = EventBus()
    return WebContext(settings=settings, orchestrator=orchestrator, bus=bus, jobs=JobRunner(bus, orchestrator))


def create_app(settings: Settings | None = None, orchestrator: Any | None = None, *, ctx: WebContext | None = None) -> FastAPI:
    ctx = ctx or build_context(settings, orchestrator)

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        import asyncio

        ctx.bus.bind_loop(asyncio.get_running_loop())
        yield
        ctx.jobs.shutdown()

    app = FastAPI(title="OneMoreShort Painel", docs_url=None, redoc_url=None, openapi_url=None, lifespan=lifespan)
    app.state.ctx = ctx
    app.add_middleware(CsrfMiddleware, token=ctx.csrf_token)
    app.add_middleware(SecurityHeadersMiddleware)

    @app.exception_handler(HumanActionRequired)
    async def _human_action(_: Request, err: HumanActionRequired) -> JSONResponse:
        return JSONResponse({"error": "human_action", "message": err.problem, "human_action": err.as_dict()}, status_code=409)

    @app.exception_handler(OMSError)
    async def _oms_error(_: Request, err: OMSError) -> JSONResponse:
        return JSONResponse({"error": "engine", "message": str(err)}, status_code=400)

    @app.exception_handler(ValueError)
    async def _value_error(_: Request, err: ValueError) -> JSONResponse:
        return JSONResponse({"error": "invalid", "message": str(err)}, status_code=400)

    for router in all_routers():
        app.include_router(router)

    app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

    @app.get("/{path:path}", include_in_schema=False)
    async def spa(path: str):
        if path.startswith("api/"):
            return JSONResponse({"error": "not_found", "message": "rota desconhecida"}, status_code=404)
        return FileResponse(STATIC_DIR / "index.html", media_type="text/html")

    return app


def main() -> None:
    import uvicorn

    settings = load_settings()
    configure_logging(settings.resolve(settings.paths.logs_dir), settings.log_level)
    log.info("web.start", host=HOST, port=PORT, mode=settings.mode)
    uvicorn.run(create_app(settings), host=HOST, port=PORT, log_level="warning")


if __name__ == "__main__":
    main()
