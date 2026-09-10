import asyncio
import os
import sys

# Ensure app path is in sys.path
sys.path.insert(0, os.path.dirname(__file__))

from app.database import init_db, list_presets, list_history, save_history_item
from app.services.chunker import TextChunker
from app.services.tts_manager import TTSManager

async def run_tests():
    print("--- 1. Testing Database & Presets ---")
    init_db()
    presets = list_presets()
    print(f"Loaded {len(presets)} presets:")
    for p in presets[:3]:
        print(f"  - [{p['language']}] {p['name']} ({p['voice_id']})")
    assert len(presets) >= 6, "Expected at least 6 default presets"

    print("\n--- 2. Testing Text Chunking (Myanmar & English) ---")
    chunker = TextChunker(max_chunk_chars=120)
    
    # Myanmar test text
    mm_text = "မင်္ဂလာပါခင်ဗျာ။ ဤစနစ်သည် မြန်မာစာသားများကို အပိုင်းလိုက် ခွဲထုတ်ပေးပါသည်။ စာပိုဒ်တစ်ခုချင်းစီကိုလည်း စနစ်တကျ စီစစ်ပေးနိုင်ပါသည်။"
    mm_chunks = chunker.chunk_text(mm_text)
    print(f"Myanmar text ({len(mm_text)} chars) split into {len(mm_chunks)} chunks:")
    for i, c in enumerate(mm_chunks):
        print(f"  Chunk {i+1}: {c}")

    # English test text
    en_text = "Good day! Welcome to TTS Studio. This application provides lifelike neural voice synthesis with authentic British English accents. Let us test how it splits long chapters."
    en_chunks = chunker.chunk_text(en_text)
    print(f"\nEnglish text ({len(en_text)} chars) split into {len(en_chunks)} chunks:")
    for i, c in enumerate(en_chunks):
        print(f"  Chunk {i+1}: {c}")

    print("\n--- 3. Testing Edge-TTS Synthesis & Multi-Chunk Stitching ---")
    storage_dir = os.path.join(os.path.dirname(__file__), "storage", "audio")
    tts_mgr = TTSManager(audio_storage_dir=storage_dir)

    # Test Myanmar Voice (Nilar)
    print("Testing Myanmar Voice synthesis (my-MM-NilarNeural)...")
    mm_result = await tts_mgr.synthesize_text(
        text="မင်္ဂလာပါခင်ဗျာ။ TTS Studio စမ်းသပ်မှု အောင်မြင်ပါသည်။",
        voice_id="my-MM-NilarNeural",
        rate="+0%",
        pitch="+0Hz"
    )
    print(f"  -> Generated: {mm_result['filename']} ({mm_result['file_size_bytes']} bytes)")
    assert mm_result['file_size_bytes'] > 0

    # Test British Voice (Sonia)
    print("Testing British Voice synthesis (en-GB-SoniaNeural)...")
    gb_result = await tts_mgr.synthesize_text(
        text="Hello! Testing the British accent narration in TTS Studio.",
        voice_id="en-GB-SoniaNeural",
        rate="-5%",
        pitch="+0Hz"
    )
    print(f"  -> Generated: {gb_result['filename']} ({gb_result['file_size_bytes']} bytes)")
    assert gb_result['file_size_bytes'] > 0

    print("\n--- 4. Testing SQLite History Record ---")
    save_history_item({
        "id": mm_result["id"],
        "title": "Test Myanmar Audio",
        "full_text": "မင်္ဂလာပါခင်ဗျာ။",
        "provider": "edge-tts",
        "voice_id": "my-MM-NilarNeural",
        "voice_name": "Nilar (နီလာ)",
        "language": "my-MM",
        "rate": "+0%",
        "pitch": "+0Hz",
        "audio_filename": mm_result["filename"],
        "char_count": mm_result["char_count"],
        "chunks_count": mm_result["chunks_count"],
        "file_size_bytes": mm_result["file_size_bytes"]
    })

    history = list_history()
    print(f"History records found: {len(history)}")
    assert len(history) >= 1

    print("\n🎉 ALL TESTS PASSED SUCCESSFULLY!")

if __name__ == "__main__":
    asyncio.run(run_tests())
