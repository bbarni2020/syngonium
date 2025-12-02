import os
import re
import time
from concurrent.futures import ThreadPoolExecutor

from .ai_helpers import local_validate, read_faq
from .config import (
    AI_CIRCUIT_FAILS,
    AI_CIRCUIT_RECOVERY,
    AI_MAX_RPS,
    AI_RPS_CAPACITY,
    LOCAL_DOCS_PATH,
    api_base,
    api_key,
    api_model,
    check_channels,
    faq_link,
    invite_channels,
    listen_channels,
)
from .utils import CircuitBreaker, TokenBucket, create_session, update_metric

session = create_session()
rate_limiter = TokenBucket(rate=AI_MAX_RPS, capacity=AI_RPS_CAPACITY)
circuit_breaker = CircuitBreaker(
    failure_threshold=AI_CIRCUIT_FAILS, recovery_timeout=AI_CIRCUIT_RECOVERY
)

CHECK_SYSTEM_PROMPT = (
    "You are a system checker. Using ONLY the FAQ below, decide whether the FAQ contains the answer. "
    "Reply ONLY 'YES' or 'NO' and include a single short justification (one sentence)."
)

ANSWER_SYSTEM_PROMPT = (
    "You are a friendly, slightly playful assistant. Use ONLY the FAQ below to answer the user's question. "
    "Start with a brief friendly greeting (for example: 'Hi', 'Hello', 'Hiya') and then provide a concise, factual answer. "
    "Keep the tone warm and approachable — you may include a short emoji or a friendly phrase (e.g., 'Cheers!') to add personality, but keep the information accurate and grounded in the FAQ. "
    "Use Slack mrkdwn formatting: *bold* for importance, `code` for commands/paths, and > for quotes. Do not use **bold** or [links](url). "
    "At the end, include a one-line disclaimer stating the information was taken from the FAQ and may be incomplete (eg. 'Information above is taken from the FAQ and may be incomplete.'). "
    "If the question is resolved by the FAQ, suggest the user close the ticket (for example: 'If this helped, please close the ticket.'). "
    "Do NOT ask the user follow-up questions, nor offer open-ended invites to follow up (avoid phrases like 'let me know', 'do you need', 'any other questions', 'contact me', 'follow up')."
)


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
        check_system = CHECK_SYSTEM_PROMPT
        answer_system = ANSWER_SYSTEM_PROMPT
        check_payload_inner = {
            "model": api_model,
            "messages": [
                {
                    "role": "system",
                    "content": check_system + "\n\nFAQ:\n" + (faq_text_inner or ""),
                },
                {
                    "role": "user",
                    "content": f"Question: {text_arg}\nDoes the FAQ above contain the answer? Reply only YES or NO and a one-line justification.",
                },
            ],
            "stream": False,
            "temperature": 0.0,
            "max_tokens": 200,
        }
        try:
            resp = _post_with_policies(
                url, check_payload_inner, headers_inner, timeout=(15, 30)
            )
            data = resp.json()
            choices = data.get("choices") or []
            if choices:
                check_reply_inner = (
                    choices[0].get("message", {}).get("content", "").strip()
                )
            else:
                check_reply_inner = "NO"
        except Exception:
            return
        if not re.search(r"\bYES\b", check_reply_inner, re.IGNORECASE):
            return
        answer_payload_inner = {
            "model": api_model,
            "messages": [
                {
                    "role": "system",
                    "content": answer_system + "\n\nFAQ:\n" + (faq_text_inner or ""),
                },
                {
                    "role": "user",
                    "content": f"Question: {text_arg}\nProvide a concise answer based only on the FAQ.",
                },
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
                resp = _post_with_policies(
                    url, answer_payload_inner, headers_inner, timeout=(20, 30)
                )
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
            ok_inner, why_inner = local_validate(
                msg_inner, faq_link or "the provided FAQ document"
            )
            if ok_inner:
                final_msg_inner = msg_inner
                break
            attempt_inner += 1
            if attempt_inner > max_retries:
                break
            fix_note_inner = (
                f"Please regenerate the answer and fix the following: {why_inner}"
                if why_inner
                else "Please regenerate the answer to match the required format."
            )
            answer_payload_inner["messages"][1][
                "content"
            ] = f"Question: {text_arg}\nProvide a concise answer based only on the FAQ. {fix_note_inner}"
        if not final_msg_inner:
            return
        try:
            client_arg.chat_postMessage(
                channel=channel_arg, text=final_msg_inner, thread_ts=ts_arg
            )
        except Exception:
            return
    except Exception:
        return


executor = ThreadPoolExecutor(max_workers=int(os.environ.get("AI_MAX_WORKERS", "5")))


def _get_channel_members(client, channel_id):
    members = set()
    cursor = None
    while True:
        try:
            kwargs = {"channel": channel_id, "limit": 1000}
            if cursor:
                kwargs["cursor"] = cursor
            resp = client.conversations_members(**kwargs)
            page_members = resp.get("members") or []
            members.update(page_members)
            cursor = resp.get("response_metadata", {}).get("next_cursor") or None
            if not cursor:
                break
        except Exception:
            break
    return members


def _is_bot_or_deleted(client, user_id):
    try:
        resp = client.users_info(user=user_id)
        user = resp.get("user") or {}
        if user.get("deleted"):
            return True
        if user.get("is_bot"):
            return True
        return False
    except Exception:
        return True


def invite_missing_users(client, logger=None):
    if not check_channels or not invite_channels:
        return
    if not hasattr(client, "conversations_members"):
        return
    for check_chan in check_channels:
        try:
            source_members = _get_channel_members(client, check_chan)
        except Exception:
            source_members = set()
        if not source_members:
            continue
        for invite_chan in invite_channels:
            try:
                target_members = _get_channel_members(client, invite_chan)
            except Exception:
                target_members = set()
            to_invite = [u for u in source_members if u not in target_members]
            if not to_invite:
                continue
            for user in to_invite:
                if _is_bot_or_deleted(client, user):
                    continue
                try:
                    client.conversations_invite(channel=invite_chan, users=user)
                    update_metric("invite_success", 1)
                except Exception as e:
                    update_metric("invite_failure", 1)
                    try:
                        msg = getattr(e, "response", {}).get("error")
                    except Exception:
                        msg = None
                    if msg and "already_in_channel" in msg:
                        continue
                    if logger:
                        try:
                            logger.error(
                                "Failed to invite %s to %s: %s", user, invite_chan, e
                            )
                        except Exception:
                            pass


def invite_user_to_channels(client, user_id, src_channel=None, logger=None):
    if not check_channels or not invite_channels:
        return
    if src_channel and check_channels and src_channel not in check_channels:
        return
    if _is_bot_or_deleted(client, user_id):
        return
    for invite_chan in invite_channels:
        try:
            target_members = _get_channel_members(client, invite_chan)
        except Exception:
            target_members = set()
        if user_id in target_members:
            continue
        try:
            client.conversations_invite(channel=invite_chan, users=user_id)
            update_metric("invite_success", 1)
        except Exception as e:
            update_metric("invite_failure", 1)
            try:
                msg = getattr(e, "response", {}).get("error")
            except Exception:
                msg = None
            if msg and "already_in_channel" in msg:
                continue
            if logger:
                try:
                    logger.error(
                        "Failed to invite %s to %s: %s", user_id, invite_chan, e
                    )
                except Exception:
                    pass


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

    @app.event("member_joined_channel")
    def handle_member_joined_channel_events(body, event, client, logger):
        try:
            user = event.get("user")
            channel = event.get("channel")
            if not user:
                return
            if channel and check_channels and channel not in check_channels:
                return
            try:
                executor.submit(invite_user_to_channels, client, user, channel, logger)
            except Exception:
                try:
                    invite_user_to_channels(client, user, channel, logger)
                except Exception:
                    pass
        except Exception:
            return
