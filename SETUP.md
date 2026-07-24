# slack-ai-app-simulator — Setup

This guide takes you from a fresh clone to a working simulator in about 15 minutes. It's written for Slack Solution Engineers who are fluent in Slack but new to Terminal, Python, and building custom Slack apps.

---

## Two ways to follow this guide — pick whichever fits

- **Open this folder in Claude Code and ask *"help me set this up."*** Claude reads this guide and `CLAUDE.md` and walks you through it one step at a time, pausing for your confirmation between steps and running the commands for you when it's safe to do so. **Best if you're new to Terminal or to building Slack apps** — at any point you can ask Claude to explain what a step does or why.
- **Read it yourself.** The steps below assume you're comfortable opening a Terminal window, copy-pasting commands, and running them yourself.

Either path uses the same instructions below. Each step is tagged with `[Claude Code]`, `[Terminal]`, or `[Slack web UI]` to tell you where to run it — those tags are explained in the primer below.

---

## Before you start — if this is your first time with Terminal or Claude Code

**Claude Code** is an AI assistant that runs inside a folder on your computer. You type requests in plain English and it reads your files and runs commands for you. If you're reading this through Claude Code, you already have it installed.

**Terminal** is the Mac/Linux app that lets you type commands directly to your computer. On Windows, the equivalent is **PowerShell**. You can open Terminal on Mac from Spotlight: `Cmd+Space`, type `Terminal`, hit Enter.

**Every command below is tagged with where to run it:**

- **`[Claude Code]`** — paste the command into your Claude Code prompt, or just ask Claude to run it. Claude handles the typing.
- **`[Terminal]`** — open a dedicated Terminal window and type the command there. Use these for things that ask you for hidden input (like pasting tokens) or that you need to watch and leave running.

**About the working directory.** All commands assume you're "inside" the project folder. Claude Code is there automatically if you opened this folder. In a fresh Terminal window, you get there once with:

```bash
cd path/to/slack-ai-app-simulator
```

Replace `path/to/` with wherever you cloned/downloaded it (e.g., `cd ~/claude-projects/slack-ai-app-simulator`).

**About the `claude` CLI.** This simulator sends every reply through your local Claude Code install — specifically, the `claude` command it puts on your system. If you can type `claude` in a Terminal and have Claude Code launch, this project will work. No extra API keys needed.

**About `.venv` (Python virtual environment).** Step 2 creates a folder called `.venv` inside the project. It's a private, sandboxed copy of Python just for this project — installing packages here won't affect the rest of your system.

> ℹ **Stuck on any step?** If you're following this through Claude Code, just ask — *"what does this step do?"*, *"why am I doing this?"*, or *"that didn't work, here's what I see"* are all fair game. The whole point of the Claude Code path is that you don't have to figure anything out alone.

---

## Prerequisites

- **Slack admin** in your demo org (you'll install an app there).
- **Python 3.12** installed. Check with:
  ```bash
  python3.12 --version
  ```
  If that fails, install it:
  ```bash
  brew install python@3.12
  ```
  > **Don't have Homebrew?** Homebrew is the standard Mac package manager. Install it once from https://brew.sh, then run the `brew install` above.
  >
  > **On Windows?** Download Python 3.12 from https://www.python.org/downloads/ and **check "Add python.exe to PATH"** on the first installer screen. Then use the [Windows commands](#windows-commands) table at the bottom of this file for any step that starts with `python3.12`, `source`, or `cp`.
- **Claude Code installed** and signed in. Check with:
  ```bash
  command -v claude
  ```
  That should print a path (not "not found"). If it doesn't, install Claude Code first.

---

## Step 1 — `[Claude Code]` Tell Claude what you want to simulate

Just type in Claude Code:

> *help me set this up*

Claude will run the onboarding wizard — it'll ask:

1. Which real app are you simulating? (Claude, Asana, Notion AI, Cursor, Glean, etc.)
2. What do you want to name your Slack app? (Claude will steer you toward a unique name so it doesn't conflict with the real app if it's installed.)
3. What's the persona — what should the bot know, how should it sound, what details should it bake in?
4. Which Claude model to use (default: `sonnet`).

Claude will write three files for you:

- `agent/personas/<your-app>.md` — the persona
- `config/app_config.json` — app name, model, loading messages
- `manifest.json` — Slack app manifest (filled in from the template)

Plus example demo prompts in `examples/demo_prompts_generated.md`.

When Claude says "Step 1 done, ready for Step 2?" — continue below.

---

## Step 2 — `[Terminal]` Set up Python

Open a Terminal window and `cd` to this folder. Then:

```bash
python3.12 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

You'll see a new `.venv/` folder appear — that's the sandboxed Python install. It's gitignored.

> If you're on Windows, replace `python3.12` with `py -3.12` and `.venv/bin/pip` with `.venv\Scripts\pip.exe`. See [Windows commands](#windows-commands).

---

## Step 3 — `[Slack web UI]` Create the Slack app from the manifest

1. Open https://api.slack.com/apps in your browser.
2. Click **Create New App** → **From an app manifest**.
3. Pick your demo workspace.
4. **Double-check the app name has a differentiator.** Open `manifest.json` and look at the `name` field near the top. It should **not** be the exact name of the real Marketplace app you're simulating — it needs some visual cue that marks it as a stand-in. Examples: `Claude App`, `Cursor Sim`, `Asana Demo`, `Notion AI (Demo)`, `Glean Bot`. Any suffix or prefix that distinguishes it is fine — the specific word doesn't matter, just that your audience (and Slack's install flow) can tell this apart from the real thing.
   > **Why this matters:** if the real app later gets installed in the same workspace, Slack will either reject the duplicate or your audience will see two identically-named apps in the sidebar and get confused mid-demo.
   >
   > **If you ran the Claude Code onboarding wizard in Step 1**, a differentiator was already baked into `manifest.json` — just confirm it looks right before moving on.
5. Paste the whole `manifest.json` file into Slack's manifest box.
   > **In Claude Code**, ask Claude to open `manifest.json` and show it to you — you can copy from there.
6. Click **Next** → **Create**.
7. **Upload an app icon.** On the app's page, go to **Basic Information** in the sidebar → scroll to **Display Information** → under **App icon**, click **Add App Icon** and upload a 512×512 PNG of the real app's logo. Grab the logo from the real app's official site or brand/press page (e.g., anthropic.com for Claude, cursor.com for Cursor, asana.com for Asana). Save.
   > **Why this matters:** without an icon, your bot shows Slack's default grey silhouette in the sidebar and DM list, which breaks the demo illusion. The icon is what makes the stand-in *look* like the real app.

> **What is a manifest?** A JSON file that pre-fills every setting for your Slack app — name, scopes (permissions), event subscriptions, Socket Mode — so you don't have to click through a dozen forms.

---

## Optional — manage this app with the Slack CLI

This is the weakest CLI fit of the bunch, because the simulator runs as a standalone process (not via `slack run`), so Socket Mode's `xapp-` token and the bot `xoxb-` token still come from the Slack UI. The CLI here only saves you the manifest paste in this step.

You do **not** need the Slack CLI for this toolkit. This is a convenience for
people who'd rather create the app and manage its manifest from the terminal
instead of the Slack web UI.

**What the CLI does here:** creates the app and applies/updates its manifest
without the browser.
**What it does *not* do:** it will not hand you the app-level `xapp-` token or
the bot `xoxb-` token — you still copy those from the Slack UI in Steps 5–7
below. Socket Mode tokens are minted on the app's App-Level Tokens page
(Step 5); the CLI only manages `xapp-` automatically when an app runs under
`slack run`, which this simulator does not.

1. **Install the Slack CLI and sign in (one-time per machine).**
   Install it from the official guide
   (https://docs.slack.dev/tools/slack-cli/), then:
   ```bash
   slack login
   ```

2. **Make the CLI aware of this app's manifest (one-time in this folder).**
   Create a one-line hook file so CLI manifest commands read the
   `manifest.json` the wizard generated in Step 1:
   ```bash
   mkdir -p .slack
   printf '{ "hooks": { "get-manifest": "cat manifest.json" } }\n' > .slack/hooks.json
   ```

3. **Bring the app under CLI management — pick one:**
   - **You already created the app** in the steps above (most people): link it.
     ```bash
     slack app link --app <APP_ID> --team <TEAM_ID>
     ```
     `<APP_ID>` (starts with `A`) is on your app's **Basic Information** page;
     `<TEAM_ID>` (starts with `T`; on Enterprise Grid you may be prompted for
     a workspace grant) is your workspace ID. Linking records those IDs in
     `.slack/` so `slack` commands target this app.
   - **Starting fresh** (no app yet): preview then create + install from the
     `manifest.json` the wizard generated in Step 1.
     ```bash
     slack manifest info          # preview the manifest the CLI will apply
     slack app install
     ```
     On Enterprise Grid, `slack app install` may prompt you for a workspace
     grant instead of needing extra flags. Read the new App ID any time with:
     ```bash
     jq -r '.default_team.app_id' .slack/apps.json
     ```

4. **Push later manifest edits** (only if you edited `manifest.json`):
   ```bash
   slack app install --update
   ```

5. **Return to Step 5 (app-level token) and Step 7 (bot token)** to copy your
   token — that part is unchanged.

> The CLI does not print your bot/user token, and (for parity with the docs)
> `slack app link` only records the App ID and Team ID; it does not fetch a
> manifest. Which manifest "wins" is governed by the `manifest.source`
> setting in `.slack/config.json`, not by linking.

---

## Step 4 — `[Slack web UI]` Install the app to your workspace

1. Still on your app's page at api.slack.com, click **Install to Workspace** (or **Install to Org** for Enterprise Grid).
2. Review the permissions and click **Allow**.

After install, you'll land on the **OAuth & Permissions** page. Leave that tab open — you'll come back for the bot token in Step 7.

---

## Step 5 — `[Slack web UI]` Generate an app-level token

The simulator connects to Slack via **Socket Mode** — a way for the app to receive events without exposing a public URL from your laptop. That requires an app-level token.

1. On your app's page, click **Basic Information** in the sidebar.
2. Scroll down to **App-Level Tokens** → **Generate Token and Scopes**.
3. Name it anything (e.g., `socket-mode`).
4. Add the scope `connections:write`. Click **Generate**.
5. Copy the token (starts with `xapp-`). Keep the window open — you'll paste it in Step 6.

---

## Step 6 — `[Terminal]` Save the app-level token

Open a Terminal window (or reuse the one from Step 2), `cd` to this folder, and run:

```bash
.venv/bin/python tokens/save_app_token.py
```

It'll ask you to paste the `xapp-` token. **Your keystrokes won't appear on screen — that's intentional, not a bug.** This uses `getpass`, a standard tool for accepting secrets like tokens without leaving them in your Terminal scrollback. Just paste, press Enter, and confirm with `y`.

---

## Step 7 — `[Terminal]` Save the bot token

Go back to the browser tab on **OAuth & Permissions** (from Step 4). Copy the **Bot User OAuth Token** (starts with `xoxb-`).

Then in Terminal:

```bash
.venv/bin/python tokens/save_bot_token.py
```

Paste when prompted (again, hidden input). Confirm with `y`.

---

## Step 8 — `[Claude Code]` Fill in `team_id` and (optional) audit channel

Ask Claude to open `tokens.json`. It should look like this after Steps 6–7 (with your actual tokens in the `agent` section):

```json
{
  "team_id": "",
  "audit_channel_id": "",
  "agent": {
    "bot_token": "xoxb-...",
    "bot_user_id": "U...",
    "app_token": "xapp-..."
  }
}
```

**Fill in `team_id`.** Find it in your Slack URL when you're signed in: `app.slack.com/client/TXXXXXXXX/...` — the `T...` part is your team ID. Paste it between the quotes.

**Optionally fill in `audit_channel_id`.** Create a channel in your demo org (e.g., `#simulator-log`), invite your bot to it, then right-click the channel → **View channel details** → scroll to the bottom → copy the **Channel ID** (starts with `C`). Paste it into `audit_channel_id`. Your simulator will post every startup, error, and reply to this channel — very handy when debugging.

If you skip the audit channel, logging silently no-ops. The simulator still works.

---

## Step 9 — `[Terminal]` Run the app

> ## ⚠ Leave this Terminal window open for the whole demo
>
> The simulator runs as a long-lived process inside this window. If you close it, the bot dies and stops answering in Slack. Tuck the window behind Slack — don't quit it.

In Terminal (in this folder):

```bash
./run_app.sh
```

You should see a banner like:

```
───────────────────────────────────────────────────────────────
  ClaudeSim — simulating: Claude (Anthropic) (model: sonnet)
───────────────────────────────────────────────────────────────
  DO NOT CLOSE THIS TERMINAL WINDOW.
  ...
```

followed by scope checks (scopes are the permissions your Slack app is allowed to use — e.g., posting messages, reading user profiles):

```
bot scopes (6): assistant:write, chat:write, chat:write.customize, ...
  assistant:write: OK
  chat:write: OK
  ...
```

If any scope says `MISSING`, stop. The manifest didn't apply cleanly. Go back to Step 4 and reinstall the app — on the **Install App** page, click **Reinstall to Workspace**.

To stop the app cleanly, press `Ctrl+C`. To restart after any change, `Ctrl+C` then `./run_app.sh` again.

---

## Step 10 — `[Slack]` Verify end-to-end

1. In Slack, open a DM with your bot (search for it by display name). Send "hi".
2. Within ~2 seconds you should see a loading indicator rotate under the bot's name: *"is thinking..."*, then *"is drafting..."*, etc.
3. After ~7–10 seconds a streamed reply should appear.
4. If your bot has Block Kit enabled (Block Kit is Slack's structured-card renderer — the thing that turns JSON into nice-looking message cards, Asana-style), ask it something structured like "show me the blockers" or "give me a status summary" — the reply should render as a card, not raw JSON.
5. If your bot has taskplan enabled (the animated "Searched… → Found…" task cards / plan checklist that some research apps show while they work), ask a multi-step question like "research X and tell me what's blocking it". You should see a short animated sequence of task cards before the answer lands in the same message. A quick one-line question won't trigger it — that's expected.
6. Invite the bot to any channel (`/invite @<display_name>`), then `@<display_name> ping`. A reply should appear in-thread.

If any of those fail, check your audit channel (if you set one up). Each error logs a specific reason.

---

## Running for a demo (after initial setup)

Once you've done Steps 1–9 once, every future demo is this short recipe. Run through it ~5 minutes before your customer call.

1. **Open a new Terminal window.** On Mac: `Cmd+Space`, type `Terminal`, hit Enter.
2. **Go to the project folder.** Example:
   ```bash
   cd ~/claude-projects/slack-ai-app-simulator
   ```
   (Replace with wherever you cloned it.)
3. **Start the app.**
   ```bash
   ./run_app.sh
   ```
4. **Wait ~3 seconds for the banner and scope check.** You should see `<AppName> — simulating: ...` followed by `bot scopes (6): ...` with every scope showing `OK`. Once that's done, the bot is live in Slack.
5. **Leave this Terminal window open for the whole demo.** Tuck it behind Slack if you want it out of the way — but don't close it, don't quit it, don't `Cmd+W`, don't let your laptop sleep. Closing the window kills the bot and it stops answering mid-demo.
6. **When the demo ends**, come back to this Terminal and press `Ctrl+C` to stop cleanly.

> **Windows users:** same recipe, but Step 3 is `.venv\Scripts\python.exe agent\demo_agent.py` instead of `./run_app.sh`. See the [Windows commands](#windows-commands) table at the bottom of this file.

**If the bot stops responding mid-demo**, 90% of the time the Terminal got closed. Open a new Terminal, `cd` back to this folder, run `./run_app.sh` again, and the bot comes back online within a few seconds.

---

## Editing the persona later

Ask Claude Code *"edit the persona"* or directly edit `agent/personas/<your-app>.md`. Then **restart the app** — go to the Terminal running it, `Ctrl+C`, then `./run_app.sh` again. The persona is re-read on startup only.

---

## Adding a second persona (optional)

You can keep multiple personas in the same clone and switch between them without re-running the wizard. Useful if you demo Claude one week and Asana the next.

1. **Add the new persona file** — copy `agent/personas/_template.md.template` to `agent/personas/<new-slug>.md` and fill in the placeholders (display name, what it simulates, persona body, sample answers).
2. **Switch `config/app_config.json` to multi-persona shape.** See `config/app_config.example.multi.json` for the worked example. The shape is:
   ```json
   {
     "personas": {
       "claudesim":  { "default": true, "app_name": "...", "persona_path": "agent/personas/claudesim.md", ... },
       "asanasim":   { "app_name": "...", "persona_path": "agent/personas/asanasim.md", ... }
     }
   }
   ```
   The single-persona shape (no `personas` key) keeps working unchanged — only switch when you actually have a second one.
3. **Pick which persona runs** at launch with the `SIM_PERSONA` env var:
   ```bash
   SIM_PERSONA=asanasim ./run_app.sh
   ```
   With no env var, the simulator runs the entry marked `"default": true` (or the first entry if none is marked).

Each persona still needs its own Slack app + tokens if you want them to appear as separate bots in Slack. If you want all personas to live behind one Slack app and only swap personality, that works too — same tokens, same `manifest.json`, just a different `SIM_PERSONA` at launch. Restart `./run_app.sh` after switching.

---

## Troubleshooting

**`claude: command not found`** — Claude Code isn't installed or isn't on your PATH. Install Claude Code. If `command -v claude` still fails after install, reopen your Terminal window (PATH updates don't apply to windows already open).

**Scopes show `MISSING` at startup** — The app install didn't apply the manifest scopes. Go to api.slack.com → your app → **Install App** → **Reinstall to Workspace**. Then `Ctrl+C` the simulator and re-run.

**`not_allowed_token_type`** — You pasted an `xoxb-` where an `xapp-` was expected, or vice versa. Re-run `tokens/save_bot_token.py` or `tokens/save_app_token.py` with the right token.

**`assistant.threads.setStatus rejected`** — Missing the `assistant:write` scope, OR the "Agents & AI Apps" feature isn't enabled on your app. In api.slack.com, go to **Agents & AI Apps** in the sidebar and toggle it on, then reinstall.

**The bot stopped responding mid-demo** — 90% of the time, the Terminal window running `./run_app.sh` was closed. Reopen a Terminal, `cd` to the project folder, `./run_app.sh`, and it'll come back online.

**"I closed the Terminal by accident and my audience is watching"** — Open a new Terminal, `cd` to this folder, `./run_app.sh`, wait ~3 seconds for the banner and scope check, and resume. Existing Slack threads will work — in-memory conversation history is lost, but the persona is what drives responses, so the bot will stay in character.

**The loading indicator shows but no reply appears** — The `claude` subprocess is probably failing silently. Check your audit channel for an error entry, or re-run with verbose logging:
```bash
./run_app.sh --debug
```

**Socket Mode disconnected silently** — `slack_sdk.SocketModeClient` auto-reconnects, but messages sent during the dead window are **not** replayed. If the bot misses a message, just re-send it.

**Bot seems to receive my message but never replies** — Re-run with `./run_app.sh --debug` and search the log for the raw Socket Mode event payload. If the event arrived but the bot didn't respond, the most common cause is an event with `bot_id` set that the filter should be passing through but isn't. Check that you haven't edited `agent/demo_agent.py` to re-introduce a blanket `if event.get("bot_id"): return` — see `CLAUDE.md` "Known persona pitfalls."

**"ERROR: Another simulator instance is already running (PID ...)"** — A second `./run_app.sh` can't run while a first is live. Either stop the first (`Ctrl+C` in that Terminal) or `kill <PID>`, then start again. This guard prevents two instances from racing over the Socket Mode connection (Slack delivers events to the last-connected instance, which creates baffling "the bot answered once then stopped" bugs).

**I renamed the bot but Slack's typing indicator still shows the old name** — The typing indicator uses the bot's Slack profile `real_name`, which isn't controlled by `config/app_config.json` `display_name` or the manifest. To change it, go to **api.slack.com → your app → Bot User → Edit** and update the name there. Calling `users.profile.set` from code does not work for bot tokens (it returns `not_allowed_token_type`).

**The task-card animation doesn't appear, or raw `taskplan` JSON shows up in the message** — The streaming task cards need `slack-sdk` 3.40 or newer (the chunk models didn't exist before then). Re-run `.venv/bin/pip install -r requirements.txt` to pick up the bumped pin, then `Ctrl+C` the app and `./run_app.sh` again. Also confirm `"taskplan_enabled": true` is set in `config/app_config.json` for the persona you're running.

---

## Windows commands

Windows users: Steps 1, 3, 4, 5 are all in the browser and work as written. The differences are in Steps 2, 6, 7, 9:

| Step | Mac/Linux | Windows (PowerShell) |
|---|---|---|
| 2 — create venv | `python3.12 -m venv .venv` | `py -3.12 -m venv .venv` |
| 2 — install deps | `.venv/bin/pip install -r requirements.txt` | `.venv\Scripts\pip.exe install -r requirements.txt` |
| 6 — save app token | `.venv/bin/python tokens/save_app_token.py` | `.venv\Scripts\python.exe tokens\save_app_token.py` |
| 7 — save bot token | `.venv/bin/python tokens/save_bot_token.py` | `.venv\Scripts\python.exe tokens\save_bot_token.py` |
| 9 — run the app | `./run_app.sh` | `.venv\Scripts\python.exe agent\demo_agent.py` |

**First-time PowerShell note:** If Windows refuses to run the venv's scripts with "running scripts is disabled," run this once and retry:

```powershell
Set-ExecutionPolicy -Scope CurrentUser RemoteSigned
```
