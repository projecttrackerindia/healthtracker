"""A photo of a lab report is read on the server (OCR) when the smart reader is off.
Run: python -m pytest -q tests/test_scan_ocr.py"""
import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from api import ai

pytestmark = pytest.mark.skipif(not shutil.which("tesseract"), reason="tesseract not installed here")
LINES = ["SUNRISE DIAGNOSTICS - BIOCHEMISTRY", "Patient: Amma   Age: 64 Y   Sex: F", "", "Test                Result   Unit     Reference",
         "HbA1c               7.8      %        4.0 - 5.6", "Fasting glucose     142      mg/dL    70 - 100", "Total cholesterol   214      mg/dL    < 200",
         "Creatinine          0.9      mg/dL    0.6 - 1.1", "TSH                 2.4      uIU/mL   0.4 - 4.0"]


def photo() -> bytes:
    f = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf", 26)
    im = Image.new("RGB", (1100, 420), (248, 246, 240))
    d = ImageDraw.Draw(im)
    for i, ln in enumerate(LINES):
        d.text((30, 20 + i * 42), ln, fill=(30, 30, 30), font=f)
    im = im.rotate(1.2, expand=True, fillcolor=(248, 246, 240)).resize((800, 320))   # a slightly tilted, small phone photo
    b = io.BytesIO()
    im.save(b, "JPEG", quality=80)
    return b.getvalue()


def test_a_report_photo_is_read_without_the_smart_reader(monkeypatch):
    monkeypatch.setattr(ai, "available", lambda: False)
    out = ai.analyze("report", photo(), "image/jpeg", "", {"age": 64, "sex": "female"})
    got = {f.get("code"): f for f in out["findings"]}
    assert out.get("scanned") is True and any("photo" in w for w in out["warnings"])
    assert "hba1c" in got and float(got["hba1c"]["value"]) == 7.8
    assert "glu_f" in got and float(got["glu_f"]["value"]) == 142
    assert len(got) >= 4
