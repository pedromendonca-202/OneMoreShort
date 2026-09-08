"""Use native boundaries when available, otherwise make a proportional estimate."""
from __future__ import annotations

import re

from pydantic import BaseModel, Field

from app.audio.schemas import NarrationPlan, WordTiming


class CaptionPhrase(BaseModel):
    text: str = Field(min_length=1)
    start_s: float = Field(ge=0)
    end_s: float = Field(ge=0)
    words: list[WordTiming]


def align_words(narration: NarrationPlan) -> list[WordTiming]:
    output: list[WordTiming] = []
    for item in narration.beats:
        local = item.words
        if local is None:
            tokens = re.findall(r"\b[\w'-]+\b", item.beat.narration)
            span = item.duration_s / max(1, len(tokens))
            local = [WordTiming(word=word, start_s=i * span, end_s=(i + 1) * span) for i, word in enumerate(tokens)]
        output.extend(WordTiming(word=word.word, start_s=round(item.start_s + word.start_s, 4),
                                 end_s=round(item.start_s + word.end_s, 4)) for word in local)
    return sorted(output, key=lambda word: (word.start_s, word.end_s))


def build_phrases(words: list[WordTiming], max_words: int = 3) -> list[CaptionPhrase]:
    if max_words < 1:
        raise ValueError("max_words must be positive")
    phrases: list[CaptionPhrase] = []
    for start in range(0, len(words), max_words):
        group = words[start:start + max_words]
        phrases.append(CaptionPhrase(text=" ".join(word.word for word in group), start_s=group[0].start_s,
                                     end_s=max(group[-1].end_s, group[0].start_s + 0.01), words=group))
    return phrases
