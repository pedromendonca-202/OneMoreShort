"""Gemini TTS adapter; imported only in live mode to keep tests offline."""
from __future__ import annotations

import wave
from pathlib import Path

from app.audio.schemas import TTSResult


class GeminiTTS:
    def __init__(self, api_key: str, model: str, voice: str):
        self.api_key, self.model, self.voice = api_key, model, voice

    def synthesize(self, text: str, out_wav: Path) -> TTSResult:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=self.api_key)
        response = client.models.generate_content(
            model=self.model, contents=text,
            config=types.GenerateContentConfig(response_modalities=["AUDIO"], speech_config=types.SpeechConfig(
                voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name=self.voice))
            )),
        )
        data = response.candidates[0].content.parts[0].inline_data.data
        # Gemini returns raw PCM in this API shape. Store canonical WAV for the
        # mixer rather than relying on an extension/mime guess.
        out_wav.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(out_wav), "wb") as handle:
            handle.setnchannels(1)
            handle.setsampwidth(2)
            handle.setframerate(24000)
            handle.writeframes(data)
        duration = len(data) / (24000 * 2)
        return TTSResult(path=out_wav, duration_s=duration, words=None, cost_usd=0)
