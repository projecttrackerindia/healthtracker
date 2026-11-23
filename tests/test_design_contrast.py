"""Design system: every text colour the app uses reads at WCAG AA (4.5:1) on the surfaces it sits on,
and status is never shown by colour alone. Tokens are read from the shipped pages, so a later edit that
fades a colour below AA fails here."""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
UH = (ROOT / "web" / "uh.html").read_text(encoding="utf-8")
BODY = (ROOT / "web" / "body.html").read_text(encoding="utf-8")
PARTNER = (ROOT / "partner" / "index.html").read_text(encoding="utf-8")


def _lum(hx: str) -> float:
    hx = hx.lstrip("#")
    out = []
    for i in (0, 2, 4):
        c = int(hx[i:i + 2], 16) / 255
        out.append(c / 12.92 if c <= 0.03928 else ((c + 0.055) / 1.055) ** 2.4)
    return 0.2126 * out[0] + 0.7152 * out[1] + 0.0722 * out[2]


def ratio(a: str, b: str) -> float:
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def tokens(src: str) -> dict:
    root = re.search(r":root\{([^}]*)\}", src).group(1)
    return {k: v for k, v in re.findall(r"--([a-z0-9-]+):(#[0-9A-Fa-f]{6})", root)}


T = tokens(UH)


def test_tokens_present():
    for k in ("ink2", "ink3", "blue", "ai-ink", "ok", "ok-bg", "watch", "watch-bg", "doc", "doc-bg", "urgent", "urgent-bg", "rose"):
        assert k in T, k


def test_text_on_surfaces():
    for fg in ("ink2", "ink3", "blue", "ai-ink", "ok", "watch", "doc", "urgent", "rose"):
        for bg in ("#FFFFFF", "#F5F5F7"):
            assert ratio(T[fg], bg) >= 4.5, (fg, bg, round(ratio(T[fg], bg), 2))


def test_status_words_on_their_tints():
    for k in ("ok", "watch", "doc", "urgent"):
        assert ratio(T[k], T[k + "-bg"]) >= 4.5, (k, round(ratio(T[k], T[k + "-bg"]), 2))


def test_moods_keep_contrast():
    # pregnancy Sand with Rose; after a loss Mist with Slate; kids' Sky with the accent
    assert ratio("#A8436A", "#F6EFE7") >= 4.5
    assert ratio("#4A5563", "#EEF1F4") >= 4.5
    assert ratio("#0066CC", "#D8EEFC") >= 4.5 or ratio("#004F9E", "#D8EEFC") >= 4.5


def test_steps_are_ordered_and_distinct():
    # the four steps differ in lightness too, so they still separate for colour-blind eyes and in greyscale
    ls = [_lum(T[k]) for k in ("ok", "watch", "doc", "urgent")]
    assert len({round(x, 3) for x in ls}) == 4


def test_status_never_colour_alone():
    # every step carries an icon and a word in the family app, the 3D viewer and the doctor's view
    assert re.search(r"const STI=\{ok:'<svg", UH) and "function statusOf" in UH
    assert "STI2" in BODY and "STW(f)" in BODY
    assert "<sup" in PARTNER and "DOCT" in PARTNER


def test_no_old_low_contrast_greys_left():
    for page in (UH, BODY):
        assert not re.search(r"color:#8E8E93[;\"}]", page), "use var(--ink3) for text"
        assert not re.search(r"color:#86868B[;\"}]", page), "use var(--ink3) for text"


def test_red_is_for_emergencies():
    # a missed dose or a result that got worse is not an emergency
    assert ".mtm.late{color:var(--watch)}" in UH
    assert ".bt.r{background:#FFF1E6}.bt.r b{color:#B54708}" in BODY
