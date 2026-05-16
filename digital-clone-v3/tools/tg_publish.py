#!/usr/bin/env python3
"""
tg_publish.py — Telegram Post Publisher
========================================
Публикует текстовые посты в Telegram канал через Bot API.

Использование:
    python tg_publish.py "Текст поста"
    echo "Текст поста" | python tg_publish.py

Требуемые переменные окружения:
    TG_BOT_TOKEN  — токен Telegram бота
    TG_CHANNEL    — ID канала или @username (default: @agent_exe23)

Exit codes:
    0 — успех
    1 — ошибка конфигурации
    2 — ошибка API
"""

import os
import sys
import urllib.request
import urllib.error
import json


# ---------------------------------------------------------------------------
# Конфигурация
# ---------------------------------------------------------------------------

API_BASE = "https://api.telegram.org/bot{token}/{method}"


def get_config():
    """Прочитать конфигурацию из переменных окружения."""
    token = os.environ.get("TG_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    channel = os.environ.get("TG_CHANNEL", "@agent_exe23")

    if not token:
        print("ERROR: TG_BOT_TOKEN not set in environment", file=sys.stderr)
        print("Set it via: export TG_BOT_TOKEN='your_token_here'", file=sys.stderr)
        sys.exit(1)

    return token, channel


def get_post_text():
    """Получить текст поста из аргументов или stdin."""
    if len(sys.argv) > 1:
        return sys.argv[1]

    # Пробуем прочитать из stdin
    if not sys.stdin.isatty():
        text = sys.stdin.read().strip()
        if text:
            return text

    print("ERROR: No post text provided.", file=sys.stderr)
    print("Usage: python tg_publish.py 'Your post text here'", file=sys.stderr)
    print("   or: echo 'Your post text' | python tg_publish.py", file=sys.stderr)
    sys.exit(1)


def send_message(token, chat_id, text):
    """Отправить сообщение через Telegram Bot API.

    Returns:
        (success: bool, response: dict or str)
    """
    url = API_BASE.format(token=token, method="sendMessage")

    payload = {
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
    }

    data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "User-Agent": "tg_publish/1.0",
    }

    try:
        req = urllib.request.Request(url, data=data, headers=headers, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            response = json.loads(body)
            return response.get("ok", False), response
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        try:
            error_data = json.loads(body)
            error_msg = error_data.get("description", body[:200])
        except json.JSONDecodeError:
            error_msg = body[:200]
        return False, {"error": f"HTTP {exc.code}: {error_msg}"}
    except Exception as exc:
        return False, {"error": f"{type(exc).__name__}: {exc}"}


def main():
    """Главная функция."""
    token, channel = get_config()
    text = get_post_text()

    print(f"Publishing to {channel}...")
    print(f"Post length: {len(text)} chars")

    success, response = send_message(token, channel, text)

    if success:
        result = response.get("result", {})
        msg_id = result.get("message_id", "unknown")
        chat = result.get("chat", {})
        chat_title = chat.get("title", channel)
        print(f"OK: message_id={msg_id} chat='{chat_title}'")
        sys.exit(0)
    else:
        error = response.get("error", response.get("description", "Unknown error"))
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":
    main()
