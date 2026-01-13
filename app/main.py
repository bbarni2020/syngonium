import http.server
import json
import logging
import os
import socketserver

from slack_bolt import App
from slack_bolt.adapter.socket_mode import SocketModeHandler

from .config import AI_DEBUG, BOT_MAINTAINER_SLACKID, HEALTH_PORT, app_token, bot_token
from .handlers import _send_maintainer_dm, register_handlers, setup_startup_handler


def create_app():
    if AI_DEBUG:
        logging.basicConfig(
            level=logging.DEBUG, format="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    else:
        logging.basicConfig(
            level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s"
        )
    if not bot_token or not app_token:
        raise SystemExit("Missing SLACK_BOT_TOKEN or SLACK_APP_TOKEN")
    app = App(token=bot_token)
    register_handlers(app)
    logger = logging.getLogger(__name__)
    setup_startup_handler(app, logger)
    return app


def _start_health_server(port: int = HEALTH_PORT, metrics=None):
    class SimpleHandler(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            if self.path == "/health":
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.end_headers()
                commit = os.environ.get("GIT_COMMIT_HASH", "unknown")
                self.wfile.write(
                    json.dumps({"status": "ok", "commit": commit}).encode()
                )
            elif self.path == "/metrics":
                self.send_response(200)
                self.send_header("Content-Type", "text/plain; version=0.0.4")
                self.end_headers()
                if metrics:
                    for k, v in metrics.items():
                        self.wfile.write(f"bot_{k} {v}\n".encode())
            else:
                self.send_response(404)
                self.end_headers()

    server_thread = None
    # port already defaults from config, but allow env override
    try:
        port = int(os.environ.get("HEALTH_PORT", str(port)))
    except Exception:
        pass
    server_thread = socketserver.TCPServer(("", port), SimpleHandler)
    server_thread.allow_reuse_address = True
    import threading

    t = threading.Thread(target=server_thread.serve_forever, daemon=True)
    t.start()
    logging.info("Health server started on port %s", port)
    return server_thread


def start():
    logging.getLogger("construct.bot")
    logger = logging.getLogger(__name__)
    app = create_app()
    handler = SocketModeHandler(app, app_token)
    _start_health_server()
    try:
        if BOT_MAINTAINER_SLACKID:
            _send_maintainer_dm(app.client, "Bot is online and ready!", logger)
    except Exception as e:
        logger.error("Failed to send startup notification: %s", e)
    handler.start()


if __name__ == "__main__":
    start()
