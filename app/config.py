import os
from pathlib import Path

import certifi

ENVIRONMENT = os.environ.get("ENVIRONMENT", "production").lower()
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENVIRONMENT == "development":
    if DOTENV_PATH.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(str(DOTENV_PATH))
        except Exception:
            try:
                with DOTENV_PATH.open("r") as fh:
                    for raw in fh:
                        line = raw.strip()
                        if not line or line.startswith("#"):
                            continue
                        if "=" not in line:
                            continue
                        k, v = line.split("=", 1)
                        k = k.strip()
                        v = v.strip()
                        # remove single/double quotes around the value if present
                        if (v.startswith('"') and v.endswith('"')) or (
                            v.startswith("'") and v.endswith("'")
                        ):
                            v = v[1:-1]
                        # if env var not already set in the environment, populate it
                        os.environ.setdefault(k, v)
            except Exception:
                pass

bot_token = os.environ.get("SLACK_BOT_TOKEN")
app_token = os.environ.get("SLACK_APP_TOKEN")
api_key = os.environ.get("AI_API_KEY")
api_base = os.environ.get("AI_API_BASE", "https://api.example.com")
api_model = os.environ.get("AI_MODEL", "qwen/qwen3-32b")
bot_name = os.environ.get("BOT_NAME", "Assistant")
faq_link = os.environ.get("FAQ_LINK", "").strip()
validation_model = os.environ.get("AI_VALIDATION_MODEL", "x-ai/grok-4.1-fast")
max_retries = int(os.environ.get("AI_MAX_RETRIES", "2"))
LOCAL_DOCS_PATH = os.environ.get("LOCAL_DOCS_PATH", "faq.md")
HEALTH_PORT = int(os.environ.get("HEALTH_PORT", "8000"))
MAX_WORKERS = int(os.environ.get("AI_MAX_WORKERS", "5"))
AI_MAX_RPS = float(os.environ.get("AI_MAX_RPS", "20"))
AI_RPS_CAPACITY = float(os.environ.get("AI_RPS_CAPACITY", "40"))
AI_CIRCUIT_FAILS = int(os.environ.get("AI_CIRCUIT_FAILS", "6"))
AI_CIRCUIT_RECOVERY = int(os.environ.get("AI_CIRCUIT_RECOVERY", "60"))
listen_env = os.environ.get("LISTEN_CHANNEL_ID", "")
if listen_env:
    listen_channels = [c.strip() for c in listen_env.split(",") if c.strip()]
else:
    listen_channels = []
check_env = os.environ.get("CHECK_CHANNELS", "")
if check_env:
    check_channels = [c.strip() for c in check_env.split(",") if c.strip()]
else:
    check_channels = []

invite_env = os.environ.get("INVITE_CHANNELS", "")
if invite_env:
    invite_channels = [c.strip() for c in invite_env.split(",") if c.strip()]
else:
    invite_channels = []
INVITE_SYNC_INTERVAL_S = int(os.environ.get("INVITE_SYNC_INTERVAL_S", "600"))
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
AI_DEBUG = os.environ.get("AI_DEBUG", "false").lower() in ("1", "true", "yes")
