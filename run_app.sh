#!/bin/bash
# Start the Slack AI app simulator.
#
# Usage:
#   ./run_app.sh          # start the app
#   ./run_app.sh --debug  # verbose logging
#
# Press Ctrl+C to stop. DO NOT close this Terminal window while demoing —
# the app runs inside this window. Closing the window kills the app and it
# stops answering Slack messages.

set -e
cd "$(dirname "$0")"

CONFIG="config/app_config.json"
if [ ! -f "$CONFIG" ]; then
  echo "Error: $CONFIG not found."
  echo ""
  echo "Onboarding hasn't run yet. Open this folder in Claude Code and say:"
  echo "    help me set this up"
  exit 1
fi

if ! command -v claude >/dev/null 2>&1; then
  echo "Error: the 'claude' CLI is not on your PATH."
  echo ""
  echo "This simulator sends every reply through your local Claude Code install."
  echo "If Claude Code works when you type 'claude' in Terminal, you're good."
  echo "If not, install Claude Code and retry."
  exit 1
fi

if [ ! -x ".venv/bin/python" ]; then
  echo "Error: .venv/bin/python not found."
  echo ""
  echo "Run this once to set up Python:"
  echo "    python3.12 -m venv .venv"
  echo "    .venv/bin/pip install -r requirements.txt"
  exit 1
fi

# Pull display values out of app_config.json for a friendly banner.
DISPLAY_NAME=$(.venv/bin/python -c "import json; print(json.load(open('$CONFIG'))['display_name'])" 2>/dev/null || echo "Simulator")
MODEL=$(.venv/bin/python -c "import json; print(json.load(open('$CONFIG'))['model'])" 2>/dev/null || echo "sonnet")
SIMULATES=$(.venv/bin/python -c "import json; print(json.load(open('$CONFIG')).get('simulates','?'))" 2>/dev/null || echo "?")

echo ""
echo "───────────────────────────────────────────────────────────────"
echo "  $DISPLAY_NAME — simulating: $SIMULATES (model: $MODEL)"
echo "───────────────────────────────────────────────────────────────"
echo "  DO NOT CLOSE THIS TERMINAL WINDOW."
echo "  The app runs here; closing this window stops it from"
echo "  answering Slack messages. Tuck this window behind Slack,"
echo "  but don't quit it."
echo ""
echo "  Ctrl+C to stop cleanly."
echo "───────────────────────────────────────────────────────────────"
echo ""

.venv/bin/python agent/demo_agent.py "$@"
