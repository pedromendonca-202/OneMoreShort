"""Render phone-safe ASS subtitles without shell interpolation."""
from __future__ import annotations

from pathlib import Path

from app.captions.aligner import CaptionPhrase
from app.captions.style import CaptionStyle


def _time(seconds: float) -> str:
    total = max(0, round(seconds * 100))
    centiseconds = total % 100
    total //= 100
    seconds_part = total % 60
    total //= 60
    minutes = total % 60
    hours = total // 60
    return f"{hours}:{minutes:02d}:{seconds_part:02d}.{centiseconds:02d}"


def _escape(text: str) -> str:
    return text.replace("\\", r"\\").replace("{", r"\{").replace("}", r"\}").replace("\n", r"\N")


def render_ass(phrases: list[CaptionPhrase], style: CaptionStyle, out_ass: Path | str) -> Path:
    output = Path(out_ass)
    output.parent.mkdir(parents=True, exist_ok=True)
    header = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1080
PlayResY: 1920
ScaledBorderAndShadow: yes

[V4+ Styles]
Format: Name,Fontname,Fontsize,PrimaryColour,SecondaryColour,OutlineColour,BackColour,Bold,Italic,Underline,StrikeOut,ScaleX,ScaleY,Spacing,Angle,BorderStyle,Outline,Shadow,Alignment,MarginL,MarginR,MarginV,Encoding
Style: Default,{style.font},{style.font_size},{style.primary_color},{style.highlight_color},{style.outline_color},&H96000000,-1,0,0,0,100,100,0,0,1,{style.outline},{style.shadow},2,80,80,{style.margin_v},1

[Events]
Format: Layer,Start,End,Style,Name,MarginL,MarginR,MarginV,Effect,Text
"""
    lines = [header]
    for phrase in phrases:
        text = _escape(phrase.text.upper() if style.uppercase else phrase.text)
        lines.append(f"Dialogue: 0,{_time(phrase.start_s)},{_time(phrase.end_s)},Default,,0,0,0,,{text}\n")
    output.write_text("".join(lines), encoding="utf-8-sig")
    return output
