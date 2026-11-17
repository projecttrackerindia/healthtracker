"""Read a signed prescription in the family's own language.

The signed English prescription is the legal record and never changes. This only gives the family a reading of
it in Hindi, Tamil, Telugu, Kannada, Malayalam, Bengali, Marathi or Gujarati, so that a grandmother who does not
read English knows how to take her tablets.

Two rules keep it safe:
1. How often a medicine is taken comes from a fixed table below, written by hand, never from a model. "Twice a
   day" must not become "two tablets" in translation.
2. Medicine names, strengths and numbers are never translated. Only the doctor's plain-language words (advice,
   note, instructions such as "after food", duration) go through the model, which is told to translate only,
   and the result is cached on the prescription so every reading is the same.

Also to_english(), used by both drafting endpoints when the doctor dictates in an Indian language. It translates
the dictation word for word into English so the usual drafting can read it. It does not prescribe; the doctor still
checks and signs every line.
"""
from __future__ import annotations

import json
import re

from fastapi import HTTPException

from . import ai as AI

LANGS = {"hi": "Hindi", "ta": "Tamil", "te": "Telugu", "kn": "Kannada", "ml": "Malayalam", "bn": "Bengali", "mr": "Marathi", "gu": "Gujarati"}

FREQ_T = {
    "en": {"od": "Once a day", "bd": "Twice a day", "tds": "Three times a day", "qid": "Four times a day", "sos": "Only when needed", "hs": "At night, before sleep", "weekly": "Once a week"},
    "hi": {"od": "दिन में एक बार", "bd": "दिन में दो बार", "tds": "दिन में तीन बार", "qid": "दिन में चार बार", "sos": "सिर्फ़ ज़रूरत होने पर", "hs": "रात को सोने से पहले", "weekly": "हफ़्ते में एक बार"},
    "ta": {"od": "நாளுக்கு ஒரு முறை", "bd": "நாளுக்கு இரண்டு முறை", "tds": "நாளுக்கு மூன்று முறை", "qid": "நாளுக்கு நான்கு முறை", "sos": "தேவைப்படும்போது மட்டும்", "hs": "இரவு தூங்குவதற்கு முன்", "weekly": "வாரத்திற்கு ஒரு முறை"},
    "te": {"od": "రోజుకు ఒకసారి", "bd": "రోజుకు రెండుసార్లు", "tds": "రోజుకు మూడుసార్లు", "qid": "రోజుకు నాలుగుసార్లు", "sos": "అవసరమైనప్పుడు మాత్రమే", "hs": "రాత్రి పడుకునే ముందు", "weekly": "వారానికి ఒకసారి"},
    "kn": {"od": "ದಿನಕ್ಕೆ ಒಂದು ಬಾರಿ", "bd": "ದಿನಕ್ಕೆ ಎರಡು ಬಾರಿ", "tds": "ದಿನಕ್ಕೆ ಮೂರು ಬಾರಿ", "qid": "ದಿನಕ್ಕೆ ನಾಲ್ಕು ಬಾರಿ", "sos": "ಅಗತ್ಯವಿದ್ದಾಗ ಮಾತ್ರ", "hs": "ರಾತ್ರಿ ಮಲಗುವ ಮುನ್ನ", "weekly": "ವಾರಕ್ಕೆ ಒಂದು ಬಾರಿ"},
    "ml": {"od": "ദിവസം ഒരു തവണ", "bd": "ദിവസം രണ്ടു തവണ", "tds": "ദിവസം മൂന്നു തവണ", "qid": "ദിവസം നാലു തവണ", "sos": "ആവശ്യമുള്ളപ്പോൾ മാത്രം", "hs": "രാത്രി ഉറങ്ങുന്നതിനു മുമ്പ്", "weekly": "ആഴ്ചയിൽ ഒരു തവണ"},
    "bn": {"od": "দিনে একবার", "bd": "দিনে দুবার", "tds": "দিনে তিনবার", "qid": "দিনে চারবার", "sos": "শুধু প্রয়োজন হলে", "hs": "রাতে ঘুমানোর আগে", "weekly": "সপ্তাহে একবার"},
    "mr": {"od": "दिवसातून एकदा", "bd": "दिवसातून दोनदा", "tds": "दिवसातून तीनदा", "qid": "दिवसातून चार वेळा", "sos": "फक्त गरज असेल तेव्हा", "hs": "रात्री झोपण्यापूर्वी", "weekly": "आठवड्यातून एकदा"},
    "gu": {"od": "દિવસમાં એક વાર", "bd": "દિવસમાં બે વાર", "tds": "દિવસમાં ત્રણ વાર", "qid": "દિવસમાં ચાર વાર", "sos": "માત્ર જરૂર પડે ત્યારે", "hs": "રાત્રે સૂતા પહેલાં", "weekly": "અઠવાડિયામાં એક વાર"},
}
LABELS = {  # the few headings the reading needs, hand-written like the table above
    "hi": ["कैसे लें", "डॉक्टर की सलाह", "डॉक्टर का नोट", "फिर से दिखाएँ", "जाँच"],
    "ta": ["எப்படி எடுப்பது", "மருத்துவரின் அறிவுரை", "மருத்துவரின் குறிப்பு", "மீண்டும் வர வேண்டியது", "பரிசோதனை"],
    "te": ["ఎలా వాడాలి", "డాక్టర్ సలహా", "డాక్టర్ నోట్", "మళ్ళీ చూపించుకోవాలి", "పరీక్ష"],
    "kn": ["ಹೇಗೆ ತೆಗೆದುಕೊಳ್ಳಬೇಕು", "ವೈದ್ಯರ ಸಲಹೆ", "ವೈದ್ಯರ ಟಿಪ್ಪಣಿ", "ಮತ್ತೆ ತೋರಿಸಬೇಕು", "ಪರೀಕ್ಷೆ"],
    "ml": ["എങ്ങനെ കഴിക്കണം", "ഡോക്ടറുടെ ഉപദേശം", "ഡോക്ടറുടെ കുറിപ്പ്", "വീണ്ടും കാണിക്കേണ്ടത്", "പരിശോധന"],
    "bn": ["কীভাবে খাবেন", "ডাক্তারের পরামর্শ", "ডাক্তারের নোট", "আবার দেখাবেন", "পরীক্ষা"],
    "mr": ["कसे घ्यावे", "डॉक्टरांचा सल्ला", "डॉक्टरांची नोंद", "पुन्हा दाखवा", "तपासणी"],
    "gu": ["કેવી રીતે લેવી", "ડૉક્ટરની સલાહ", "ડૉક્ટરની નોંધ", "ફરી બતાવો", "તપાસ"],
}
INDIC = re.compile(r"[ऀ-෿]")


def _ask(system: str, payload: dict, max_tokens: int = 1200) -> dict:
    res = AI.create(max_tokens=max_tokens, system=system, messages=[{"role": "user", "content": json.dumps(payload, ensure_ascii=False)[:8000]}])
    raw = "".join(b.text for b in res.content if getattr(b, "type", "") == "text").strip()
    return json.loads(raw[raw.index("{"):raw.rindex("}") + 1])


def read_in(rx: dict, lang: str) -> dict:
    """The prescription for a family member who reads `lang`. Cached in rx['tr'][lang] by the caller."""
    if lang not in LANGS:
        raise HTTPException(400, "Choose one of: " + ", ".join(LANGS.values()))
    words = {"diagnosis": rx.get("diagnosis", ""), "advice": rx.get("advice", ""), "followUp": rx.get("followUp", ""),
             "items": [{"instructions": i.get("instructions", ""), "duration": i.get("duration", "")} for i in rx.get("items", [])],
             "tests": [t.get("when", "") for t in rx.get("tests", []) or []]}
    out = {"diagnosis": "", "advice": "", "followUp": "", "items": [{"instructions": "", "duration": ""} for _ in rx.get("items", [])], "tests": ["" for _ in rx.get("tests", []) or []]}
    has_words = any([words["diagnosis"], words["advice"], words["followUp"], any(x["instructions"] or x["duration"] for x in words["items"]), any(words["tests"])])
    machine = False
    if has_words and AI.available():
        system = (f"Translate a doctor's short notes from English into simple, everyday {LANGS[lang]} that an elderly patient understands. "
                  "Translate only. Do not add, remove, soften or explain anything. Keep every number, unit and medicine or test name exactly as "
                  "written, in English letters. Keep the same JSON shape and keys; empty strings stay empty. Return ONLY the JSON.")
        try:
            got = _ask(system, words)
            out["diagnosis"] = str(got.get("diagnosis") or "")[:300]
            out["advice"] = str(got.get("advice") or "")[:1200]
            out["followUp"] = str(got.get("followUp") or "")[:120]
            gi = got.get("items") or []
            for k in range(len(out["items"])):
                g = gi[k] if k < len(gi) and isinstance(gi[k], dict) else {}
                out["items"][k] = {"instructions": str(g.get("instructions") or "")[:160], "duration": str(g.get("duration") or "")[:60]}
            gt = got.get("tests") or []
            out["tests"] = [str(gt[k])[:40] if k < len(gt) else "" for k in range(len(out["tests"]))]
            machine = True
        except Exception as e:
            AI._fail("rx read-in", e)
    ft = FREQ_T[lang]
    return {"lang": lang, "language": LANGS[lang], "labels": LABELS[lang], "machine": machine, "wordsLeftInEnglish": has_words and not machine,
            "items": [{"name": i.get("name", ""), "strength": i.get("strength", ""), "how": ft.get(i.get("frequency", ""), ""),
                       "instructions": out["items"][k]["instructions"] or (i.get("instructions", "") if not machine else ""),
                       "duration": out["items"][k]["duration"] or (i.get("duration", "") if not machine else "")} for k, i in enumerate(rx.get("items", []))],
            "tests": [{"name": t.get("name", ""), "when": out["tests"][k] or t.get("when", "")} for k, t in enumerate(rx.get("tests", []) or [])],
            "diagnosis": out["diagnosis"] or rx.get("diagnosis", ""), "advice": out["advice"] or rx.get("advice", ""), "followUp": out["followUp"] or rx.get("followUp", "")}


def cached(rx: dict, lang: str) -> tuple[dict, bool]:
    """(reading, changed). Readings are kept on the prescription so the family sees the same words every time."""
    tr = dict(rx.get("tr") or {})
    if lang in tr and not tr[lang].get("wordsLeftInEnglish"):
        return tr[lang], False
    got = read_in(rx, lang)
    tr[lang] = got
    return got, True


def to_english(text: str) -> str:
    """A doctor's dictation in an Indian language, word for word in English, for the drafting rules to read.

    Returns the text unchanged when it is already English. Raises 503 when it is not and translation is off,
    so the doctor is told plainly instead of getting an empty draft."""
    if not INDIC.search(text or ""):
        return text
    if not AI.available():
        raise HTTPException(503, "Drafting from Tamil, Hindi and other languages needs the language service, which is off just now. "
                                 "Please type it in English, or add the medicines line by line.")
    system = ("Translate a doctor's spoken prescription from an Indian language (it may mix English words) into plain English, word for word. "
              "You do not prescribe. Never add a medicine, dose, number, timing or test that was not said. Keep medicine and test names as the "
              "doctor said them, spelled in English. Write numbers as digits. Return ONLY JSON: {\"english\":\"...\"}")
    try:
        return str(_ask(system, {"dictation": text[:3500]}, 900).get("english") or "")[:4000]
    except Exception as e:
        AI._fail("rx to english", e)
        raise HTTPException(503, "The dictation could not be read just now. Please type it in English, or add the medicines line by line.")
