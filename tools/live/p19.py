"""Round 19 patch: Bluetooth inside the phone app, Withings and Oura clouds beside Fitbit."""
from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
W = ROOT / "web" / "index.html"
HERE = Path(__file__).resolve().parent
MARK = "/*live-p19*/"
s = W.read_text(encoding="utf-8")
if "/*live-p18*/" not in s:
    sys.exit("apply p18 first")
if MARK in s:
    sys.exit("already applied")


def one(old, new):
    global s
    n = s.count(old)
    if n != 1:
        sys.exit(f"expected 1 match, found {n}: {old[:80]!r}")
    s = s.replace(old, new)


# the phone app used to send the "Read from a device" button to Health Connect; with the native Bluetooth bridge it reads the device
one("if(SX.native){const ble0=SX.act.bledev;SX.act.bledev=()=>SX.act.hcsync();void ble0}",
    "if(SX.native){const ble0=SX.act.bledev;SX.act.bledev=(...a)=>(navigator.bluetooth&&navigator.bluetooth.requestDevice)?ble0(...a):SX.act.hcsync()}")
# source labels for the new clouds
one("const SRC={dev:'Bluetooth',hc:'Phone (Health Connect)',apple:'Apple Health',fitbit:'Fitbit',polar:'Polar H10'};",
    "const SRC={dev:'Bluetooth',hc:'Phone (Health Connect)',apple:'Apple Health',fitbit:'Fitbit',polar:'Polar H10',withings:'Withings',oura:'Oura'};")
HEAD = "</head>\n<body>"
if s.count(HEAD) != 1:
    sys.exit("head anchor")
s = s.replace(HEAD, '<style id="live19-css">' + (HERE / "live19.css").read_text(encoding="utf-8") + "</style>\n" + HEAD)
BOOT = "SX.boot();\n})();"
if s.count(BOOT) != 1:
    sys.exit("boot anchor not unique")
s = s.replace(BOOT, MARK + "\n" + (HERE / "live19.js").read_text(encoding="utf-8") + "\n" + BOOT)
W.write_text(s, encoding="utf-8")
print("patched", W.relative_to(ROOT))
subprocess.run([sys.executable, str(ROOT / "tools" / "compress.py")], check=True)
