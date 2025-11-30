import os
import re
import json
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from .ai_helpers import read_faq, local_validate
from .config import (
    api_base,
    api_model,
    api_key,
    faq_link,
    listen_channels,
    MAX_WORKERS,
    AI_MAX_RPS,
    AI_RPS_CAPACITY,
    AI_CIRCUIT_FAILS,
    AI_CIRCUIT_RECOVERY,
    bot_name,
    LOCAL_DOCS_PATH,
)
from .utils import update_metric, create_session, CircuitBreaker, TokenBucket
from typing import Callable

session = create_session()
rate_limiter = TokenBucket(rate=AI_MAX_RPS, capacity=AI_RPS_CAPACITY)
circuit_breaker = CircuitBreaker(failure_threshold=AI_CIRCUIT_FAILS, recovery_timeout=AI_CIRCUIT_RECOVERY)


def _post_with_policies(url, payload, headers, timeout=(20, 30)):
    if not circuit_breaker.allow():
        raise RuntimeError("Circuit open")
    if not rate_limiter.consume(timeout=1.0):
        raise RuntimeError("Rate limited")
    start = time.monotonic()
    update_metric("api_requests_total", 1)
    resp = session.post(url, headers=headers, json=payload, timeout=timeout)
    resp.raise_for_status()
    elapsed = int((time.monotonic() - start) * 1000)
    update_metric("api_request_success", 1)
    update_metric("api_request_latency_ms_sum", elapsed)
    circuit_breaker.record_success()
    return resp


def process_message(channel_arg, ts_arg, text_arg, client_arg, logger_arg):
    try:
        url = f"{api_base.rstrip('/')}/proxy/v1/chat/completions"
        local_path_inner = LOCAL_DOCS_PATH
        faq_text_inner = read_faq(local_path_inner)
        if not faq_text_inner:
            return
        headers_inner = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        check_system = (
            f"You are a system checker. Using ONLY the FAQ below, decide whether the FAQ contains the answer. Reply ONLY 'YES' or 'NO' and include a single short justification (one sentence)."
        )
        answer_system = (
            f"You are a friendly assistant. Use ONLY the FAQ below to answer the user's question. Start with a brief greeting and give a concise answer. At the end, add a one-line disclaimer stating that the information was taken from the FAQ and may be incomplete. Also suggest the user close the ticket if the question is resolved."
        )
        check_payload_inner = {
            "model": api_model,
            "messages": [
                {"role": "system", "content": check_system + "\n\nFAQ:\n" + (faq_text_inner or "")},
                {"role": "user", "content": f"Question: {text_arg}\nDoes the FAQ above contain the answer? Reply only YES or NO and a one-line justification."},
            ],
            "stream": False,
            "temperature": 0.0,
            "max_tokens": 200,
        }
        try:
            resp = _post_with_policies(url, check_payload_inner, headers_inner, timeout=(15, 30))
            data = resp.json()
            choices = data.get("choices") or []
            if choices:
                check_reply_inner = choices[0].get("message", {}).get("content", "").strip()
            else:
                check_reply_inner = "NO"
        except Exception:
            return
        if not re.search(r"\bYES\b", check_reply_inner, re.IGNORECASE):
            return
        answer_payload_inner = {
            "model": api_model,
            "messages": [
                {"role": "system", "content": answer_system + "\n\nFAQ:\n" + (faq_text_inner or "")},
                {"role": "user", "content": f"Question: {text_arg}\nProvide a concise answer based only on the FAQ."},
            ],
            "stream": False,
            "temperature": 0.2,
            "max_tokens": 512,
        }
        attempt_inner = 0
        final_msg_inner = None
        max_retries = int(os.environ.get("AI_MAX_RETRIES", "2"))
        while attempt_inner <= max_retries:
            try:
                resp = _post_with_policies(url, answer_payload_inner, headers_inner, timeout=(20, 30))
                data = resp.json()
                choices = data.get("choices") or []
                if choices:
                    msg_inner = choices[0].get("message", {}).get("content")
                else:
                    msg_inner = None
            except Exception:
                msg_inner = None
            if not msg_inner:
                return
            ok_inner, why_inner = local_validate(msg_inner, faq_link or "the provided FAQ document")
            if ok_inner:
                final_msg_inner = msg_inner
                break
            attempt_inner += 1
            if attempt_inner > max_retries:
                break
            fix_note_inner = f"Please regenerate the answer and fix the following: {why_inner}" if why_inner else "Please regenerate the answer to match the required format."
            answer_payload_inner["messages"][1]["content"] = f"Question: {text_arg}\nProvide a concise answer based only on the FAQ. {fix_note_inner}"
        if not final_msg_inner:
            return
        try:
            client_arg.chat_postMessage(channel=channel_arg, text=final_msg_inner, thread_ts=ts_arg)
        except Exception:
            return
    except Exception:
        return


executor = ThreadPoolExecutor(max_workers=int(os.environ.get("AI_MAX_WORKERS", "5")))


def register_handlers(app):
    @app.event("message")
    def handle_message_events(body, event, client, logger):
        if event.get("subtype") is not None:
            return
        if event.get("bot_id"):
            return
        if event.get("thread_ts"):
            return
        channel = event.get("channel")
        ts = event.get("ts")
        text = event.get("text")
        if not (channel and ts and text):
            return
        if listen_channels and channel not in listen_channels:
            return
        try:
            executor.submit(process_message, channel, ts, text, client, logger)
        except Exception:
            raise
