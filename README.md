# slack-ai-app-simulator

## About

**slack-ai-app-simulator** lets Slack Solution Engineers spin up a Slack bot that impersonates any AI marketplace app — Claude, Asana AI, Notion AI, Cursor, Glean, and more — for live customer demos.

- **No API keys.** Runs entirely through your local `claude` CLI (the same Claude Code you're using right now).
- **No coding required.** An onboarding wizard inside Claude Code handles all configuration via conversation.
- **Any app, any persona.** One conversation generates the persona, Slack app manifest, and vetted demo prompts for whatever app you're simulating.
- **One command to start.** After setup, `./run_app.sh` brings the bot online in ~3 seconds.

Setup is one-time, ~15 minutes. After that, each demo takes one command to start.

> **New to building Slack apps or vibe coding?** No problem. Claude Code can guide you through every step — at any point you can ask it to explain what something does or why. This project was built with first-time builders in mind.

---

> ## ⚠ The Terminal window must stay open
>
> This simulator runs as a long-lived process inside a Terminal window. **If you close the window, the bot dies and stops answering in Slack.**
>
> Tuck the window behind Slack during your demo — don't quit it. When you're done, press `Ctrl+C` in the Terminal to stop cleanly.

---

## First time? Pick one

You can follow setup either way, whichever you're more comfortable with:

- **Open this folder in Claude Code and type *"help me set this up."*** Claude reads `SETUP.md` and `CLAUDE.md`, then walks you through it one step at a time — pausing for confirmation, running commands for you when safe, and handling the gotchas (which token goes where, why the Terminal window has to stay open, what to do if a scope check fails). You don't need to read any Python. **Best for first-time Terminal users.**
- **Read [SETUP.md](SETUP.md) yourself.** Step-by-step instructions, ~15 minutes.

Either way, Claude will ask which AI app you want to simulate, help you pick a unique name, generate the persona, and write the Slack app manifest.

## Already configured? Activating the bot for a demo

~5 minutes before your demo:

1. Open a new Terminal window (on Mac: `Cmd+Space` → `Terminal`).
2. `cd` into this project folder. Example: `cd ~/claude-projects/slack-ai-app-simulator`.
3. Start the app:
   ```bash
   ./run_app.sh
   ```
4. Wait ~3 seconds for the banner and scope check. Once you see every scope as `OK`, the bot is live in Slack.
5. **Leave this Terminal window open for the whole demo.** Tuck it behind Slack — don't close it, don't quit it, don't let your laptop sleep. Closing the window kills the bot mid-demo.
6. When the demo ends, come back to the Terminal and press `Ctrl+C` to stop cleanly.

Windows users: replace step 3 with `.venv\Scripts\python.exe agent\demo_agent.py`. See `SETUP.md` for the full Windows table.

## How it works (in one paragraph)

The simulator is a small Python program that connects to Slack via Socket Mode (Slack's real-time event channel for apps that don't have a public URL). When someone DMs the bot or `@mentions` it, the program sends the conversation plus a **persona** markdown file to your local `claude` command (the same Claude Code you're using right now) and streams the reply back into Slack. The persona is what makes the bot "act like" Asana, Claude, Cursor, etc.

No API keys in this project. Your local Claude Code install handles authentication.

## What's in the folder

| Path | What it is |
|---|---|
| `SETUP.md` | Step-by-step setup guide. Tagged `[Claude Code]` vs `[Terminal]` for each step. |
| `CLAUDE.md` | Instructions Claude Code follows to drive the onboarding wizard and help you. |
| `run_app.sh` | The command to start the simulator. |
| `manifest.template.json` | Template for creating your Slack app. Filled in during onboarding. |
| `agent/personas/*.md` | Your persona file (created during onboarding). Edit to change how the bot talks. |
| `config/app_config.json` | App name, model, loading messages, persona path. Created during onboarding. |
| `tokens.json` | Your Slack tokens. Created during setup. **Never committed.** |

## Reconfiguring for a different demo

Open this folder in Claude Code and say *"I want to simulate a different app"*. Claude will walk you through restarting the wizard with a fresh persona.

## Running more than one persona from the same clone

Once you've done the wizard once, you can add additional personas without re-running it: copy `agent/personas/_template.md.template` to `agent/personas/<new-slug>.md`, fill in the placeholders, and switch `config/app_config.json` to the multi-persona shape shown in `config/app_config.example.multi.json`. Pick which persona runs at launch with `SIM_PERSONA=<slug> ./run_app.sh`. See `SETUP.md` "Adding a second persona" for the full walkthrough.

## Stopping and restarting

| What happened | What to do |
|---|---|
| Your demo finished | `Ctrl+C` in the Terminal running the app. |
| You edited the persona or loading messages | `Ctrl+C`, then `./run_app.sh` again. The app reads these on startup only. |
| The bot stopped responding mid-demo | 9 times out of 10 the Terminal window closed. Reopen it, `cd` to this folder, `./run_app.sh`. |

See `SETUP.md` troubleshooting for more.
