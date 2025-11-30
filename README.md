# Slack FAQ Assistant (short)

A tiny Slack bot that answers short Qs using your FAQ. It reads a local FAQ and posts concise, FAQ-backed replies in threads.

Requirements
- Python 3.8+
- Install deps: `pip install -r bot/requirements.txt`

Quick setup
1. Copy `.env.example` → `.env` and set at least:
   - `SLACK_BOT_TOKEN`, `SLACK_APP_TOKEN`, `AI_API_KEY`, `LOCAL_DOCS_PATH`
   - Optional/Helpful envs: `AI_API_BASE`, `AI_MODEL`, `AI_VALIDATION_MODEL`, `BOT_NAME`, `LISTEN_CHANNEL_ID`, `FAQ_LINK`, `AI_DEBUG`, `HEALTH_PORT`
2. Add your FAQ to `LOCAL_DOCS_PATH` (default `bot/faq.md`).

Note: The app will only auto-load `.env` if `ENVIRONMENT=development`. To run locally and have `.env` be read automatically, use:
```bash
ENVIRONMENT=development python -m app.main
```

## Secret scanning (pre-commit)

This repository now includes secret-scanning hooks via pre-commit to help prevent accidental commits of secrets. We check for private keys and other tokens using `detect-secrets` and related hooks.

Recommended quick steps:

```bash
# Install pre-commit and the hooks
pip install pre-commit
pre-commit install

# Generate a baseline of current findings (do this if you're setting hooks up for the first time)
detect-secrets scan > .secrets.baseline

# Run all the hooks on the repo (useful to scan and surface any issues locally)
pre-commit run --all-files
```

If an existing rule flags a known/acceptable value, regenerate the baseline and commit the new `.secrets.baseline` file so it won't block future commits.

If you upgrade detect-secrets or add new plugins, re-generate the baseline to avoid incompatible plugin versions in the baseline.


Run (locally)
```bash
python -m app.main
```

Run (Docker)
```bash
docker build -t slack-faq-bot .
docker run --env-file .env -it slack-faq-bot
```

Config
- `AI_MAX_WORKERS` — concurrent requests (default 5)
- `AI_MAX_RETRIES` — retry attempts (default 2)
 - `AI_API_BASE` — base URL for the AI api (default https://api.example.com)
 - `AI_MODEL` — model used for generation (default qwen/qwen3-32b)
 - `AI_VALIDATION_MODEL` — model used to validate replies (default x-ai/grok-4.1-fast)
 - `BOT_NAME` — display name of the bot (default Assistant)
 - `LISTEN_CHANNEL_ID` — channel id to limit listening to specific channels
 - `LOCAL_DOCS_PATH` — path to the local FAQ file (default: `faq.md`)
 - `FAQ_LINK` — link to the FAQ used for references
 - `AI_DEBUG` — toggle debug level logging when set to true
 - `HEALTH_PORT` — port for the health server (default 8000)

# Slack FAQ Assistant Bot

Why it exists
- Because people ask the same things and we want consistent, FAQ-backed answers.
- The bot keeps replies short and cites the FAQ so people can trust the answer and close their tickets quickly.

Quick start
1. Set up the Python environment and install dependencies:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Create a Slack app with Socket Mode enabled, add `chat:write` and install it.
3. Make a `.env` file (copy `.env.example`) and fill in the tokens and API keys.
4. Put your FAQ in `bot/faq.md` or point `LOCAL_DOCS_PATH` to your document.

Run it

```bash
source .venv/bin/activate
python -m bot.bot
```

Tip: If imports cause headaches, run as a module with `python -m bot.bot` — that helps Python find the `bot` package.

Pre-commit & code style
- Install pre-commit in your development environment:

```bash
pip install pre-commit
pre-commit install
pre-commit run --all-files # optional, to fix and format all files once
```

You'll also find a GitHub Actions workflow at `.github/workflows/pre-commit.yml` that runs the hooks on push/PR to ensure CI checks match local checks.

Config highlights
- `AI_MAX_WORKERS` — concurrent workers (default 5)
- `AI_MAX_RETRIES` — retries for generation/validation (default 2)
- `AI_MODEL`, `AI_VALIDATION_MODEL`, `AI_API_BASE` — model and endpoint (if applicable)
- `LOCAL_DOCS_PATH` — where your FAQ lives
- `ENVIRONMENT` — set to `production` during deployment; set to `development` locally to enable `.env` auto-loading (default `production`)
- `AI_MAX_RPS` — max requests per second allowed to upstream AI service (default `20`)
- `AI_RPS_CAPACITY` — burst capacity for the token-bucket rate limiter (default `40`)
- `AI_CIRCUIT_FAILS`, `AI_CIRCUIT_RECOVERY` — circuit breaker tuning (defaults 6 fails, 60s recovery)
