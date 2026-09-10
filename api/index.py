import sys
import os

# Ensure root project directory is on sys.path so app package can be imported
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app

# Vercel ASGI handler
# app is exported as the ASGI entrypoint
