"""What may be pinned on the 3D body, and whose result it is.

Found on the live app (24 Nov 2026): a scan's "Expected date of delivery" was pinned on the liver as an in-range result,
because the liver rule matched the letters inside "de-liver-y"; and the baby's scan measurements were listed as the
mother's own results. These rules live in web/uh.html, so the test runs them with Node (skipped where Node is missing).
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

UH = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text()


def _run(expr: str):
    node = shutil.which("node")
    if not node:
        pytest.skip("node is not installed")
    parts = []
    for name in ("const FEVER=", "const ORG_RX=", "const nameOrg=", "const isFactRow="):
        i = UH.index(name)
        end = {"const FEVER=": "/i;", "const ORG_RX=": "]];", "const nameOrg=": "return null};", "const isFactRow=": "/i;"}[name]
        j = UH.index(end, UH.index("BABY_RX=", i) if name == "const isFactRow=" else i) + len(end)
        parts.append(UH[i:j])
    out = subprocess.run([node, "-e", "\n".join(parts) + f"\nconsole.log(JSON.stringify({expr}))"], capture_output=True, text=True, timeout=20)
    assert out.returncode == 0, out.stderr[-400:]
    return json.loads(out.stdout)


def test_delivery_is_not_the_liver():
    assert _run("['Expected date of delivery','Delivery date','Mode of delivery'].map(nameOrg)") == [None, None, None]


def test_liver_tests_still_reach_the_liver():
    got = _run("['Liver function test','SGPT (ALT)','Total bilirubin','HBsAg','Anti HCV','Fatty liver grade'].map(nameOrg)")
    assert got == ["liver"] * 6


def test_a_date_is_a_fact_not_a_result():
    rows = [{"test": "Expected date of delivery", "value": "31-01-2027"}, {"test": "LMP", "value": "20 Apr 2026"},
            {"test": "Report date", "value": "15/11/2026"}, {"test": "Haemoglobin", "value": "11.2"}]
    assert _run(f"{json.dumps(rows)}.map(isFactRow)") == [True, True, True, False]


def test_baby_measurements_are_the_babys():
    names = ["Fetal heart rate", "BPD", "HC", "AC", "FL", "EFW", "Cerebellar transverse diameter", "Cisterna magna",
             "Lateral ventricles", "Estimated fetal age by ultrasound", "Nuchal translucency"]
    assert _run(f"{json.dumps(names)}.map(t=>BABY_RX.test(t))") == [True] * len(names)
    own = ["Mean arterial pressure (MAP)", "Cervical length", "Haemoglobin", "HbA1c", "Glucose fasting"]
    assert _run(f"{json.dumps(own)}.map(t=>BABY_RX.test(t))") == [False] * len(own)


def test_the_way_back_is_at_the_top_of_all_results():
    body = (Path(__file__).resolve().parents[1] / "web" / "body.html").read_text()
    fn = body[body.index("function vAll()"):]
    fn = fn[:fn.index("\n")]
    assert fn.index("‹ Back") < fn.index("mlist"), "Back must come before the list"
    assert "BABY’S MEASUREMENTS" in fn


def test_landing_and_app_agree_on_the_sos_hold():
    home = (Path(__file__).resolve().parents[1] / "site" / "home" / "index.html").read_text()
    assert "Hold for one second" in UH or "Hold for one second." in UH
    assert not re.search(r"hold (for )?3 seconds", home, re.I)
