from pathlib import Path
import os
import certifi

ENVIRONMENT = os.environ.get("ENVIRONMENT", "production").lower()
DOTENV_PATH = Path(__file__).resolve().parents[1] / ".env"
if ENVIRONMENT == "development":
    if DOTENV_PATH.exists():
        try:
            from dotenv import load_dotenv

            load_dotenv(str(DOTENV_PATH))
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
os.environ.setdefault("SSL_CERT_FILE", certifi.where())
AI_DEBUG = os.environ.get("AI_DEBUG", "false").lower() in ("1", "true", "yes")
