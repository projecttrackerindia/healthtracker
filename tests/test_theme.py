"""The app is light by default. Dark is a choice, and so is following the phone.

This exists because the default has already been lost once. A layer made the "System" setting work by
removing the data-theme attribute whenever nothing was stored — correct for System, but it also handed the
decision to the phone for everyone who had never opened Settings. Every visitor with a dark phone got a dark
app, which is not what this product ships as.

Three states, and the third is the one that keeps getting dropped:

    stored "light" / "dark"  ->  that, explicitly
    stored "system"          ->  no attribute, the phone decides
    nothing stored           ->  light

Run: python -m pytest -q tests/test_theme.py
"""
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
APP = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
LAYER = (ROOT / "tools" / "live" / "p35.py").read_text(encoding="utf-8")


def _boot() -> str:
    """The <script> in <head> that sets the theme before the first paint."""
    m = re.search(r'<script>try\{var _t=localStorage\.getItem\("tht\.theme"\);.*?</script>', APP, re.S)
    assert m, "the theme boot script is gone from web/index.html"
    return m.group(0)


def test_the_boot_script_defaults_to_light():
    """No stored preference must mean light, not 'ask the phone'."""
    b = _boot()
    assert 'dataset.theme="light"' in b, "nothing stored no longer falls back to light"
    # the attribute may only be removed for an explicit "system", never as the default
    for m in re.finditer(r'removeAttribute\("data-theme"\)', b):
        before = b[:m.start()]
        assert '_t==="system"' in before, \
            "the boot script removes data-theme outside the explicit 'system' branch, " \
            "which hands a first-time visitor's theme to their phone"


def test_the_boot_script_still_honours_an_explicit_choice():
    b = _boot()
    assert '_t==="dark"' in b and '_t==="light"' in b
    assert '_t==="system"' in b, "System stopped being a real option"


def test_a_failure_to_read_storage_still_gives_light():
    """Private mode and blocked storage throw. The catch must not leave the theme to the phone."""
    b = _boot()
    catch = b[b.index("catch("):]
    assert 'dataset.theme="light"' in catch, "a storage error leaves the theme unset"


def test_the_runtime_theme_logic_matches_the_boot_script():
    """A second block re-applies the theme after boot; if it disagrees, the page flashes and then changes."""
    m = re.search(r"\{const r=document\.documentElement,saved=ls\('tht\.theme'\);.*?attributeFilter:\['data-theme'\]\}\)\}",
                  APP, re.S)
    assert m, "the runtime theme block is gone"
    blk = m.group(0)
    assert "else r.dataset.theme='light'" in blk, "the runtime fallback is not light"
    assert "saved==='system'" in blk, "System is not handled at runtime"


def test_the_patch_layer_agrees_so_a_rebuild_keeps_it():
    """web/index.html is built from these layers. Fixing only the built file lasts until the next rebuild."""
    assert 'else document.documentElement.dataset.theme="light"' in LAYER
    assert "else r.dataset.theme='light';" in LAYER
    assert '_t==="system"' in LAYER


def test_dark_styling_stays_behind_the_light_guard():
    """Every dark rule must be guarded, or an explicit light theme cannot win on a dark phone."""
    unguarded = []
    for m in re.finditer(r'@media \(prefers-color-scheme:\s*dark\)\s*\{([^{]{0,120})', APP):
        head = m.group(1)
        if "data-theme" not in head:
            unguarded.append(head.strip()[:70])
    assert not unguarded, (
        "dark rules not guarded by :root:not([data-theme=light]) — these win over an explicit "
        "light choice on a dark phone: " + "; ".join(unguarded)
    )
