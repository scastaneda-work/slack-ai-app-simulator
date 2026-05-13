"""Tests for the fcntl-based instance lock.

The lock uses fcntl.flock, which is per-OS-process. To exercise the
"second instance is blocked" path without spawning a real subprocess,
we open the same lock file from a separate file descriptor and call
flock() directly from the test."""
import fcntl
import os

import pytest

import agent.demo_agent as demo


@pytest.fixture(autouse=True)
def isolate_lock(tmp_path, monkeypatch):
    """Point the module-level LOCK_FILE at a per-test temp path so tests
    don't fight each other or stomp on a real running simulator."""
    monkeypatch.setattr(demo, "LOCK_FILE", tmp_path / ".simulator.lock")
    yield
    demo._release_lock()


def test_first_acquire_succeeds():
    assert demo._acquire_lock() is True
    assert demo.LOCK_FILE.exists()
    assert demo.LOCK_FILE.read_text().strip() == str(os.getpid())


def test_second_acquire_blocked_by_external_holder():
    """An outside fd holding LOCK_EX must block our acquisition."""
    holder = open(demo.LOCK_FILE, "a+")
    fcntl.flock(holder.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    try:
        assert demo._acquire_lock() is False
    finally:
        fcntl.flock(holder.fileno(), fcntl.LOCK_UN)
        holder.close()


def test_release_lets_next_acquire_succeed():
    assert demo._acquire_lock() is True
    demo._release_lock()
    assert demo._acquire_lock() is True


def test_stale_lock_is_reclaimed_after_holder_exits():
    """Simulate a previous instance that wrote a PID file and exited
    without unlinking. Closing its fd drops the OS lock; the next
    flock() succeeds without us needing to inspect the PID."""
    stale = open(demo.LOCK_FILE, "a+")
    fcntl.flock(stale.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    stale.write("99999")
    stale.flush()
    stale.close()  # Closing the fd releases the kernel lock.

    assert demo._acquire_lock() is True
