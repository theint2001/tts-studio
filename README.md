# 🎙️ Personal TTS Studio (Myanmar Unicode & British English)

A private, local Text-to-Speech (TTS) studio web application built for macOS. It provides lifelike neural voice synthesis for **Myanmar Unicode (🇲🇲)** and **British English (🇬🇧)** using Microsoft Edge Neural Voices (`edge-tts`), stored locally with SQLite.

---

## 🌟 Key Features

1. **Native Myanmar Unicode & British English Support**:
   - **Myanmar (မြန်မာ)**: `my-MM-NilarNeural` (Female) and `my-MM-ThihaNeural` (Male). Natural prosody, clean pause intervals, fully compatible with Myanmar Unicode fonts (Pyidaungsu, Noto Sans Myanmar).
   - **British English (en-GB)**: `en-GB-SoniaNeural`, `en-GB-RyanNeural`, `en-GB-LibbyNeural`, `en-GB-ThomasNeural`, `en-GB-OliverNeural`, `en-GB-MaisieNeural`, etc. Perfect for audiobooks, documentaries, and narration.

2. **Long-Form Narration Chunking Engine**:
   - Automatically segments lengthy chapters, articles, and essays without hitting character limits or audio clipping.
   - Punctuation-aware boundary detection:
     - **Myanmar**: `။` (section / full stop), `၊` (comma / clause pause), line breaks.
     - **English**: `.`, `!`, `?`, `;`, `,`, paragraphs.
   - Seamlessly stitches audio chunks using `ffmpeg` (with fallback to direct MP3 frame concatenation).

3. **100% Free & Zero Paid APIs**:
   - Uses `edge-tts` directly via Python. No API keys, no subscriptions, and no credit cards required.

4. **Modular Architecture for Voice Cloning**:
   - Built on an extensible `BaseTTSProvider` abstract class.
   - To integrate local voice cloning (e.g. F5-TTS, Kokoro, Chatterbox, or StyleTTS):
     - Create a new provider class inheriting from `BaseTTSProvider` in `app/providers/`.
     - Register it in `TTSManager`: `tts_manager.register_provider(MyVoiceCloneProvider())`.
     - Your cloned voices will automatically appear in the studio UI!

5. **Local SQLite History & MP3 Export**:
   - Stores all generated narrations, text previews, speed/pitch settings, timestamps, and file sizes in `storage/tts_studio.db`.
   - All audio files are safely preserved in `storage/audio/`.
   - Full playback deck with waveforms, seek controls, speed toggles (0.75x - 2.0x), and one-click MP3 download.

6. **Single-User & No Authentication**:
   - Optimized for personal local use with zero login hassles.

---

## 📂 Project Structure

```
tts-studio/
├── app/
│   ├── main.py                     # FastAPI server, REST routes & static file hosting
│   ├── database.py                 # SQLite schema, presets & history queries
│   ├── providers/
│   │   ├── base.py                 # Abstract BaseTTSProvider interface
│   │   └── edge_provider.py        # Edge-TTS implementation with retry logic
│   ├── services/
│   │   ├── chunker.py              # Myanmar & English sentence/clause chunker
│   │   └── tts_manager.py          # Provider manager & multi-chunk audio stitcher
│   └── static/
│       ├── index.html              # Responsive dark studio UI
│       ├── css/style.css           # Glassmorphism, animations & Myanmar fonts
│       └── js/app.js               # Audio player deck, history & voice controls
├── storage/
│   ├── audio/                      # Stored generated MP3 files
│   └── tts_studio.db               # Local SQLite database
├── requirements.txt                # Python dependencies
├── run.sh                          # Startup runner script
└── README.md                       # Documentation
```

---

## 🚀 Quick Start on macOS

### 1. Launch the Studio
Open Terminal in the project directory and run:

```bash
./run.sh
```

The script automatically sets up the Python virtual environment and launches the server at:
👉 **`http://127.0.0.1:8000`**

### 2. Manual Launch (Alternative)
```bash
source venv/bin/activate
uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
```

---

## 🛠️ How to Add a Local Voice Cloning Provider

The studio was specifically designed with modularity in mind. To add a voice cloning provider:

1. Create `app/providers/my_clone_provider.py`:
```python
from app.providers.base import BaseTTSProvider

class MyCloneProvider(BaseTTSProvider):
    @property
    def provider_id(self) -> str:
        return "my-local-clone"

    @property
    def provider_name(self) -> str:
        return "Local Voice Cloning (F5-TTS)"

    async def get_voices(self):
        return [
            {
                "id": "my_cloned_voice_1",
                "name": "My Cloned Voice",
                "gender": "Custom",
                "language": "my-MM",
                "language_name": "Myanmar Cloned",
                "description": "Locally cloned voice model"
            }
        ]

    async def synthesize(self, text, voice_id, output_path, rate="+0%", pitch="+0Hz", volume="+0%"):
        # Run local model inference here and save to output_path
        ...
        return True
```

2. Register in `app/main.py`:
```python
from app.providers.my_clone_provider import MyCloneProvider
tts_manager.register_provider(MyCloneProvider())
```

---

## 🛡️ Error Handling & Reliability

- **Network Glitches**: `EdgeTTSProvider` includes automatic 3-tier exponential backoff retries. If your internet is disconnected, it displays a clear notification without crashing the app.
- **Malformed Text / Encoding**: Myanmar Unicode normalization and regex splitting preserve characters like `်`, `္`, and tone marks without distortion.
- **Audio Stitching Fallback**: If `ffmpeg` is not present, the app gracefully falls back to binary MP3 frame joining.

---

## 📜 License
Personal Project - Free to customize and extend.
