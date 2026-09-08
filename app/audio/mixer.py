"""Mix narration over Veo ambience with ducking and broadcast loudness."""
from __future__ import annotations

from pathlib import Path
from typing import Any

from app.audio.schemas import NarrationPlan
from app.editing.ffmpeg import run_ffmpeg


def _value(cfg: Any, section: str, field: str, default: Any) -> Any:
    return getattr(getattr(cfg, section, cfg), field, default)


def mix_audio(video_in: Path | str, narration: NarrationPlan, music: Path | None, out_wav: Path | str, cfg: Any) -> Path:
    if not narration.beats:
        raise ValueError("cannot mix an empty narration plan")
    video, output = Path(video_in).resolve(), Path(out_wav).resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    inputs = ["-i", str(video)]
    for item in narration.beats:
        inputs += ["-i", str(item.path)]
    music_index = None
    if music:
        music_index = len(narration.beats) + 1
        inputs += ["-stream_loop", "-1", "-i", str(Path(music).resolve())]
    delayed = []
    for i, item in enumerate(narration.beats, start=1):
        delay_ms = max(0, round(item.start_s * 1000))
        delayed.append(f"[{i}:a]adelay={delay_ms}|{delay_ms}[n{i}]")
    narr_inputs = "".join(f"[n{i}]" for i in range(1, len(narration.beats) + 1))
    filters = delayed + [f"{narr_inputs}amix=inputs={len(narration.beats)}:normalize=0[narr]"]
    bed = "[0:a]"
    if music_index is not None:
        gain = float(_value(cfg, "video", "music_gain_db", -18))
        filters.append(f"[{music_index}:a]volume={gain}dB[music]")
        filters.append(f"[0:a][music]amix=inputs=2:duration=first[bed]")
        bed = "[bed]"
    filters += [
        f"{bed}[narr]sidechaincompress=threshold=0.03:ratio=8:attack=20:release=250[ducked]",
        "[ducked][narr]amix=inputs=2:normalize=0[mixed]",
        # loudnorm upsamples to 192 kHz internally; bring the bed back to broadcast 48 kHz.
        f"[mixed]loudnorm=I={_value(cfg, 'video', 'loudness_lufs', -14)}:TP={_value(cfg, 'video', 'true_peak_dbtp', -1)},aresample=48000[out]",
    ]
    run_ffmpeg(["-y", *inputs, "-filter_complex", ";".join(filters), "-map", "[out]", "-ar", "48000", "-c:a", "pcm_s16le", str(output)], cwd=output.parent)
    return output
