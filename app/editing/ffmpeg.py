"""Locate and safely invoke the local ffmpeg toolchain."""
from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

from app.core.errors import FFmpegError


def _with_exe(name: str) -> str:
    return f"{name}.exe" if os.name == "nt" else name


def _probe_beside(ffmpeg: Path) -> Path | None:
    candidate = ffmpeg.with_name(_with_exe("ffprobe"))
    return candidate if candidate.is_file() else None


def resolve_ffmpeg() -> tuple[Path, Path]:
    """Resolve ffmpeg/ffprobe: explicit env, PATH, winget, then imageio."""
    configured = os.getenv("OMS_FFMPEG")
    if configured:
        ffmpeg = Path(configured).expanduser()
        probe = _probe_beside(ffmpeg)
        if ffmpeg.is_file() and probe:
            return ffmpeg, probe
        raise FileNotFoundError("OMS_FFMPEG must point to ffmpeg with ffprobe beside it")

    on_path = shutil.which(_with_exe("ffmpeg"))
    if on_path:
        ffmpeg = Path(on_path)
        probe_path = shutil.which(_with_exe("ffprobe"))
        if probe_path:
            return ffmpeg, Path(probe_path)

    local = os.getenv("LOCALAPPDATA")
    if local:
        packages = Path(local) / "Microsoft" / "WinGet" / "Packages"
        for ffmpeg in packages.glob("Gyan.FFmpeg*/**/bin/ffmpeg.exe"):
            probe = _probe_beside(ffmpeg)
            if probe:
                return ffmpeg, probe

    try:
        import imageio_ffmpeg

        ffmpeg = Path(imageio_ffmpeg.get_ffmpeg_exe())
        probe = _probe_beside(ffmpeg)
        on_path_probe = shutil.which(_with_exe("ffprobe"))
        if probe:
            return ffmpeg, probe
        if on_path_probe:
            return ffmpeg, Path(on_path_probe)
    except ImportError:
        pass
    raise FileNotFoundError("ffmpeg + ffprobe were not found. Install FFmpeg or set OMS_FFMPEG to its executable.")


def run_ffmpeg(args: list[str], *, cwd: Path | str | None = None, timeout_s: float = 300) -> subprocess.CompletedProcess[str]:
    """Run ffmpeg with captured diagnostics suitable for error reports."""
    ffmpeg, _ = resolve_ffmpeg()
    workdir = Path(cwd).resolve() if cwd else None
    try:
        # ffmpeg prints UTF-8 on Windows; decoding with the console code page (cp1252) crashes the
        # pipe reader thread on accented paths, so decode explicitly and never fail on stray bytes.
        completed = subprocess.run(
            [str(ffmpeg), "-hide_banner", "-nostdin", *map(str, args)], cwd=workdir, text=True,
            encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_s, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError([str(ffmpeg), *args], f"timed out after {timeout_s}s\n{exc.stderr or ''}") from exc
    if completed.returncode != 0:
        raise FFmpegError([str(ffmpeg), *args], completed.stderr, completed.returncode)
    return completed


def run_ffprobe(args: list[str], *, cwd: Path | str | None = None, timeout_s: float = 60) -> subprocess.CompletedProcess[str]:
    """Run ffprobe using the same error convention as ffmpeg."""
    _, ffprobe = resolve_ffmpeg()
    workdir = Path(cwd).resolve() if cwd else None
    try:
        completed = subprocess.run(
            [str(ffprobe), "-hide_banner", *map(str, args)], cwd=workdir, text=True,
            encoding="utf-8", errors="replace",
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout_s, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise FFmpegError([str(ffprobe), *args], f"timed out after {timeout_s}s\n{exc.stderr or ''}") from exc
    if completed.returncode != 0:
        raise FFmpegError([str(ffprobe), *args], completed.stderr, completed.returncode)
    return completed
