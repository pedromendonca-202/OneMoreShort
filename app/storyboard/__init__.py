"""Five-segment visual plan for the continuous video."""

from app.storyboard.generator import generate_storyboard
from app.storyboard.schemas import Segment, Storyboard

__all__ = ["Segment", "Storyboard", "generate_storyboard"]
