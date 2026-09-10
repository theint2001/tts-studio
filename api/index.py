import sys
import os
from urllib.parse import parse_qs, urlencode

# Ensure root project directory is on sys.path so app package can be imported
root_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if root_dir not in sys.path:
    sys.path.insert(0, root_dir)

from app.main import app as fastapi_app

class VercelPathFixer:
    """
    ASGI middleware for Vercel Serverless Functions.
    Restores the original request path from the query parameter '__path__'
    when Vercel rewrites /api/(.*) to /api/index.py.
    """
    def __init__(self, app):
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope.get("type") == "http":
            qs_bytes = scope.get("query_string", b"")
            qs = qs_bytes.decode("latin-1")
            params = parse_qs(qs, keep_blank_values=True)

            if "__path__" in params and params["__path__"]:
                subpath = params.pop("__path__")[0]
                clean_subpath = subpath if subpath.startswith("/") else f"/{subpath}"
                scope["path"] = f"/api{clean_subpath}"
                scope["raw_path"] = scope["path"].encode("latin-1")
                scope["query_string"] = urlencode(params, doseq=True).encode("latin-1")

        await self.app(scope, receive, send)

# Export ASGI entrypoint for Vercel
app = VercelPathFixer(fastapi_app)
