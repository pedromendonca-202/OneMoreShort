"""Turn a script into one consistently voiced, timeline-aware narration plan."""
from __future__ import annotations

from pathlib import Path

from app.audio.schemas import BeatAudio, NarrationPlan, TightenedText, TTSResult, WordTiming
from app.audio.tts.base import TTSProvider
from app.core.storage import Storage
from app.editing.ffmpeg import run_ffmpeg
from app.editing.probe import probe
from app.llm.base import LLMProvider, LLMRequest, structured
from app.scripting.schemas import Script


def _total(results: list[BeatAudio]) -> float:
    return round(max((item.start_s + item.duration_s for item in results), default=0), 3)


def _build(script: Script, texts: list[str], tts: TTSProvider, storage: Storage, production_id: str) -> list[BeatAudio]:
    plan: list[BeatAudio] = []
    for beat, text in zip(script.beats, texts):
        output = storage.path_for(production_id, "audio", f"narration_beat_{beat.index:02d}.wav")
        result = tts.synthesize(text, output)
        plan.append(BeatAudio(beat=beat.model_copy(update={"narration": text}), path=result.path, start_s=beat.start_s,
                              duration_s=result.duration_s, words=result.words))
    return plan


def _tighten(llm: LLMProvider, text: str) -> str:
    result = structured(llm, LLMRequest(
        task="tighten_narration", role="fast", temperature=0.1, response_model=TightenedText,
        prompt=f"Shorten this narration while preserving only its essential factual meaning. Return fewer spoken words.\n\n{text}",
    ))
    return result.text


def _atempo(item: BeatAudio, target_duration: float) -> BeatAudio:
    speed = item.duration_s / target_duration
    if speed <= 1 or speed > 1.08:
        raise ValueError(f"narration needs {speed:.2f}x tempo, outside allowed 1.00–1.08")
    output = item.path.with_name(item.path.stem + "_fast.wav")
    run_ffmpeg(["-y", "-i", str(item.path), "-filter:a", f"atempo={speed:.5f}", "-c:a", "pcm_s16le", str(output)], cwd=output.parent)
    duration = probe(output).duration_s
    words = [WordTiming(word=w.word, start_s=w.start_s / speed, end_s=w.end_s / speed) for w in item.words] if item.words else None
    return item.model_copy(update={"path": output, "duration_s": duration, "words": words})


def narrate(script: Script, tts: TTSProvider, llm: LLMProvider, storage: Storage, production_id: str, max_total_s: float, *, tighten_passes: int = 2) -> NarrationPlan:
    texts = [beat.narration for beat in script.beats]
    plan = _build(script, texts, tts, storage, production_id)
    for _ in range(tighten_passes):
        if _total(plan) <= max_total_s:
            return NarrationPlan(beats=plan, total_s=_total(plan))
        texts = [_tighten(llm, text) for text in texts]
        plan = _build(script, texts, tts, storage, production_id)
    total = _total(plan)
    if total <= max_total_s:
        return NarrationPlan(beats=plan, total_s=total)
    # At this point use a bounded speed-up only on the final beat(s) that
    # actually overflow the allowed timeline.
    adjusted: list[BeatAudio] = []
    for item in plan:
        remaining = max_total_s - item.start_s
        adjusted.append(_atempo(item, remaining) if item.start_s + item.duration_s > max_total_s else item)
    total = _total(adjusted)
    if total > max_total_s + 0.02:
        raise ValueError(f"narration remains {total:.2f}s above {max_total_s:.2f}s after tightening")
    return NarrationPlan(beats=adjusted, total_s=total)
