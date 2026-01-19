from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TESTKIT_SRC = ROOT / "packages" / "testkit" / "src"
if str(TESTKIT_SRC) not in sys.path:
    sys.path.insert(0, str(TESTKIT_SRC))

from agentmarket_testkit.fixtures import *  # noqa: F401,F403
