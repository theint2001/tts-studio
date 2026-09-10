import os
import asyncio
import edge_tts
from typing import List, Dict, Any
from app.providers.base import BaseTTSProvider

class EdgeTTSProvider(BaseTTSProvider):
    """
    Edge-TTS Provider using Microsoft Edge Neural Voices.
    100% Free, no API keys required, authentic British English (en-GB) voices.
    """

    SUPPORTED_VOICES = [
        {
            "id": "en-GB-SoniaNeural",
            "name": "Sonia",
            "gender": "Female",
            "language": "en-GB",
            "language_name": "British English",
            "flag": "🇬🇧",
            "description": "Warm, natural, clear",
            "avatar": "https://images.unsplash.com/photo-1544005313-94ddf0286df2?w=150&auto=format&fit=crop&q=80",
            "tags": ["Popular", "Warm", "Audiobook"]
        },
        {
            "id": "en-GB-RyanNeural",
            "name": "Ryan",
            "gender": "Male",
            "language": "en-GB",
            "language_name": "British English",
            "flag": "🇬🇧",
            "description": "Clear, engaging",
            "avatar": "https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?w=150&auto=format&fit=crop&q=80",
            "tags": ["Narrator", "Documentary"]
        },
        {
            "id": "en-GB-LibbyNeural",
            "name": "Libby",
            "gender": "Female",
            "language": "en-GB",
            "language_name": "British English",
            "flag": "🇬🇧",
            "description": "Bright, friendly",
            "avatar": "https://images.unsplash.com/photo-1573496359142-b8d87734a5a2?w=150&auto=format&fit=crop&q=80",
            "tags": ["Conversational", "Friendly"]
        },
        {
            "id": "en-GB-ThomasNeural",
            "name": "Thomas",
            "gender": "Male",
            "language": "en-GB",
            "language_name": "British English",
            "flag": "🇬🇧",
            "description": "Deep, authoritative",
            "avatar": "https://images.unsplash.com/photo-1500648767791-00dcc994a43e?w=150&auto=format&fit=crop&q=80",
            "tags": ["Authoritative", "Classic"]
        },
        {
            "id": "en-GB-MaisieNeural",
            "name": "Maisie",
            "gender": "Female",
            "language": "en-GB",
            "language_name": "British English",
            "flag": "🇬🇧",
            "description": "Young, expressive",
            "avatar": "https://images.unsplash.com/photo-1517841905240-472988babdf9?w=150&auto=format&fit=crop&q=80",
            "tags": ["Young", "Storytelling"]
        },
        {
            "id": "en-GB-OliverNeural",
            "name": "Oliver",
            "gender": "Male",
            "language": "en-GB",
            "language_name": "British English",
            "flag": "🇬🇧",
            "description": "Articulate, measured",
            "avatar": "https://images.unsplash.com/photo-1492562080023-ab3db95bfbce?w=150&auto=format&fit=crop&q=80",
            "tags": ["Measured", "Gentleman"]
        }
    ]

    @property
    def provider_id(self) -> str:
        return "edge-tts"

    @property
    def provider_name(self) -> str:
        return "Microsoft Edge Neural TTS"

    async def get_voices(self) -> List[Dict[str, Any]]:
        return self.SUPPORTED_VOICES

    @staticmethod
    def _format_rate(rate: Any) -> str:
        if isinstance(rate, (int, float)):
            r = int(rate)
            return f"+{r}%" if r >= 0 else f"{r}%"
        rate_str = str(rate).strip()
        if not rate_str:
            return "+0%"
        if rate_str.endswith("%"):
            if not rate_str.startswith(("+", "-")):
                return f"+{rate_str}"
            return rate_str
        try:
            val = int(rate_str)
            return f"+{val}%" if val >= 0 else f"{val}%"
        except ValueError:
            return "+0%"

    @staticmethod
    def _format_pitch(pitch: Any) -> str:
        if isinstance(pitch, (int, float)):
            p = int(pitch)
            return f"+{p}Hz" if p >= 0 else f"{p}Hz"
        pitch_str = str(pitch).strip()
        if not pitch_str:
            return "+0Hz"
        if pitch_str.endswith("Hz"):
            if not pitch_str.startswith(("+", "-")):
                return f"+{pitch_str}"
            return pitch_str
        try:
            val = int(pitch_str)
            return f"+{val}Hz" if val >= 0 else f"{val}Hz"
        except ValueError:
            return "+0Hz"

    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%"
    ) -> bool:
        clean_text = text.strip()
        if not clean_text:
            raise ValueError("Text cannot be empty")

        fmt_rate = self._format_rate(rate)
        fmt_pitch = self._format_pitch(pitch)
        fmt_volume = "+0%"

        max_retries = 3
        last_err = None

        for attempt in range(1, max_retries + 1):
            try:
                communicate = edge_tts.Communicate(
                    text=clean_text,
                    voice=voice_id,
                    rate=fmt_rate,
                    pitch=fmt_pitch,
                    volume=fmt_volume,
                    connect_timeout=20,
                    receive_timeout=60
                )
                await communicate.save(output_path)
                
                if os.path.exists(output_path) and os.path.getsize(output_path) > 500:
                    return True
                else:
                    raise IOError("Generated audio file is empty or too small")
            except Exception as e:
                last_err = e
                if attempt < max_retries:
                    await asyncio.sleep(1.0 * attempt)

        raise RuntimeError(
            f"Edge Neural TTS failed for '{voice_id}': {str(last_err)}. "
            "Please check your network connection and try again."
        )
