import os
import uuid
import shutil
import asyncio
import subprocess
from typing import Dict, List, Any, Optional
from app.providers.base import BaseTTSProvider
from app.providers.edge_provider import EdgeTTSProvider
from app.services.chunker import TextChunker

class TTSManager:
    """
    Central TTS orchestrator managing providers, chunking,
    audio stitching for long-form narration, and audio storage.
    """

    def __init__(self, audio_storage_dir: str):
        self.audio_storage_dir = audio_storage_dir
        os.makedirs(self.audio_storage_dir, exist_ok=True)
        
        self.chunker = TextChunker(max_chunk_chars=650)
        self.providers: Dict[str, BaseTTSProvider] = {}
        
        # Register default Edge-TTS provider
        self.register_provider(EdgeTTSProvider())

    def register_provider(self, provider: BaseTTSProvider):
        """Register a new provider (e.g., future local voice clone provider)."""
        self.providers[provider.provider_id] = provider

    def get_provider(self, provider_id: str) -> BaseTTSProvider:
        if provider_id not in self.providers:
            raise ValueError(f"TTS Provider '{provider_id}' is not registered.")
        return self.providers[provider_id]

    async def get_all_voices(self) -> List[Dict[str, Any]]:
        all_voices = []
        for pid, provider in self.providers.items():
            voices = await provider.get_voices()
            for v in voices:
                v_copy = dict(v)
                v_copy["provider_id"] = pid
                v_copy["provider_name"] = provider.provider_name
                all_voices.append(v_copy)
        return all_voices

    def _concatenate_mp3s_ffmpeg(self, input_files: List[str], output_file: str) -> bool:
        """Concatenates multiple MP3 files seamlessly using ffmpeg concat demuxer."""
        list_file = f"{output_file}.concat.txt"
        try:
            with open(list_file, "w", encoding="utf-8") as f:
                for file_path in input_files:
                    # Escape single quotes for ffmpeg
                    safe_path = os.path.abspath(file_path).replace("'", "'\\''")
                    f.write(f"file '{safe_path}'\n")

            cmd = [
                "ffmpeg", "-y", "-f", "concat", "-safe", "0",
                "-i", list_file, "-c", "copy", output_file
            ]
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
            return result.returncode == 0 and os.path.exists(output_file) and os.path.getsize(output_file) > 0
        except Exception:
            return False
        finally:
            if os.path.exists(list_file):
                try:
                    os.remove(list_file)
                except OSError:
                    pass

    def _concatenate_mp3s_binary(self, input_files: List[str], output_file: str):
        """Fallback concatenation using raw MP3 frame stream joining."""
        with open(output_file, "wb") as outfile:
            for infile in input_files:
                with open(infile, "rb") as f:
                    shutil.copyfileobj(f, outfile)

    async def synthesize_text(
        self,
        text: str,
        voice_id: str,
        provider_id: str = "edge-tts",
        rate: str = "+0%",
        pitch: str = "+0Hz",
        volume: str = "+0%"
    ) -> Dict[str, Any]:
        """
        Synthesizes text into an MP3 file with long-form chunking support.
        """
        cleaned_text = text.strip()
        if not cleaned_text:
            raise ValueError("Input text cannot be empty.")

        provider = self.get_provider(provider_id)
        chunks = self.chunker.chunk_text(cleaned_text)
        
        generation_id = str(uuid.uuid4())
        final_filename = f"{generation_id}.mp3"
        final_output_path = os.path.join(self.audio_storage_dir, final_filename)

        if len(chunks) == 1:
            # Single chunk: direct synthesis
            await provider.synthesize(
                text=chunks[0],
                voice_id=voice_id,
                output_path=final_output_path,
                rate=rate,
                pitch=pitch,
                volume=volume
            )
        else:
            # Multi-chunk narration workflow
            temp_files: List[str] = []
            try:
                for idx, chunk in enumerate(chunks):
                    temp_chunk_path = os.path.join(
                        self.audio_storage_dir, f"temp_{generation_id}_{idx:03d}.mp3"
                    )
                    await provider.synthesize(
                        text=chunk,
                        voice_id=voice_id,
                        output_path=temp_chunk_path,
                        rate=rate,
                        pitch=pitch,
                        volume=volume
                    )
                    temp_files.append(temp_chunk_path)

                # Merge audio chunks
                ffmpeg_success = self._concatenate_mp3s_ffmpeg(temp_files, final_output_path)
                if not ffmpeg_success:
                    # Fallback to direct frame copy
                    self._concatenate_mp3s_binary(temp_files, final_output_path)

            finally:
                # Clean up temporary chunk files
                for tf in temp_files:
                    if os.path.exists(tf):
                        try:
                            os.remove(tf)
                        except OSError:
                            pass

        file_size = os.path.getsize(final_output_path) if os.path.exists(final_output_path) else 0

        return {
            "id": generation_id,
            "filename": final_filename,
            "audio_url": f"/api/audio/{final_filename}",
            "char_count": len(cleaned_text),
            "chunks_count": len(chunks),
            "file_size_bytes": file_size
        }
