"""Save the simulator bot's xoxb- token into tokens.json.

Paste from the "Install App" page of your simulator app at api.slack.com/apps.
Token is hidden during input via getpass so it doesn't appear on screen or in
Terminal scrollback.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

from slack_sdk import WebClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import audit_log, load_tokens, save_tokens  # noqa: E402


def main() -> int:
    token = getpass.getpass("Paste your app's Bot User OAuth Token (xoxb-...): ").strip()
    if not token.startswith("xoxb-"):
        print("That doesn't look like a bot token (should start with 'xoxb-').", file=sys.stderr)
        return 1

    print("Validating with Slack...")
    resp = WebClient(token=token).auth_test()
    if not resp.get("ok"):
        print(f"Slack rejected the token: {resp.get('error')}", file=sys.stderr)
        return 1

    bot_user_id = resp.get("user_id")
    bot_id = resp.get("bot_id")
    user_name = resp.get("user", "?")
    team = resp.get("team", "?")

    print(f"  bot:  {user_name} (user_id={bot_user_id}, bot_id={bot_id})")
    print(f"  team: {team}")
    confirm = input("Save under tokens['agent']['bot_token']? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return 1

    tokens = load_tokens()
    agent = tokens.setdefault("agent", {})
    agent["bot_token"] = token
    agent["bot_user_id"] = bot_user_id
    save_tokens(tokens)
    audit_log(f":robot_face: Simulator bot token saved (bot_user_id `{bot_user_id}`)")
    print("\nSaved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
