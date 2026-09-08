from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.core.db import session_scope
from app.web.chat import TOOLS, Assistant, history
from app.web.deps import WebContext, get_ctx
from app.web.queries import recent_activity, to_local
from app.web.schemas import ChatMessage

router = APIRouter(prefix="/api/chat", tags=["chat"])

QUICK_COMMANDS = [
    {"icon": "play", "title": "Começar o dia", "text": "Tema + roteiro + prompts", "message": "começa o vídeo de hoje"},
    {"icon": "refresh-cw", "title": "Trocar tema", "text": "Sugerir um novo assunto", "message": "o tema tá fraco, tenta outro"},
    {"icon": "file-text", "title": "Refazer roteiro", "text": "Melhorar o roteiro atual", "message": "refaz o roteiro"},
    {"icon": "clapperboard", "title": "Montar vídeo", "text": "Gerar no estúdio", "message": "monta o vídeo"},
    {"icon": "upload", "title": "Publicar", "text": "Enviar para o YouTube", "message": "publica o vídeo"},
]

CAPABILITIES = [
    {"icon": "clapperboard", "title": "Produzir", "text": "Encontra temas, escreve roteiros e gera prompts."},
    {"icon": "bar-chart-3", "title": "Consultar", "text": "Analisa desempenho e traz insights."},
    {"icon": "upload", "title": "Publicar", "text": "Monta, edita e publica no YouTube."},
    {"icon": "lightbulb", "title": "Explicar", "text": "Tira dúvidas e ensina como usar melhor."},
]


@router.post("")
def send(body: ChatMessage, ctx: WebContext = Depends(get_ctx)) -> dict:
    if not ctx.limit("chat"):
        raise HTTPException(429, "muitas mensagens seguidas; aguarde um minuto")
    reply = Assistant(ctx).respond(body.message)
    local = ctx.local_now()
    return {**reply.model_dump(), "time": local.strftime("%H:%M")}


@router.get("/history")
def get_history(ctx: WebContext = Depends(get_ctx)) -> dict:
    with session_scope(ctx.orchestrator.engine) as session:
        activity = recent_activity(session, ctx.now(), ctx.settings.timezone)
    return {"messages": history(ctx), "activity": activity, "quick_commands": QUICK_COMMANDS, "capabilities": CAPABILITIES,
            "tools": [{"name": name, "description": spec["description"]} for name, spec in TOOLS.items()]}
