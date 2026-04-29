"""Save the simulator app's app-level xapp- token (Socket Mode) into tokens.json.

Paste from "Basic Information → App-Level Tokens" of your simulator app.
Validates by opening (and immediately discarding) a Socket Mode connection.
"""
from __future__ import annotations

import getpass
import sys
from pathlib import Path

from slack_sdk import WebClient

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from config import audit_log, load_tokens, save_tokens  # noqa: E402


def main() -> int:
    token = getpass.getpass("Paste your app's App-Level Token (xapp-...): ").strip()
    if not token.startswith("xapp-"):
        print("That doesn't look like an app-level token (should start with 'xapp-').", file=sys.stderr)
        return 1

    print("Validating via apps.connections.open...")
    resp = WebClient(token=token).api_call("apps.connections.open")
    if not resp.get("ok"):
        err = resp.get("error")
        print(f"Slack rejected the token: {err}", file=sys.stderr)
        if err == "missing_scope":
            print("  The xapp- token needs the 'connections:write' scope.", file=sys.stderr)
        return 1

    print("  OK — Socket Mode connection issued and discarded.")
    confirm = input("Save under tokens['agent']['app_token']? [y/N]: ").strip().lower()
    if confirm != "y":
        print("Aborted.")
        return 1

    tokens = load_tokens()
    agent = tokens.setdefault("agent", {})
    agent["app_token"] = token
    save_tokens(tokens)
    audit_log(":electric_plug: Simulator app-level (Socket Mode) token saved")
    print("\nSaved.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
