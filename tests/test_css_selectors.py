"""A selector list cut off by a comment (`.page,.sheetx .sh,/* ... */#layer{...}`) silently merges two rules: on
14 Nov it gave every app page `overflow:hidden`, so long screens like Settings stopped scrolling on phones."""
import re
from pathlib import Path

FILES = ["web/uh.html", "partner/index.html", "admin/index.html", "web/body.html", "site/authfx.js"]


def _css(text):
    return "\n".join(re.findall(r"<style[^>]*>(.*?)</style>", text, re.S)) or text


def test_no_selector_list_runs_into_a_comment():
    for f in FILES:
        p = Path(f)
        if p.exists():
            assert not re.search(r",\s*/\*", _css(p.read_text())), f"{f}: selector list ends in a comma before a comment"


def test_app_pages_can_scroll():
    css = re.sub(r"/\*.*?\*/", "", _css(Path("web/uh.html").read_text()), flags=re.S)
    for sel, body in re.findall(r"([^{}]+)\{([^{}]*)\}", css):
        names = [s.strip() for s in sel.split(",")]
        if ".page" in names or ".sheetx .sh" in names:
            assert not re.search(r"(^|;)\s*overflow\s*:\s*hidden", body), f"{sel.strip()} must not hide overflow"
            assert "contain:strict" not in body.replace(" ", ""), f"{sel.strip()} must not use contain:strict"
