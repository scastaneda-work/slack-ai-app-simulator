"""Tests for the subprocess env allowlist."""
import os
from unittest.mock import patch

from agent.claude_subprocess import _build_env


def test_keeps_path_and_home():
    with patch.dict(os.environ, {"PATH": "/x:/y", "HOME": "/Users/abc"}, clear=True):
        env = _build_env()
    assert env["PATH"] == "/x:/y"
    assert env["HOME"] == "/Users/abc"


def test_always_sets_claude_code_simple():
    with patch.dict(os.environ, {}, clear=True):
        env = _build_env()
    assert env["CLAUDE_CODE_SIMPLE"] == "1"


def test_strips_unrelated_secrets():
    with patch.dict(
        os.environ,
        {
            "PATH": "/usr/bin",
            "GITHUB_TOKEN": "ghp_secret123",
            "DATABASE_URL": "postgres://...",
            "SECRET_KEY": "abcdef",
            "MY_PERSONAL_API_KEY": "leaked",
        },
        clear=True,
    ):
        env = _build_env()
    assert "GITHUB_TOKEN" not in env
    assert "DATABASE_URL" not in env
    assert "SECRET_KEY" not in env
    assert "MY_PERSONAL_API_KEY" not in env


def test_keeps_anthropic_aws_claude_node_npm():
    with patch.dict(
        os.environ,
        {
            "PATH": "/x",
            "ANTHROPIC_BASE_URL": "https://api.example.com",
            "AWS_REGION": "us-west-2",
            "AWS_PROFILE": "default",
            "CLAUDE_CONFIG_DIR": "/tmp/claude",
            "NODE_OPTIONS": "--max-old-space-size=4096",
            "NPM_CONFIG_REGISTRY": "https://npm.example.com",
        },
        clear=True,
    ):
        env = _build_env()
    assert env["ANTHROPIC_BASE_URL"] == "https://api.example.com"
    assert env["AWS_REGION"] == "us-west-2"
    assert env["AWS_PROFILE"] == "default"
    assert env["CLAUDE_CONFIG_DIR"] == "/tmp/claude"
    assert env["NODE_OPTIONS"] == "--max-old-space-size=4096"
    assert env["NPM_CONFIG_REGISTRY"] == "https://npm.example.com"


def test_keeps_lc_locale_vars():
    with patch.dict(
        os.environ,
        {"PATH": "/x", "LC_ALL": "en_US.UTF-8", "LC_CTYPE": "C"},
        clear=True,
    ):
        env = _build_env()
    assert env["LC_ALL"] == "en_US.UTF-8"
    assert env["LC_CTYPE"] == "C"
