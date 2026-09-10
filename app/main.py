import os
import shutil
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, File, UploadFile, Request
from fastapi.responses import FileResponse, HTMLResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from app.database import (
    init_db,
    save_history_item,
    list_history,
    get_history_by_id,
    delete_history_by_id,
    clear_all_history,
    list_presets,
    save_custom_preset,
    delete_preset_by_id
)
from app.services.tts_manager import TTSManager
from app.services.image_service import ImageService
from app.services.video_service import VideoService

# Initialize paths
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
STORAGE_DIR = os.environ.get("STORAGE_DIR", "/tmp/tts_storage" if IS_VERCEL else os.path.join(BASE_DIR, "storage"))
AUDIO_STORAGE_DIR = os.path.join(STORAGE_DIR, "audio")
IMAGE_STORAGE_DIR = os.path.join(STORAGE_DIR, "images")
VIDEO_STORAGE_DIR = os.path.join(STORAGE_DIR, "video")
STATIC_DIR = os.path.join(BASE_DIR, "app", "static")

# Ensure required directories exist
os.makedirs(AUDIO_STORAGE_DIR, exist_ok=True)
os.makedirs(IMAGE_STORAGE_DIR, exist_ok=True)
os.makedirs(VIDEO_STORAGE_DIR, exist_ok=True)
os.makedirs(STATIC_DIR, exist_ok=True)

# Initialize database
init_db()

# Initialize TTS Manager, Image Service & Video Service
tts_manager = TTSManager(audio_storage_dir=AUDIO_STORAGE_DIR)
image_service = ImageService(storage_dir=IMAGE_STORAGE_DIR)
video_service = VideoService(video_storage_dir=VIDEO_STORAGE_DIR)

# FastAPI app
app = FastAPI(
    title="Personal TTS Studio",
    description="Local Text-to-Speech Studio supporting Myanmar Unicode and British English",
    version="1.0.0",
    redirect_slashes=False
)

# CORS enabled for local access
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")

# Request Models
class SynthesizeRequest(BaseModel):
    text: str = Field(..., min_length=1, description="Text to synthesize")
    voice_id: str = Field(..., description="Target voice ID")
    provider_id: str = Field(default="edge-tts", description="TTS Provider")
    rate: str = Field(default="+0%", description="Speaking rate, e.g. +10%, -5%")
    pitch: str = Field(default="+0Hz", description="Pitch adjustment, e.g. +3Hz, -2Hz")
    volume: str = Field(default="+0%", description="Volume adjustment")
    title: Optional[str] = Field(default=None, description="Optional title or chapter name")

class PresetCreateRequest(BaseModel):
    id: Optional[str] = None
    name: str = Field(..., min_length=1)
    language: str = Field(...)
    voice_id: str = Field(...)
    rate: str = Field(default="+0%")
    pitch: str = Field(default="+0Hz")
    description: Optional[str] = ""

class VideoGenerateRequest(BaseModel):
    audio_filename: str = Field(..., description="Filename of synthesized audio MP3")
    aspect_ratio: str = Field(default="16:9", description="16:9 or 9:16")
    image_paths: List[str] = Field(default_factory=list, description="List of local image file paths attached by user")
    motion_effect: str = Field(default="none", description="Motion effect: none, zoom_in, zoom_out")
    title: Optional[str] = None

@app.get("/", response_class=HTMLResponse)
async def serve_index():
    for p in [
        os.path.join(STATIC_DIR, "index.html"),
        os.path.join(BASE_DIR, "public", "index.html")
    ]:
        if os.path.exists(p):
            with open(p, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
    raise HTTPException(status_code=404, detail="Studio frontend not found.")

@app.exception_handler(404)
async def custom_404_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=404,
        content={
            "detail": f"Route not found: {request.method} {request.url.path}",
            "path": request.url.path
        }
    )

@app.get("/api")
@app.get("/api/")
async def api_health():
    return {"status": "ok", "service": "TTS Studio API"}

@app.get("/api/voices")
@app.get("/voices")
async def get_voices():
    """Retrieve all available voices from registered providers."""
    try:
        voices = await tts_manager.get_all_voices()
        return {"voices": voices}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch voices: {str(e)}")

@app.get("/api/presets")
@app.get("/presets")
async def get_presets():
    """Retrieve all built-in and user-created presets."""
    try:
        presets = list_presets()
        return {"presets": presets}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to fetch presets: {str(e)}")

@app.post("/api/presets")
@app.post("/presets")
async def create_preset(payload: PresetCreateRequest):
    """Save a custom voice preset."""
    import uuid
    preset_id = payload.id or f"custom-{uuid.uuid4().hex[:8]}"
    data = {
        "id": preset_id,
        "name": payload.name,
        "language": payload.language,
        "provider": "edge-tts",
        "voice_id": payload.voice_id,
        "rate": payload.rate,
        "pitch": payload.pitch,
        "description": payload.description or ""
    }
    save_custom_preset(data)
    return {"message": "Preset saved successfully", "preset": data}

@app.delete("/api/presets/{preset_id}")
@app.delete("/presets/{preset_id}")
async def delete_preset(preset_id: str):
    """Delete a custom preset."""
    delete_preset_by_id(preset_id)
    return {"message": "Preset deleted successfully"}

@app.post("/api/synthesize")
@app.post("/synthesize")
async def synthesize_speech(payload: SynthesizeRequest):
    """Synthesize speech with long-form chunking and local storage."""
    text = payload.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="Text cannot be empty.")

    try:
        # Synthesize via TTSManager
        result = await tts_manager.synthesize_text(
            text=text,
            voice_id=payload.voice_id,
            provider_id=payload.provider_id,
            rate=payload.rate,
            pitch=payload.pitch,
            volume=payload.volume
        )

        # Detect language / voice details
        voices = await tts_manager.get_all_voices()
        matched_voice = next((v for v in voices if v["id"] == payload.voice_id), None)
        voice_name = matched_voice["name"] if matched_voice else payload.voice_id
        language = matched_voice["language"] if matched_voice else (
            "my-MM" if tts_manager.chunker.is_primarily_myanmar(text) else "en-GB"
        )

        # Save record to SQLite
        history_record = {
            "id": result["id"],
            "title": payload.title,
            "full_text": text,
            "provider": payload.provider_id,
            "voice_id": payload.voice_id,
            "voice_name": voice_name,
            "language": language,
            "rate": payload.rate,
            "pitch": payload.pitch,
            "audio_filename": result["filename"],
            "char_count": result["char_count"],
            "chunks_count": result["chunks_count"],
            "file_size_bytes": result["file_size_bytes"]
        }
        save_history_item(history_record)

        return {
            "status": "success",
            "data": {
                **result,
                "voice_name": voice_name,
                "language": language,
                "created_at": "Just now"
            }
        }

    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        # Clean, user-friendly error output
        err_msg = str(e)
        if "nodename nor servname provided" in err_msg or "Failed to connect" in err_msg:
            err_msg = "Network connection failed. Edge TTS requires an active internet connection to download speech."
        elif "Invalid voice" in err_msg:
            err_msg = f"The selected voice '{payload.voice_id}' is currently unavailable."
        raise HTTPException(status_code=500, detail=f"TTS Generation Error: {err_msg}")

@app.get("/api/audio/{filename}")
@app.get("/audio/{filename}")
async def get_audio_file(filename: str, download: bool = Query(default=False)):
    """Serve or download generated audio file."""
    # Sanitize filename
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(AUDIO_STORAGE_DIR, safe_filename)

    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Audio file not found.")

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'

    return FileResponse(
        path=file_path,
        media_type="audio/mpeg",
        filename=safe_filename if download else None,
        headers=headers
    )

@app.get("/api/history")
@app.get("/history")
async def get_history(
    search: Optional[str] = Query(default=None),
    language: Optional[str] = Query(default=None),
    limit: int = Query(default=50, le=200)
):
    """Retrieve history of synthesized narrations."""
    items = list_history(search=search, language=language, limit=limit)
    for item in items:
        item["audio_url"] = f"/api/audio/{item['audio_filename']}"
    return {"history": items}

@app.delete("/api/history/{item_id}")
@app.delete("/history/{item_id}")
async def delete_history(item_id: str):
    """Delete a history record and its associated audio file."""
    filename = delete_history_by_id(item_id)
    if filename:
        audio_file = os.path.join(AUDIO_STORAGE_DIR, filename)
        if os.path.exists(audio_file):
            try:
                os.remove(audio_file)
            except OSError:
                pass
        return {"status": "success", "message": f"Deleted history item {item_id}"}
    raise HTTPException(status_code=404, detail="Item not found")

@app.get("/api/images/defaults")
async def get_default_images():
    """Returns the pre-loaded default sample slides."""
    slides = image_service.get_default_slides()
    return {"status": "success", "images": slides}

@app.post("/api/images/upload")
async def upload_image(file: UploadFile = File(...)):
    """Uploads, validates and stores an image for the Video Composer."""
    if not file.filename:
        raise HTTPException(status_code=400, detail="No filename provided.")
    
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in image_service.SUPPORTED_EXTS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{ext}'. Only JPG, PNG, and WEBP images are supported."
        )

    try:
        contents = await file.read()
        res = image_service.save_upload(contents, file.filename)
        return {"status": "success", "image": res}
    except ValueError as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Image upload error: {str(e)}")

@app.get("/api/images/{filename}")
async def get_image_file(filename: str):
    """Serves a user-uploaded image."""
    safe_name = os.path.basename(filename)
    path = os.path.join(IMAGE_STORAGE_DIR, safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Image not found.")
    ext = os.path.splitext(safe_name)[1].lower()
    media_type = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
    return FileResponse(path=path, media_type=media_type)

@app.get("/api/images/default/{filename}")
async def get_default_image_file(filename: str):
    """Serves a default sample slide image."""
    safe_name = os.path.basename(filename)
    path = os.path.join(IMAGE_STORAGE_DIR, "default", safe_name)
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="Default image not found.")
    ext = os.path.splitext(safe_name)[1].lower()
    media_type = "image/png" if ext == ".png" else "image/webp" if ext == ".webp" else "image/jpeg"
    return FileResponse(path=path, media_type=media_type)

@app.post("/api/video/generate")
async def generate_video(payload: VideoGenerateRequest):
    """Generates an MP4 video combining synthesized audio and attached image slideshow with motion effect."""
    safe_audio_name = os.path.basename(payload.audio_filename)
    audio_path = os.path.join(AUDIO_STORAGE_DIR, safe_audio_name)
    if not os.path.exists(audio_path):
        raise HTTPException(status_code=404, detail="Audio file not found. Please synthesize speech first.")

    # Validation 1: Check attached images count
    if not payload.image_paths or len(payload.image_paths) == 0:
        raise HTTPException(
            status_code=400,
            detail="No images attached. Please attach at least one image before creating video."
        )

    # Validation 2: Validate each image path and file format
    for img_path in payload.image_paths:
        if not os.path.exists(img_path):
            raise HTTPException(
                status_code=400,
                detail=f"Invalid image path: '{os.path.basename(img_path)}' not found on server."
            )
        ext = os.path.splitext(img_path)[1].lower()
        if ext not in image_service.SUPPORTED_EXTS:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported format '{ext}' in '{os.path.basename(img_path)}'. Only JPG, PNG, and WEBP images are supported."
            )
        try:
            image_service.validate_image_file(img_path)
        except Exception as err:
            raise HTTPException(status_code=400, detail=str(err))

    # Validate motion effect
    motion = payload.motion_effect.lower().strip() if payload.motion_effect else "none"
    if motion not in ("none", "zoom_in", "zoom_out"):
        motion = "none"

    try:
        # Render MP4 video with attached images and selected motion effect
        result = video_service.render_slideshow_video(
            audio_path=audio_path,
            image_paths=payload.image_paths,
            aspect_ratio=payload.aspect_ratio,
            motion_effect=motion
        )

        return {
            "status": "success",
            "data": result
        }
    except (ValueError, FileNotFoundError) as ve:
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Video rendering error: {str(e)}")

@app.get("/api/video/{filename}")
async def get_video_file(filename: str, download: bool = Query(default=False)):
    """Serves or downloads the generated MP4 video."""
    safe_filename = os.path.basename(filename)
    file_path = os.path.join(VIDEO_STORAGE_DIR, safe_filename)
    if not os.path.exists(file_path):
        raise HTTPException(status_code=404, detail="Video file not found.")

    headers = {}
    if download:
        headers["Content-Disposition"] = f'attachment; filename="{safe_filename}"'

    return FileResponse(
        path=file_path,
        media_type="video/mp4",
        filename=safe_filename if download else None,
        headers=headers
    )

@app.get("/api/storage/stats")
async def get_storage_stats():
    """Returns the count and total size of audio, video, and image files stored locally."""
    total_bytes = 0
    total_files = 0
    for folder in [AUDIO_STORAGE_DIR, VIDEO_STORAGE_DIR, IMAGE_STORAGE_DIR]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp):
                    total_bytes += os.path.getsize(fp)
                    total_files += 1

    k = 1024
    if total_bytes == 0:
        formatted = "0 KB"
    elif total_bytes < k * k:
        formatted = f"{total_bytes / k:.1f} KB"
    else:
        formatted = f"{total_bytes / (k * k):.2f} MB"

    return {
        "total_files": total_files,
        "total_bytes": total_bytes,
        "formatted_size": formatted
    }

@app.post("/api/cleanup")
async def cleanup_all_storage():
    """Wipes all generated audio, video, and image files and history so storage is 0 KB."""
    clear_all_history()

    deleted_count = 0
    for folder in [AUDIO_STORAGE_DIR, VIDEO_STORAGE_DIR, IMAGE_STORAGE_DIR]:
        if os.path.exists(folder):
            for f in os.listdir(folder):
                fp = os.path.join(folder, f)
                if os.path.isfile(fp):
                    try:
                        os.remove(fp)
                        deleted_count += 1
                    except OSError:
                        pass

    return {
        "status": "success",
        "message": f"Cleared {deleted_count} files. Storage is 0 KB.",
        "storage_size": "0 KB"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app.main:app", host="127.0.0.1", port=8000, reload=True)
