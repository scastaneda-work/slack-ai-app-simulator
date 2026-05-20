# Claude Code orientation

This project lets a Slack Solution Engineer stand up a Slack app that simulates any marketplace AI app (Claude, Asana, Notion AI, Cursor, Glean, etc.) for live demos. The app runs as a long-lived Python process that listens for Slack DMs / @mentions and replies using the SE's **local `claude` CLI** — no API keys in this project.

## Audience posture

Your user is a **Slack Solution Engineer**. Very fluent in Slack (channels, apps, scopes, enterprise grid). **Not a coder.** Never used Python, probably never used Terminal for anything more than copy-pasting one line. **They may also be new to vibe coding (working with Claude Code as a pair-programmer) and to building custom Slack apps end-to-end** — for many SEs, this project will be their first time taking a Slack app from manifest → install → live process. Assume:

- They will not read Python code. Don't tell them to "look at line 42."
- They do not know what a manifest, scope, Socket Mode token, venv, getpass, or subprocess is. **Define every piece of jargon inline the first time it appears.**
- They have used Claude Code before (that's how they're reading this), but may not have used it as a guided builder before — invite them to ask "what does this do?" or "why?" at any step.
- They have their own Slack demo org where they're an admin.

Default to narrating what you're about to do before doing it, pause after each step for confirmation, and when in doubt explain *what* a step does and *why* before running it.

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

*"Pick a name with some kind of differentiator — a suffix, prefix, or tag that signals 'this is a demo stand-in' and visually sets it apart from the real Marketplace app in your Slack sidebar. The specific word doesn't matter; what matters is that you and your audience can tell them apart. A few examples you could use for <real app>:"*
- `<RealApp> App`
- `<RealApp> Sim`
- `<RealApp> Demo`
- `<RealApp> Bot`
- `<RealApp> (Demo)`
- `<RealApp>DX`

*"Or something else you like — anything that marks it as a stand-in works. What would you like to call it?"*

If they answer with the exact name of the real app, push back once: *"Heads up — `<name>` is identical to the real Slack Marketplace app. If the real one is installed in your demo org, Slack will reject this one on install, and even if it doesn't, your audience will see two identical entries. Want to add a differentiator like `<RealApp> App` or `<RealApp> Sim`, or are you sure?"* If they insist, respect their choice and move on.

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

- *`claude-sonnet-4-6` — **Recommended.** Matches what most SEs have configured locally for Claude Code, and is what the QA harness in this repo (`agent/qa.py`) was validated against. Fast and good for most demos.*
- *`opus` / `claude-opus-4-7` — higher quality, slightly slower. Pick if your persona has a lot of nuance (big product, many stakeholders, subtle tone).*
- *`haiku` / `claude-haiku-4-5` — fastest, cheapest, lowest quality. Fine for very simple personas.*
- *Or paste a full model ID if you want to pin something else."*

Default: `claude-sonnet-4-6`.

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

1. **`agent/personas/<slug>.md`** — the persona markdown. Don't write this from scratch — *copy* `agent/personas/_template.md.template` to `agent/personas/<slug>.md` and substitute these placeholders:

   | Placeholder | Fill with |
   |---|---|
   | `{{DISPLAY_NAME}}` | The display name from Step 3 |
   | `{{SIMULATES}}` | The real app from Step 1 (e.g., "Claude (Anthropic)", "Asana AI") |
   | `{{ROLE_ONE_LINER}}` | A one-line role description, e.g. *"a project management AI that tracks tasks and blockers"* |
   | `{{PERSONA_BODY_PLACEHOLDER}}` | The product-specific persona body — features, stakeholders, scenarios, dates, pricing — synthesized from Step 4. This is where the demo content lives. |
   | `{{SAMPLE_ANSWERS_PLACEHOLDER}}` | 3–4 sample answers to representative questions in the persona's voice. Use `*single asterisks*` for bold (they'll be emitted verbatim). |

   The template already bakes in: Slack mrkdwn rules (single-asterisk bold, no `**double asterisks**`, no H1/H2 headings, no prose code fences), the `:large_yellow_circle:` shortcode (`:yellow_circle:` renders blank), Block Kit fence rules (entire response is one ` ```blockkit ` fence — first character is a backtick), the "you already know who the user is" rule, and the default behavior rules (lead with the answer, commit to a first pass, match the register). Don't re-state these in the substituted body — they're already there.

   The `slug` is the app name lowercased, spaces → hyphens, anything non-alphanumeric stripped (e.g., "Asana Demo" → `asana-demo`).

   **After writing, show the SE the persona body and sample answers (the parts you actually filled in) and ask for confirmation before moving on.** They're the only parts that depend on Step 4 — everything else is template.

2. **`config/app_config.json`** — with fields: `app_name`, `display_name`, `simulates`, `model` (default `claude-sonnet-4-6`), `loading_messages` (4 strings), `persona_path` (relative, e.g., `agent/personas/asana-demo.md`), `blockkit_enabled` (boolean).

3. **`manifest.json`** — copy `manifest.template.json` and substitute `{{APP_NAME}}`, `{{DISPLAY_NAME}}`, `{{SIMULATES}}`.

4. **`examples/demo_prompts_generated.md`** — **exactly 5 demo prompts** tailored to the persona, drawn directly from the Step 4 answers (stakeholders, scenarios, dates the SE said the demo should cover). These are the prompts `agent/qa.py --vet-questions` will load + vet in Step 9, so **they must follow a strict format** the parser can read:

   - Flat markdown list. Each prompt on its own bullet starting with `- `.
   - One prompt per bullet. No sub-bullets, no multi-line prompts.
   - No headings, no section dividers, no explanatory prose in between.
   - Optional surrounding quotes are stripped by the parser, so `- "What's overdue?"` and `- What's overdue?` both work.

   Cover this mix across the 5:
   1. An overview / status question that exercises the persona's data.
   2. A drill-down on a specific item named in Step 4.
   3. If Block Kit is enabled: one question that should trigger a card (list/board/summary). If not: a second text question from a different angle.
   4. A question the bot should politely refuse (out of scope for the persona).
   5. A follow-up / clarification question that builds on one of the earlier prompts.

   Example file contents (generic template — replace the prompts with Step 4 specifics):

   ```
   - What's the status of the launch?
   - Who's blocking the design review?
   - Show me the full project board.
   - Can you write me a poem?
   - Draft a message to the owner of that blocker.
   ```

### Step 8.5 — Known persona pitfalls baked in

The Formatting and Behavior rules above encode runtime learnings the simulator has already absorbed — SEs shouldn't have to rediscover these. Quick reference:

| Pitfall | Rule in persona |
|---|---|
| `**double asterisks**` renders as literal asterisks in Slack mrkdwn | Bold is `*single asterisks*` |
| Prose before ` ```blockkit ` fence makes the card render broken | First output char must be a backtick |
| `:yellow_circle:` renders as blank in Slack | Use `:large_yellow_circle:` |
| Model asks "who are you?" on "my priorities" style questions | System prompt tells the bot the user's name at runtime; persona says never ask |
| Block Kit JSON > Slack schema limits | Runtime validates and audit-logs violations; persona caps sections at 6 |

Runtime pitfalls (not persona-related, but worth naming here so you don't regress them when editing `agent/demo_agent.py`):

| Pitfall | Rule in the code |
|---|---|
| Bot's "is typing…" name doesn't match `display_name` in `app_config.json` | Typing indicator uses the bot's Slack profile `real_name` — rename via api.slack.com → Bot User → Edit. Not fixable from code (bot tokens can't call `users.profile.set`) |
| Admin-token or service-app posts arrive with a `bot_id` set and get silently dropped | `_should_skip_event` compares `bot_id` to *our own* `self.bot_id` only. Do NOT regress by re-adding `if event.get("bot_id"): return`. QA fixtures guard this |
| Two simulator instances fight over the Socket Mode connection | `main()` uses a PID lock at `.simulator.lock`; stale locks are auto-reclaimed. Don't remove the lock without a plan for this |

If a new failure mode comes up in live use, the fix belongs in both places: the **persona template here** (so new installs bake it in) AND the **QA fixtures in `agent/qa.py`** (so `--self-test` catches regressions).

### Step 9 — Vet the demo prompts

Two-step gate before handing prompts to the SE: a fast offline self-test that catches runtime regressions, then the live CLI vetting against the persona.

**9a. Offline self-test (cheap pre-flight):**

```bash
.venv/bin/python agent/qa.py --self-test
```

This runs in under a second — no `claude` CLI calls, no Slack calls. It exercises the Block Kit extractor, validator, streaming-decision helper, drop handler, and identity resolution against fixtures. **If it fails, stop here and don't run `--vet-questions`** — the runtime is broken and the live vetting won't tell you anything useful. Surface the failure, fix the cause, then continue.

**9b. Live vetting:**

The 5 prompts in `examples/demo_prompts_generated.md` came straight from the SE's Step 4 answers — these are the questions they'll actually ask in the demo. Before handing them over, vet them through the real CLI to catch any that break character or hit persona gaps.

```bash
.venv/bin/python agent/qa.py --vet-questions
```

`--vet-questions` reads `examples/demo_prompts_generated.md` by default (the 5 prompts you just wrote), fires each at the configured persona via the same `claude` CLI path the bot uses, extracts + validates any Block Kit output, checks for character-break markers (the model asking "who are you?", leaning on "as an AI", etc.), and prints PASS/FAIL per question.

**Handling the results:**
- **All 5 PASS** → you're done. Show the SE the prompt list; it's ready to demo.
- **Any FAIL** → show the SE which prompts failed and why (char-break / schema / parse). Offer to either (a) rewrite the failing prompts to avoid the failure mode, or (b) tighten the persona to cover the gap. Loop until all 5 pass.

Don't skip the vetting step — this is the load-bearing checkpoint that turns "here are some demo prompts" into "here are 5 demo prompts I've confirmed work end-to-end."

If the SE wants to vet more than 5 (deeper coverage, more nuanced personas), bump with `--count N`. If they want to vet an ad-hoc set instead of the generated file, pass `--questions "q1|q2|q3"`.

### Step 10 — Recap

*"You're set up as **<display_name>**, simulating <simulates>, using model `<model>`."*

Then surface this checklist verbatim — it's the canonical "what's left to fill in / verify" gate before the SE goes live:

| Where | Gate |
|---|---|
| `agent/personas/<slug>.md` | Persona body and sample answers reflect the Step 4 answers (everything else is template — don't edit) |
| `examples/demo_prompts_generated.md` | All 5 prompts PASSed `agent/qa.py --vet-questions` |
| `config/app_config.json` | `display_name`, `simulates`, `model`, `loading_messages`, `persona_path`, `blockkit_enabled` look right |
| `manifest.json` | App name has a differentiator vs the real Marketplace app |
| `tokens.json` | Empty for now — Steps 6–8 of `SETUP.md` fill it in |
| Slack `@username` (post-install) | Manifest install sets `Default username` once; rename via api.slack.com → Bot User if the handle leaks the simulator (e.g. mentions show `@claudesim_local`) |

Then: *"Next, follow `SETUP.md` from Step 2 onward. Step 1 (this wizard) is done. The launch command after setup is `./run_app.sh`. Want me to walk you through Step 2 now?"*

If the SE later wants to add a *second* persona to the same install (no re-clone), point them at `config/app_config.example.multi.json` and the persona template. They can copy the persona stub, fill it in, and add an entry under `personas:` in `app_config.json`. Switch which one runs with `SIM_PERSONA=<slug> ./run_app.sh`.

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
