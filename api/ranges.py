"""Reading a lab's own printed reference range, the way Indian labs print it, so a result is judged against what the lab
itself says (Nov 2026 audit). We never invent a range here: when the printed text cannot be read with certainty we
return None and the caller keeps what the lab marked.

Handles: "13.0 - 17.0", "0.70 to 1.30", "Up to 40", "< 200", "> 40", "1,50,000 - 4,10,000",
sex-specific ("Male: 13-17 Female: 12-15", "M 0.7-1.3 / F 0.6-1.1"),
banded ranges where one band is the healthy one ("Desirable < 200, Borderline 200-239, High >= 240",
"<5.7 Non-diabetic 5.7-6.4 Prediabetic >=6.5 Diabetic", "Deficiency <20, Insufficiency 20-29, Sufficiency 30-100"),
and timed ranges ("Fasting: <95 1 hr: <180 2 hr: <155") when the test name says which time it is."""
from __future__ import annotations

import re

NUM = r"\d+(?:\.\d+)?"
GOOD = re.compile(r"(?<!ab)normal|non[- ]?diabetic|desirable|(?<!near )optimal|(?<!in)sufficien|reference|biological|healthy|negative|adequate|ideal|acceptable|euthyroid", re.I)
BAD = re.compile(r"near|pre[- ]?diabet|diabet|borderline|high|low|deficien|insufficien|toxic|risk|elevated|impaired|abnormal|border", re.I)
SEXES = (("male", r"(?<![a-z])(?:male|men|m)(?![a-z])"), ("female", r"(?<![a-z])(?:female|women|f)(?![a-z])"))
TIMES = (("fasting", r"fasting|\b0\s*(?:min|hr|h)\b|basal|\bfbs\b"), ("1h", r"\b(?:1|one)\s*(?:hr|hour|h)\b|\b60\s*min"),
         ("2h", r"\b(?:2|two)\s*(?:hr|hours?|h)\b|\b120\s*min"), ("3h", r"\b(?:3|three)\s*(?:hr|hours?|h)\b|\b180\s*min"))


def timepoint(name: str) -> str | None:
    t = (name or "").lower()
    for k, rx in TIMES:
        if re.search(rx, t):
            return k
    return None


def _clean(ref: str) -> str:
    t = str(ref or "")
    t = re.sub(r"(?<=\d),(?=\d)", "", t)                      # 1,50,000 -> 150000
    t = t.replace("–", "-").replace("—", "-").replace("−", "-").replace("≤", "<=").replace("≥", ">=")
    t = re.sub(r"(?i)\b(?:up\s*to|upto|less than or equal to|not more than)\b", "<=", t)
    t = re.sub(r"(?i)\b(?:less than|below|under)\b", "<", t)
    t = re.sub(r"(?i)\b(?:more than|greater than|above|over)\b", ">", t)
    t = re.sub(r"(?i)\s+to\s+(?=\d)", " - ", t)
    return t


RANGE = re.compile(rf"(?P<a>{NUM})\s*-\s*(?P<b>{NUM})|(?P<op><=|>=|<|>)\s*=?\s*(?P<c>{NUM})")


def _ranges(t: str) -> list[tuple[int, int, tuple]]:
    out = []
    for m in RANGE.finditer(t):
        if m.group("a") is not None:
            a, b = float(m.group("a")), float(m.group("b"))
            if b > a:
                out.append((m.start(), m.end(), (a, b, True, True)))
        else:
            v, op = float(m.group("c")), m.group("op")
            out.append((m.start(), m.end(), (None, v, True, op == "<=") if op in ("<", "<=") else (v, None, op == ">=", True)))
    return out


def _pick_band(t: str) -> tuple | None:
    """The healthy band of a banded range, or the only range when there is one."""
    rs = _ranges(t)
    if not rs:
        return None
    if len(rs) == 1:
        return rs[0][2]
    labels_after = bool(re.match(r"\s*(?:<=|>=|<|>|\d)", t))
    labels = []
    for i, (s, e, r) in enumerate(rs):
        lab = t[e: rs[i + 1][0]] if labels_after and i + 1 < len(rs) else t[e:] if labels_after else t[(rs[i - 1][1] if i else 0): s]
        labels.append(lab)
    good = [r for (_, _, r), lab in zip(rs, labels) if GOOD.search(lab) and not BAD.search(re.sub(GOOD, "", lab))]
    if len(good) == 1:
        return good[0]
    if any(labels) and any(BAD.search(x) for x in labels):
        return None          # banded, but no single healthy band we can name with certainty
    return None              # several plain ranges with no labels: ambiguous


def parse_ref(ref: str, sex: str = "", test: str = "") -> tuple | None:
    """(lo, hi, lo_inclusive, hi_inclusive) with lo or hi None for one-sided ranges; None when not certain."""
    t = _clean(ref)
    if not t.strip():
        return None
    low = t.lower()
    # timed ranges (glucose tolerance): use the band for this test's time point, or nothing
    hits = [(k, m.start()) for k, rx in TIMES for m in [re.search(rx, low)] if m]
    if len(hits) >= 2:
        tp = timepoint(test)
        if not tp:
            return None
        hits.sort(key=lambda x: x[1])
        for i, (k, s) in enumerate(hits):
            if k == tp:
                seg = t[s: hits[i + 1][1] if i + 1 < len(hits) else len(t)]
                seg = re.sub(TIMES[[x[0] for x in TIMES].index(k)][1], " ", seg, flags=re.I)
                return _pick_band(seg)
        return None
    # sex-specific ranges
    sx = [(k, m.start(), m.end()) for k, rx in SEXES for m in re.finditer(rx, low)]
    if len({k for k, _, _ in sx}) == 2:
        if sex not in ("male", "female"):
            return None
        sx.sort(key=lambda x: x[1])
        first_num = re.search(r"\d", t)
        if first_num and first_num.start() < sx[0][1]:      # "3.5 - 7.2 (Male), 2.6 - 6.0 (Female)": the label follows its range
            for i, (k, s, e) in enumerate(sx):
                if k == sex:
                    return _pick_band(t[(sx[i - 1][2] if i else 0): s])
            return None
        for i, (k, s, e) in enumerate(sx):
            if k == sex:
                nxt = next((x[1] for x in sx[i + 1:] if x[0] != k), len(t))
                return _pick_band(t[e:nxt])
        return None
    return _pick_band(t)


def judge(value, ref: str, sex: str = "", test: str = "") -> tuple[str, tuple] | None:
    """('low'|'normal'|'high', band) against the lab's own printed range; None when the range is unreadable."""
    try:
        v = float(str(value).replace(",", ""))
    except (TypeError, ValueError):
        return None
    band = parse_ref(ref, sex, test)
    if not band:
        return None
    lo, hi, li, hi_in = band
    if lo is not None and (v < lo or (v == lo and not li)):
        return "low", band
    if hi is not None and (v > hi or (v == hi and not hi_in)):
        return "high", band
    return "normal", band


def rejudge(findings: list, sex: str = "") -> list:
    """Re-decide each numeric result against its own printed range; mark where that differs from the first reading.
    Adds lo/hi so the app draws the green band from the same numbers it judged with. Never touches text results."""
    for f in findings or []:
        if not isinstance(f, dict):
            continue
        j = judge(f.get("value"), f.get("ref", ""), sex, f.get("test", ""))
        if not j:
            f.pop("lo", None), f.pop("hi", None)
            continue
        flag, (lo, hi, _, _) = j
        if f.get("flag") not in (None, "", "unknown", flag):
            f["flagWas"] = f.get("flag")
        f["flag"], f["by"] = flag, "lab range"
        f["lo"], f["hi"] = lo, hi
    return findings
