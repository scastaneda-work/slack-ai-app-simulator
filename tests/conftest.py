"""Make the repo root importable so tests can `from agent.retry import ...` etc."""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
