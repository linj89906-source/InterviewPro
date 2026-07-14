import os
from pathlib import Path

# Load .env from the backend directory (only works in local dev)
try:
    from dotenv import load_dotenv
    env_path = Path(__file__).resolve().parent.parent / ".env"
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
except Exception:
    pass  # Render / production uses system environment variables

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_BASE_URL = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
AMAP_API_KEY = os.getenv("AMAP_API_KEY", "")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./interview.db")

if not OPENAI_API_KEY:
    print("[Config] WARNING: OPENAI_API_KEY is not set! AI features will not work.")
else:
    print(f"[Config] OPENAI_API_KEY loaded. Base: {OPENAI_BASE_URL} Model: {OPENAI_MODEL}")

if not AMAP_API_KEY:
    print("[Config] WARNING: AMAP_API_KEY is not set! Location features will not work.")
