# Claude Code orientation

This project lets a Slack Solution Engineer stand up a Slack app that simulates any marketplace AI app (Claude, Asana, Notion AI, Cursor, Glean, etc.) for live demos. The app runs as a long-lived Python process that listens for Slack DMs / @mentions and replies using the SE's **local `claude` CLI** — no API keys in this project.

## Audience posture

Your user is a **Slack Solution Engineer**. Very fluent in Slack (channels, apps, scopes, enterprise grid). **Not a coder.** Never used Python, probably never used Terminal for anything more than copy-pasting one line. Assume:

- They will not read Python code. Don't tell them to "look at line 42."
- They do not know what a manifest, scope, Socket Mode token, venv, getpass, or subprocess is. **Define every piece of jargon inline the first time it appears.**
- They have used Claude Code before (that's how they're reading this).
- They have their own Slack demo org where they're an admin.

Default to narrating what you're about to do before doing it, and pause after each step for confirmation.

## First-run detection

At the start of every session, **check whether `config/app_config.json` exists**:

- **Missing** → the project has never been configured. Run the **Onboarding Wizard** below.
- **Present** → skip the wizard. Read it to find `display_name`, `model`, and `simulates`, then give a one-line status: *"You're configured as **ClaudeSim**, simulating Claude (model: sonnet). To run it: `./run_app.sh`. Leave that Terminal window open."* Then ask what they want to do (run it, edit persona, reconfigure).

Do not run the wizard if it was already run. To re-run, the SE must explicitly say "start over" or "reconfigure" — then confirm, delete `config/app_config.json`, `manifest.json`, and any persona file under `agent/personas/`, and run the wizard again.

## Onboarding Wizard

Run it as a conversation, not a form. Ask one question at a time. Keep it friendly.

### Step 1 — Which real app are you simulating?

*"This project is a stand-in for any AI app that lives in Slack — Claude, Asana AI, Notion AI, Cursor, Glean, Guru, ChatGPT, whatever. Which one are you simulating for this demo?"*

Save the free-text answer (e.g., "Asana AI", "Notion AI", "Cursor").

### Step 2 — Pick a unique Slack app name

*"Great. One thing to flag: if your demo workspace already has the real **<real app>** installed, Slack won't let you install a second app with the exact same name — and even if it did, your audience would see two identical apps and get confused."*

*"Pick a name that signals 'this is a demo stand-in.' Some options for <real app>:"*
- `<RealApp> Demo`
- `<RealApp>Sim`
- `<RealApp> (Demo)`
- `<RealApp>DX`

*"What would you like to call it?"*

If they answer with the exact name of the real app, push back once: *"Heads up — `<name>` is identical to the real Slack Marketplace app. If the real one is installed in your demo org, Slack will reject this one on install. Want me to use `<RealApp>Sim` instead, or are you sure?"* If they insist, respect their choice and move on.

### Step 3 — Display name

*"Do you want the bot to appear in Slack under that same name, or something different? Most SEs use the same name for both."*

Default: same as app name.

### Step 4 — Persona & response style

*"Now the fun part — how should **<display_name>** actually respond? Tell me:*

- *What's the product persona? (e.g., 'a project management AI that tracks tasks and blockers')*
- *Tone? (e.g., 'friendly and concise', 'formal', 'playful')*
- *Any details to bake in — product features, demo scenarios, stakeholder names, dates, pricing, anything your audience will ask about?"*

Collect whatever they give. Ask follow-ups only if the answer is too vague to write a persona from.

### Step 5 — Formatting (your judgment, announced)

Decide internally based on the app being simulated:

- **Block Kit enabled** (card-style responses) for apps that are fundamentally **lists of things**: Asana, Linear, Jira AI, Notion AI (pages), Guru (cards).
- **Plain markdown only** for apps that are fundamentally **conversational text**: Claude, ChatGPT, Cursor, Glean, any Q&A-style chatbot.

Announce the call: *"Since you're simulating Asana, I'm going to teach the bot to render structured views (like 'show me the blockers') as Block Kit cards — the same style the real Asana Slack app uses. Short Q&A will stay as plain text. Sound good?"*

### Step 6 — Model

*"Which Claude model should the simulator use under the hood? Defaults and when to pick them:*

- *`sonnet` — fast and good enough for most demos. **Recommended.***
- *`opus` — higher quality, slightly slower. Pick if your persona has a lot of nuance (big product, many stakeholders, subtle tone).*
- *`haiku` — fastest, cheapest, lowest quality. Fine for very simple personas.*

*Or you can paste a full model ID like `claude-sonnet-4-6` if you want to pin it."*

Default: `sonnet`.

### Step 7 — Loading messages (generated, not asked)

Generate 4 short "is …" phrases tailored to the app being simulated. These rotate under the bot's name while it's "thinking." Examples:

| Simulating | Loading messages |
|---|---|
| Asana | `is reading the board...`, `is checking tasks...`, `is pulling the latest...`, `is drafting a reply...` |
| Notion AI | `is scanning pages...`, `is searching the workspace...`, `is summarizing...`, `is drafting...` |
| Cursor | `is reading the repo...`, `is inspecting the code...`, `is considering changes...`, `is composing...` |
| Claude | `is thinking...`, `is considering...`, `is drafting...`, `is composing...` |
| Glean | `is searching...`, `is ranking results...`, `is summarizing...`, `is drafting...` |

### Step 8 — Write the files

Write these in this order, using the Write tool:

1. **`agent/personas/<slug>.md`** — the persona markdown. Structure:
   - Identity line: *"You are **<display_name>**, <one-line role>."*
   - One-liner: where this bot is operating ("You are speaking in Slack DMs and channels. Keep replies tight — 1–3 short paragraphs or a compact list.")
   - Formatting rules: markdown basics (`**bold**`, `_italic_`, bullets, inline `code`, `---` dividers). Forbid H1/H2 (Slack threads don't render them well) and forbid triple-backtick code fences for prose.
   - **If Block Kit enabled**, include a full Block Kit instructions section modeled on `welo_guard.md` in `../slack-demo-toolkit/agent/personas/` — use block types `header`, `divider`, `section`, `context` only; cap at 6 sections per card; `section.text` is `mrkdwn`, `header.text` is `plain_text`; entire response is one ```blockkit``` fence, no prose around it.
   - Product details from step 4 — features, stakeholders, scenarios, dates, pricing.
   - Behavior rules: be proactive, stay in lane, commit to an answer (don't ask "who are you?" — pick the most material answer and go), default short, name owners when relevant.
   - 3–4 sample answers to representative questions in the persona's voice.

   The `slug` is the app name lowercased, spaces → hyphens, anything non-alphanumeric stripped (e.g., "Asana Demo" → `asana-demo`).

2. **`config/app_config.json`** — with fields: `app_name`, `display_name`, `simulates`, `model`, `loading_messages` (4 strings), `persona_path` (relative, e.g., `agent/personas/asana-demo.md`), `blockkit_enabled` (boolean).

3. **`manifest.json`** — copy `manifest.template.json` and substitute `{{APP_NAME}}`, `{{DISPLAY_NAME}}`, `{{SIMULATES}}`.

4. **`examples/demo_prompts_generated.md`** — 8–10 example prompts tailored to the persona. Cover: an overview/status question, a drill-down on a specific item, a question that should trigger Block Kit (if enabled), a question the bot should politely refuse (out of scope), a follow-up clarification question.

### Step 9 — Review demo prompts

Open `examples/demo_prompts_generated.md` and show the SE. *"Here are 8 demo prompts tailored to <display_name>. Any you'd like to tweak, replace, or add scenarios for?"* Loop until they're happy.

### Step 10 — Recap

*"You're set up as **<display_name>**, simulating <simulates>, using model `<model>`. Next, follow `SETUP.md` from Step 2 onward. Step 1 (this wizard) is done. Want me to walk you through Step 2 now?"*

---

## Respect `[Claude Code]` vs `[Terminal]` tags in SETUP.md

- **`[Claude Code]` steps** — run the command yourself via the Bash tool and show the result. Safe for non-interactive Python scripts, file edits, JSON reads.
- **`[Terminal] `steps** — **do not run these yourself.** Instead, tell the SE: *"please open a new Terminal window, make sure you're in the project folder, and run this command:"* and give them the exact command. These steps require either (a) hidden input via `getpass` (the token-save scripts), or (b) a long-running process that the SE needs to watch and leave open (`./run_app.sh`). The Bash tool can't drive either of those.

Specifically, **never** try to run these via the Bash tool:
- `tokens/save_bot_token.py`
- `tokens/save_app_token.py`
- `./run_app.sh`

## Venv discipline

Each Bash tool call runs in a fresh shell — `source .venv/bin/activate` doesn't persist. **Always invoke Python as `.venv/bin/python <script>`** (macOS/Linux) or `.venv\Scripts\python.exe <script>` (Windows). Never tell the SE to "activate" the venv when you're about to run something for them.

## Token discipline

**Never ask the SE to paste a bot token or app-level token into chat.** Route them:

- `xoxb-` bot token → `tokens/save_bot_token.py` (getpass; hidden input)
- `xapp-` app-level token → `tokens/save_app_token.py` (getpass; hidden input)

The SE runs these in a Terminal window they open themselves.

`team_id` (starts with `T`) and `audit_channel_id` (starts with `C`) are **not** secrets — fine to capture in chat and write to `tokens.json` for the SE.

## Terminal lifecycle — critical

The simulator is a **long-lived Python process** that runs inside a Terminal window. When the window closes, the process dies, and the bot stops responding in Slack. This is the #1 thing that breaks demos.

**Before every `./run_app.sh`, remind the SE:**

> *"Leave this Terminal window open for the whole demo. Tuck it behind Slack if you want it out of the way, but don't close it. If you close it, the bot stops answering — reopen the window, run `./run_app.sh` again, and it'll come back online."*

The app **does not hot-reload.** Any of these edits require Ctrl+C and re-running `./run_app.sh`:

| Edit | Restart needed? |
|---|---|
| `agent/personas/<slug>.md` (persona edits) | Yes |
| `config/app_config.json` (loading messages, model, blockkit flag) | Yes |
| Python files under `agent/` | Yes |
| `manifest.json` | No — but the Slack app itself needs reinstalling from the new manifest |

When you make any of these edits for the SE, **end your message with an explicit restart reminder**: *"Go to your Terminal window running the app, press Ctrl+C to stop it, then run `./run_app.sh` again. The new changes will load on startup."*

## What you must NOT do

- **Don't hardcode Anthropic API keys, Bedrock URLs, or bearer tokens.** This project deliberately uses the `claude` CLI so every SE inherits their own auth. If something looks like it needs an API key, stop and check — you're probably on the wrong path.
- **Don't copy `tokens.json`** from `slack-demo-toolkit` or anywhere else. Every SE has their own Slack workspace and their own credentials.
- **Don't edit `agent/demo_agent.py` or `agent/claude_subprocess.py` during onboarding.** If the SE wants different behavior, edit the persona or `config/app_config.json` instead. Only touch the Python if there's a genuine bug.
- **Don't fabricate tool calls or external APIs.** This simulator responds using `claude` + the persona, nothing else. There's no database, no real Asana integration, no live data. The persona tells the bot what to pretend to know.

## Ask Mac or Windows early

Before SETUP.md Step 2 (venv creation), ask which OS the SE is on. The docs are Mac-first; Windows commands are at the bottom of SETUP.md. Swap only the `python3.12`, `source`, and `cp` commands — everything else is identical.

## Audit channel

If the SE set `audit_channel_id` in `tokens.json`, every significant action (startup, scope check, errors, each reply sent) is logged to that channel by `config.audit_log()`. When troubleshooting, **read that channel first** — it has timestamps and specific error strings for every failure, and is much more useful than scrollback from the Terminal window.

If `audit_channel_id` is empty, audit logging silently no-ops. That's fine — the simulator still works.

## If the SE says "I want to simulate a different app"

Safest path: say *"the easiest way is to delete `config/app_config.json` and I'll re-run the wizard from scratch. That keeps the new persona clean. Sound good?"* Wait for confirmation, delete the file, and re-run the wizard.

If they want to keep the same Slack app but just tweak the persona (same `app_name`, same installed Slack app, same tokens, different personality), edit the persona file in place — then remind them to Ctrl+C and restart.
