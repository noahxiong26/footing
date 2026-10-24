"""Spanish display text for the Fit Score reasons (footing/web/i18n.js). Needs node, like the parity test."""
import json
import shutil
import subprocess
from pathlib import Path

import pytest

HERE = Path(__file__).resolve().parent
pytestmark = pytest.mark.skipif(shutil.which("node") is None, reason="node not installed")


def test_every_engine_reason_has_spanish():
    out = json.loads(subprocess.run(["node", str(HERE / "js" / "check_reasons.js")], capture_output=True,
                                    text=True, check=True).stdout)
    assert out["checked"] > 10000
    assert out["bad"] == [], out["bad"][:5]
