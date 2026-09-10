from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class BaseTTSProvider(ABC):
    """
    Abstract base class for TTS Providers.
    Allows easy plug-and-play addition of local voice cloning engines
    (e.g., F5-TTS, Kokoro, Coqui TTS) alongside cloud or edge engines.
    """
    
    @property
    @abstractmethod
    def provider_id(self) -> str:
        """Unique identifier for the provider (e.g. 'edge-tts', 'f5-clone')"""
        pass

    @property
    @abstractmethod
    def provider_name(self) -> str:
        """Human readable display name"""
        pass

    @abstractmethod
    async def get_voices(self) -> List[Dict[str, Any]]:
        """
        Return list of supported voices.
        Each voice is a dict:
        {
            "id": "my-MM-NilarNeural",
            "name": "Nilar (နီလာ)",
            "gender": "Female",
            "language": "my-MM",
            "language_name": "Myanmar (မြန်မာ)",
            "description": "Natural female Myanmar voice"
        }
        """
        pass

    @abstractmethod
    async def synthesize(
        self,
        text: str,
        voice_id: str,
        output_path: str,
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%"
    ) -> bool:
        """
        Synthesize text to an audio file (MP3 format).
        Returns True on success, raises Exception on failure.
        """
        pass
