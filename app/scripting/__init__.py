"""Short-form script schemas, generation, and hook classification."""

from app.scripting.generator import generate_script
from app.scripting.schemas import Beat, HookType, Script

__all__ = ["Beat", "HookType", "Script", "generate_script"]
