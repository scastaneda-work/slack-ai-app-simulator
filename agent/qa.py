"""Pre-demo QA harness for the Slack AI app simulator.

Two modes:

  --self-test                 Offline fixture tests for the Block Kit
                              extractor, validator, streaming-decision
                              helper, replay helper, drop handler, and
                              user-identity resolution. No CLI calls.
                              Runs in under a second. Use this in CI
                              or as a smoke check after editing the
                              runtime.

  --vet-questions             Live vetting: fire N candidate questions
                              at the currently-configured persona via
                              the `claude` CLI (same path the bot uses),
                              check each reply for in-character quality,
                              Block Kit parseability when expected, and
                              absence of character-break markers. Prints
                              PASS / FAIL per question. Exit non-zero on
                              any FAIL. Use before a demo to catch
                              regressions the persona would hit live.

Usage (from repo root):

  .venv/bin/python agent/qa.py --self-test
  .venv/bin/python agent/qa.py --vet-questions
  .venv/bin/python agent/qa.py --vet-questions --count 3
  .venv/bin/python agent/qa.py --vet-questions --questions "q1|q2|q3"

Default question count is 5 (any more and the CLI round-trip starts to
drag; any fewer and you miss coverage). Override with --count.

Exit code is non-zero on any failure, so this drops into a pre-demo
script or a pre-commit hook cleanly.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path
from threading import Event, Lock

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))  # repo root for `config`
sys.path.insert(0, str(_HERE))         # this dir for `demo_agent`

from demo_agent import (  # noqa: E402
    Simulator,
    _blockkit_decision,
    _extract_blockkit_json,
    _extract_taskplan_json,
    _has_blockkit_candidate,
    _render_taskplan_chunks,
    _should_skip_event,
    _validate_blocks,
    _validate_taskplan,
)


# Character-break markers — phrases that indicate the model stepped out
# of persona to ask who the user is, deflect to its underlying identity,
# or admit missing context the persona should have absorbed. Extend this
# list as new failure modes are observed. Match is case-insensitive.
CHAR_BREAK_MARKERS = [
    "i don't have access",
    "i can't tell",
    "who are you",
    "what's your name",
    "as an ai",
    "i don't know who you are",
    "could you tell me your name",
    "i'm not sure who you",
    "which person you are",
    "i am an ai language model",
]


# Path to the onboarding-wizard-generated demo prompts. This is the same
# list the SE will actually use in the demo — vetting them here means we're
# QA-ing real demo prompts, not generic placeholders.
GENERATED_PROMPTS_PATH = Path("examples") / "demo_prompts_generated.md"

# Fallback generic questions used only when examples/demo_prompts_generated.md
# doesn't exist yet (fresh clone, onboarding not run). They probe the core
# regressions — identity-awareness, short-reply handling, and a generic
# follow-up — so the harness still does useful smoke-testing pre-onboarding.
FALLBACK_QUESTIONS = [
    "What's the overall status of my current work?",
    "Who should I follow up with first?",
    "Draft a quick message to my team about this week's priorities.",
    "What are my top priorities this week?",
    "Tell me about the most recent thing you can help with.",
]


def _load_generated_prompts() -> list[str] | None:
    """Parse the wizard-generated demo prompts into a flat list of questions.

    The onboarding wizard writes `examples/demo_prompts_generated.md` as a
    plain markdown list — one question per `- ` bullet, no sub-sections,
    no headings. Returns None if the file doesn't exist (fresh clone) so
    the caller can fall back to the generic probes."""
    path = _HERE.parent / GENERATED_PROMPTS_PATH
    if not path.exists():
        return None
    prompts: list[str] = []
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line.startswith(("- ", "* ")):
            continue
        q = line[2:].strip()
        # Strip surrounding quotes if present (prompts often written as bullets
        # like `- "What's overdue?"` in the generator).
        if len(q) >= 2 and q[0] in "\"'" and q[-1] == q[0]:
            q = q[1:-1].strip()
        if q:
            prompts.append(q)
    return prompts or None


def _run_self_test() -> int:
    """Offline fixtures for every helper. Returns 0 on full pass, 1 otherwise."""
    fail = 0

    # Block Kit extractor: happy paths + every failure tier.
    fixtures: list[tuple[str, str, str, int]] = [
        # (label, raw_text, expected_tier, expected_violation_count)
        (
            "valid strict",
            '```blockkit\n[{"type":"divider"}]\n```',
            "strict",
            0,
        ),
        (
            "trailing prose",
            '```blockkit\n[{"type":"divider"}]\n```\nLet me know if you want more.',
            "trailing_prose",
            0,
        ),
        (
            "truncated (no closing fence)",
            '```blockkit\n[{"type":"header","text":{"type":"plain_text","text":"hi"}}]',
            "truncated",
            0,
        ),
        (
            "parse error (bad json)",
            '```blockkit\n[{"type": "divider",}]\n```',
            "parse_error",
            0,
        ),
        (
            "no fence",
            "Here is a regular plain-text reply.",
            "no_fence",
            0,
        ),
        (
            "schema error: unknown block type",
            '```blockkit\n[{"type":"divider"},{"type":"weird"}]\n```',
            "strict",
            1,
        ),
        (
            "schema error: section too long",
            '```blockkit\n[{"type":"section","text":{"type":"mrkdwn","text":"'
            + ("x" * 3100)
            + '"}}]\n```',
            "strict",
            1,
        ),
        (
            "prose before fence",
            'Here are the highest-priority items across all projects this week:\n\n'
            '```blockkit\n[{"type":"divider"}]\n```',
            "trailing_prose",
            0,
        ),
    ]
    for label, raw, expected_tier, expected_v_count in fixtures:
        blocks, tier = _extract_blockkit_json(raw)
        violations = _validate_blocks(blocks) if blocks else []
        ok = tier == expected_tier and len(violations) == expected_v_count
        status = "OK  " if ok else "FAIL"
        print(f"[self-test] {status} extractor: {label} → tier={tier} violations={len(violations)}")
        if not ok:
            fail += 1

    # Decision helper: buffer vs blockkit vs text at various elapsed/floor points.
    decision_cases: list[tuple[str, str, float, float, str]] = [
        # (label, buf, elapsed_s, floor_s, expected)
        ("blockkit prefix only", "```blockkit\n[", 0.5, 4.0, "blockkit"),
        ("prose then fence", "Here are the top priorities:\n\n```blockkit", 1.2, 4.0, "blockkit"),
        ("too early to decide", "Here are ", 0.3, 4.0, "buffer"),
        ("pure prose, mid-floor", "Let me tell you about this in detail. ", 1.0, 4.0, "buffer"),
        ("pure prose, near floor end", "Let me tell you about this in detail. ", 3.9, 4.0, "text"),
        ("empty buf, past floor", "", 4.5, 4.0, "buffer"),
        (
            "fast short reply, mid-floor",
            "Here are your top priorities this week: item one, item two, item three.",
            2.5, 4.0, "buffer",
        ),
    ]
    for label, buf, elapsed, floor, expected in decision_cases:
        got = _blockkit_decision(buf, elapsed, floor)
        ok = got == expected
        status = "OK  " if ok else "FAIL"
        print(f"[self-test] {status} decision: {label} → {got} (want {expected})")
        if not ok:
            fail += 1

    # Final-result classifier: keep terminal-only CLI results aligned with the
    # streaming detector, which scans for a blockkit fence anywhere in the text.
    final_classifier_cases: list[tuple[str, str, bool]] = [
        (
            "strict final card",
            '```blockkit\n[{"type":"divider"}]\n```',
            True,
        ),
        (
            "prefaced final card",
            'Here are the top priorities:\n\n```blockkit\n[{"type":"divider"}]\n```',
            True,
        ),
        (
            "malformed final card",
            '```blockkit\n[{"type": "divider",}]\n```',
            True,
        ),
        (
            "plain final text",
            "Here is a regular markdown reply.",
            False,
        ),
    ]
    for label, raw, expected in final_classifier_cases:
        got = _has_blockkit_candidate(raw)
        ok = got == expected
        status = "OK  " if ok else "FAIL"
        print(f"[self-test] {status} final classifier: {label} → {got} (want {expected})")
        if not ok:
            fail += 1

    # Event filter. The pitfall: admin-token posts arrive with `bot_id` set
    # to the Slack Admin app's id, not ours. A naive "drop any bot_id" filter
    # silently ignores those events and the app appears not to respond. These
    # fixtures guard against that regression.
    OUR_BOT_USER = "UOURBOT"
    OUR_BOT_ID = "BOURBOT"
    event_filter_cases: list[tuple[str, dict, bool]] = [
        (
            "real user message",
            {"user": "UHUMAN", "text": "hi", "channel": "C1"},
            False,
        ),
        (
            "our own echo (by user id)",
            {"user": OUR_BOT_USER, "text": "(my own post)", "channel": "C1"},
            True,
        ),
        (
            "our own echo (by bot_id)",
            {"user": OUR_BOT_USER, "bot_id": OUR_BOT_ID, "text": "echo", "channel": "C1"},
            True,
        ),
        (
            "admin-token user post — MUST RESPOND",
            {"user": "UHUMAN", "bot_id": "BADMINAPP", "text": "<@UOURBOT> help", "channel": "C1"},
            False,
        ),
        (
            "other app's message — respond (or let text-filter handle it later)",
            {"user": "UOTHERBOT", "bot_id": "BOTHERAPP", "text": "status update", "channel": "C1"},
            False,
        ),
        (
            "message_changed edit — skip",
            {"user": "UHUMAN", "subtype": "message_changed", "text": "edited", "channel": "C1"},
            True,
        ),
        (
            "message_deleted — skip",
            {"user": "UHUMAN", "subtype": "message_deleted", "text": "", "channel": "C1"},
            True,
        ),
    ]
    for label, ev, expected in event_filter_cases:
        got = _should_skip_event(ev, OUR_BOT_USER, OUR_BOT_ID)
        ok = got == expected
        status = "OK  " if ok else "FAIL"
        print(f"[self-test] {status} event filter: {label} → skip={got} (want skip={expected})")
        if not ok:
            fail += 1

    # Replay helper: 250-char input splits into paced chunks + final chunk
    # on chat.stopStream. Monkeypatch time.sleep so the test runs instantly
    # instead of ~4s per call.
    import demo_agent as _demo_agent_mod
    from slack_sdk.errors import SlackApiError

    class _RecWeb:
        def __init__(self) -> None:
            self.calls: list[tuple[str, dict]] = []

        def chat_appendStream(self, **kwargs):
            self.calls.append(("appendStream", kwargs))

        def chat_stopStream(self, **kwargs):
            self.calls.append(("stopStream", kwargs))

        def chat_postMessage(self, **kwargs):
            self.calls.append(("postMessage", kwargs))
            return {"ts": "post.1"}

        def chat_startStream(self, **kwargs):
            self.calls.append(("startStream", kwargs))
            return {"ts": "stream.1"}

        def assistant_threads_setStatus(self, **kwargs):
            self.calls.append(("setStatus", kwargs))

    orig_sleep = _demo_agent_mod.time.sleep
    orig_stream_reply = _demo_agent_mod.stream_reply
    _demo_agent_mod.time.sleep = lambda _s: None
    try:
        def _make_stream_shim(web, *, blockkit_enabled: bool = True, taskplan_enabled: bool = False):
            shim = object.__new__(Simulator)
            shim.web = web
            shim.display_name = "TestBot"
            shim.team_id = "T123"
            shim.model = "test-model"
            shim.blockkit_enabled = blockkit_enabled
            shim.taskplan_enabled = taskplan_enabled
            shim.stream = True
            return shim

        def _run_stream_case(events, *, blockkit_enabled: bool = True, taskplan_enabled: bool = False):
            def fake_stream_reply(**_kwargs):
                yield from events

            _demo_agent_mod.stream_reply = fake_stream_reply
            web_case = _RecWeb()
            shim_case = _make_stream_shim(
                web_case, blockkit_enabled=blockkit_enabled, taskplan_enabled=taskplan_enabled
            )
            reply, _usage = Simulator._stream_reply(
                shim_case,
                "C123",
                "thread.1",
                "U123",
                "system",
                [{"role": "user", "content": "show me blockers"}],
                Event(),
            )
            return reply, web_case.calls

        # A terminal-only result with prose before a valid card should still
        # post Block Kit, not stream or post the raw fenced JSON.
        prefaced_reply, prefaced_calls = _run_stream_case([
            (
                "final",
                'Here are the top priorities:\n\n'
                '```blockkit\n[{"type":"divider"}]\n```',
            )
        ])
        prefaced_block_posts = [
            c for c in prefaced_calls
            if c[0] == "postMessage" and "blocks" in c[1]
        ]
        prefaced_raw_posts = [
            c for c in prefaced_calls
            if c[0] == "postMessage" and "```blockkit" in c[1].get("text", "")
        ]
        prefaced_stream_starts = [c for c in prefaced_calls if c[0] == "startStream"]
        if prefaced_block_posts and not prefaced_raw_posts and not prefaced_stream_starts:
            print("[self-test] OK   stream reply: prefaced final Block Kit posts as blocks")
        else:
            fail += 1
            print(
                "[self-test] FAIL stream reply prefaced Block Kit: "
                f"block_posts={len(prefaced_block_posts)} "
                f"raw_posts={len(prefaced_raw_posts)} starts={len(prefaced_stream_starts)} "
                f"reply_len={len(prefaced_reply)}"
            )

        # A malformed card should not leak fenced JSON into Slack.
        malformed_reply, malformed_calls = _run_stream_case([
            ("final", '```blockkit\n[{"type": "divider",}]\n```')
        ])
        malformed_raw_posts = [
            c for c in malformed_calls
            if c[0] == "postMessage" and "```blockkit" in c[1].get("text", "")
        ]
        malformed_apologies = [
            c for c in malformed_calls
            if c[0] == "postMessage" and "botched the card formatting" in c[1].get("text", "")
        ]
        malformed_stream_starts = [c for c in malformed_calls if c[0] == "startStream"]
        if malformed_apologies and not malformed_raw_posts and not malformed_stream_starts:
            print("[self-test] OK   stream reply: malformed Block Kit posts clean apology")
        else:
            fail += 1
            print(
                "[self-test] FAIL stream reply malformed Block Kit: "
                f"apologies={len(malformed_apologies)} "
                f"raw_posts={len(malformed_raw_posts)} starts={len(malformed_stream_starts)} "
                f"reply_len={len(malformed_reply)}"
            )

        # If Slack rejects a valid blocks payload, fall back to a clear text
        # error instead of posting the raw fenced JSON.
        class _RejectBlocksWeb(_RecWeb):
            def chat_postMessage(self, **kwargs):
                self.calls.append(("postMessage", kwargs))
                if "blocks" in kwargs:
                    raise SlackApiError(
                        "invalid_blocks",
                        {"ok": False, "error": "invalid_blocks"},
                    )
                return {"ts": "post.1"}

        reject_web = _RejectBlocksWeb()
        reject_shim = _make_stream_shim(reject_web, blockkit_enabled=True)
        _demo_agent_mod.stream_reply = lambda **_kwargs: iter([
            ("final", '```blockkit\n[{"type":"divider"}]\n```')
        ])
        rejected_reply, _usage = Simulator._stream_reply(
            reject_shim,
            "C123",
            "thread.1",
            "U123",
            "system",
            [{"role": "user", "content": "show me blockers"}],
            Event(),
        )
        reject_block_attempts = [
            c for c in reject_web.calls
            if c[0] == "postMessage" and "blocks" in c[1]
        ]
        reject_text_fallbacks = [
            c for c in reject_web.calls
            if c[0] == "postMessage"
            and "Slack rejected" in c[1].get("text", "")
        ]
        reject_raw_posts = [
            c for c in reject_web.calls
            if c[0] == "postMessage" and "```blockkit" in c[1].get("text", "")
        ]
        if reject_block_attempts and reject_text_fallbacks and not reject_raw_posts:
            print("[self-test] OK   stream reply: rejected blocks post clean fallback")
        else:
            fail += 1
            print(
                "[self-test] FAIL stream reply rejected blocks: "
                f"block_attempts={len(reject_block_attempts)} "
                f"fallbacks={len(reject_text_fallbacks)} "
                f"raw_posts={len(reject_raw_posts)} reply_len={len(rejected_reply)}"
            )

        # Taskplan path: a taskplan-enabled persona should open the stream with
        # task_display_mode, animate the steps, then finalize the SAME message
        # with the answer text (no separate post, no raw taskplan JSON).
        tp_reply, tp_calls = _run_stream_case(
            [(
                "final",
                '```taskplan\n{"mode":"timeline","steps":['
                '{"id":"1","title":"Searched","status":"complete"},'
                '{"id":"2","title":"Synthesized","status":"complete"}]}'
                '\n```\nThe answer is 42.',
            )],
            blockkit_enabled=False,
            taskplan_enabled=True,
        )
        tp_starts = [
            c for c in tp_calls
            if c[0] == "startStream" and c[1].get("task_display_mode") == "timeline"
        ]
        tp_stops = [
            c for c in tp_calls
            if c[0] == "stopStream" and "The answer is 42." in c[1].get("markdown_text", "")
        ]
        tp_raw = [
            c for c in tp_calls
            if "```taskplan" in str(c[1].get("markdown_text", "") or c[1].get("text", ""))
        ]
        if tp_starts and tp_stops and not tp_raw:
            print("[self-test] OK   stream reply: taskplan animates then finalizes answer")
        else:
            fail += 1
            print(
                "[self-test] FAIL taskplan stream: "
                f"starts={len(tp_starts)} stops={len(tp_stops)} raw_leak={len(tp_raw)}"
            )

        web = _RecWeb()
        shim = type("Shim", (), {"web": web, "display_name": "TestBot"})()
        sample = "x" * 250
        Simulator._replay_buffered_text(shim, "C123", "ts.1", sample)
        appends = [c for c in web.calls if c[0] == "appendStream"]
        stops = [c for c in web.calls if c[0] == "stopStream"]
        total = sum(len(c[1].get("markdown_text", "")) for c in appends)
        tail = len(stops[0][1].get("markdown_text", "")) if stops else 0
        if len(appends) >= 2 and len(stops) == 1 and total + tail == 250 and tail <= 30:
            print(f"[self-test] OK   replay helper: {len(appends)} chunks + 1 stopStream, {total}+{tail}=250 delivered")
        else:
            fail += 1
            print(f"[self-test] FAIL replay helper: appends={len(appends)} stops={len(stops)} total={total + tail} tail={tail}")

        # ts=None → skip stopStream.
        web2 = _RecWeb()
        shim2 = type("Shim", (), {"web": web2, "display_name": "TestBot"})()
        Simulator._replay_buffered_text(shim2, "C123", None, "hello")
        if not [c for c in web2.calls if c[0] == "stopStream"]:
            print("[self-test] OK   replay helper: skips stopStream when ts=None")
        else:
            fail += 1
            print("[self-test] FAIL replay helper called stopStream with ts=None")
    finally:
        _demo_agent_mod.time.sleep = orig_sleep
        _demo_agent_mod.stream_reply = orig_stream_reply

    # Drop handler: happy path + ts=None no-op + SlackApiError swallowed.
    class _FakeResponse(dict):
        def __init__(self, data: dict) -> None:
            super().__init__(data)

        def get(self, key, default=None):
            return super().get(key, default)

    fake_drop = _RecWeb()
    drop_shim = type("Shim", (), {"web": fake_drop, "display_name": "TestBot"})()
    Simulator._finalize_dropped_stream(drop_shim, "C123", "ts.1", "partial reply")
    kinds = [c[0] for c in fake_drop.calls]
    tail_ok = any(
        c[0] == "stopStream" and "connection dropped" in c[1].get("markdown_text", "")
        for c in fake_drop.calls
    )
    if kinds == ["appendStream", "stopStream"] and tail_ok:
        print("[self-test] OK   drop handler: flushed buf + stopStream with retry note")
    else:
        fail += 1
        print(f"[self-test] FAIL drop handler: calls={kinds} tail_ok={tail_ok}")

    fake_drop2 = _RecWeb()
    drop_shim2 = type("Shim", (), {"web": fake_drop2, "display_name": "TestBot"})()
    Simulator._finalize_dropped_stream(drop_shim2, "C123", None, "whatever")
    if not fake_drop2.calls:
        print("[self-test] OK   drop handler: no-op when ts=None")
    else:
        fail += 1
        print(f"[self-test] FAIL drop handler ran with ts=None: {fake_drop2.calls}")

    class _RaisingStopWeb(_RecWeb):
        def chat_stopStream(self, **kwargs):
            self.calls.append(("stopStream", kwargs))
            resp = _FakeResponse({
                "ok": False, "error": "invalid_arguments",
                "response_metadata": {"messages": ["ts must be a valid timestamp"]},
            })
            raise SlackApiError("invalid_arguments", resp)

    raising = _RaisingStopWeb()
    rshim = type("Shim", (), {"web": raising, "display_name": "TestBot"})()
    try:
        Simulator._finalize_dropped_stream(rshim, "C123", "ts.1", "partial")
    except Exception as e:
        fail += 1
        print(f"[self-test] FAIL drop handler re-raised on stopStream failure: {e!r}")
    else:
        kinds = [c[0] for c in raising.calls]
        if kinds == ["appendStream", "stopStream"]:
            print("[self-test] OK   drop handler: swallows stopStream SlackApiError")
        else:
            fail += 1
            print(f"[self-test] FAIL drop handler calls={kinds} (want append+stop)")

    # User-identity resolution: display_name preference, fallback, cache, API-error.
    class _UsersInfoWeb:
        def __init__(self, payload, *, error: bool = False) -> None:
            self.payload = payload
            self.error = error
            self.calls = 0

        def users_info(self, user: str):
            self.calls += 1
            if self.error:
                raise self.payload
            return _FakeResponse(self.payload)

    def _make_id_shim(web):
        return type(
            "Shim", (),
            {"web": web, "user_names": {}, "user_names_lock": Lock()},
        )()

    # display_name preferred over real_name.
    web_a = _UsersInfoWeb({
        "user": {
            "real_name": "Alex Morgan",
            "profile": {"display_name": "Alex", "real_name": "Alex Morgan"},
        }
    })
    shim_a = _make_id_shim(web_a)
    if Simulator._resolve_user_name(shim_a, "U001") == "Alex":
        print("[self-test] OK   user identity: prefers profile.display_name")
    else:
        fail += 1
        print("[self-test] FAIL user identity display_name")
    # Cache hit: second lookup doesn't call users.info again.
    _ = Simulator._resolve_user_name(shim_a, "U001")
    if web_a.calls == 1:
        print("[self-test] OK   user identity: cached after first lookup")
    else:
        fail += 1
        print(f"[self-test] FAIL user identity cache: users.info calls={web_a.calls}")
    # Empty display_name → fall back to profile.real_name.
    web_b = _UsersInfoWeb({
        "user": {
            "real_name": "Sam Rivera",
            "profile": {"display_name": "", "real_name": "Sam Rivera"},
        }
    })
    shim_b = _make_id_shim(web_b)
    if Simulator._resolve_user_name(shim_b, "U002") == "Sam Rivera":
        print("[self-test] OK   user identity: falls back to profile.real_name")
    else:
        fail += 1
        print("[self-test] FAIL user identity real_name")
    # API error → None, no raise.
    err_resp = _FakeResponse({"ok": False, "error": "user_not_found"})
    web_c = _UsersInfoWeb(SlackApiError("user_not_found", err_resp), error=True)
    shim_c = _make_id_shim(web_c)
    try:
        name_c = Simulator._resolve_user_name(shim_c, "U003")
    except Exception as e:
        fail += 1
        print(f"[self-test] FAIL user identity raised on API error: {e!r}")
        name_c = "RAISED"
    if name_c is None:
        print("[self-test] OK   user identity: returns None on SlackApiError")
    else:
        fail += 1
        print(f"[self-test] FAIL user identity on error → {name_c!r}")

    # Taskplan extractor: tiers + the plan/rest split (the answer text after
    # the fence must survive so it can finalize the streamed message).
    taskplan_cases: list[tuple[str, str, str, bool, int]] = [
        # (label, raw, expected_tier, expect_rest_nonempty, expected_violations)
        (
            "strict timeline + answer",
            '```taskplan\n{"mode":"timeline","title":"Researching",'
            '"steps":[{"id":"1","title":"Searched docs","status":"complete"}]}'
            '\n```\nHere is the answer.',
            "strict", True, 0,
        ),
        (
            "strict plan with sources",
            '```taskplan\n{"mode":"plan","title":"Plan","steps":['
            '{"id":"1","title":"Step one","status":"complete",'
            '"sources":[{"url":"https://x.com","text":"X"}]}]}\n```\nAnswer body.',
            "strict", True, 0,
        ),
        (
            "trailing prose (lead-in before fence)",
            'Let me work through this:\n\n```taskplan\n'
            '{"mode":"timeline","steps":[{"id":"1","title":"a","status":"complete"}]}'
            '\n```\nAnswer.',
            "trailing_prose", True, 0,
        ),
        (
            "no fence",
            "Just a normal reply.",
            "no_fence", True, 0,
        ),
        (
            "parse error (bad json)",
            '```taskplan\n{"mode":"timeline",,}\n```\nAnswer.',
            "parse_error", True, 0,
        ),
        (
            "schema: bad mode",
            '```taskplan\n{"mode":"grid","steps":[{"id":"1","title":"a"}]}\n```',
            "strict", False, 1,
        ),
        (
            "schema: source missing text",
            '```taskplan\n{"mode":"plan","title":"P","steps":[{"id":"1",'
            '"title":"a","sources":[{"url":"https://x.com"}]}]}\n```',
            "strict", False, 1,
        ),
        (
            "schema: duplicate ids",
            '```taskplan\n{"mode":"timeline","steps":['
            '{"id":"1","title":"a"},{"id":"1","title":"b"}]}\n```',
            "strict", False, 1,
        ),
    ]
    for label, raw, exp_tier, exp_rest, exp_v in taskplan_cases:
        plan, rest, tier = _extract_taskplan_json(raw)
        violations = _validate_taskplan(plan) if plan else []
        ok = (
            tier == exp_tier
            and (bool(rest.strip()) == exp_rest)
            and len(violations) == exp_v
        )
        status = "OK  " if ok else "FAIL"
        print(
            f"[self-test] {status} taskplan: {label} → tier={tier} "
            f"rest={'y' if rest.strip() else 'n'} violations={len(violations)}"
        )
        if not ok:
            fail += 1

    # Renderer: plan mode emits a leading plan_update frame; timeline does not.
    taskplan_render_fail = 0
    plan_plan = {"mode": "plan", "title": "Doing X", "steps": [
        {"id": "1", "title": "a", "status": "complete"},
        {"id": "2", "title": "b"},
    ]}
    frames_plan, mode_plan = _render_taskplan_chunks(plan_plan)
    task_chunks = [c for f in frames_plan for c in f if c["type"] == "task_update"]
    plan_ok = (
        mode_plan == "plan"
        and frames_plan[0][0]["type"] == "plan_update"
        and frames_plan[0][0]["title"] == "Doing X"
        and len(task_chunks) == 2
        and task_chunks[1]["status"] == "complete"  # default when omitted
    )
    print(f"[self-test] {'OK  ' if plan_ok else 'FAIL'} taskplan render: plan mode title + 2 tasks")
    if not plan_ok:
        fail += 1
        taskplan_render_fail += 1

    tl = {"mode": "timeline", "steps": [
        {"id": "1", "title": "a", "sources": [{"url": "https://x.com", "text": "X"}]},
    ]}
    frames_tl, mode_tl = _render_taskplan_chunks(tl)
    tl_ok = (
        mode_tl == "timeline"
        and not any(c["type"] == "plan_update" for f in frames_tl for c in f)
        and frames_tl[0][0]["type"] == "task_update"
        and frames_tl[0][0]["sources"][0] == {"type": "url", "url": "https://x.com", "text": "X"}
    )
    print(f"[self-test] {'OK  ' if tl_ok else 'FAIL'} taskplan render: timeline mode, no plan_update, source ok")
    if not tl_ok:
        fail += 1

    total = (
        len(fixtures)
        + len(decision_cases)
        + len(final_classifier_cases)
        + len(event_filter_cases)
        + len(taskplan_cases)
        + 2  # taskplan renderer assertions
        + 1  # taskplan stream-reply case
        + 3 + 2 + 3 + 4
    )
    print(f"\nself-test: {total - fail} pass / {fail} fail")
    return 1 if fail else 0


def _load_persona_and_model() -> tuple[str, str, str]:
    """Load the persona system prompt + model from config/app_config.json.
    Returns (display_name, model, system_prompt). Raises if config is missing."""
    from config import load_app_config

    cfg = load_app_config()
    persona_rel = cfg.get("persona_path")
    if not persona_rel:
        raise SystemExit("config/app_config.json missing 'persona_path'. Re-run onboarding.")
    persona_path = _HERE.parent / persona_rel
    if not persona_path.exists():
        raise SystemExit(f"Persona file not found: {persona_path}. Re-run onboarding.")
    system_prompt = persona_path.read_text().strip()
    return (
        cfg.get("display_name", "Bot"),
        cfg.get("model", "claude-sonnet-4-6"),
        system_prompt,
    )


def _vet_one(*, model: str, system_prompt: str, question: str) -> dict:
    """Fire one question at the CLI and classify the response. Returns a
    dict with `question`, `text`, `tier`, `violations`, `char_break`, `pass`."""
    from claude_subprocess import one_shot

    text = one_shot(
        model=model,
        system_prompt=system_prompt,
        user_text=question,
        timeout=120,
    )
    blocks, tier = _extract_blockkit_json(text)
    violations = _validate_blocks(blocks) if blocks else []
    low = text.lower()
    char_break = [m for m in CHAR_BREAK_MARKERS if m in low]
    # A candidate passes if: (a) no character-break markers AND (b) either
    # it's a postable Block Kit card OR it's plain text with no schema
    # violations. "no_fence" for a question that wasn't meant to trigger
    # a card is expected and fine.
    is_postable_card = blocks is not None and not violations
    is_clean_text = tier == "no_fence"
    passed = (not char_break) and (is_postable_card or is_clean_text)
    return {
        "question": question,
        "text": text,
        "tier": tier,
        "violations": violations,
        "char_break": char_break,
        "pass": passed,
        "is_card": is_postable_card,
    }


def _run_vet_questions(*, count: int, questions: list[str] | None, verbose: bool) -> int:
    display_name, model, system_prompt = _load_persona_and_model()
    source = "--questions flag"
    if questions is None:
        generated = _load_generated_prompts()
        if generated:
            questions = generated[:count]
            source = str(GENERATED_PROMPTS_PATH)
        else:
            questions = FALLBACK_QUESTIONS[:count]
            source = "built-in fallback (no generated prompts found)"
    else:
        questions = questions[:count]

    print(f"\nVetting — display={display_name} model={model} n={len(questions)}")
    print(f"Source: {source}")
    print("=" * 72)

    fail = 0
    for i, q in enumerate(questions, 1):
        try:
            res = _vet_one(model=model, system_prompt=system_prompt, question=q)
        except Exception as e:
            fail += 1
            print(f"[{i}] FAIL  {q[:60]!r} → harness error: {type(e).__name__}: {e}")
            continue
        if res["pass"]:
            shape = "card" if res["is_card"] else "text"
            print(f"[{i}] PASS  {q[:60]!r} → {shape}, {len(res['text'])} chars")
        else:
            fail += 1
            reasons = []
            if res["char_break"]:
                reasons.append(f"char-break: {res['char_break']}")
            if res["violations"]:
                reasons.append(f"schema: {res['violations']}")
            if res["tier"] in ("parse_error",):
                reasons.append(f"parse: tier={res['tier']}")
            print(f"[{i}] FAIL  {q[:60]!r} → {'; '.join(reasons) or 'see response'}")
            if verbose:
                print(f"       text: {res['text'][:500]}")

    print("=" * 72)
    print(f"Vetting: {len(questions) - fail} pass / {fail} fail")
    return 1 if fail else 0


def main() -> int:
    p = argparse.ArgumentParser(description="Slack AI app simulator QA harness")
    p.add_argument(
        "--self-test", action="store_true",
        help="Run offline fixture tests (fast, no CLI calls).",
    )
    p.add_argument(
        "--vet-questions", action="store_true",
        help="Fire candidate questions at the CLI and classify each response.",
    )
    p.add_argument(
        "--count", type=int, default=5,
        help="Number of questions to vet when --vet-questions (default: 5).",
    )
    p.add_argument(
        "--questions", type=str, default=None,
        help="Pipe-separated candidate questions. Overrides defaults.",
    )
    p.add_argument(
        "--verbose", action="store_true",
        help="Print full response text on failure.",
    )
    args = p.parse_args()

    if args.self_test:
        return _run_self_test()
    if args.vet_questions:
        questions = args.questions.split("|") if args.questions else None
        return _run_vet_questions(
            count=args.count, questions=questions, verbose=args.verbose
        )
    p.error("specify --self-test or --vet-questions")


if __name__ == "__main__":
    sys.exit(main())
