"""The assistant that acts before it is asked: daily nudges and the weekly family report.

Every morning (08:00–09:00 IST) the server opens each family's encrypted record once, works out what is due — a repeat
test for a result that was out of range, a vaccine the schedule says is due, a policy about to lapse, a pregnancy
milestone, a care-plan review, a reading that has drifted — and writes at most three notices (each with a push), each
once. On Monday mornings it adds the weekly report: trends per person over the last four weeks against the four before,
blood-pressure control, medicine adherence, pregnancy weight gain against the IOM ranges, and anomalies.

Everything here is computed from the record in plain Python, so it costs nothing and works without the AI key; the
health assistant only writes the two-sentence narrative on top of the weekly report when the key is present.
"""
from __future__ import annotations

import json
import os
import statistics
import threading
import time
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from . import ai as AI
from .db import get_db, session
from .family import decrypt
from .inbox import notify
from .models import AiCache, Household, HouseholdState, ReminderSent, now
from .routes import household

r = APIRouter(prefix="/api/v1")
IST = timezone(timedelta(hours=5, minutes=30))
MAX_NUDGES_PER_DAY = 3

# how soon a flagged result deserves a repeat (days), by lab key; a normal result is not nagged
REPEAT_DAYS = {"hba1c": 90, "glu_f": 90, "glu_pp": 90, "glu_r": 60, "tc": 180, "ldl": 180, "hdl": 180, "tg": 180, "tsh": 90, "t3": 90, "t4": 90,
               "creat": 180, "urea": 180, "uric": 180, "alt": 180, "ast": 180, "bili": 90, "hb": 120, "ferr": 120, "vitd": 180, "b12": 180, "crp": 30, "plt": 14, "wbc": 30}
LAB_NAME = {"hba1c": "HbA1c", "glu_f": "fasting sugar", "glu_pp": "post-meal sugar", "glu_r": "random sugar", "tc": "total cholesterol", "ldl": "LDL cholesterol",
            "hdl": "HDL cholesterol", "tg": "triglycerides", "tsh": "TSH", "t3": "T3", "t4": "T4", "creat": "creatinine", "urea": "urea", "uric": "uric acid", "alt": "SGPT (ALT)",
            "ast": "SGOT (AST)", "bili": "bilirubin", "hb": "haemoglobin", "ferr": "ferritin", "vitd": "vitamin D", "b12": "vitamin B12", "crp": "CRP", "plt": "platelets", "wbc": "white cells"}
# pregnancy milestones by completed week → what is usually due (Indian antenatal practice; FOGSI / MoHFW schedule)
PREG_WEEKS = {8: "First antenatal visit: register the pregnancy, blood group, haemoglobin, sugar, thyroid, HIV/HBsAg, urine; start folic acid.",
              11: "Week 11–13: NT scan and double-marker (first-trimester screening) are due this fortnight.",
              14: "Second trimester starts. Iron and calcium usually begin now; ask about the Tdap timing.",
              18: "Week 18–22: the anomaly (TIFFA) scan is due. Book it this fortnight.",
              24: "Week 24–28: glucose challenge (GTT), repeat haemoglobin; register for the hospital's birthing classes.",
              27: "Week 27–36: Tdap vaccine window. Start counting kicks daily from week 28.",
              32: "Week 32: growth scan and blood pressure check; discuss the birth plan and the hospital bag.",
              36: "Week 36: weekly visits start. GBS swab where offered; confirm the baby's position with the doctor.",
              38: "Full term is close. Know the signs of labour and when to go in; keep the hospital documents in Cards ready."}
IOM_GAIN = {"under": (12.5, 18.0), "normal": (11.5, 16.0), "over": (7.0, 11.5), "obese": (5.0, 9.0)}  # total kg at term by pre-pregnancy BMI class


def _d(s: str) -> date | None:
    try:
        return date.fromisoformat(str(s)[:10])
    except Exception:
        return None


def _first(name: str) -> str:
    return (name or "").split(" ")[0] or "Someone"


def _age_weeks(m: dict, today: date) -> float | None:
    d = _d(m.get("dob") or "")
    if not d:
        return None
    return (today - d).days / 7


def _lab_series(state: dict, mid: str) -> dict[str, list[dict]]:
    out: dict[str, list[dict]] = {}
    for x in ((state.get("results") or {}).get(mid) or []):
        if x.get("k") == "lab" and x.get("key") and isinstance(x.get("val"), (int, float)) and _d(x.get("date", "")):
            out.setdefault(x["key"], []).append(x)
    for k in out:
        out[k].sort(key=lambda x: x["date"])
    return out


def _flag(key: str, val: float, sex: str) -> str:
    lab = AI.LAB.get(key)
    if not lab:
        return "normal"
    lo, hi = lab[2], lab[3]
    if sex == "female" and key in AI.FEMALE_ADJ:
        lo, hi = AI.FEMALE_ADJ[key]
    return "low" if val < lo else "high" if val > hi else "normal"


# ---- daily nudges -----------------------------------------------------------------------------------------------------------
def _day_of(v: dict) -> str:
    return datetime.fromtimestamp(v["t"] / 1000, IST).strftime("%Y-%m-%d")


def _fasting(v: dict) -> bool:
    """A reading marked fasting, or an unmarked one taken before 10:00 (the usual fasting slot)."""
    gt = str(v.get("gt") or "").lower()
    if gt:
        return gt.startswith("fast")
    return datetime.fromtimestamp(v["t"] / 1000, IST).hour < 10


PATTERN_RULES = (
    # field, label, test on one reading, minimum days with readings, share of those days, what to say
    ("sys", "blood pressure", lambda v: isinstance(v.get("sys"), (int, float)) and isinstance(v.get("dia"), (int, float)) and (v["sys"] >= 140 or v["dia"] >= 90), 3, 0.6,
     "was 140/90 or above on {days} of the {of} days with a reading this week. Worth a word with the doctor; keep measuring at the same time each day, seated, after 5 minutes of rest."),
    ("glu", "fasting sugar", lambda v: isinstance(v.get("glu"), (int, float)) and _fasting(v) and v["glu"] > 130, 3, 0.6,
     "was above 130 mg/dL on {days} of the {of} days with a fasting reading this week. Mention it to the doctor before the next visit; do not change medicine doses on your own."),
    ("spo2", "oxygen level", lambda v: isinstance(v.get("spo2"), (int, float)) and v["spo2"] < 94, 2, 0.5,
     "was below 94% on {days} of the {of} days with a reading this week. If there is breathlessness or it drops below 90%, call a doctor today."),
    ("hr", "resting heart rate", lambda v: isinstance(v.get("hr"), (int, float)) and v["hr"] > 100, 3, 0.6,
     "was above 100 bpm on {days} of the {of} days with a reading this week. Fever, dehydration, thyroid and some medicines can do this; worth a check."),
)


def patterns(week: list[dict], first: str) -> list[dict]:
    """Readings from the last 7 days → day-counted patterns a family would notice if they kept a diary."""
    out = []
    for field, label, test, min_days, share, text in PATTERN_RULES:
        days_with = sorted({_day_of(v) for v in week if isinstance(v.get(field), (int, float))})
        flagged = sorted({_day_of(v) for v in week if test(v)})
        if len(days_with) >= min_days and len(flagged) >= min_days and len(flagged) / len(days_with) >= share:
            out.append({"field": field, "days": len(flagged), "of": len(days_with), "title": f"{first}: {label} high this week",
                        "body": f"{first}'s {label} " + text.format(days=len(flagged), of=len(days_with))})
    return out


def nudges(state: dict, today: date) -> list[dict]:
    """What the family should hear this morning. Each item: key (dedupe), kind, title, body, member, url."""
    out: list[dict] = []
    members = state.get("members") or []
    for m in members:
        mid, first = m.get("id", ""), _first(m.get("name", ""))
        sex = m.get("sex") or ""
        # 1. repeat tests for results that were out of range
        for key, series in _lab_series(state, mid).items():
            last = series[-1]
            if _flag(key, float(last["val"]), sex) == "normal" or key not in REPEAT_DAYS:
                continue
            days = (today - _d(last["date"])).days
            if days >= REPEAT_DAYS[key]:
                out.append({"key": f"repeat:{mid}:{key}:{today.strftime('%Y-%m')}", "kind": "nudge_test", "member": mid,
                            "title": f"{first}: time to repeat {LAB_NAME.get(key, key)}",
                            "body": f"The last {LAB_NAME.get(key, key)} ({last['val']:g} on {_d(last['date']).strftime('%d/%m/%Y')}) was outside the usual range and is {days} days old. Book it from Nearby labs; the new result goes straight onto the body.",
                            "url": "/app#page=nearlabs", "ref": {"member": mid, "lab": key}})
        # 2. pregnancy milestones (by completed week, once per week)
        preg = ((state.get("preg") or {}).get(mid) or {})
        lmp = _d(preg.get("lmp") or "")
        if lmp:
            wk = (today - lmp).days // 7
            if wk in PREG_WEEKS:
                out.append({"key": f"preg:{mid}:{wk}", "kind": "nudge_preg", "member": mid, "title": f"{first}: week {wk} of pregnancy",
                            "body": PREG_WEEKS[wk], "url": "/app#page=preg", "ref": {"member": mid, "week": wk}})
        # 3. vaccines due for children (national schedule in the app: age window in weeks or months)
        age_w = _age_weeks(m, today)
        if age_w is not None and age_w < 16 * 52:
            given = (state.get("vax") or {}).get(mid) or {}
            due = []
            for v in VAX:
                code, name, _label, lo, hi, unit, _opt = v[:7]
                if code in given:
                    continue
                lo_w = lo if unit == "w" else lo * 52 / 12 if unit == "m" else lo * 52
                hi_w = hi if unit == "w" else hi * 52 / 12 if unit == "m" else hi * 52
                if lo_w <= age_w <= hi_w + 2:
                    due.append(name)
            if due:
                out.append({"key": f"vax:{mid}:{today.strftime('%Y-%m')}", "kind": "nudge_vax", "member": mid, "title": f"{first}: vaccines due now",
                            "body": ", ".join(due[:4]) + (f" and {len(due) - 4} more" if len(due) > 4 else "") + ". Book at your paediatrician or the nearest government centre (free under UIP).",
                            "url": "/app#page=vax", "ref": {"member": mid, "due": due[:8]}})
        # 3b. a child has turned 18: their records are theirs now — hand over with their own sign-in
        if age_w is not None and 18 * 52.18 <= age_w <= 18 * 52.18 + 5:
            out.append({"key": f"adult:{mid}", "kind": "nudge_handover", "member": mid, "title": f"{first} is 18 — hand over the records",
                        "body": f"Invite {first} to their own sign-in from Family → Accounts. Their profile, results and documents move with them, and they decide what the family still sees.",
                        "url": "/app#page=family", "ref": {"member": mid}})
        # 4. readings drifting (last 7 days of BP / sugar against the 30 before)
        vit = sorted([v for v in ((state.get("vitals") or {}).get(mid) or []) if isinstance(v.get("t"), (int, float))], key=lambda v: v["t"])
        if vit:
            t_now = datetime.combine(today, datetime.min.time(), IST).timestamp() * 1000
            recent = [v for v in vit if v["t"] >= t_now - 7 * 86400000]
            before = [v for v in vit if t_now - 37 * 86400000 <= v["t"] < t_now - 7 * 86400000]
            for fld, label, unit, thresh in (("sys", "systolic BP", "mmHg", 10), ("glu", "sugar", "mg/dL", 25)):
                a = [v[fld] for v in recent if isinstance(v.get(fld), (int, float))]
                b = [v[fld] for v in before if isinstance(v.get(fld), (int, float))]
                if len(a) >= 3 and len(b) >= 3 and statistics.mean(a) - statistics.mean(b) >= thresh:
                    out.append({"key": f"drift:{mid}:{fld}:{today.isocalendar()[1]}", "kind": "nudge_drift", "member": mid,
                                "title": f"{first}: {label} is running higher",
                                "body": f"Average {label} this week {statistics.mean(a):.0f} {unit} vs {statistics.mean(b):.0f} before. Ask the health assistant what changed, and mention it to the doctor.",
                                "url": "/app#page=assist", "ref": {"member": mid, "field": fld}})
        # 4b. patterns over the last 7 days, counted in days ("high on 5 of the 6 days with readings"), one per week
        if vit:
            t_now = datetime.combine(today, datetime.min.time(), IST).timestamp() * 1000
            week = [v for v in vit if v["t"] >= t_now - 7 * 86400000]
            for p in patterns(week, first):
                out.append({"key": f"pattern:{mid}:{p['field']}:{today.isocalendar()[1]}", "kind": "nudge_drift", "member": mid, "title": p["title"], "body": p["body"],
                            "url": "/app#page=assist", "ref": {"member": mid, "field": p["field"], "days": p["days"], "of": p["of"]}})
    # 5. health cover about to lapse
    for c in state.get("cards") or []:
        f = c.get("f") or {}
        exp = _d(f.get("valid_to") or "")
        if exp and 0 <= (exp - today).days <= 30:
            name = f.get("insurer") or f.get("scheme_name") or f.get("employer") or "Health cover"
            out.append({"key": f"policy:{c.get('id')}:{exp.isoformat()}", "kind": "nudge_policy", "member": c.get("member") or "",
                        "title": f"{name} renews in {(exp - today).days} days",
                        "body": f"Valid till {exp.strftime('%d/%m/%Y')}. Renew before it lapses so the waiting periods carry over; keep the renewed card in Cards.",
                        "url": "/app#page=cards", "ref": {"card": c.get("id")}})
    # 6. care plan review (every 30 days while hyper-care is on)
    care = state.get("care") or {}
    for mid, plan in care.items():
        if not isinstance(plan, dict) or not plan.get("on"):
            continue
        rev = _d(plan.get("review") or "")
        since = plan.get("reviewed") or plan.get("t") or 0
        due = (rev is not None and rev <= today) or (not rev and since and time.time() * 1000 - since > 30 * 86400000)
        if due:
            m = next((x for x in members if x.get("id") == mid), None)
            out.append({"key": f"care:{mid}:{today.strftime('%Y-%m')}", "kind": "nudge_care", "member": mid,
                        "title": f"Review {_first((m or {}).get('name', ''))}'s care plan", "body": "It is a month since the plan was last reviewed. Tick what still applies and drop what does not.",
                        "url": "/app#page=careplan", "ref": {"member": mid}})
    return out


try:  # the app's vaccine schedule, read from the single-file app so the two never disagree
    import re
    from pathlib import Path

    _src = (Path(__file__).resolve().parents[1] / "web" / "index.html").read_text(encoding="utf-8")
    _m = re.search(r"const VAX=\[(.*?)\];", _src, re.S)
    VAX = json.loads("[" + _m.group(1).replace("'", '"') + "]") if _m else []
    VAX = [v for v in VAX if isinstance(v, list) and len(v) >= 7]
except Exception:  # pragma: no cover
    VAX = []


# ---- weekly report ----------------------------------------------------------------------------------------------------------
def _slope(points: list[tuple[float, float]]) -> float:
    """Least-squares slope per day."""
    if len(points) < 3:
        return 0.0
    xs, ys = [p[0] for p in points], [p[1] for p in points]
    mx, my = statistics.mean(xs), statistics.mean(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else 0.0


def weekly(state: dict, today: date) -> dict:
    """Four weeks against the four before, per person. Pure, no network."""
    t_end = datetime.combine(today, datetime.min.time(), IST).timestamp() * 1000
    t_mid, t_start = t_end - 28 * 86400000, t_end - 56 * 86400000
    people = []
    for m in state.get("members") or []:
        mid = m.get("id", "")
        vit = sorted([v for v in ((state.get("vitals") or {}).get(mid) or []) if isinstance(v.get("t"), (int, float)) and t_start <= v["t"] < t_end], key=lambda v: v["t"])
        cur = [v for v in vit if v["t"] >= t_mid]
        prev = [v for v in vit if v["t"] < t_mid]
        series = []
        for fld, label, unit, lo, hi in (("sys", "Systolic BP", "mmHg", 90, 140), ("dia", "Diastolic BP", "mmHg", 60, 90), ("glu", "Blood sugar", "mg/dL", 70, 140),
                                         ("hr", "Resting heart rate", "bpm", 50, 100), ("spo2", "SpO₂", "%", 94, 100), ("w", "Weight", "kg", 0, 10 ** 6)):
            a = [v for v in cur if isinstance(v.get(fld), (int, float))]
            b = [v[fld] for v in prev if isinstance(v.get(fld), (int, float))]
            if not a:
                continue
            vals = [v[fld] for v in a]
            mean_a = statistics.mean(vals)
            slope = _slope([((v["t"] - t_mid) / 86400000, v[fld]) for v in a]) * 7  # per week
            entry = {"field": fld, "label": label, "unit": unit, "n": len(vals), "mean": round(mean_a, 1), "min": min(vals), "max": max(vals),
                     "perWeek": round(slope, 1), "inRange": round(100 * sum(lo <= x <= hi for x in vals) / len(vals)),
                     "previous": round(statistics.mean(b), 1) if b else None, "change": round(mean_a - statistics.mean(b), 1) if b else None}
            series.append(entry)
        bp = [v for v in cur if isinstance(v.get("sys"), (int, float)) and isinstance(v.get("dia"), (int, float))]
        bp_control = round(100 * sum(v["sys"] < 140 and v["dia"] < 90 for v in bp) / len(bp)) if bp else None
        adh = (state.get("adh") or {}).get(mid) or {}
        days = [(d, x) for d, x in adh.items() if _d(d) and (today - _d(d)).days <= 28 and isinstance(x, dict) and x.get("total")]
        adherence = round(100 * sum(min(x.get("done", 0), x["total"]) for _, x in days) / sum(x["total"] for _, x in days)) if days else None
        labs = []
        for key, s in _lab_series(state, mid).items():
            last = s[-1]
            if (today - _d(last["date"])).days <= 28:
                labs.append({"key": key, "name": LAB_NAME.get(key, key), "value": last["val"], "date": last["date"], "flag": _flag(key, float(last["val"]), m.get("sex") or ""),
                             "previous": s[-2]["val"] if len(s) > 1 else None})
        preg = ((state.get("preg") or {}).get(mid) or {})
        preg_out = None
        lmp = _d(preg.get("lmp") or "")
        if lmp:
            wk = (today - lmp).days // 7
            h = m.get("h")
            wts = [v for v in sorted(((state.get("vitals") or {}).get(mid) or []), key=lambda v: v.get("t", 0)) if isinstance(v.get("w"), (int, float)) and isinstance(v.get("t"), (int, float))]
            wnow = wts[-1]["w"] if wts else m.get("w")
            lmp_ms = datetime.combine(lmp, datetime.min.time(), IST).timestamp() * 1000
            base = [v for v in wts if v["t"] <= lmp_ms + 14 * 86400000]
            w0 = preg.get("w0") or (base[-1]["w"] if base else None)
            preg_out = {"week": wk, "weight": wnow}
            if w0 and h and wnow:
                bmi = w0 / ((h / 100) ** 2)
                cls = "under" if bmi < 18.5 else "normal" if bmi < 25 else "over" if bmi < 30 else "obese"
                lo, hi = IOM_GAIN[cls]
                frac = min(1.0, max(0.0, (wk - 13) / 27)) if wk > 13 else 0.0  # most gain is after the first trimester
                preg_out.update({"gain": round(wnow - w0, 1), "expected": [round(1 + lo * frac if wk > 13 else 0, 1), round(2 + hi * frac if wk > 13 else 2, 1)], "bmiClass": cls})
        anomalies = []
        for v in cur:
            if isinstance(v.get("sys"), (int, float)) and (v["sys"] >= 180 or (isinstance(v.get("dia"), (int, float)) and v["dia"] >= 120)):
                anomalies.append({"t": v["t"], "what": f"BP {v['sys']}/{v.get('dia', '')} mmHg"})
            if isinstance(v.get("glu"), (int, float)) and (v["glu"] < 70 or v["glu"] > 300):
                anomalies.append({"t": v["t"], "what": f"Sugar {v['glu']} mg/dL"})
            if isinstance(v.get("spo2"), (int, float)) and v["spo2"] < 92:
                anomalies.append({"t": v["t"], "what": f"SpO₂ {v['spo2']}%"})
        people.append({"id": mid, "name": m.get("name", ""), "series": series, "bpControl": bp_control, "adherence": adherence, "labs": labs, "pregnancy": preg_out,
                       "anomalies": anomalies[-5:], "readings": len(cur)})
    return {"from": (today - timedelta(days=28)).isoformat(), "to": today.isoformat(), "people": people}


def narrate(report: dict, lang: str = "en") -> str:
    if not AI.available():
        return ""
    system = ("You write the two-to-four sentence opening of a weekly family health report for TheHealthTracker (India). Input is JSON computed from the "
              "family's own readings: per person, 4-week means with change vs the previous 4 weeks, % in range, BP control %, medicine adherence %, recent "
              "lab values with flags, pregnancy week and weight gain against the expected range, anomalies. Say what is going well first, then the one or two "
              "things to act on, with numbers. Never diagnose, never change doses, never mention AI or vendors. Plain text, no headings, no markdown. "
              f"Write in {'Hindi' if lang == 'hi' else 'Telugu' if lang == 'te' else 'English'}; keep medical terms in English.")
    try:
        res = AI.create(max_tokens=400, system=system, messages=[{"role": "user", "content": json.dumps(report, ensure_ascii=False)[:12000]}])
        return "".join(b.text for b in res.content if getattr(b, "type", "") == "text").strip()[:1200]
    except Exception as e:
        AI._fail("weekly report", e)
        return ""


@r.get("/report/weekly")
def weekly_report(lang: str = "en", db: Session = Depends(get_db), x_dokko_key: str | None = Header(None)):
    """The family's weekly report, computed from the encrypted record on request (cached for the day)."""
    h = household(db, x_dokko_key, create=False)
    if not h:
        raise HTTPException(400, "missing household key")
    st = db.get(HouseholdState, h.id)
    if not st:
        return {"from": "", "to": "", "people": [], "narrative": ""}
    today = datetime.now(IST).date()
    key = f"weekly:{h.id}:{today.isoformat()}:{st.version}:{lang[:2]}"
    hit = db.get(AiCache, key)
    if hit:
        return {**hit.value, "cached": True}
    report = weekly(decrypt(st.blob), today)
    report["narrative"] = ""
    if any(p["readings"] or p["labs"] for p in report["people"]):
        from .routes import ai_budget, _job
        try:
            ai_budget(db, h)
            report["narrative"] = narrate(report, lang[:2])
            db.add(_job(h, "report", "claude" if report["narrative"] else "error", ok=bool(report["narrative"])))
        except HTTPException:
            pass   # out of today's tokens: the numbers still stand, the narrative comes tomorrow
    db.merge(AiCache(key=key, household_id=h.id, value=report))
    return report


# ---- the morning loop -------------------------------------------------------------------------------------------------------
def housekeeping(db, today: date) -> int:
    """Loops that must close on their own: plans end when they end, renewals are nudged, forgotten calls are closed."""
    from .models import Appointment
    n = 0
    t = int(time.time())
    # demo sessions (website "see a demo") touch the server with a throw-away key; their rows go after an hour
    for h in db.scalars(select(Household).where(Household.key.like("demo-%"), Household.created < t - 3600)).all():
        from .models import HouseholdState
        try:
            with db.begin_nested():
                st = db.get(HouseholdState, h.id)
                if st:
                    db.delete(st)
                db.delete(h)
            n += 1
        except Exception:
            pass
    for h in db.scalars(select(Household).where(Household.plan != "free", Household.plan_until != None)).all():  # noqa: E711
        if h.plan_until < t:
            old = h.plan
            h.plan, h.plan_until = "free", None
            notify(db, h.id, "plan", f"Your {old.title()} plan has ended", "You are on the Free plan now: records, reminders and partners continue; smart reading and the assistant return to the free monthly limits. Renew any time from Family & Privacy → Plan.",
                   {"plan": old, "ended": True}, "", "/app#page=plan")
            n += 1
        elif 0 < h.plan_until - t <= 5 * 86400 and not db.get(ReminderSent, f"renew:{h.id}:{h.plan_until}"):
            db.add(ReminderSent(key=f"renew:{h.id}:{h.plan_until}"))
            notify(db, h.id, "plan", f"Your {h.plan.title()} plan renews in {max(1, (h.plan_until - t) // 86400)} days", "Pay by UPI from the plan page to continue without a break; nothing is charged automatically.",
                   {"plan": h.plan, "until": h.plan_until}, "", "/app#page=plan")
            n += 1
    for a in db.scalars(select(Appointment).where(Appointment.call_started != None, Appointment.call_ended == None)).all():  # noqa: E711
        if t - a.call_started > 3 * 3600:
            a.call_ended, a.status, a.updated = t, "done", t
            n += 1
    return n


def run_morning(today: date | None = None, force: bool = False) -> int:
    """One pass over every family: housekeeping, nudges (and the weekly report on Mondays). Returns notices written."""
    today = today or datetime.now(IST).date()
    written = 0
    with session() as db:
        written += housekeeping(db, today)
        for st in db.scalars(select(HouseholdState)).all():
            h = db.get(Household, st.household_id)
            if not h or h.blocked:
                continue
            try:
                state = decrypt(st.blob)
            except Exception:
                continue
            items = nudges(state, today)
            # the cap is per day, not per run: a second pass the same day (restart, force) writes nothing more
            day_key = lambda i: f"nudgeday:{h.id}:{today.isoformat()}:{i}"  # noqa: E731
            sent_today = sum(1 for i in range(MAX_NUDGES_PER_DAY) if db.get(ReminderSent, day_key(i)))
            for n in items:
                if sent_today >= MAX_NUDGES_PER_DAY:
                    break
                k = f"nudge:{h.id}:{n['key']}"[:120]
                if db.get(ReminderSent, k):
                    continue
                db.add(ReminderSent(key=k))
                db.add(ReminderSent(key=day_key(sent_today)))
                notify(db, h.id, n["kind"], n["title"], n["body"], n.get("ref"), n.get("member", ""), n.get("url", "/app"))
                sent_today += 1
                written += 1
            if today.weekday() == 0 or force:
                k = f"weekly:{h.id}:{today.isoformat()}"
                if not db.get(ReminderSent, k):
                    rep = weekly(state, today)
                    if any(p["readings"] or p["labs"] for p in rep["people"]):
                        db.add(ReminderSent(key=k))
                        who = ", ".join(_first(p["name"]) for p in rep["people"] if p["readings"] or p["labs"])
                        notify(db, h.id, "weekly", "Your family's weekly health report is ready", f"Trends for {who} over the last four weeks. Open Home → Today to read it.",
                               {"from": rep["from"], "to": rep["to"]}, "", "/app#page=today")
                        written += 1
        db.query(ReminderSent).filter(ReminderSent.key.like("nudge:%"), ReminderSent.t < int(time.time()) - 400 * 86400).delete(synchronize_session=False)
    try:
        from .backup import monthly
        with session() as db:
            written += monthly(db, today)
    except Exception as e:
        print("[backup] monthly failed:", str(e)[:160], flush=True)
    return written


def start() -> None:
    def loop():
        while True:
            try:
                nowi = datetime.now(IST)
                with session() as db:
                    housekeeping(db, nowi.date())
                if 8 <= nowi.hour < 9:
                    k = f"morning:{nowi.date().isoformat()}"
                    with session() as db:
                        done = db.get(ReminderSent, k)
                        if not done:
                            db.add(ReminderSent(key=k))
                    if not done:
                        n = run_morning(nowi.date())
                        print(f"[proactive] morning pass wrote {n} notices", flush=True)
            except Exception as e:
                print("[proactive] failed:", type(e).__name__, str(e)[:200], flush=True)
            time.sleep(600)

    threading.Thread(target=loop, name="proactive", daemon=True).start()
    print("[proactive] morning nudges + weekly report on", flush=True)
