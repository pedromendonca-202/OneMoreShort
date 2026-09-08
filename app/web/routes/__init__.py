"""API routers of the panel."""
from __future__ import annotations

from fastapi import APIRouter


def all_routers() -> list[APIRouter]:
    from app.web.routes import analytics, chat, intelligence, productions, settings, system, today

    return [system.router, today.router, productions.router, analytics.router, intelligence.router, settings.router, chat.router]
