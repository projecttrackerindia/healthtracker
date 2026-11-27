"""27 Nov audit: every result is judged against the lab's OWN printed range, read the way Indian labs print it.
When the printed range can't be read with certainty, we say nothing rather than guess.
Run: python -m pytest -q tests/test_ranges.py"""
import pytest

from api.ranges import judge, rejudge, timepoint

T = "Fasting: <95 1 hr: <180 2 hr: <155"
CASES = [
    (14.2, "13.0 - 17.0", "male", "", "normal"), (11.0, "12.0-15.0 g/dL", "female", "", "low"),
    (12.5, "Male: 13-17 Female: 12-15", "female", "", "normal"), (12.5, "Men 13.0-17.0 / Women 12.0-15.0", "male", "", "low"),
    (1.2, "Male: 0.7-1.3 mg/dL Female: 0.6-1.1 mg/dL", "female", "", "high"),
    (7.0, "3.5 - 7.2 mg/dL (Male), 2.6 - 6.0 mg/dL (Female)", "female", "", "high"),
    (5.08, "<5.7 Non-diabetic 5.7-6.4 Prediabetic >=6.5 Diabetic", "", "", "normal"),
    (6.0, "Non-diabetic: <5.7, Pre-diabetic: 5.7-6.4, Diabetic: >=6.5", "", "", "high"),
    (110, "Normal: 70-100 Impaired: 100-125 Diabetic: >=126", "", "", "high"), (99, "70 - 110", "", "", "normal"),
    (210, "Desirable < 200, Borderline 200-239, High >= 240", "", "", "high"),
    (120, "Optimal <100; Near optimal 100-129; Borderline 130-159", "", "", "high"),
    (180, "Normal <150, Borderline High 150-199, High 200-499", "", "", "high"),
    (35, "> 40", "male", "", "low"), (18, "Deficiency <20, Insufficiency 20-30, Sufficiency 30-100", "", "", "low"),
    (25, "Deficiency: < 20 ng/mL Insufficiency: 20 - 29 Sufficiency: 30 - 100", "", "", "low"),
    (2.1, "1.5 - 4.0 lakhs/cumm", "", "", "normal"), (160000, "1,50,000 - 4,10,000", "", "", "normal"),
    (48, "Up to 40", "", "", "high"), (40, "Up to 40", "", "", "normal"), (1.3, "Upto 1.2", "", "", "high"),
    (5.7, "< 5.7", "", "", "high"), (4.6, "0.27 - 4.20", "", "", "high"), (0.9, "0.70 to 1.30", "", "", "normal"), (3.4, "3.5–5.1 mmol/L", "", "", "low"),
    (140, T, "", "Glucose tolerance, 2 hours", "normal"), (160, T, "", "Glucose 2 hr", "high"), (99, T, "", "Glucose tolerance, fasting", "high"),
    # cannot be certain: say nothing
    (140, T, "", "Glucose Tolerance Test", None), (12.5, "Male: 13-17 Female: 12-15", "", "", None), (45, "Low <40, High >60", "", "", None),
    ("Negative", "Negative", "", "", None), (5, "", "", "", None),
]


@pytest.mark.parametrize("v,ref,sex,test,want", CASES)
def test_lab_range(v, ref, sex, test, want):
    j = judge(v, ref, sex, test)
    assert (j[0] if j else None) == want


def test_rejudge_uses_the_printed_range_and_keeps_text_results():
    fs = [{"test": "Glucose tolerance, 2 hours", "value": 140, "ref": T, "flag": "high"},
          {"test": "HIV", "value": "Non reactive", "ref": "Non reactive", "flag": "normal"},
          {"test": "TSH", "value": 4.6, "ref": "0.27 - 4.20", "flag": "normal"}]
    rejudge(fs, "female")
    assert fs[0]["flag"] == "normal" and fs[0]["flagWas"] == "high" and fs[0]["hi"] == 155
    assert fs[1]["flag"] == "normal" and "by" not in fs[1]
    assert fs[2]["flag"] == "high" and fs[2]["lo"] == 0.27 and fs[2]["by"] == "lab range"


def test_timepoints():
    assert timepoint("Glucose tolerance, fasting") == "fasting" and timepoint("GTT 1 hr") == "1h" and timepoint("Glucose 120 min") == "2h"
    assert timepoint("Glucose Tolerance Test") is None


def test_app_names_and_places():
    from pathlib import Path
    H = (Path(__file__).resolve().parents[1] / "web" / "uh.html").read_text()
    assert "glyc(o?syl)?ated" in H and "'pituitary'],[/\\brdw\\b" in H
    assert "f.test=f.test+' · reading '+c[k]" in H and "if(f.by==='lab range'&&(f.lo!=null||f.hi!=null))" in H
