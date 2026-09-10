import os
import uuid
import io
from typing import List, Dict, Any, Optional
from PIL import Image, ImageDraw

class ImageService:
    """
    Manages slide images for long-form video generation.
    Supports default sample slides, user uploads, validation,
    and fallback slide generation.
    """

    SUPPORTED_EXTS = {".jpg", ".jpeg", ".png", ".webp"}

    def __init__(self, storage_dir: str):
        self.storage_dir = storage_dir
        self.default_dir = os.path.join(storage_dir, "default")
        os.makedirs(self.storage_dir, exist_ok=True)
        os.makedirs(self.default_dir, exist_ok=True)
        self._ensure_default_slides()

    def _ensure_default_slides(self):
        """Ensures 4 high-quality default sample slides exist locally."""
        defaults = [
            ("slide_1.jpg", (16, 37, 66), (37, 99, 235), "Chapter I: The Journey Begins"),
            ("slide_2.jpg", (15, 23, 42), (79, 70, 229), "Chapter II: Navigating Unknown Waters"),
            ("slide_3.jpg", (17, 24, 39), (20, 184, 166), "Chapter III: The Uncharted Coast"),
            ("slide_4.jpg", (30, 27, 75), (217, 70, 239), "Chapter IV: A New Beginning"),
        ]
        for fname, col1, col2, text in defaults:
            fpath = os.path.join(self.default_dir, fname)
            if not os.path.exists(fpath) or os.path.getsize(fpath) == 0:
                im = Image.new("RGB", (1920, 1080), col1)
                d = ImageDraw.Draw(im)
                for y in range(1080):
                    ratio = y / 1080.0
                    r = int(col1[0] * (1 - ratio) + col2[0] * ratio)
                    g = int(col1[1] * (1 - ratio) + col2[1] * ratio)
                    b = int(col1[2] * (1 - ratio) + col2[2] * ratio)
                    d.line([(0, y), (1920, y)], fill=(r, g, b))
                d.rectangle([100, 100, 1820, 980], outline=(255, 255, 255), width=3)
                d.text((160, 520), text, fill=(255, 255, 255))
                im.save(fpath, "JPEG", quality=92)

    def get_default_slides(self) -> List[Dict[str, Any]]:
        """Returns the list of 4 default sample slides with paths and URLs."""
        slides = []
        for i in range(1, 5):
            fname = f"slide_{i}.jpg"
            fpath = os.path.join(self.default_dir, fname)
            if os.path.exists(fpath):
                slides.append({
                    "id": f"default-{i}",
                    "name": f"Slide {i}",
                    "filename": fname,
                    "path": fpath,
                    "url": f"/api/images/default/{fname}"
                })
        return slides

    def validate_image_file(self, file_path: str) -> None:
        """Validates that a local image file exists and is a valid format."""
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"Image not found: '{os.path.basename(file_path)}'")
        ext = os.path.splitext(file_path)[1].lower()
        if ext not in self.SUPPORTED_EXTS:
            raise ValueError(
                f"Unsupported format: '{os.path.basename(file_path)}'. Only JPG, PNG, and WEBP are supported."
            )
        try:
            with Image.open(file_path) as img:
                img.verify()
        except Exception as e:
            raise ValueError(f"Corrupted or invalid image: '{os.path.basename(file_path)}' ({str(e)})")

    def save_upload(self, file_bytes: bytes, original_filename: str) -> Dict[str, Any]:
        """Validates and saves an uploaded image file."""
        if not file_bytes or len(file_bytes) == 0:
            raise ValueError("Uploaded file is empty.")

        ext = os.path.splitext(original_filename)[1].lower()
        if ext not in self.SUPPORTED_EXTS:
            raise ValueError(
                f"Unsupported format '{ext}'. Only JPG, PNG, and WEBP images are supported."
            )

        # Verify image content
        try:
            with Image.open(io.BytesIO(file_bytes)) as img:
                img.verify()
        except Exception as e:
            raise ValueError(f"Corrupted or invalid image file: {str(e)}")

        file_id = uuid.uuid4().hex[:12]
        saved_filename = f"upload_{file_id}{ext}"
        saved_path = os.path.join(self.storage_dir, saved_filename)

        with open(saved_path, "wb") as f:
            f.write(file_bytes)

        return {
            "id": file_id,
            "name": original_filename,
            "filename": saved_filename,
            "path": saved_path,
            "url": f"/api/images/{saved_filename}",
            "size_bytes": len(file_bytes)
        }
