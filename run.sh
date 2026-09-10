#!/usr/bin/env bash
set -e

DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR"

echo "🎙️  Starting Personal TTS Studio..."

# 1. Virtual Environment Setup
if [ ! -d "venv" ]; then
    echo "Creating Python virtual environment..."
    python3 -m venv venv
    ./venv/bin/pip install --upgrade pip
    ./venv/bin/pip install -r requirements.txt
fi

# 2. Storage Setup
mkdir -p storage/audio

# 3. Clean up any existing process on port 8000 if running
PID=$(lsof -ti :8000 2>/dev/null || true)
if [ -n "$PID" ]; then
    echo "⚠️  Port 8000 was in use by PID $PID. Freeing up port..."
    kill -9 $PID 2>/dev/null || true
    sleep 1
fi

echo ""
echo "============================================================"
echo "  🚀 Personal TTS Studio is running!"
echo "  🔊 Myanmar Unicode (🇲🇲) & British English (🇬🇧)"
echo "  🌐 Open in your browser: http://127.0.0.1:8000"
echo "============================================================"
echo ""

# 4. Auto-open in default browser on macOS in background
(sleep 1.5 && open "http://127.0.0.1:8000") &

# 5. Launch FastAPI Server
./venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 8000 --reload
