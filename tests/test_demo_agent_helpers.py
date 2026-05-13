"""Tests for module-level helpers in agent/demo_agent.py.

These are pure functions, no Slack/Claude IO needed."""
import json

import pytest

from agent.demo_agent import (
    MAX_BLOCKS_JSON_BYTES,
    _blocks_too_large,
    _trim_history,
)


# ---- _trim_history ----------------------------------------------------------

def _msg(role, content):
    return {"role": role, "content": content}


def test_trim_history_passes_through_when_under_cap():
    history = [_msg("user", "hi"), _msg("assistant", "hello"), _msg("user", "ok")]
    assert _trim_history(history, max_chars=1000) == history


def test_trim_history_drops_oldest_until_fits():
    history = [
        _msg("user", "A" * 30),
        _msg("assistant", "B" * 30),
        _msg("user", "C" * 30),
    ]
    trimmed = _trim_history(history, max_chars=70)
    # First message dropped to fit under 70 chars (60 remaining).
    assert len(trimmed) == 2
    assert trimmed[0]["content"] == "B" * 30


def test_trim_history_always_keeps_most_recent():
    """Even a single huge message gets sent — we won't ship an empty conversation."""
    history = [_msg("user", "X" * 99999)]
    trimmed = _trim_history(history, max_chars=100)
    assert len(trimmed) == 1
    assert trimmed[0]["content"] == "X" * 99999


def test_trim_history_handles_empty_input():
    assert _trim_history([], max_chars=1000) == []


# ---- _blocks_too_large -------------------------------------------------------

def test_blocks_too_large_under_limit():
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": "tiny"}}]
    assert _blocks_too_large(blocks, MAX_BLOCKS_JSON_BYTES) is False


def test_blocks_too_large_over_limit():
    big_text = "x" * 50_000
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": big_text}}]
    assert _blocks_too_large(blocks, MAX_BLOCKS_JSON_BYTES) is True


def test_blocks_too_large_uses_byte_length_not_char_length():
    """Multi-byte unicode: 4-byte chars count as 4, not 1."""
    # Each rocket emoji is 4 bytes in UTF-8.
    text = "🚀" * 10_000  # 40_000 bytes, 10_000 characters
    blocks = [{"type": "section", "text": {"type": "mrkdwn", "text": text}}]
    assert _blocks_too_large(blocks, max_bytes=20_000) is True


def test_blocks_too_large_returns_true_on_unencodable_input():
    """Non-JSON-serializable input (a set) is treated as too large rather
    than crashing the post call."""
    blocks = [{"type": "section", "extra": {1, 2, 3}}]
    assert _blocks_too_large(blocks, MAX_BLOCKS_JSON_BYTES) is True
