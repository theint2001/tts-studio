import sqlite3
import os
import datetime
from typing import List, Dict, Any, Optional

BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IS_VERCEL = bool(os.environ.get("VERCEL") or os.environ.get("AWS_LAMBDA_FUNCTION_NAME"))
STORAGE_DIR = os.environ.get("STORAGE_DIR", "/tmp/tts_storage" if IS_VERCEL else os.path.join(BASE_DIR, "storage"))
os.makedirs(STORAGE_DIR, exist_ok=True)
DB_FILE = os.path.join(STORAGE_DIR, "tts_studio.db")

DEFAULT_PRESETS = [
    {
        "id": "preset-mm-news",
        "name": "မြန်မာ သတင်းဖတ် (News Anchor)",
        "language": "my-MM",
        "provider": "edge-tts",
        "voice_id": "my-MM-ThihaNeural",
        "rate": "+0%",
        "pitch": "+0Hz",
        "description": "သတင်း၊ အစီရင်ခံစာနှင့် တရားဝင်ထုတ်ပြန်ချက်များအတွက် တည်ကြည်သော အသံ",
        "is_default": 1
    },
    {
        "id": "preset-mm-story",
        "name": "မြန်မာ ဝတ္ထုပြောသူ (Storyteller)",
        "language": "my-MM",
        "provider": "edge-tts",
        "voice_id": "my-MM-NilarNeural",
        "rate": "-5%",
        "pitch": "+2Hz",
        "description": "ရသစာပေ၊ ဝတ္ထုနှင့် ပုံပြင်များအတွက် သာယာနူးညံ့သော အသံ",
        "is_default": 1
    },
    {
        "id": "preset-mm-podcast",
        "name": "မြန်မာ ပေါ့တ်ကတ်စ် (Podcast Host)",
        "language": "my-MM",
        "provider": "edge-tts",
        "voice_id": "my-MM-NilarNeural",
        "rate": "+5%",
        "pitch": "+0Hz",
        "description": "ဗဟုသုတဆောင်းပါးများနှင့် ပေါ့ပေါ့ပါးပါး တင်ဆက်မှုများအတွက်",
        "is_default": 1
    },
    {
        "id": "preset-gb-audiobook",
        "name": "British Audiobook (Sonia)",
        "language": "en-GB",
        "provider": "edge-tts",
        "voice_id": "en-GB-SoniaNeural",
        "rate": "-5%",
        "pitch": "+0Hz",
        "description": "Warm, articulate and immersive British narration for literature",
        "is_default": 1
    },
    {
        "id": "preset-gb-documentary",
        "name": "British Documentary (Ryan)",
        "language": "en-GB",
        "provider": "edge-tts",
        "voice_id": "en-GB-RyanNeural",
        "rate": "+0%",
        "pitch": "-2Hz",
        "description": "Classic BBC-style documentary narration with depth and clarity",
        "is_default": 1
    },
    {
        "id": "preset-gb-casual",
        "name": "British Conversational (Libby)",
        "language": "en-GB",
        "provider": "edge-tts",
        "voice_id": "en-GB-LibbyNeural",
        "rate": "+5%",
        "pitch": "+0Hz",
        "description": "Modern, friendly and approachable British female voice",
        "is_default": 1
    },
    {
        "id": "preset-gb-gentleman",
        "name": "British Distinguished (Thomas)",
        "language": "en-GB",
        "provider": "edge-tts",
        "voice_id": "en-GB-ThomasNeural",
        "rate": "-5%",
        "pitch": "-3Hz",
        "description": "Authoritative, dignified British gentleman's voice",
        "is_default": 1
    }
]

def get_connection():
    os.makedirs(os.path.dirname(DB_FILE), exist_ok=True)
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()

    # Create history table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS history (
        id TEXT PRIMARY KEY,
        title TEXT,
        text_preview TEXT,
        full_text TEXT,
        provider TEXT,
        voice_id TEXT,
        voice_name TEXT,
        language TEXT,
        rate TEXT,
        pitch TEXT,
        audio_filename TEXT,
        char_count INTEGER,
        chunks_count INTEGER,
        file_size_bytes INTEGER,
        created_at TEXT
    );
    """)

    # Create presets table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS presets (
        id TEXT PRIMARY KEY,
        name TEXT,
        language TEXT,
        provider TEXT,
        voice_id TEXT,
        rate TEXT,
        pitch TEXT,
        description TEXT,
        is_default INTEGER DEFAULT 0
    );
    """)

    # Seed default presets if empty
    cursor.execute("SELECT COUNT(*) as cnt FROM presets WHERE is_default = 1")
    count = cursor.fetchone()["cnt"]
    if count == 0:
        for p in DEFAULT_PRESETS:
            cursor.execute("""
            INSERT OR REPLACE INTO presets (id, name, language, provider, voice_id, rate, pitch, description, is_default)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (p["id"], p["name"], p["language"], p["provider"], p["voice_id"], p["rate"], p["pitch"], p["description"], p["is_default"]))

    conn.commit()
    conn.close()

def save_history_item(data: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    
    # Generate clean preview
    text = data.get("full_text", "")
    preview = (text[:120] + "...") if len(text) > 120 else text
    title = data.get("title") or (preview.split("\n")[0][:50] if preview else "Audio Narration")

    created_at = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    cursor.execute("""
    INSERT INTO history (
        id, title, text_preview, full_text, provider, voice_id, voice_name,
        language, rate, pitch, audio_filename, char_count, chunks_count,
        file_size_bytes, created_at
    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data["id"],
        title,
        preview,
        text,
        data.get("provider", "edge-tts"),
        data.get("voice_id", ""),
        data.get("voice_name", ""),
        data.get("language", ""),
        data.get("rate", "+0%"),
        data.get("pitch", "+0Hz"),
        data.get("audio_filename", ""),
        data.get("char_count", 0),
        data.get("chunks_count", 1),
        data.get("file_size_bytes", 0),
        created_at
    ))

    conn.commit()
    conn.close()

def list_history(search: Optional[str] = None, language: Optional[str] = None, limit: int = 100) -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()

    query = "SELECT * FROM history WHERE 1=1"
    params = []

    if search:
        query += " AND (title LIKE ? OR full_text LIKE ?)"
        params.extend([f"%{search}%", f"%{search}%"])

    if language:
        query += " AND language = ?"
        params.append(language)

    query += " ORDER BY created_at DESC LIMIT ?"
    params.append(limit)

    cursor.execute(query, params)
    rows = cursor.fetchall()
    result = [dict(row) for row in rows]
    conn.close()
    return result

def get_history_by_id(item_id: str) -> Optional[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM history WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    conn.close()
    return dict(row) if row else None

def delete_history_by_id(item_id: str) -> Optional[str]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT audio_filename FROM history WHERE id = ?", (item_id,))
    row = cursor.fetchone()
    filename = row["audio_filename"] if row else None

    if filename:
        cursor.execute("DELETE FROM history WHERE id = ?", (item_id,))
        conn.commit()
    conn.close()
    return filename

def list_presets() -> List[Dict[str, Any]]:
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM presets ORDER BY is_default DESC, name ASC")
    rows = cursor.fetchall()
    presets = [dict(row) for row in rows]
    conn.close()
    return presets

def save_custom_preset(data: Dict[str, Any]):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("""
    INSERT OR REPLACE INTO presets (id, name, language, provider, voice_id, rate, pitch, description, is_default)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, 0)
    """, (
        data["id"], data["name"], data.get("language", ""),
        data.get("provider", "edge-tts"), data["voice_id"],
        data.get("rate", "+0%"), data.get("pitch", "+0Hz"),
        data.get("description", "")
    ))
    conn.commit()
    conn.close()

def clear_all_history() -> List[str]:
    """Deletes all history records from DB and returns the list of filenames to remove from disk."""
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT audio_filename FROM history")
    rows = cursor.fetchall()
    filenames = [row["audio_filename"] for row in rows if row["audio_filename"]]
    
    cursor.execute("DELETE FROM history")
    conn.commit()
    conn.close()
    return filenames

def delete_preset_by_id(preset_id: str):
    conn = get_connection()
    cursor = conn.cursor()
    # Only allow deleting non-default presets
    cursor.execute("DELETE FROM presets WHERE id = ? AND is_default = 0", (preset_id,))
    conn.commit()
    conn.close()

