"""Artifact storage layout: storage/<kind>/<production_id>/<file>."""
from __future__ import annotations

import os
from pathlib import Path

KINDS = (
    "research", "scripts", "storyboards", "continuity", "prompts", "segments", "frames",
    "audio", "captions", "renders", "published", "analytics", "reports", "trends",
)


class Storage:
    def __init__(self, root: Path | str):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def dir_for(self, production_id: str, kind: str) -> Path:
        if kind not in KINDS:
            raise ValueError(f"unknown storage kind: {kind}")
        d = self.root / kind / production_id
        d.mkdir(parents=True, exist_ok=True)
        return d

    def path_for(self, production_id: str, kind: str, filename: str) -> Path:
        return self.dir_for(production_id, kind) / filename

    def shared_dir(self, kind: str) -> Path:
        if kind not in KINDS:
            raise ValueError(f"unknown storage kind: {kind}")
        d = self.root / kind
        d.mkdir(parents=True, exist_ok=True)
        return d

    @staticmethod
    def relpath(path: Path | str, cwd: Path | str) -> str:
        """Relative POSIX-style path for ffmpeg filter arguments (safe with accents/colons in the absolute path)."""
        return Path(os.path.relpath(Path(path), Path(cwd))).as_posix()
