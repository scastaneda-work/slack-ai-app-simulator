"""Subprocess wrapper around the `claude` CLI.

Why subprocess: lets any Slack SE run this simulator without configuring an API
key or Bedrock/Vertex gateway directly. The CLI inherits whatever auth lives in
~/.claude/settings.json — the same auth the SE uses when they type `claude` in
a Terminal.

The simulator feeds in:
  - the persona (as --system-prompt, replacing the default coding-agent prompt)
  - the full conversation history (re-sent each turn; cheap, and keeps state in
    the Python process rather than in claude's session store)
  - the selected model alias/id from config/app_config.json

and reads the stream-json event stream to forward text deltas to Slack.
"""
from __future__ import annotations

import json
import logging
import os
import subprocess
from collections.abc import Iterator

log = logging.getLogger("claude_subprocess")

EMPTY_USAGE: dict[str, int] = {
    "input_tokens": 0,
    "output_tokens": 0,
    "cache_read_input_tokens": 0,
    "cache_creation_input_tokens": 0,
}


def _build_env() -> dict[str, str]:
    """Build a minimal environment for the `claude` subprocess.

    Forwarding the full parent env leaks every variable in the SE's shell
    (AWS keys, GitHub tokens, demo secrets) into a child process whose stderr
    we capture and audit-log. Pass only what `claude` actually needs:
      - PATH, HOME, SHELL, USER: standard tooling
      - LANG / LC_*: terminal encoding
      - ANTHROPIC_*, AWS_*, CLAUDE_*: claude's own auth + behavior knobs
        (the SE may have any of these set in their shell to point at a
        non-default gateway / region / model)
      - NODE_*, NPM_*: claude is a Node CLI; respect npm config
    """
    keep_keys = {"PATH", "HOME", "SHELL", "USER", "TERM", "LANG", "TMPDIR", "PWD"}
    keep_prefixes = ("LC_", "ANTHROPIC_", "AWS_", "CLAUDE_", "NODE_", "NPM_")
    env: dict[str, str] = {}
    for key, value in os.environ.items():
        if key in keep_keys or key.startswith(keep_prefixes):
            env[key] = value
    env["CLAUDE_CODE_SIMPLE"] = "1"
    return env


def _format_prompt(messages: list[dict[str, str]]) -> str:
    """Flatten conversation history into one prompt string.

    We re-send the full history each turn (capped upstream in demo_agent.py at
    MAX_TURNS) rather than juggling --resume sessions — keeps state in one
    place and avoids --no-session-persistence conflicts.
    """
    parts: list[str] = []
    for m in messages[:-1]:
        role = "User" if m["role"] == "user" else "Assistant"
        parts.append(f"{role}: {m['content']}")
    parts.append(f"User: {messages[-1]['content']}")
    parts.append("Assistant:")
    return "\n\n".join(parts)


def _build_command(
    *, model: str, system_prompt: str, prompt: str, stream: bool
) -> list[str]:
    cmd = [
        "claude",
        "-p", prompt,
        "--model", model,
        "--system-prompt", system_prompt,
        "--no-session-persistence",
        "--disable-slash-commands",
        "--tools", "",
    ]
    if stream:
        cmd += ["--output-format", "stream-json", "--include-partial-messages", "--verbose"]
    else:
        cmd += ["--output-format", "text"]
    return cmd


def stream_reply(
    *,
    model: str,
    system_prompt: str,
    messages: list[dict[str, str]],
) -> Iterator[tuple[str, str]]:
    """Yield ("delta", text) events as claude streams, then ("final", full_text).

    On failure, yields ("error", stderr_tail) and stops. The caller
    (demo_agent.py._stream_reply) reassembles deltas, forwards them to
    chat.appendStream, and uses "final" to close out.

    Only text_delta events are emitted as deltas — thinking_delta and tool_use
    events are swallowed (we never want the model's internal reasoning or tool
    calls to reach Slack).
    """
    prompt = _format_prompt(messages)
    cmd = _build_command(model=model, system_prompt=system_prompt, prompt=prompt, stream=True)

    log.info("claude subprocess: model=%s sys_chars=%d hist=%d", model, len(system_prompt), len(messages))

    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        env=_build_env(),
    )

    final_parts: list[str] = []
    got_result = False

    try:
        assert proc.stdout is not None
        for line in proc.stdout:
            line = line.strip()
            if not line:
                continue
            try:
                evt = json.loads(line)
            except json.JSONDecodeError:
                log.debug("non-JSON line: %r", line[:200])
                continue

            etype = evt.get("type")
            if etype == "stream_event":
                inner = evt.get("event", {})
                if inner.get("type") == "content_block_delta":
                    delta = inner.get("delta", {})
                    if delta.get("type") == "text_delta":
                        text = delta.get("text", "")
                        if text:
                            final_parts.append(text)
                            yield ("delta", text)
            elif etype == "result":
                got_result = True
                final = evt.get("result") or "".join(final_parts)
                yield ("final", final)
                return

        if not got_result:
            yield ("final", "".join(final_parts))
    finally:
        try:
            rc = proc.wait(timeout=5)
        except subprocess.TimeoutExpired:
            proc.kill()
            rc = -1
        if rc != 0 and not got_result:
            stderr_tail = ""
            if proc.stderr is not None:
                stderr_tail = (proc.stderr.read() or "")[-1500:]
            log.error("claude exited rc=%d: %s", rc, stderr_tail)
            yield ("error", stderr_tail or f"claude exited with code {rc}")


def one_shot(*, model: str, system_prompt: str, user_text: str, timeout: int = 60) -> str:
    """Non-streaming single call — used for auto-title generation."""
    cmd = _build_command(model=model, system_prompt=system_prompt, prompt=user_text, stream=False)
    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=timeout,
        env=_build_env(),
    )
    if result.returncode != 0:
        raise RuntimeError(
            f"claude CLI failed (rc={result.returncode}): {result.stderr[-500:]}"
        )
    return result.stdout.strip()
