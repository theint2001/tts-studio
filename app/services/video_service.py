import os
import uuid
import subprocess
import shutil
from typing import List, Dict, Any, Optional
from PIL import Image

class VideoService:
    """
    Renders high-quality MP4 videos combining synthesized TTS audio
    and a sequence of images into a dynamic slideshow without subtitles.
    Supports 16:9 (YouTube) and 9:16 (Shorts/TikTok), with Ken Burns motion effects.
    """

    SUPPORTED_IMAGE_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, video_storage_dir: str):
        self.video_storage_dir = video_storage_dir
        os.makedirs(self.video_storage_dir, exist_ok=True)

    def get_audio_duration(self, audio_path: str) -> float:
        """Retrieves exact duration of audio file in seconds using ffprobe."""
        cmd = [
            "ffprobe", "-v", "error", "-show_entries",
            "format=duration", "-of", "default=noprint_wrappers=1:nokey=1",
            audio_path
        ]
        try:
            result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)
            return float(result.stdout.strip())
        except Exception:
            # Fallback estimation if ffprobe fails: ~16KB per sec for 128k MP3
            size = os.path.getsize(audio_path)
            return max(5.0, size / 16000.0)

    def validate_image_paths(self, image_paths: List[str]) -> None:
        """Validates that image paths exist, have valid extensions, and are valid image files."""
        if not image_paths or len(image_paths) == 0:
            raise ValueError("No images attached. Please provide at least one image.")

        for p in image_paths:
            if not os.path.exists(p):
                raise FileNotFoundError(f"Image not found: '{os.path.basename(p)}'")
            ext = os.path.splitext(p)[1].lower()
            if ext not in self.SUPPORTED_IMAGE_EXTS:
                raise ValueError(
                    f"Unsupported image format: '{os.path.basename(p)}'. Supported formats: JPG, PNG, WEBP."
                )
            try:
                with Image.open(p) as img:
                    img.verify()
            except Exception as e:
                raise ValueError(f"Corrupted or invalid image file: '{os.path.basename(p)}' ({str(e)})")

    def render_slideshow_video(
        self,
        audio_path: str,
        image_paths: List[str],
        aspect_ratio: str = "16:9",
        motion_effect: str = "none",
        output_filename: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Renders an MP4 video with multi-image slideshow synchronized to audio.
        Supports motion effects: 'none', 'zoom_in', 'zoom_out'.
        """
        if not os.path.exists(audio_path):
            raise FileNotFoundError(f"Audio file '{audio_path}' does not exist.")

        # Strict validation of attached images
        self.validate_image_paths(image_paths)

        total_duration = self.get_audio_duration(audio_path)
        video_id = str(uuid.uuid4())
        filename = output_filename or f"{video_id}.mp4"
        output_path = os.path.join(self.video_storage_dir, filename)

        width, height = (1080, 1920) if aspect_ratio == "9:16" else (1920, 1080)
        num_images = len(image_paths)
        fps = 25
        motion = motion_effect.lower().strip() if motion_effect else "none"
        if motion not in ("none", "zoom_in", "zoom_out"):
            motion = "none"

        # Calculate exact duration and frame count per image slide
        base_frames = max(25, int((total_duration / num_images) * fps))

        cmd = ["ffmpeg", "-y"]
        for img in image_paths:
            cmd.extend(["-i", os.path.abspath(img)])
        cmd.extend(["-i", os.path.abspath(audio_path)])

        filter_parts = []
        concat_inputs = []

        for idx in range(num_images):
            # For the last slide, add margin frames so video finishes cleanly with -shortest
            if idx == num_images - 1:
                frames = max(25, int(total_duration * fps) - base_frames * (num_images - 1) + 25)
            else:
                frames = base_frames

            if motion == "zoom_in":
                # Subtle Ken Burns zoom in: 1.0 -> 1.15 centered
                z_expr = f"1.0+0.15*(on/{frames})"
                xy_expr = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                zp = f"zoompan=z='{z_expr}':{xy_expr}:d={frames}:s={width}x{height}:fps={fps}"
            elif motion == "zoom_out":
                # Subtle Ken Burns zoom out: 1.15 -> 1.0 centered
                z_expr = f"1.15-0.15*(on/{frames})"
                xy_expr = "x='iw/2-(iw/zoom/2)':y='ih/2-(ih/zoom/2)'"
                zp = f"zoompan=z='{z_expr}':{xy_expr}:d={frames}:s={width}x{height}:fps={fps}"
            else:
                # Static slide
                zp = f"zoompan=z=1.0:x=0:y=0:d={frames}:s={width}x{height}:fps={fps}"

            filter_parts.append(
                f"[{idx}:v]scale={width}:{height}:force_original_aspect_ratio=increase,"
                f"crop={width}:{height},{zp},format=yuv420p,setsar=1[v{idx}]"
            )
            concat_inputs.append(f"[v{idx}]")

        if num_images > 1:
            filter_parts.append(f"{''.join(concat_inputs)}concat=n={num_images}:v=1:a=0[outv]")
            out_v_map = "[outv]"
        else:
            out_v_map = "[v0]"

        filter_complex = "; ".join(filter_parts)

        cmd.extend([
            "-filter_complex", filter_complex,
            "-map", out_v_map,
            "-map", f"{num_images}:a",
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-c:a", "aac",
            "-b:a", "192k",
            "-shortest",
            "-movflags", "+faststart",
            output_path
        ])

        result = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True)

        if result.returncode != 0 or not os.path.exists(output_path) or os.path.getsize(output_path) == 0:
            raise RuntimeError(f"FFmpeg video encoding failed: {result.stderr[-500:]}")

        file_size = os.path.getsize(output_path)

        return {
            "id": video_id,
            "filename": filename,
            "video_url": f"/api/video/{filename}",
            "duration_seconds": round(total_duration, 1),
            "aspect_ratio": aspect_ratio,
            "motion_effect": motion,
            "slides_count": num_images,
            "file_size_bytes": file_size
        }
