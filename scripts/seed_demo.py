"""Populate a SEPARATE demo database with data equivalent to the design references (design/*.png).

Used only to compare the built screens with the mockups pixel by pixel. Never touches database/oms.db:
it writes database/demo.db and storage_demo/ (thumbnails copied from app/web/static/img/demo).

Run:   .venv/Scripts/python.exe scripts/seed_demo.py [--clips 0|4|5]
Serve: scripts/demo.ps1   (sets OMS_PATHS__DATABASE_URL / OMS_PATHS__STORAGE_ROOT and starts the panel)
"""
from __future__ import annotations

import argparse
import shutil
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from app.core.db import get_engine, init_db, session_scope  # noqa: E402
from app.core.models import (  # noqa: E402
    AnalyticsSnapshot, Event, FinalVideo, Insight, Production, Prompt, RetentionCurve, Script, Storyboard, StrategyWeightsRow, Topic,
    Upload, VideoMetadata, VideoReport,
)
from app.core.states import State  # noqa: E402

DB_PATH = ROOT / "database" / "demo.db"
STORAGE = ROOT / "storage_demo"
DEMO_IMG = ROOT / "app" / "web" / "static" / "img" / "demo"
TZ = ZoneInfo("America/Sao_Paulo")
TODAY = datetime(2026, 9, 8, 8, 30, tzinfo=TZ)


def local(day_offset: int, hour: int, minute: int = 0) -> datetime:
    return (TODAY + timedelta(days=day_offset)).replace(hour=hour, minute=minute, second=0, microsecond=0).astimezone(UTC)


SCENES = [
    ("O impacto visual", "Close-up cinematográfico de um copo de vidro vazio. Água sendo despejada em câmera lenta, com gotas e reflexos dramáticos. Fundo escuro, iluminação cinematográfica, realista, ultra detalhado.",
     "Close-up, lente 50mm, movimento suave de aproximação (slow push-in), profundidade de campo rasa, 4K, 60fps, estilo cinematográfico."),
    ("A transformação", "O mesmo copo agora cheio; a água congela lentamente formando um bloco de gelo translúcido com rachaduras internas iluminadas.",
     "Mesmo enquadramento, lente 50mm, leve movimento orbital, luz lateral fria."),
    ("O contexto", "Uma janela de catedral antiga ao amanhecer; a luz atravessa o vidro irregular e ondulado.",
     "Plano médio, 35mm, câmera fixa com leve respiração, contraluz dourado."),
    ("O benefício", "Uma xícara de café sobre a mesa ao lado do copo; vapor sobe devagar; a luz da manhã revela o vidro perfeitamente estável.",
     "Plano detalhe, 50mm, travelling lateral lento, luz quente."),
    ("O encerramento", "O copo volta ao centro, intacto, com um reflexo do logo em vermelho no fundo escuro; o loop fecha na primeira imagem.",
     "Close-up, 50mm, push-in final até o reflexo, luz cinematográfica."),
]
NEGATIVE = "texto, legenda, logotipo, pessoas, mãos, marcas, low quality, blur, pixelado, cartoon, animation, artefatos, deformações."

BEATS_GLASS = [
    (1, 0, 3, "hook", "Glass is not a solid. Not really."),
    (2, 3, 9, "setup", "Everything you were told about glass in school is a simplification."),
    (3, 9, 17, "escalation", "Zoom in far enough and its atoms look like a liquid frozen mid-motion."),
    (4, 17, 25, "revelation", "That is why old cathedral windows look thicker at the bottom. Or is it?"),
    (5, 25, 33, "payoff", "It would take longer than the age of the universe for glass to flow."),
    (6, 33, 38, "ending", "So glass is a liquid that never moves. Say that at your next dinner."),
]
BEATS_MAP = [
    (1, 0, 3, "hook", "Você sabia que esse mapa que você viu a vida toda está errado?"),
    (2, 3, 9, "setup", "O que mostram os mapas: a Groenlândia parece do tamanho da África."),
    (3, 9, 17, "escalation", "Mas isso não é bem verdade. A África é catorze vezes maior."),
    (4, 17, 25, "revelation", "A explicação real: a projeção de Mercator estica tudo perto dos polos."),
    (5, 25, 33, "payoff", "Exemplos e comparação: o Brasil cabe dentro da Groenlândia? Nem perto."),
    (6, 33, 34, "ending", "Fecho em loop: agora você nunca mais vai ver o mapa do mesmo jeito."),
]


def beats(rows):
    return [{"index": i, "start_s": s, "end_s": e, "purpose": p, "narration": n} for i, s, e, p, n in rows]


PUBLISHED = [
    # id, title, category, thumb, days_ago, hour, views, retention, likes, subs, duration, curve, structure
    ("OMS-20260907-0001", "O erro do mapa mundial viral", "science", "globe.jpg", -1, 18, 312480, 81, 18204, 2140, 34,
     [100, 96, 92, 90, 88, 86, 84, 82, 80, 78, 76, 74, 72, 70, 68, 67, 66, 65, 64, 63, 62, 61, 49, 48, 47, 46, 45, 44, 42, 40, 37, 34, 31, 29, 28],
     "hook-setup-escalation-revelation-payoff-ending"),
    ("OMS-20260906-0001", "A cor que não existe", "curiosities", "eye.jpg", -2, 18, 18000, 64, 900, 120, 52,
     [100, 88, 80, 74, 70, 66, 62, 58, 55, 50, 46, 42, 38, 34, 30, 26, 22, 18, 15, 12, 12], "hook-setup-revelation-payoff-ending"),
    ("OMS-20260905-0001", "Por que o café acorda?", "health", "coffee.jpg", -3, 18, 24000, 67, 1400, 150, 46,
     [100, 90, 84, 78, 72, 68, 64, 60, 56, 52, 48, 44, 40, 36, 32, 28, 24, 20, 16, 13, 12], "hook-setup-escalation-revelation-payoff-ending"),
    ("OMS-20260827-0001", "O mito da memória fotográfica", "psychology", "brain.jpg", -12, 18, 96000, 72, 5200, 610, 50,
     [100, 92, 86, 80, 76, 72, 68, 64, 60, 56, 52, 48, 44, 40, 36, 32, 28, 24, 20, 17, 15], "hook-escalation-revelation-ending"),
    ("OMS-20260825-0001", "A cidade que afunda sozinha", "world", "city.jpg", -14, 18, 41000, 69, 2100, 240, 47,
     [100, 91, 84, 78, 73, 69, 65, 61, 57, 53, 49, 45, 41, 37, 33, 29, 25, 21, 18, 15, 13], "hook-setup-escalation-revelation-payoff-ending"),
    ("OMS-20260819-0001", "O som que ninguém consegue ouvir", "illusions", "eye-clean.jpg", -20, 18, 33000, 70, 1500, 220, 33,
     [100, 90, 84, 78, 74, 70, 66, 62, 58, 54, 50, 46, 42, 38, 34, 30, 27, 24, 21, 19, 18], "hook-setup-revelation-payoff-ending"),
    ("OMS-20260817-0001", "A ilusão que engana o cérebro", "illusions", None, -22, 18, 21000, 66, 900, 130, 35,
     [100, 88, 80, 74, 68, 64, 60, 56, 52, 48, 44, 40, 36, 32, 28, 25, 22, 19, 17, 15, 14], "hook-setup-revelation-payoff-ending"),
    ("OMS-20260814-0001", "O império que sumiu em uma noite", "history", None, -25, 18, 15000, 63, 700, 60, 44,
     [100, 86, 78, 70, 64, 60, 56, 52, 48, 44, 40, 36, 32, 28, 24, 20, 17, 14, 12, 10, 9], "hook-setup-escalation-revelation-payoff-ending"),
    ("OMS-20260812-0001", "A batalha decidida por um erro", "history", None, -27, 18, 12000, 59, 500, 50, 38,
     [100, 84, 76, 68, 62, 58, 54, 50, 46, 42, 38, 34, 30, 26, 22, 18, 15, 12, 10, 8, 7], "hook-setup-escalation-revelation-payoff-ending"),
    ("OMS-20260810-0001", "O chip que pensa como um cérebro", "technology", None, -29, 18, 9000, 58, 300, 40, 55,
     [100, 82, 74, 66, 60, 55, 50, 46, 42, 38, 34, 30, 26, 22, 19, 16, 13, 11, 9, 8, 7], "hook-setup-revelation-payoff-ending"),
    ("OMS-20260808-0001", "Por que a curiosidade vicia", "curiosities", None, -31, 18, 27000, 74, 1600, 300, 30,
     [100, 92, 86, 80, 76, 72, 68, 64, 60, 56, 52, 48, 44, 41, 38, 35, 32, 29, 27, 25, 24], "hook-escalation-revelation-ending"),
    ("OMS-20260806-0001", "O experimento que ninguém repete", "science", None, -33, 18, 45000, 77, 2300, 520, 36,
     [100, 94, 88, 84, 80, 76, 72, 68, 64, 60, 56, 52, 48, 45, 42, 39, 36, 33, 30, 28, 27], "hook-escalation-revelation-ending"),
]
IN_PRODUCTION = [
    ("OMS-20260907-0002", "O som que só quem tem menos de 25 anos escuta", "technology", "headphones.jpg", State.GENERATING, 0),
    ("OMS-20260904-0001", "Por que sonhamos em preto e branco?", "psychology", None, State.NEEDS_REVIEW, -4),
    ("OMS-20260903-0001", "A ponte que canta com o vento", "world", None, State.EDITING, -5),
    ("OMS-20260901-0001", "O metal que lembra a própria forma", "science", None, State.READY, -7),
]
FAILED = [("OMS-20260823-0001", "Por que o vidro é um líquido?", "science", "hourglass.jpg", -16)]
DRAFTS = [
    ("OMS-20260821-0001", "O que tem no lado escuro da Lua?", "space", "moon.jpg", -18),
    ("OMS-20260820-0001", "A cor do universo", "space", None, -19),
    ("OMS-20260818-0001", "O relógio que atrasa no espaço", "science", None, -21),
    ("OMS-20260816-0001", "A planta que conta até vinte", "nature", None, -23),
    ("OMS-20260815-0001", "O truque das vitrines", "psychology", None, -24),
    ("OMS-20260813-0001", "Dinheiro que evapora", "money", None, -26),
]


def add_topic(session, pid, title, category, score=84, reason=None):
    session.add(Topic(production_id=pid, topic=title, category=category, trend_score=80, viral_potential=82, us_relevance=88, competition=30,
                      shorts_fit=92, originality=80, risk=8, final_score=score, selected=True, selection_reason=reason or "Escolhido entre 12 candidatos."))


def add_script(session, pid, title, rows, duration):
    data = {"title_working": title, "beats": beats(rows), "hook_type": "shock", "ending_type": "loop", "cta_used": False, "loop_used": True,
            "total_words": 96, "est_duration_s": duration}
    session.add(Script(production_id=pid, data=data, text="\n".join(r[4] for r in rows), hook_type="shock", ending_type="loop", total_words=96, est_duration_s=duration))


def add_prompts(session, pid):
    for i, (label, context, camera) in enumerate(SCENES, start=1):
        text = f"SCENE CONTEXT:\n{context}\n\nCAMERA:\n{camera}"
        session.add(Prompt(production_id=pid, segment_index=i, attempt=1, prompt=text, negative_prompt=NEGATIVE,
                           config={"duration_seconds": 8, "aspect_ratio": "9:16"}))
    session.add(Storyboard(production_id=pid, data={"segments": [{"segment": i, "purpose": label, "duration": 8} for i, (label, _, _) in enumerate(SCENES, 1)],
                                                     "visual_style": "cinematic", "palette": "deep black, red"}, visual_style="cinematic"))


def thumb(pid: str, name: str | None) -> None:
    if not name:
        return
    (STORAGE / "thumbs").mkdir(parents=True, exist_ok=True)
    shutil.copyfile(DEMO_IMG / name, STORAGE / "thumbs" / f"{pid}.jpg")


def seed(clips: int) -> None:
    if DB_PATH.exists():
        DB_PATH.unlink()
    for suffix in ("-wal", "-shm"):
        Path(str(DB_PATH) + suffix).unlink(missing_ok=True)
    if STORAGE.exists():
        shutil.rmtree(STORAGE)
    engine = get_engine(f"sqlite:///{DB_PATH.as_posix()}")
    init_db(engine)
    with session_scope(engine) as session:
        # ---- today's production (waiting for clips)
        pid = "OMS-20260908-0001"
        session.add(Production(id=pid, state=State.GENERATING, previous_state=State.STORYBOARDING, created_at=local(0, 8, 10), started_at=local(0, 8, 10)))
        add_topic(session, pid, "Por que o vidro é realmente um líquido parado", "science", 84,
                  "Escolhido entre 12 candidatos. Alta curiosidade, baixa saturação e ótimo encaixe em 40s.")
        add_script(session, pid, "Por que o vidro é realmente um líquido parado", BEATS_GLASS, 40)
        add_prompts(session, pid)
        for stage, hour, minute in (("discover", 8, 10), ("research", 8, 11), ("script", 8, 12), ("storyboard", 8, 25), ("prompts", 8, 28)):
            session.add(Event(at=local(0, hour, minute), production_id=pid, stage=stage, action="run", status="ok", duration_ms=1200))
        thumb(pid, "hourglass-clean.jpg")

        # ---- published videos with analytics
        for (vid, title, cat, img, days, hour, views, ret, likes, subs, dur, curve, structure) in PUBLISHED:
            when = local(days, hour)
            session.add(Production(id=vid, state=State.LEARNED if days < -7 else State.ANALYZING, created_at=when - timedelta(hours=9),
                                   started_at=when - timedelta(hours=9), finished_at=when - timedelta(hours=1),
                                   features={"production_id": vid, "title": title, "topic": title, "category": cat, "hook_type": "shock",
                                             "ending_type": "loop", "duration_s": dur, "retention": ret / 100, "completion": curve[-1] / 100,
                                             "views": views, "sub_conversion": subs / views, "narrative_structure": structure, "engagement": likes / views}))
            add_topic(session, vid, title, cat, 80 + (views % 15))
            add_script(session, vid, title, BEATS_MAP if vid == "OMS-20260907-0001" else BEATS_GLASS, dur)
            session.add(VideoMetadata(production_id=vid, title=title, hashtags=["#Shorts"],
                                      description="Descubra por que o mapa que você sempre viu está errado e como isso muda a forma de ver o mundo."
                                      if vid == "OMS-20260907-0001" else f"{title}. Um Short do OneMoreShort."))
            session.add(FinalVideo(production_id=vid, path=str(STORAGE / "renders" / vid / "OneMoreShort_Final.mp4"), probe={"duration_s": dur}, passed=True))
            session.add(Upload(production_id=vid, youtube_video_id=f"yt{vid[-8:]}", url=f"https://youtube.com/shorts/{vid[-8:]}", status="published",
                               privacy="public", uploaded_at=when, published_at=when))
            session.add(AnalyticsSnapshot(production_id=vid, youtube_video_id=f"yt{vid[-8:]}", captured_at=local(0, 8, 25), age_minutes=-days * 1440,
                                          schedule_slot_min=1440, source="analytics_api", views=views, likes=likes, comments=views // 90,
                                          shares=views // 45, subscribers_gained=subs, avg_view_pct=ret, avg_view_duration_s=dur * ret / 100))
            points = [{"elapsed_ratio": i / (len(curve) - 1), "watch_ratio": v / 100} for i, v in enumerate(curve)]
            analysis = {"points": [[p["elapsed_ratio"], p["watch_ratio"]] for p in points], "avg_pct": ret / 100, "completion_est": curve[-1] / 100, "drops": []}
            if vid == "OMS-20260907-0001":
                analysis["drops"] = [{"t_s": 22, "delta": 0.12, "beat": 4, "segment": 3, "sentence": "mas isso não é bem verdade",
                                      "likely_cause": "transição lenta entre cenas 3 e 4"}]
            session.add(RetentionCurve(production_id=vid, youtube_video_id=f"yt{vid[-8:]}", captured_at=local(0, 8, 25), points=points, analysis=analysis))
            for stage, offset in (("script", 9), ("storyboard", 8), ("prompts", 8), ("validate", 4), ("render", 2), ("quality_gate", 2), ("upload", 0)):
                session.add(Event(at=when - timedelta(hours=offset), production_id=vid, stage=stage, action="run", status="ok", duration_ms=900))
            thumb(vid, img)
        session.add(VideoReport(production_id="OMS-20260907-0001", youtube_video_id="yt20260907", created_at=local(0, 8, 25), virality_score=91,
                                markdown="ONE MORE SHORT\nVIDEO PERFORMANCE REPORT\n\nVideo: \"O erro do mapa mundial viral\"\n\nViews: 312,480\nAverage Percentage Viewed: 81%\n",
                                verdict={"growth": "viral",
                                         "what_worked": ["Gancho de choque nos 2 primeiros segundos: Alta taxa de retenção inicial (92%).",
                                                         "Payoff inesperado aos 28s: Pico de interesse na reta final.",
                                                         "Fecho em loop: Mantém o interesse até o último segundo.",
                                                         "Duração de 34 segundos: Formato ideal para o tema e boa retenção."],
                                         "what_failed": ["Queda de retenção aos 22s: Cena 3, na frase \"mas isso não é bem verdade\".",
                                                         "Transição lenta entre cenas 3 e 4: Pequena perda de ritmo (queda de 12%)."],
                                         "next_recommendation": "Manter o gancho de choque e a duração: Os primeiros 2 segundos funcionaram muito bem; "
                                                                "Encurtar a transição da cena 3: Tornar a explicação mais direta e ágil; "
                                                                "Repetir o fecho em loop: Funciona bem para retenção e inscritos"}))

        # ---- in production, failed, drafts
        for vid, title, cat, img, state, days in IN_PRODUCTION:
            session.add(Production(id=vid, state=state, created_at=local(days, 9, 17), started_at=local(days, 9, 17)))
            add_topic(session, vid, title, cat, 89)
            add_script(session, vid, title, BEATS_GLASS, 38)
            add_prompts(session, vid)
            thumb(vid, img)
        for vid, title, cat, img, days in FAILED:
            when = local(days, 18)
            session.add(Production(id=vid, state=State.FAILED, previous_state=State.QUALITY_CHECK, error="Quality gate: duration 41.3s above 40s", created_at=when, started_at=when))
            add_topic(session, vid, title, cat, 70)
            add_script(session, vid, title, BEATS_GLASS, 41)
            session.add(Upload(production_id=vid, youtube_video_id=f"yt{vid[-8:]}", url="https://youtube.com/shorts/x", status="published", uploaded_at=when, published_at=when))
            session.add(AnalyticsSnapshot(production_id=vid, youtube_video_id=f"yt{vid[-8:]}", captured_at=local(0, 8), age_minutes=99, schedule_slot_min=60,
                                          views=12000, likes=200, comments=5, avg_view_pct=18))
            thumb(vid, img)
        for vid, title, cat, img, days in DRAFTS:
            session.add(Production(id=vid, state=State.SELECTED, created_at=local(days, 9), started_at=local(days, 9)))
            add_topic(session, vid, title, cat, 75)
            thumb(vid, img)

        # ---- intelligence
        session.add_all([
            Insight(feature="hook_type", value="question", metric="retention", effect=0.1954, n=18, confidence=0.92,
                    detail={"title": "Gancho com pergunta + revelação visual segura", "tags": ["Gancho", "Retenção"]}),
            Insight(feature="duration_bucket", value="32-40s", metric="completion", effect=0.27, n=16, confidence=0.87,
                    detail={"title": "Vídeos entre 31s e 36s têm melhor conclusão", "tags": ["Duração", "Conclusão"], "gain": "+27%", "suffix": "de conclusão"}),
            Insight(feature="category", value="science", metric="sub_conversion", effect=2.2, n=18, confidence=0.84,
                    detail={"title": "Temas de ciência e curiosidades convertem mais inscritos", "tags": ["Tema", "Inscritos"], "gain": "+3,2x", "suffix": "inscritos"}),
            Insight(feature="ending_type", value="question", metric="sub_conversion", effect=1.8, n=14, confidence=0.78,
                    detail={"title": "Finais com pergunta direta aumentam inscrições em", "tags": ["Final", "Conversão"], "gain": "+180%", "suffix": ""}),
            Insight(feature="visual_style", value="dynamic", metric="retention", effect=0.32, n=12, confidence=0.71,
                    detail={"title": "Vídeos com elementos visuais dinâmicos têm", "tags": ["Edição", "Retenção"], "gain": "+32%", "suffix": "de retenção"}),
        ])
        session.add(StrategyWeightsRow(created_at=local(0, 8, 25), weights={"duration_pref": 33.5, "category_weights": {"science": 1.4}}, exploration_ratio=0.3, based_on_n=18))
        session.add(Event(at=local(0, 8, 25), stage="intelligence", action="learn", status="ok", duration_ms=800))

        # ---- conversation history and recent actions
        chat = [
            ("chat.user", local(0, 10, 24), "começa o vídeo de hoje", {}),
            ("chat.assistant", local(0, 10, 24), "Pesquisei 6 fontes e escolhi “Por que o vidro é um líquido parado”, score 84. Roteiro de 38 segundos escrito e 5 prompts prontos.",
             {"cards": [{"kind": "theme", "title": "Por que o vidro é realmente um líquido parado?", "thumb_url": "/api/thumbs/OMS-20260908-0001", "production_id": pid,
                         "pills": [{"label": "ciência", "variant": "red"}, {"label": "score 84", "variant": "grey"}],
                         "buttons": [{"label": "Ver os prompts", "href": f"/estudio/{pid}?step=2", "icon": "file-text"}]}]}),
            ("chat.user", local(0, 10, 26), "o tema tá fraco, tenta outro", {}),
            ("chat.assistant", local(0, 10, 26), "Troquei para “O som que só quem tem menos de 25 anos escuta”, score 89. Roteiro refeito. Quer ver o roteiro antes dos prompts?",
             {"cards": [{"kind": "theme", "title": "O som que só quem tem menos de 25 anos escuta?", "thumb_url": "/api/thumbs/OMS-20260906-0001", "production_id": "OMS-20260907-0002",
                         "pills": [{"label": "cultura", "variant": "purple"}, {"label": "score 89", "variant": "grey"}],
                         "buttons": [{"label": "Ver roteiro", "href": "/estudio/OMS-20260907-0002?step=1", "icon": "file-text"},
                                     {"label": "Gerar prompts", "href": "/estudio/OMS-20260907-0002?step=2", "icon": "sparkles", "trailing": True}]}]}),
            ("chat.user", local(0, 10, 28), "como foi o vídeo de ontem?", {}),
            ("chat.assistant", local(0, 10, 28), "312 mil views em 24h, classificado como viral. Retenção média 81%, acima da média do canal. Queda de 12% aos 22s.",
             {"cards": [{"kind": "report", "title": "O erro do mapa mundial viral", "thumb_url": "/api/thumbs/OMS-20260907-0001", "production_id": "OMS-20260907-0001",
                         "pills": [{"label": "viral", "variant": "red"}],
                         "buttons": [{"label": "Abrir relatório", "href": "/desempenho/OMS-20260907-0001", "icon": "chart-column-big"}]}]}),
        ]
        for action, at, text, detail in chat:
            session.add(Event(at=at, action=action, status="ok", detail={"text": text, **detail}))
        activity = [
            (local(0, 10, 28), "consultar_desempenho", "Analisou desempenho do vídeo", "“O erro do mapa mundial viral”"),
            (local(0, 10, 26), "trocar_tema", "Gerou novos prompts", "“O som que só quem tem menos de 25 anos...”"),
            (local(0, 10, 24), "iniciar_producao", "Criou roteiro", "“Por que o vidro é um líquido parado”"),
            (local(0, 9, 17), "preparar_publicacao", "Publicou no YouTube", "“A cor que não existe”"),
            (local(-1, 5, 42), "montar_video", "Finalizou edição", "“Por que o café acorda?”"),
        ]
        for at, tool, label, subject in activity:
            session.add(Event(at=at, action="chat.tool", status="ok", detail={"text": tool, "label": label, "subject": subject,
                                                                                "color": "blue" if "Publicou" in label else "green"}))

    # ---- optional synthetic clips in the inbox (Estúdio step 3)
    if clips:
        from app.editing.synth import synth_segment

        inbox = STORAGE / "manual_input" / "OMS-20260908-0001"
        inbox.mkdir(parents=True, exist_ok=True)
        durations = [8.0, 8.0, 9.4, 8.0, 8.0]
        sizes = ["glass.jpg", "ice.jpg", "mountains.jpg", "coffee-small.jpg", "logo-thumb.jpg"]
        for scene in range(1, clips + 1):
            synth_segment(inbox / f"segment_{scene:02d}.mp4", durations[scene - 1], "0x0F1419", f"cena {scene}")
        (STORAGE / "thumbs").mkdir(exist_ok=True)
        for scene in range(1, 6):
            shutil.copyfile(DEMO_IMG / sizes[scene - 1], STORAGE / "thumbs" / f"OMS-20260908-0001_clip{scene}.jpg")
    print(f"demo database: {DB_PATH}\nstorage: {STORAGE}\nclips in inbox: {clips}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--clips", type=int, default=0, choices=[0, 1, 2, 3, 4, 5])
    seed(parser.parse_args().clips)
