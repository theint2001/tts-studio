import os
import sys
import asyncio

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from app.services.tts_manager import TTSManager
from app.services.image_service import ImageService
from app.services.video_service import VideoService

async def test_video_generation():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    audio_dir = os.path.join(base_dir, "storage", "audio")
    image_dir = os.path.join(base_dir, "storage", "images")
    video_dir = os.path.join(base_dir, "storage", "video")

    tts_mgr = TTSManager(audio_dir)
    img_svc = ImageService(image_dir)
    vid_svc = VideoService(video_dir)

    print("1. Synthesizing audio for video test...")
    audio_res = await tts_mgr.synthesize_text(
        text="မင်္ဂလာပါ။ ဤဗီဒီယိုသည် TTS Studio မှ စာသားနှင့် ပုံများကို အလိုအလျောက် ပေါင်းစပ်၍ MP4 ဗီဒီယိုအဖြစ် ထုတ်လုပ်ပေးခြင်း ဖြစ်ပါသည်။",
        voice_id="my-MM-NilarNeural"
    )
    audio_path = os.path.join(audio_dir, audio_res["filename"])
    print(f"   Audio ready: {audio_path} ({audio_res['file_size_bytes']} bytes)")

    print("2. Preparing 3 image slides (16:9)...")
    slides = img_svc.prepare_slides(count=3, aspect_ratio="16:9", seed="test_seed")
    print(f"   Prepared {len(slides)} slides:")
    for s in slides:
        print(f"     - {os.path.basename(s)}")

    print("3. Rendering MP4 Video...")
    vid_res = vid_svc.render_slideshow_video(
        audio_path=audio_path,
        image_paths=slides,
        aspect_ratio="16:9"
    )
    print(f"   Video generated successfully!")
    print(f"   Filename: {vid_res['filename']}")
    print(f"   Duration: {vid_res['duration_seconds']}s")
    print(f"   Size: {vid_res['file_size_bytes']} bytes")
    print(f"   URL: {vid_res['video_url']}")
    assert vid_res["file_size_bytes"] > 10000

    print("\n🎉 VIDEO GENERATION TEST PASSED!")

if __name__ == "__main__":
    asyncio.run(test_video_generation())
