"""Shared config: token loading, Slack client init, app config, audit logging."""
from __future__ import annotations

import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError

ROOT = Path(__file__).resolve().parent
TOKENS_PATH = ROOT / "tokens.json"
APP_CONFIG_PATH = ROOT / "config" / "app_config.json"


def load_tokens() -> dict[str, Any]:
    if not TOKENS_PATH.exists():
        raise RuntimeError(
            f"tokens.json not found at {TOKENS_PATH}. "
            "Copy tokens.example.json to tokens.json and follow SETUP.md to fill it in."
        )
    with TOKENS_PATH.open() as f:
        return json.load(f)


def save_tokens(tokens: dict[str, Any]) -> None:
    """Write tokens.json atomically with owner-only permissions.

    Atomic: write to a sibling tmp file, then os.replace() — a crash mid-write
    can never leave tokens.json half-written.
    Permissions: 0600 so other users on the machine can't read xoxb-/xapp-
    tokens. Applied before the rename so the final file is never briefly
    world-readable. (No-op on Windows beyond the read-only bit.)
    """
    tmp = TOKENS_PATH.with_suffix(".json.tmp")
    with tmp.open("w") as f:
        json.dump(tokens, f, indent=2)
        f.write("\n")
    os.chmod(tmp, 0o600)
    os.replace(tmp, TOKENS_PATH)


def load_app_config() -> dict[str, Any]:
    """Return the per-SE app config (name, persona path, model, loading messages).

    Missing file means onboarding hasn't run — tell the user to open this folder
    in Claude Code and say 'help me set this up.'
    """
    if not APP_CONFIG_PATH.exists():
        raise RuntimeError(
            f"{APP_CONFIG_PATH} not found. Run the onboarding wizard: open this "
            "folder in Claude Code and say 'help me set this up.'"
        )
    with APP_CONFIG_PATH.open() as f:
        return json.load(f)


def agent_bot_client() -> WebClient:
    """Returns a WebClient using the simulator bot's xoxb- token."""
    tokens = load_tokens()
    bot_token = tokens.get("agent", {}).get("bot_token")
    if not bot_token:
        raise RuntimeError(
            "No agent.bot_token in tokens.json. Run `tokens/save_bot_token.py` first."
        )
    return WebClient(token=bot_token)


def audit_log(message: str, *, client: WebClient | None = None) -> None:
    """Post a timestamped entry to the audit channel. Never raises.

    Silently no-ops if `audit_channel_id` is empty in tokens.json, so audit
    logging is opt-in for SEs who haven't set up a dedicated log channel yet.
    """
    try:
        tokens = load_tokens()
    except Exception:
        return
    channel = tokens.get("audit_channel_id")
    if not channel:
        return
    bot_token = tokens.get("agent", {}).get("bot_token")
    if not bot_token:
        return
    client = client or WebClient(token=bot_token)
    timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%SZ")
    try:
        client.chat_postMessage(channel=channel, text=f"`{timestamp}` {message}")
    except SlackApiError as e:
        print(f"[audit_log failed] {e.response['error']}: {message}")
