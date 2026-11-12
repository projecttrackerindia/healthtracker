"""The app's own version (used to reload a long-open home-screen app) must match the service-worker version."""
import re
from pathlib import Path

WEB = Path(__file__).resolve().parents[1] / "web"


def test_app_version_matches_service_worker():
    sw = re.search(r"const V='([^']+)'", (WEB / "sw.js").read_text()).group(1)
    app = re.search(r"const APPV='([^']+)'", (WEB / "uh.html").read_text()).group(1)
    assert sw == app
