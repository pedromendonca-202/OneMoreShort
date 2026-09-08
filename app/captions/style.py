from __future__ import annotations

from pydantic import BaseModel, Field


class CaptionStyle(BaseModel):
    font: str = "Impact"
    font_size: int = Field(default=72, ge=12)
    primary_color: str = "&H00FFFFFF"
    highlight_color: str = "&H0000E5FF"
    outline_color: str = "&H00000000"
    outline: int = Field(default=5, ge=0)
    shadow: int = Field(default=2, ge=0)
    margin_v: int = Field(default=450, ge=0)
    uppercase: bool = True
