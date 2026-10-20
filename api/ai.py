"""Report and prescription understanding.

Two engines, same JSON shape:
* claude  — when ANTHROPIC_API_KEY is set: the PDF/photo/text goes to the Claude API with a strict JSON instruction.
* local   — otherwise: PDF/plain text is parsed with a dictionary of common Indian lab panels and medicine patterns.
            Photos cannot be read without the API (no OCR on the server), and the response says so.

Nothing is diagnosed. Every result is phrased for discussion with a doctor, and the document is never stored.
"""
from __future__ import annotations

import base64
import io
import json
import os
import re
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
CATALOG = json.loads((HERE / "data" / "catalog.json").read_text(encoding="utf-8"))
MODEL = os.getenv("DOKKO_AI_MODEL", "claude-sonnet-5-5")
# if the configured model is not available to this API key, the next one is tried and remembered for the process
FALLBACK_MODELS = [m for m in [MODEL, "claude-sonnet-5-5", "claude-haiku-5-5", "claude-sonnet-4-5", "claude-3-5-sonnet-latest"] if m]
LAST_ERROR: dict = {}   # admins see this on the dashboard; users never do
FOCUS = {"heart", "lungs", "liver", "kidneys", "pancreas", "thyroid", "stomach", "intestines", "brain", "spleen", "bones", "spine", "uterus", "prostate", "bladder", "breast", "skin", "eyes", "blood", "whole_body"}
_WORKING: dict = {"model": None, "gemini": None, "provider": None}
# token accounting: every successful call adds to USAGE for the request that is running; routes move it into AiJob rows
import contextvars as _cv
USAGE: _cv.ContextVar = _cv.ContextVar("ai_usage", default=None)


def take_usage() -> tuple[int, int]:
    """Tokens used by the AI calls made since the last take (input, output). Zero when nothing ran."""
    u = USAGE.get()
    USAGE.set(None)
    return (u[0], u[1]) if u else (0, 0)


def _note_usage(r) -> None:
    try:
        u = USAGE.get() or (0, 0)
        USAGE.set((u[0] + int(r.usage.input_tokens or 0), u[1] + int(r.usage.output_tokens or 0)))
    except Exception:
        pass


# ---------------------------------------------------------------------------------------------------------------------
# Providers. The app never names a vendor; "smart reading" runs on whichever key is configured:
#   AI_PROVIDER=auto (default) → Gemini when GEMINI_API_KEY is set, otherwise Anthropic; the other one is the fallback.
#   AI_PROVIDER=gemini | anthropic → that one first, the other as fallback when its key exists.
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
GEMINI_FALLBACK = [m for m in [GEMINI_MODEL, "gemini-2.5-flash", "gemini-2.0-flash"] if m]


def available() -> bool:
    return bool(os.getenv("ANTHROPIC_API_KEY") or os.getenv("GEMINI_API_KEY"))


def provider_order() -> list[str]:
    pref = (os.getenv("AI_PROVIDER") or "auto").strip().lower()
    have = [p for p in ("gemini", "anthropic") if os.getenv("GEMINI_API_KEY" if p == "gemini" else "ANTHROPIC_API_KEY")]
    if pref in ("gemini", "anthropic") and pref in have:
        return [pref] + [p for p in have if p != pref]
    return have  # auto: gemini first when both exist


class _Block:
    def __init__(self, text: str):
        self.type, self.text = "text", text


class _Usage:
    def __init__(self, i: int, o: int):
        self.input_tokens, self.output_tokens = i, o


class _Resp:
    """Shape shared by both providers: .content[].text and .usage.input_tokens/.output_tokens."""

    def __init__(self, text: str, i: int, o: int):
        self.content, self.usage = [_Block(text)], _Usage(i, o)


def _gemini_parts(content) -> list[dict]:
    if isinstance(content, str):
        return [{"text": content}]
    parts = []
    for b in content:
        t = b.get("type")
        if t == "text":
            parts.append({"text": b["text"]})
        elif t in ("image", "document"):
            src = b.get("source", {})
            parts.append({"inline_data": {"mime_type": src.get("media_type", "application/octet-stream"), "data": src.get("data", "")}})
    return parts


def _gemini_create(max_tokens: int = 2000, system: str = "", messages: list | None = None, **_):
    import httpx

    key = os.getenv("GEMINI_API_KEY", "")
    body = {"contents": [{"role": "model" if m["role"] == "assistant" else "user", "parts": _gemini_parts(m["content"])} for m in (messages or [])],
            "generationConfig": {"maxOutputTokens": int(max_tokens), "temperature": 0.2}}
    if system:
        body["systemInstruction"] = {"parts": [{"text": system}]}
    last = None
    for m in dict.fromkeys([_WORKING.get("gemini") or GEMINI_MODEL] + GEMINI_FALLBACK):
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{m}:generateContent"
        try:
            with httpx.Client(timeout=120) as c:
                r = c.post(url, params={"key": key}, json=body)
            if r.status_code == 404:
                last = RuntimeError(f"model {m} not found")
                continue
            r.raise_for_status()
            j = r.json()
            cands = j.get("candidates") or []
            text = "".join(p.get("text", "") for p in (cands[0].get("content", {}).get("parts", []) if cands else []))
            if not text and cands and cands[0].get("finishReason") not in (None, "STOP", "MAX_TOKENS"):
                raise RuntimeError(f"blocked: {cands[0].get('finishReason')}")
            u = j.get("usageMetadata", {})
            if _WORKING.get("gemini") != m:
                _WORKING["gemini"] = m
                print(f"[ai] using model {m}", flush=True)
            return _Resp(text, int(u.get("promptTokenCount", 0) or 0), int(u.get("candidatesTokenCount", 0) or 0))
        except httpx.HTTPStatusError as e:
            raise RuntimeError(f"gemini {e.response.status_code}: {e.response.text[:200]}") from e
    raise RuntimeError(f"No usable Gemini model: {last}")


def create(**kw):
    """One call, whichever provider is configured; the other provider is tried when the first fails."""
    order = provider_order()
    if not order:
        raise RuntimeError("No AI key configured (GEMINI_API_KEY or ANTHROPIC_API_KEY).")
    last = None
    for p in order:
        try:
            r = _gemini_create(**kw) if p == "gemini" else _anthropic_create(**kw)
            _note_usage(r)
            _WORKING["provider"] = p
            return r
        except Exception as e:  # noqa: BLE001 — the next provider gets its turn; the last error is reported
            last = e
            print(f"[ai] {p} failed: {type(e).__name__}: {str(e)[:200]}", flush=True)
    raise last if last else RuntimeError("AI unavailable")


def _anthropic_create(**kw):
    """messages.create with model fallback: a 404 'model not found' moves to the next candidate instead of failing the user."""
    import anthropic
    from anthropic import DefaultHttpxClient

    # the installed brotli package's C-extension API doesn't match what this SDK's HTTP client expects when
    # decoding a brotli-encoded response ("process() takes no keyword arguments"); gzip is always available,
    # so just don't advertise brotli support to the server instead of fighting the brotli package version.
    client = anthropic.Anthropic(http_client=DefaultHttpxClient(headers={"Accept-Encoding": "gzip, identity"}))
    tried = []
    order = ([_WORKING["model"]] if _WORKING["model"] else []) + [m for m in FALLBACK_MODELS if m != _WORKING["model"]]
    last = None
    for m in dict.fromkeys(order):
        try:
            r = client.messages.create(model=m, **kw)
            if _WORKING["model"] != m:
                _WORKING["model"] = m
                print(f"[ai] using model {m}", flush=True)
            return r
        except anthropic.NotFoundError as e:
            tried.append(m); last = e
            continue
        except anthropic.BadRequestError as e:
            if "model" in str(e).lower():
                tried.append(m); last = e
                continue
            raise
    raise RuntimeError(f"No usable model for this API key (tried {', '.join(tried)}): {last}")


def current_model() -> str:
    if _WORKING.get("provider") == "gemini" or (not _WORKING.get("provider") and provider_order()[:1] == ["gemini"]):
        return _WORKING.get("gemini") or GEMINI_MODEL
    return _WORKING["model"] or MODEL


def _fail(where: str, e: Exception) -> None:
    cause = f" cause={type(e.__cause__).__name__}: {str(e.__cause__)[:300]}" if e.__cause__ else ""
    LAST_ERROR.update({"t": int(time.time()), "where": where, "error": f"{type(e).__name__}: {str(e)[:300]}{cause}"})
    print(f"[ai] {where} failed: {type(e).__name__}: {str(e)[:300]}{cause}", flush=True)


def pdf_pages_as_images(data: bytes, max_pages: int = 4) -> list[bytes]:
    """Render PDF pages to JPEG so scanned reports can be read as images when the document route is unavailable."""
    try:
        import pymupdf  # type: ignore
    except ImportError:
        try:
            import fitz as pymupdf  # type: ignore
        except ImportError:
            return []
    out = []
    try:
        doc = pymupdf.open(stream=data, filetype="pdf")
        for i, page in enumerate(doc):
            if i >= max_pages:
                break
            pix = page.get_pixmap(dpi=110)
            out.append(pix.tobytes("jpeg"))
    except Exception as e:
        _fail("pdf render", e)
    return out
DISCLAIMER = ("This is an educational summary, not a diagnosis or treatment advice. Reference ranges vary by lab, age and pregnancy. "
              "Please discuss these results with your doctor before changing any medicine.")

# ---- lab dictionary: code -> (names regex, unit, low, high, plain-language meaning) ; ranges are general adult values ----
LAB = {
    "hb": (r"h(?:ae|e)moglobin|\bhb\b|hgb", "g/dL", 12.0, 17.0, "Haemoglobin carries oxygen. Low values suggest anaemia (often iron deficiency); high values can follow dehydration or smoking."),
    "wbc": (r"wbc|white blood|total leu[ck]ocyte|tlc", "/µL", 4000, 11000, "White cells fight infection. High counts often mean infection or inflammation; low counts can follow viral illness or some medicines."),
    "plt": (r"platelet", "/µL", 150000, 410000, "Platelets help blood clot. Low counts happen in dengue and some infections; very low counts can cause bleeding."),
    "glu_f": (r"fasting (?:blood )?(?:glucose|sugar)|fbs|glucose,? fasting|fasting plasma glucose", "mg/dL", 70, 99, "Fasting sugar 100–125 is pre-diabetes range; 126 or more on two occasions suggests diabetes."),
    "glu_pp": (r"post ?prandial|\bpp(?:bs)?\b|2 ?hr? (?:glucose|sugar)|after (?:meal|food)", "mg/dL", 70, 139, "Sugar 2 hours after a meal. 140–199 is pre-diabetes range; 200 or more suggests diabetes."),
    "glu_r": (r"random (?:blood )?(?:glucose|sugar)|rbs", "mg/dL", 70, 139, "Random sugar; 200 or more with symptoms suggests diabetes."),
    "hba1c": (r"hba1c|glycated|glycosylated", "%", 4.0, 5.6, "Average sugar over 3 months. 5.7–6.4 is pre-diabetes range; 6.5 or more suggests diabetes; people with diabetes often aim below 7."),
    "tc": (r"total cholesterol|cholesterol,? total|\bcholesterol\b(?! ?hdl| ?ldl)", "mg/dL", 0, 200, "Total cholesterol; below 200 is desirable."),
    "ldl": (r"\bldl", "mg/dL", 0, 100, "'Bad' cholesterol that builds plaque; targets are lower with diabetes or heart disease."),
    "hdl": (r"\bhdl", "mg/dL", 40, 100, "'Good' cholesterol; higher is better (40+ men, 50+ women)."),
    "tg": (r"triglycerid", "mg/dL", 0, 150, "Fats in blood; rises with sugar, alcohol and refined carbohydrates."),
    "vldl": (r"\bvldl", "mg/dL", 0, 30, "Carries triglycerides."),
    "alt": (r"\balt\b|sgpt|alanine", "U/L", 0, 40, "Liver enzyme; rises with fatty liver, hepatitis, alcohol or some medicines."),
    "ast": (r"\bast\b|sgot|aspartate", "U/L", 0, 40, "Liver (and muscle) enzyme."),
    "alp": (r"alkaline phosphatase|\balp\b", "U/L", 40, 130, "Rises with bile duct or bone problems; normally higher in children and pregnancy."),
    "bili": (r"total bilirubin|bilirubin,? total|\bbilirubin\b", "mg/dL", 0.1, 1.2, "Yellow pigment; high values cause jaundice."),
    "alb": (r"albumin(?! ?/)|serum albumin", "g/dL", 3.5, 5.2, "Main blood protein, made by the liver."),
    "creat": (r"creatinine", "mg/dL", 0.6, 1.2, "Kidney filter marker; rises when kidneys filter less."),
    "urea": (r"blood urea|\burea\b|\bbun\b", "mg/dL", 15, 45, "Waste product cleared by the kidneys."),
    "uric": (r"uric acid", "mg/dL", 2.5, 7.0, "High uric acid can cause gout and kidney stones."),
    "na": (r"sodium|\bna\+?\b", "mmol/L", 135, 145, "Salt balance."),
    "k": (r"potassium|\bk\+?\b", "mmol/L", 3.5, 5.1, "Important for heart rhythm; both low and high values matter."),
    "ca": (r"calcium", "mg/dL", 8.5, 10.5, "Bone and nerve mineral."),
    "tsh": (r"\btsh\b|thyroid stimulating", "µIU/mL", 0.4, 4.5, "High TSH suggests an underactive thyroid; low TSH an overactive one. Ranges differ in pregnancy."),
    "t3": (r"\bt3\b|triiodothyronine", "ng/dL", 80, 200, "Thyroid hormone."),
    "t4": (r"\bt4\b|thyroxine", "µg/dL", 4.5, 12.0, "Thyroid hormone."),
    "vitd": (r"vitamin d|25.?oh|25-hydroxy", "ng/mL", 30, 100, "Below 20 is deficiency, 20–29 insufficient; very common in India."),
    "b12": (r"b ?12|cobalamin", "pg/mL", 200, 900, "Low B12 causes tiredness, numbness and anaemia; common with vegetarian diets."),
    "ferr": (r"ferritin", "ng/mL", 20, 250, "Iron stores; low ferritin means iron deficiency."),
    "crp": (r"\bcrp\b|c-?reactive", "mg/L", 0, 6, "Inflammation marker; rises with infection."),
    "esr": (r"\besr\b|sedimentation", "mm/hr", 0, 20, "Non-specific inflammation marker."),
    "rbc": (r"\brbc\b|red blood cell count", "million/µL", 4.0, 5.8, "Red cell count."),
    "mcv": (r"\bmcv\b", "fL", 80, 100, "Red cell size: small in iron deficiency, large with B12/folate deficiency."),
    "pcv": (r"\bpcv\b|h(?:ae|e)matocrit|\bhct\b", "%", 36, 50, "Share of blood that is red cells."),
    "sbp": (r"systolic|\bbp\b|blood pressure", "mmHg", 90, 129, "Upper blood-pressure number; 130–139 is stage 1, 140+ stage 2 hypertension."),
    "spo2": (r"spo2|oxygen sat", "%", 95, 100, "Oxygen saturation."),
    "egfr": (r"egfr|gfr", "mL/min", 90, 200, "Kidney filtration rate; below 60 for 3 months is chronic kidney disease."),
    "psa": (r"\bpsa\b|prostate specific", "ng/mL", 0, 4, "Prostate marker; rises with enlargement, infection or cancer; decide further tests with a doctor."),
}
CANON = {"hb": "Haemoglobin", "wbc": "White blood cells", "plt": "Platelets", "glu_f": "Fasting glucose", "glu_pp": "Post-meal glucose", "glu_r": "Random glucose", "hba1c": "HbA1c", "tc": "Total cholesterol", "ldl": "LDL cholesterol", "hdl": "HDL cholesterol", "tg": "Triglycerides", "vldl": "VLDL", "alt": "ALT (SGPT)", "ast": "AST (SGOT)", "alp": "Alkaline phosphatase", "bili": "Total bilirubin", "alb": "Albumin", "creat": "Creatinine", "urea": "Blood urea", "uric": "Uric acid", "na": "Sodium", "k": "Potassium", "ca": "Calcium", "tsh": "TSH", "t3": "T3", "t4": "T4", "vitd": "Vitamin D", "b12": "Vitamin B12", "ferr": "Ferritin", "crp": "CRP", "esr": "ESR", "rbc": "RBC count", "mcv": "MCV", "pcv": "PCV / haematocrit", "sbp": "Blood pressure (systolic)", "spo2": "SpO2", "egfr": "eGFR", "psa": "PSA"}
FEMALE_ADJ = {"hb": (11.5, 15.5), "pcv": (36, 46), "uric": (2.5, 6.0)}
NUM = r"(-?\d+(?:[.,]\d+)?)"

FREQ = {r"\b(?:od|once daily|once a day|1-0-0|0-0-1|0-1-0|daily|hs|at night|bedtime)\b": "once a day",
        r"\b(?:bd|bid|twice (?:a )?daily|twice a day|1-0-1|1-1-0|0-1-1)\b": "twice a day",
        r"\b(?:tds|tid|thrice|three times|1-1-1)\b": "three times a day",
        r"\b(?:qid|four times|1-1-1-1)\b": "four times a day", r"\b(?:sos|prn|when (?:needed|required)|as needed)\b": "when needed",
        r"\b(?:weekly|once a week)\b": "once a week", r"\balternate day\b": "every other day"}
DUR = r"(?:x|for|×)\s*(\d+)\s*(day|days|wk|wks|week|weeks|month|months|mth)"
STRENGTH = r"(\d+(?:\.\d+)?)\s*(mg|mcg|µg|g|ml|iu|%)"
EXTRA_MEDS = ["amoxicillin", "amoxicillin-clavulanate", "azithromycin", "cefixime", "ciprofloxacin", "levofloxacin", "doxycycline", "metronidazole",
              "ofloxacin", "metformin", "glimepiride", "sitagliptin", "amlodipine", "telmisartan", "losartan", "atenolol", "metoprolol", "atorvastatin",
              "rosuvastatin", "aspirin", "clopidogrel", "pantoprazole", "omeprazole", "rabeprazole", "domperidone", "ondansetron", "cetirizine",
              "levocetirizine", "montelukast", "fexofenadine", "paracetamol", "ibuprofen", "diclofenac", "aceclofenac", "tramadol", "levothyroxine",
              "thyroxine", "salbutamol", "budesonide", "prednisolone", "dexamethasone", "folic acid", "ferrous", "iron", "calcium", "vitamin d3",
              "cholecalciferol", "methylcobalamin", "b-complex", "ors", "zinc", "albendazole", "chlorpheniramine", "ambroxol", "dextromethorphan",
              "insulin", "glipizide", "vildagliptin", "dapagliflozin", "empagliflozin", "hydrochlorothiazide", "furosemide", "spironolactone",
              "ursodeoxycholic", "ranitidine", "famotidine", "sucralfate", "nitrofurantoin", "fluconazole", "clotrimazole", "mupirocin", "betamethasone"]
RX_WORDS = {"amoxicillin", "amoxicillin-clavulanate", "azithromycin", "cefixime", "ciprofloxacin", "levofloxacin", "doxycycline", "metronidazole", "ofloxacin",
            "metformin", "glimepiride", "sitagliptin", "amlodipine", "telmisartan", "losartan", "atenolol", "metoprolol", "atorvastatin", "rosuvastatin",
            "clopidogrel", "tramadol", "levothyroxine", "thyroxine", "prednisolone", "dexamethasone", "insulin", "glipizide", "vildagliptin",
            "dapagliflozin", "empagliflozin", "hydrochlorothiazide", "furosemide", "spironolactone", "ursodeoxycholic", "nitrofurantoin", "fluconazole"}
TEST_WORDS = {"cbc": r"cbc|complete blood|h(?:ae|e)mogram", "lipid": r"lipid", "lft": r"\blft\b|liver function", "kft": r"\bkft\b|\brft\b|kidney function|renal",
              "hba1c": r"hba1c", "glu_f": r"fbs|fasting", "glu_pp": r"ppbs|post ?prandial", "thy": r"thyroid profile|t3.*t4|tft", "tsh": r"\btsh\b",
              "vitd": r"vitamin d|vit\.? d", "b12": r"b ?12", "urine": r"urine", "ecg": r"\becg\b|\bekg\b", "xray": r"x-?ray", "usg": r"ultrasound|usg|sonography",
              "echo": r"\becho\b|2d echo", "dengue": r"dengue|ns1", "malaria": r"malaria", "typhoid": r"typhoid|widal", "crp": r"\bcrp\b", "esr": r"\besr\b",
              "urea": r"\burea\b", "creat": r"creatinine", "uric": r"uric", "iron": r"ferritin|iron", "ogtt": r"ogtt|glucose tolerance", "psa": r"\bpsa\b",
              "hpylori": r"pylori", "pap": r"pap smear"}


def text_from(data: bytes, mime: str) -> str:
    if mime == "application/pdf" or data[:4] == b"%PDF":
        try:
            from pypdf import PdfReader
            r = PdfReader(io.BytesIO(data))
            return "\n".join((p.extract_text() or "") for p in r.pages[:12])
        except Exception:
            return ""
    if mime.startswith("text/"):
        return data.decode("utf-8", "ignore")
    return ""


def match_sku(name: str, hint: str = ""):
    """Catalogue item for a medicine name; `hint` (the surrounding text) picks syrup/drops/gel forms over tablets."""
    n = name.lower()
    liquid = bool(re.search(r"syp|syrup|susp|drops|gel|cream|oint|inhaler|spray", hint.lower()))
    cands = []
    for m in CATALOG:
        mn = m["name"].lower()
        if n == mn or n in mn or mn.split()[0] in n:
            cands.append(m)
    if not cands:
        return None
    def rank(m):
        mn = m["name"].lower()
        liq = bool(re.search(r"syrup|drops|gel|cream|ointment|inhaler|spray|suspension", mn + " " + m["form"].lower()))
        return (0 if liq == liquid else 1, 0 if mn == n else 1, len(mn))
    return sorted(cands, key=rank)[0]


def _flag(code, val, sex):
    lo, hi = LAB[code][2], LAB[code][3]
    if sex == "female" and code in FEMALE_ADJ:
        lo, hi = FEMALE_ADJ[code]
    if val < lo:
        return "low", f"{lo:g}–{hi:g}"
    if val > hi:
        return "high", f"{lo:g}–{hi:g}"
    return "normal", f"{lo:g}–{hi:g}"


def local_report(text: str, ctx: dict) -> dict:
    sex = (ctx or {}).get("sex", "")
    out, seen = [], set()
    for line in re.split(r"[\r\n]+", text):
        l = line.strip()
        if not l or len(l) > 200:
            continue
        for code, (rx, unit, lo, hi, plain) in LAB.items():
            if code in seen:
                continue
            m = re.search(rf"(?i)(?:{rx})[^0-9\-]{{0,40}}{NUM}", l)
            if not m:
                continue
            if code == "tc" and re.search(r"(?i)ldl|hdl", l):
                continue
            try:
                val = float(m.group(1).replace(",", "."))
            except ValueError:
                continue
            tail = l[m.end(): m.end() + 14].lower()
            if code in ("wbc", "plt"):
                if "lakh" in tail or "lac" in tail:
                    val *= 100000
                elif re.match(r"\s*(k\b|thousand|x ?10\^?3|×10)", tail) or val < 1000:
                    val *= 1000
            if code == "sbp":
                d = re.search(rf"{NUM}\s*/\s*{NUM}", l)
                if d:
                    val = float(d.group(1))
            flag, ref = _flag(code, val, sex)
            seen.add(code)
            out.append({"code": code, "test": CANON.get(code, code), "value": val, "unit": unit, "ref": ref, "flag": flag, "plain": plain})
    abn = [f for f in out if f["flag"] != "normal"]
    if out:
        summary = f"{len(out)} results read. " + (f"{len(abn)} outside the usual adult range: " + ", ".join(f"{f['test']} ({f['flag']})" for f in abn) + "." if abn else "All within the usual adult ranges.")
    else:
        summary = "No lab values could be read from this document. Photos and scanned PDFs need smart reading, which is not available right now. You can type the values instead."
    return {"summary": summary, "findings": out, "medicines": [], "tests_needed": [], "followups": _followups(out),
            "questions_for_doctor": [f"My {f['test']} is {f['flag']} at {f['value']:g} {f['unit']}: what does it mean for me?" for f in abn[:4]], "warnings": []}


def _followups(findings):
    f = {x["code"]: x for x in findings}
    out = []
    if f.get("hba1c", {}).get("flag") == "high" or f.get("glu_f", {}).get("flag") == "high":
        out.append({"code": "hba1c", "name": "HbA1c in 3 months", "why": "to see the sugar trend after diet or medicine changes"})
        out.append({"code": "kft", "name": "Kidney function and urine albumin", "why": "diabetes check-up tests"})
    if f.get("ldl", {}).get("flag") == "high" or f.get("tc", {}).get("flag") == "high":
        out.append({"code": "lipid", "name": "Lipid profile in 3–6 months", "why": "to see the effect of diet, exercise or statins"})
    if f.get("hb", {}).get("flag") == "low":
        out.append({"code": "iron", "name": "Iron studies (ferritin)", "why": "to find the cause of low haemoglobin"})
        out.append({"code": "b12", "name": "Vitamin B12", "why": "another common cause of anaemia"})
    if f.get("tsh", {}).get("flag") in ("high", "low"):
        out.append({"code": "thy", "name": "Thyroid profile (T3, T4, TSH)", "why": "to confirm the TSH change"})
    if f.get("creat", {}).get("flag") == "high":
        out.append({"code": "kft", "name": "Kidney function test with eGFR", "why": "to assess kidney filtration"})
    if f.get("alt", {}).get("flag") == "high" or f.get("ast", {}).get("flag") == "high":
        out.append({"code": "usg", "name": "Ultrasound abdomen", "why": "to look for fatty liver"})
    return out


def local_prescription(text: str, ctx: dict) -> dict:
    t = text.lower()
    meds, seen = [], set()
    names = sorted({m["name"].lower() for m in CATALOG} | set(EXTRA_MEDS), key=len, reverse=True)
    for n in names:
        for m in re.finditer(r"(?i)\b" + re.escape(n) + r"\b", t):
            key = n.split()[0]
            if key in seen:
                break
            seen.add(key)
            seg = t[m.start(): m.start() + 110]
            cut = re.search(r"\n|\.\s|;|\b(?:tab|cap|syp|inj|syr)\.?\s", seg[len(n):])
            if cut:
                seg = seg[: len(n) + cut.start()]
            st = re.search(STRENGTH, seg)
            fr = next((v for rx, v in FREQ.items() if re.search(rx, seg)), "")
            du = re.search(DUR, seg)
            sku = match_sku(n, t[max(0, m.start() - 8): m.start()] + seg)
            meds.append({"name": n.title(), "generic": n, "strength": (st.group(1) + " " + st.group(2)) if st else "", "frequency": fr,
                         "duration": (du.group(1) + " " + du.group(2)) if du else "", "instructions": "after food" if "after food" in seg or "a/f" in seg else "before food" if "before food" in seg or "b/f" in seg else "",
                         "sku": sku["id"] if sku else "", "rx": (sku["rx"] if sku else key in RX_WORDS)})
            break
    from .seed import TESTS
    tests = [{"code": c, "name": TESTS.get(c, (c,))[0], "why": "written on the prescription"} for c, rx in TEST_WORDS.items() if re.search(rx, t)]
    summary = (f"{len(meds)} medicine{'s' if len(meds) != 1 else ''} and {len(tests)} test{'s' if len(tests) != 1 else ''} found on this prescription."
               if meds or tests else "No medicines or tests could be read. Photos of handwritten prescriptions need smart reading, which is not available right now; you can also type the medicine names.")
    return {"summary": summary, "findings": [], "medicines": meds, "tests_needed": tests, "followups": [], "questions_for_doctor": [], "warnings": []}


# ---------------------------------------------------------------------------------------------------------------------
CLAUDE_SYSTEM = """You read Indian medical documents for a family health app. Output ONLY a JSON object, no prose, with keys:
summary (string, 1-3 plain sentences), findings (array of {test, value (number or string), unit, ref (string, lab's own range if printed), flag (low|normal|high|unknown), plain (one friendly sentence explaining what it measures and what the value may mean), code (one of: hb,wbc,plt,glu_f,glu_pp,glu_r,hba1c,tc,ldl,hdl,tg,alt,ast,alp,bili,alb,creat,urea,uric,na,k,ca,tsh,t3,t4,vitd,b12,ferr,crp,esr,rbc,mcv,pcv,sbp,spo2,egfr,psa or "" )}),
medicines (array of {name, generic, strength, form, frequency, duration, instructions, rx (true if prescription-only in India)}), tests_needed (array of {code (one of: cbc,lipid,lft,kft,hba1c,glu_f,glu_pp,thy,tsh,vitd,b12,urine,ecg,xray,usg,echo,dengue,malaria,typhoid,crp,esr,urea,creat,uric,iron,ogtt,psa,hpylori,pap or ""), name, why}),
followups (array of {code,name,why}: tests worth repeating or adding, phrased as suggestions to discuss), questions_for_doctor (array of 2-5 strings in the patient's voice), warnings (array of strings: interactions with the patient's listed medicines/allergies/pregnancy, or urgent-looking values), doctor (string: prescriber name and date if printed, else ""), patient_match (boolean: does the name/age/sex on the document match the context?),
focus (array of 0-3 body areas this document is about, for the 3D body, from exactly: heart, lungs, liver, kidneys, pancreas, thyroid, stomach, intestines, brain, spleen, bones, spine, uterus, prostate, bladder, breast, skin, eyes, blood, whole_body).
Rules: never diagnose; say "suggests" and "discuss with your doctor". Use the document's printed reference range when present. Mark HbA1c>=6.5, fasting glucose>=126, platelets<100000, potassium>5.5 or <3, sodium<130, creatinine>1.5, haemoglobin<8, SpO2<92 as warnings. Flag any medicine that is unsafe in pregnancy if the context says pregnant. If the document is unreadable, say so in summary and return empty arrays."""


POLICY_SYSTEM = """You read an Indian health insurance policy document (schedule, policy wording, welcome kit or e-card with terms) for a family health app, so the family knows what they are covered for before a hospital visit. Output ONLY a JSON object:
{"readable": boolean, "insurer": string, "plan_name": string, "policy_number": string, "policy_type": one of "individual"|"floater"|"corporate"|"top_up"|"critical_illness"|"other",
"sum_insured": number in rupees or null, "valid_from": "YYYY-MM-DD" or "", "valid_to": "YYYY-MM-DD" or "", "members_covered": [names], "holder": string,
"room_rent": string (limit or "no limit", as written), "icu_limit": string, "copay": string (e.g. "10% above age 60" or "none"), "deductible": string,
"waiting_initial_days": integer or null, "waiting_specific_months": integer or null (specific diseases), "waiting_ped_months": integer or null (pre-existing diseases),
"maternity": string (covered / not covered / limit and waiting), "daycare": boolean or null, "pre_post_hospitalisation": string (e.g. "30 / 60 days"), "ambulance": string,
"restoration": string, "no_claim_bonus": string, "exclusions": [up to 10 short strings], "network_url": string, "claim_helpline": string, "tpa": string, "tpa_phone": string,
"cashless_steps": [up to 5 short strings: how to get cashless admission under this policy], "plain_summary": string (3-5 sentences in plain English for the family: what is covered, the main limits, and the one thing to watch), "text": up to 800 chars of key legible text}.
Rules: copy numbers exactly; "" or null when not printed; never guess; no advice beyond what the document says."""


def claude_policy(data: bytes | None, mime: str, text: str) -> dict:
    content = []
    if data:
        if mime == "application/pdf" or data[:4] == b"%PDF":
            content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(data).decode()}})
        elif mime.startswith("image/"):
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()}})
    if text:
        content.append({"type": "text", "text": "Document text:\n" + text[:14000]})
    content.append({"type": "text", "text": "Return the JSON now."})
    r = create(max_tokens=3000, system=POLICY_SYSTEM, messages=[{"role": "user", "content": content}])
    raw = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    out = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    out["usage"] = {"in": r.usage.input_tokens, "out": r.usage.output_tokens}
    return out


def analyze_policy(data: bytes | None, mime: str, text: str) -> dict:
    t0 = time.time()
    if not available():
        return {"engine": "local", "kind": "policy", "readable": False, "ms": 0, "warnings": ["Policy reading needs the smart reader, which is not available right now. Enter the key terms yourself."]}
    try:
        out = claude_policy(data, mime, text)
    except Exception as e:
        _fail("policy reading", e)
        raise
    out.update({"engine": "claude", "kind": "policy", "model": current_model(), "ms": int((time.time() - t0) * 1000), "warnings": []})
    return out


MEDCHECK_SYSTEM = """You are the medicine-safety check inside TheHealthTracker, an Indian family health app. Input: one person's current medicines (names, strengths, how often), allergies, conditions, age, sex, pregnancy/breastfeeding, and recent kidney/liver values when present. Output ONLY a JSON object:
{"alerts": [0-8 of {"level": "stop"|"ask"|"note", "about": [medicine names involved], "title": max 10 words, "detail": 1-2 plain sentences on what the concern is and what to do (ask the doctor/pharmacist; never tell them to stop a prescribed medicine yourself unless it is an allergy to a listed allergen, then say stop and call the doctor)}],
"duplicates": [{"ingredient": string, "medicines": [names]}] (same active ingredient under two brands, or two drugs of the same class doing the same job),
"timing": [0-4 short strings: practical timing tips, e.g. "Take levothyroxine on an empty stomach, 30-60 min before breakfast; keep calcium and iron 4 hours away"],
"ok": boolean (true when there is nothing above "note")}.
Rules: Indian brand names are common — map them to generics (e.g. Dolo = paracetamol, Glycomet = metformin, Telma = telmisartan, Ecosprin = aspirin, Pan = pantoprazole). Flag: allergy matches, known serious interactions, duplicate ingredients (e.g. two paracetamol combinations), NSAIDs with reduced kidney function or with anticoagulants, metformin with creatinine > 1.5, pregnancy-unsafe medicines when pregnant, doses in children only as "ask". Never diagnose. No vendor or model names."""


def medcheck(ctx: dict) -> dict:
    r = create(max_tokens=1800, system=MEDCHECK_SYSTEM, messages=[{"role": "user", "content": json.dumps(ctx, ensure_ascii=False)[:8000] + "\n\nReturn the JSON now."}])
    raw = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    out = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    alerts = []
    for a in (out.get("alerts") or [])[:8]:
        if not isinstance(a, dict):
            continue
        alerts.append({"level": a.get("level") if a.get("level") in ("stop", "ask", "note") else "note", "about": [str(x)[:60] for x in (a.get("about") or [])][:4],
                       "title": str(a.get("title", ""))[:80], "detail": str(a.get("detail", ""))[:400]})
    return {"alerts": alerts, "duplicates": [{"ingredient": str(d.get("ingredient", ""))[:60], "medicines": [str(x)[:60] for x in (d.get("medicines") or [])][:4]} for d in (out.get("duplicates") or [])[:6] if isinstance(d, dict)],
            "timing": [str(x)[:200] for x in (out.get("timing") or [])][:4], "ok": not any(a["level"] != "note" for a in alerts)}


def claude_analyze(kind: str, data: bytes | None, mime: str, text: str, ctx: dict) -> dict:
    content = []
    if data:
        if mime == "application/pdf" or data[:4] == b"%PDF":
            content.append({"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(data).decode()}})
        elif mime.startswith("image/"):
            content.append({"type": "image", "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()}})
    if text:
        content.append({"type": "text", "text": "Document text:\n" + text[:12000]})
    content.append({"type": "text", "text": f"Document kind: {kind}. Patient context (from the app, may be incomplete): {json.dumps(ctx)[:1500]}. Return the JSON now."})
    try:
        r = create(max_tokens=8000, system=CLAUDE_SYSTEM, messages=[{"role": "user", "content": content}])
    except Exception as e:
        imgs = pdf_pages_as_images(data) if data and (mime == "application/pdf" or data[:4] == b"%PDF") else []
        if not imgs:
            raise
        _fail("pdf document block (retrying as images)", e)
        content = [{"type": "image", "source": {"type": "base64", "media_type": "image/jpeg", "data": base64.b64encode(b).decode()}} for b in imgs] + content[1:]
        r = create(max_tokens=8000, system=CLAUDE_SYSTEM, messages=[{"role": "user", "content": content}])
    raw = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    raw = raw[raw.find("{"): raw.rfind("}") + 1]
    out = json.loads(raw)
    for m in out.get("medicines", []):
        sku = match_sku(m.get("generic") or m.get("name") or "", (m.get("form") or "") + " " + (m.get("name") or ""))
        m["sku"] = sku["id"] if sku else ""
        if sku:
            m["rx"] = bool(m.get("rx", False) or sku["rx"])
    for f in out.get("findings", []):
        if isinstance(f.get("value"), str):
            try:
                f["value"] = float(re.sub(r"[^\d.\-]", "", f["value"]))
            except ValueError:
                pass
    out["usage"] = {"in": r.usage.input_tokens, "out": r.usage.output_tokens}
    return out

CARD_SYSTEM = """You read a photo or scan of an Indian health-related card for a family health app: a health insurance card (individual, family floater, corporate/employer group policy or TPA card), a government scheme card (Ayushman Bharat PM-JAY, state schemes such as Aarogyasri, CGHS, ECHS, ESIC, EHS), an ABHA (Ayushman Bharat Health Account) card, or a hospital membership card. Output ONLY a JSON object with keys:
kind (one of: insurance, corporate, scheme, abha, hospital, other), readable (boolean), confidence (0-1),
fields: {holder_name, insurer, plan_name, policy_number, member_id, employer, employee_id, tpa, tpa_phone, insurer_phone, sum_insured (string as printed, e.g. "5,00,000"), valid_from (YYYY-MM-DD or ""), valid_to (YYYY-MM-DD or ""), scheme_name, card_number, abha_number (14 digits, formatted 12-3456-7890-1234 if printed), abha_address, date_of_birth (YYYY-MM-DD or ""), sex, blood_group, members_covered (array of names), hospital, notes (anything else important, one line)},
text (all legible text on the card, in reading order, max 1200 chars).
Rules: copy numbers exactly; leave a field "" when not printed; never guess; dates in ISO form; do not include anything that is not on the card."""


def claude_card(data: bytes, mime: str) -> dict:
    import anthropic

    client = anthropic.Anthropic()
    if mime == "application/pdf" or data[:4] == b"%PDF":
        src = {"type": "document", "source": {"type": "base64", "media_type": "application/pdf", "data": base64.b64encode(data).decode()}}
    else:
        src = {"type": "image", "source": {"type": "base64", "media_type": mime, "data": base64.b64encode(data).decode()}}
    r = create(max_tokens=4000, system=CARD_SYSTEM,
                               messages=[{"role": "user", "content": [src, {"type": "text", "text": "Read this card and return the JSON now."}]}])
    raw = "".join(b.text for b in r.content if getattr(b, "type", "") == "text").strip()
    out = json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
    out.setdefault("fields", {})
    out["usage"] = {"in": r.usage.input_tokens, "out": r.usage.output_tokens}
    return out


def analyze_card(data: bytes | None, mime: str) -> dict:
    """Cards are read only by the smart reader; without it the app offers manual entry."""
    t0 = time.time()
    if not data:
        return {"engine": "local", "kind": "card", "readable": False, "fields": {}, "warnings": ["No file was received."], "ms": 0}
    if not available():
        return {"engine": "local", "kind": "card", "readable": False, "fields": {}, "warnings": ["Smart reading is not available right now. Fill in the details yourself; the photo is kept with the card."], "ms": 0}
    try:
        out = claude_card(data, mime)
    except Exception as e:
        _fail("card reading", e)
        return {"engine": "local", "kind": "card", "readable": False, "fields": {}, "warnings": ["Smart reading could not read this card right now. Fill in the details yourself; the photo is kept with the card."], "ms": int((time.time() - t0) * 1000)}
    out.update({"engine": "claude", "kind": "card", "ms": int((time.time() - t0) * 1000)})
    out.setdefault("warnings", [])
    return out


def test_connection() -> dict:
    """Admin check: can this server reach the smart reader? Returns ok or the exact error, never shown to users."""
    if not available():
        return {"ok": False, "error": "No AI key is set on this server (GEMINI_API_KEY or ANTHROPIC_API_KEY)."}
    try:
        import anthropic
    except ImportError:
        return {"ok": False, "error": "The anthropic package is not installed (requirements.txt)."}
    t0 = time.time()
    try:
        r = create(max_tokens=5, messages=[{"role": "user", "content": "Reply with OK"}])
        return {"ok": True, "model": current_model(), "ms": int((time.time() - t0) * 1000), "reply": "".join(b.text for b in r.content if getattr(b, "type", "") == "text")[:20]}
    except Exception as e:
        _fail("test connection", e)
        return {"ok": False, "model": MODEL, "error": f"{type(e).__name__}: {str(e)[:400]}"}


def analyze(kind: str, data: bytes | None, mime: str, text: str, ctx: dict, force_local: bool = False) -> dict:
    t0 = time.time()
    engine = "claude" if available() and not force_local else "local"
    out = None
    if engine == "claude":
        try:
            out = claude_analyze(kind, data, mime, text, ctx)
        except Exception as e:  # fall back rather than fail the user
            out = None
            engine = "local"
            err = str(e)[:160]
            _fail("smart reading (basic reader used)", e)
    if out is None:
        txt = text or (text_from(data, mime) if data else "")
        if not txt and data and mime.startswith("image/"):
            out = {"summary": "Reading photos is not available right now. Upload a PDF with selectable text, or type the values.",
                   "findings": [], "medicines": [], "tests_needed": [], "followups": [], "questions_for_doctor": [], "warnings": []}
        else:
            out = local_prescription(txt, ctx) if kind == "prescription" else local_report(txt, ctx)
        if "err" in locals():
            out["warnings"] = list(out.get("warnings", [])) + ["Smart reading is unavailable right now; this is the basic reader."]
    out.update({"engine": engine, "kind": kind, "model": current_model() if engine == "claude" else "rules-v1", "ms": int((time.time() - t0) * 1000), "disclaimer": DISCLAIMER})
    out.setdefault("findings", [])
    out.setdefault("medicines", [])
    out.setdefault("tests_needed", [])
    out.setdefault("followups", [])
    out.setdefault("questions_for_doctor", [])
    out.setdefault("warnings", [])
    out["focus"] = [str(x) for x in (out.get("focus") or []) if str(x) in FOCUS][:3]
    return out
