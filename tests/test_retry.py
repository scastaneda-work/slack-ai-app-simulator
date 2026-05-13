"""Tests for the retry decorator."""
from unittest.mock import MagicMock

import pytest
from slack_sdk.errors import SlackApiError

from agent.retry import retry_on_rate_limit


def _ratelimit_error(retry_after="2"):
    response = MagicMock()
    response.get.side_effect = lambda key, default=None: {"error": "ratelimited"}.get(key, default)
    response.headers = {"Retry-After": retry_after} if retry_after is not None else {}
    return SlackApiError(message="rate limited", response=response)


def _other_error(code="not_in_channel"):
    response = MagicMock()
    response.get.side_effect = lambda key, default=None: {"error": code}.get(key, default)
    response.headers = {}
    return SlackApiError(message=code, response=response)


def test_returns_immediately_on_success():
    sleeps = []
    fn = MagicMock(return_value="ok")
    decorated = retry_on_rate_limit(sleep=sleeps.append)(fn)

    assert decorated("a") == "ok"
    assert fn.call_count == 1
    assert sleeps == []


def test_retries_on_ratelimited_then_succeeds():
    sleeps = []
    fn = MagicMock(side_effect=[_ratelimit_error("3"), "ok"])
    decorated = retry_on_rate_limit(sleep=sleeps.append)(fn)

    assert decorated() == "ok"
    assert fn.call_count == 2
    assert sleeps == [3.0]


def test_gives_up_after_attempts_exhausted():
    sleeps = []
    err = _ratelimit_error("1")
    fn = MagicMock(side_effect=[err, err, err])
    decorated = retry_on_rate_limit(attempts=3, sleep=sleeps.append)(fn)

    with pytest.raises(SlackApiError):
        decorated()
    assert fn.call_count == 3
    assert sleeps == [1.0, 1.0]


def test_other_errors_propagate_without_retry():
    sleeps = []
    fn = MagicMock(side_effect=_other_error("not_in_channel"))
    decorated = retry_on_rate_limit(sleep=sleeps.append)(fn)

    with pytest.raises(SlackApiError):
        decorated()
    assert fn.call_count == 1
    assert sleeps == []


def test_clamps_retry_after_to_max():
    sleeps = []
    fn = MagicMock(side_effect=[_ratelimit_error("9999"), "ok"])
    decorated = retry_on_rate_limit(sleep=sleeps.append)(fn)

    decorated()
    assert sleeps == [30.0]
