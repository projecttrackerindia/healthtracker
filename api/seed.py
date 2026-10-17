"""Sample partners, price lists, plans and advisories so the app works out of the box.

Everything here is FICTIONAL demo data (store names, prices, ratings) except the seasonal guidance, which is general
public-health information, and the first-aid videos, which are real public videos from official organisations.
Admins replace or extend it from /admin.
"""
from __future__ import annotations

import json
import math
import os
import random
from pathlib import Path

from sqlalchemy import select

from .models import Admin, LabTest, Plan, Seasonal, Store, StoreItem, Video
from .security import hash_pw

HERE = Path(__file__).resolve().parent
CATALOG = json.loads((HERE / "data" / "catalog.json").read_text(encoding="utf-8"))

# ---- lab test price list: code -> (name, typical price INR, turnaround hours, fasting) ----
TESTS = {
    "cbc": ("Complete blood count (CBC)", 350, 12, False),
    "hb": ("Haemoglobin", 120, 6, False),
    "wbc": ("White blood cells", 150, 6, False),
    "plt": ("Platelet count", 150, 6, False),
    "glu_f": ("Fasting glucose", 90, 6, True),
    "glu_pp": ("Post-meal glucose (PP)", 90, 6, False),
    "hba1c": ("HbA1c", 450, 24, False),
    "lipid": ("Lipid profile", 650, 24, True),
    "tc": ("Total cholesterol", 200, 24, True),
    "ldl": ("LDL cholesterol", 250, 24, True),
    "hdl": ("HDL cholesterol", 250, 24, True),
    "tg": ("Triglycerides", 220, 24, True),
    "lft": ("Liver function test (LFT)", 600, 24, False),
    "alt": ("ALT (SGPT)", 180, 24, False),
    "ast": ("AST (SGOT)", 180, 24, False),
    "kft": ("Kidney function test (KFT)", 650, 24, False),
    "creat": ("Creatinine", 180, 12, False),
    "urea": ("Blood urea", 160, 12, False),
    "uric": ("Uric acid", 180, 12, False),
    "na": ("Sodium", 200, 12, False),
    "k": ("Potassium", 200, 12, False),
    "tsh": ("TSH", 300, 24, False),
    "thy": ("Thyroid profile (T3, T4, TSH)", 550, 24, False),
    "vitd": ("Vitamin D (25-OH)", 1200, 48, False),
    "b12": ("Vitamin B12", 900, 48, False),
    "iron": ("Iron studies (ferritin)", 900, 48, False),
    "urine": ("Urine routine", 150, 12, False),
    "crp": ("CRP", 450, 24, False),
    "esr": ("ESR", 120, 12, False),
    "dengue": ("Dengue NS1 + IgM", 900, 24, False),
    "malaria": ("Malaria antigen / smear", 400, 12, False),
    "typhoid": ("Typhoid (Widal / Typhidot)", 350, 24, False),
    "ecg": ("ECG", 300, 1, False),
    "xray": ("Chest X-ray", 450, 4, False),
    "usg": ("Ultrasound abdomen", 1400, 4, True),
    "echo": ("Echocardiogram", 2200, 4, False),
    "ogtt": ("Glucose tolerance test (OGTT)", 350, 6, True),
    "pap": ("Pap smear", 900, 72, False),
    "psa": ("PSA", 700, 24, False),
    "hpylori": ("H. pylori test", 1100, 48, False),
}

# ---- demo partners per city. (lat, lng) are area centres; names are fictional. ----
CITIES = {
    "Hyderabad": {
        "areas": [("Madhapur", 17.448, 78.391), ("Gachibowli", 17.440, 78.348), ("Kukatpally", 17.494, 78.399),
                  ("Banjara Hills", 17.414, 78.435), ("Secunderabad", 17.439, 78.498), ("Ameerpet", 17.437, 78.448),
                  ("Dilsukhnagar", 17.368, 78.524), ("Kondapur", 17.464, 78.364), ("Jubilee Hills", 17.431, 78.407),
                  ("Begumpet", 17.444, 78.467), ("LB Nagar", 17.349, 78.552), ("Miyapur", 17.496, 78.359)],
        "state": "TS"},
    "Bengaluru": {"areas": [("Indiranagar", 12.978, 77.640), ("Koramangala", 12.935, 77.624), ("Whitefield", 12.970, 77.750),
                            ("Jayanagar", 12.925, 77.593), ("Malleshwaram", 13.003, 77.570), ("HSR Layout", 12.912, 77.645)], "state": "KA"},
    "Mumbai": {"areas": [("Andheri", 19.119, 72.846), ("Bandra", 19.055, 72.840), ("Dadar", 19.018, 72.843),
                         ("Powai", 19.117, 72.906), ("Thane", 19.218, 72.978), ("Borivali", 19.229, 72.857)], "state": "MH"},
    "Delhi": {"areas": [("Dwarka", 28.592, 77.046), ("Lajpat Nagar", 28.567, 77.243), ("Rohini", 28.749, 77.067),
                        ("Saket", 28.524, 77.206), ("Noida Sec 18", 28.570, 77.321), ("Gurugram Sec 29", 28.469, 77.064)], "state": "DL"},
    "Chennai": {"areas": [("Adyar", 13.006, 80.257), ("T Nagar", 13.040, 80.234), ("Anna Nagar", 13.085, 80.210),
                          ("Velachery", 12.979, 80.221), ("Porur", 13.035, 80.158)], "state": "TN"},
    "Pune": {"areas": [("Kothrud", 18.507, 73.807), ("Hinjewadi", 18.591, 73.738), ("Viman Nagar", 18.567, 73.914),
                       ("Hadapsar", 18.509, 73.926)], "state": "MH"},
    "Kolkata": {"areas": [("Salt Lake", 22.580, 88.418), ("Park Street", 22.553, 88.352), ("Behala", 22.498, 88.312),
                          ("New Town", 22.580, 88.470)], "state": "WB"},
    "Visakhapatnam": {"areas": [("MVP Colony", 17.740, 83.335), ("Gajuwaka", 17.683, 83.209), ("Dwaraka Nagar", 17.726, 83.306)], "state": "AP"},
    "Vijayawada": {"areas": [("Benz Circle", 16.498, 80.656), ("Governorpet", 16.512, 80.628)], "state": "AP"},
    "Warangal": {"areas": [("Hanamkonda", 18.011, 79.558), ("Kazipet", 17.978, 79.498)], "state": "TS"},
}

PHARM_BRANDS = [("GreenCross Pharmacy", 12, 30, 499, 45), ("CityCare Chemist", 8, 40, 499, 90), ("Wellnest Pharmacy", 18, 0, 0, 240),
                ("Sanjeevani Medicals", 10, 25, 399, 60), ("Nirog 24×7 Pharmacy", 5, 49, 799, 35), ("Arogya Generic Store", 25, 35, 299, 120)]
LAB_BRANDS = [("Pathlab Prime", 0.0, True, 100), ("Clearview Diagnostics", 10.0, True, 150), ("Nidaan Labs", 20.0, True, 0),
              ("Suraksha Diagnostic Centre", 5.0, False, 0)]
HOSP_BRANDS = ["Lotus Multispeciality Hospital", "Sunrise Care Hospital", "Sri Vani Hospital & Trauma Centre", "Harmony Children's Hospital"]


def _rnd(seed: str) -> random.Random:
    return random.Random(seed)


def _jitter(r: random.Random, lat: float, lng: float, km: float = 1.2):
    d = km / 111.0
    return round(lat + r.uniform(-d, d), 5), round(lng + r.uniform(-d, d) / math.cos(math.radians(lat)), 5)


def seed_partners(db):
    if db.scalar(select(Store.id).limit(1)):
        return
    for city, c in CITIES.items():
        r = _rnd(city)
        areas = c["areas"]
        # pharmacies: one brand per area, cycling
        for i, (area, lat, lng) in enumerate(areas):
            for j in range(2 if i % 2 == 0 else 1):
                brand, disc, fee, free, eta = PHARM_BRANDS[(i + j * 3) % len(PHARM_BRANDS)]
                la, lo = _jitter(r, lat, lng)
                st = Store(kind="pharmacy", name=f"{brand} · {area}", brand=brand, area=area, city=city, lat=la, lng=lo,
                           address=f"{r.randint(1, 120)}, Main Road, {area}, {city}", phone=f"0{r.randint(40, 99)} {r.randint(2000, 4999)} {r.randint(1000, 9999)}",
                           hours="24 hours" if "24" in brand else "8 am – 10:30 pm", open_24h="24" in brand,
                           rating=round(r.uniform(3.9, 4.8), 1), rating_n=r.randint(40, 900), discount_pct=disc,
                           delivery=True, delivery_fee=fee, free_above=free, eta_min=eta + r.randint(-10, 20),
                           verified=True, licence=f"{c['state']}/{r.randint(10000, 99999)}/20B-21B")
                db.add(st)
                db.flush()
                for m in CATALOG:
                    if r.random() < 0.08:  # a few items out of stock per store
                        continue
                    own = r.random() < 0.15  # some items priced individually
                    price = m["mrp"] if own else round(m["mrp"] * (1 - disc / 100))
                    db.add(StoreItem(store_id=st.id, sku=m["id"], name=m["name"], mrp=m["mrp"], price=max(1, price), stock=r.randint(3, 60)))
        # labs
        for i, (area, lat, lng) in enumerate(areas):
            if i % 2:
                continue
            brand, off, home, cfee = LAB_BRANDS[i % len(LAB_BRANDS)]
            la, lo = _jitter(r, lat, lng, .8)
            st = Store(kind="lab", name=f"{brand} · {area}", brand=brand, area=area, city=city, lat=la, lng=lo,
                       address=f"{r.randint(1, 80)}, {area}, {city}", phone=f"0{r.randint(40, 99)} {r.randint(2000, 4999)} {r.randint(1000, 9999)}",
                       hours="6:30 am – 9 pm", rating=round(r.uniform(4.0, 4.9), 1), rating_n=r.randint(60, 1500), discount_pct=off,
                       delivery=False, delivery_fee=0, free_above=0, eta_min=24 * 60, home_collection=home, collection_fee=cfee,
                       verified=True, licence=f"NABL MC-{r.randint(1000, 9999)}" if r.random() < .7 else "")
            db.add(st)
            db.flush()
            for code, (name, price, tat, fast) in TESTS.items():
                p = round(price * (1 - off / 100) * r.uniform(.9, 1.15) / 10) * 10
                db.add(LabTest(store_id=st.id, code=code, name=name, price=max(50, p), tat_hours=tat, fasting=fast))
        # hospitals (for the nearest-hospital card; no price lists)
        for i, (area, lat, lng) in enumerate(areas[: len(HOSP_BRANDS)]):
            la, lo = _jitter(r, lat, lng, .6)
            db.add(Store(kind="hospital", name=f"{HOSP_BRANDS[i]} · {area}", brand=HOSP_BRANDS[i], area=area, city=city, lat=la, lng=lo,
                         address=f"{area}, {city}", phone=f"0{r.randint(40, 99)} {r.randint(2000, 4999)} {r.randint(1000, 9999)}",
                         hours="24 hours", open_24h=True, rating=round(r.uniform(3.8, 4.7), 1), rating_n=r.randint(200, 5000),
                         delivery=False, verified=True))


PLANS = [
    ("free", "Free", 0, 0, 5, ["Family profiles and records on this device", "3D body, Heart Lab and Pregnancy", "SOS, first aid and Medical ID",
                               "Medicine and lab price comparison", "AI report analysis: 3 a month"], 0),
    ("family", "Family", 39, 390, 8, ["Everything in Free", "AI report and prescription analysis: 30 a month", "Order tracking and delivery ratings",
                                         "Home sample collection booking", "Seasonal alerts for your city", "Email support"], 1),
    ("plus", "Plus", 99, 990, 12, ["Everything in Family", "Unlimited AI analysis", "Priority partner pharmacies and labs",
                                      "Shareable doctor summaries (PDF)", "Early access to new features", "Phone support"], 2),
]


def seed_plans(db):
    if db.scalar(select(Plan.code).limit(1)):
        # one-time move from the first price list (149/299) to the launch prices (39/99); admin edits are left alone
        for code, name, pm, py, mem, feats, sort in PLANS:
            p = db.get(Plan, code)
            if p and (code, p.price_month) in (("family", 149), ("plus", 299)):
                p.price_month, p.price_year = pm, py
        return
    for code, name, pm, py, mem, feats, sort in PLANS:
        db.add(Plan(code=code, name=name, price_month=pm, price_year=py, members=mem, features=feats, sort=sort))


SEASONAL = [
    ("Dengue", "🦟", [6, 7, 8, 9, 10, 11], "high", "Spread by day-biting Aedes mosquitoes that breed in clean standing water. Cases rise through the monsoon and peak after it.",
     ["High fever for 2–7 days", "Severe headache and pain behind the eyes", "Muscle and joint pain", "Rash", "Warning signs: belly pain, vomiting, bleeding gums, drowsiness"],
     ["Empty and scrub water containers, coolers and plant trays weekly", "Use repellent and full sleeves in the daytime", "Window nets and screens",
      "Do not take ibuprofen or aspirin for fever: paracetamol only, and plenty of fluids"],
     "Fever with any warning sign, or fever that continues beyond 2 days: see a doctor the same day and ask for a dengue test and platelet count.", "NCDC / NVBDCP"),
    ("Malaria", "🦟", [6, 7, 8, 9, 10], "medium", "Spread by Anopheles mosquitoes that bite from dusk to dawn.",
     ["Fever with chills and sweats, often in cycles", "Headache, body ache, vomiting"],
     ["Sleep under a treated bed net", "Repellent in the evening", "Drain stagnant water around the house"],
     "Any fever with chills in the monsoon deserves a malaria test within 24 hours.", "NVBDCP"),
    ("Chikungunya", "🦟", [7, 8, 9, 10], "medium", "Same mosquito as dengue; sudden fever with severe joint pain that can last weeks.",
     ["Sudden high fever", "Severe joint pain and swelling, especially hands, wrists and ankles", "Rash"],
     ["Same mosquito control as dengue", "Rest, fluids and paracetamol; avoid NSAIDs until dengue is ruled out"],
     "Joint pain that stops you walking, or any dengue warning sign.", "NCDC"),
    ("Typhoid & food/water infections", "🥤", [4, 5, 6, 7, 8, 9], "medium", "Contaminated water and street food cause typhoid, cholera, hepatitis A/E and diarrhoea, especially in summer and the monsoon.",
     ["Fever rising over days (typhoid)", "Watery diarrhoea, vomiting", "Yellow eyes and dark urine (hepatitis)"],
     ["Boiled or filtered water; avoid ice from unknown sources", "Freshly cooked, hot food; wash fruit", "Hand-washing with soap", "Typhoid and hepatitis A vaccines are available"],
     "Diarrhoea with blood, signs of dehydration (very little urine, dizziness), fever beyond 3 days, or yellow eyes.", "MoHFW IDSP"),
    ("Leptospirosis", "🌧️", [7, 8, 9], "medium", "Bacteria in floodwater contaminated by rat urine enter through cuts in the skin, common after wading through waterlogged streets.",
     ["Fever, severe calf pain, red eyes", "Headache; later jaundice or reduced urine"],
     ["Avoid wading in floodwater; wear boots", "Wash and cover cuts", "Ask a doctor about preventive doxycycline after unavoidable exposure"],
     "Fever within 2 weeks of floodwater contact: tell the doctor about the exposure.", "NCDC"),
    ("Viral fever, flu & conjunctivitis", "🤧", [7, 8, 9], "medium", "Crowded, damp weather spreads respiratory viruses and eye flu.",
     ["Fever, sore throat, cough, body ache", "Red, sticky, itchy eyes"],
     ["Hand hygiene; do not share towels", "Masks when you have symptoms", "Annual flu vaccine for pregnant women, over-65s and people with long-term illness"],
     "Breathlessness, chest pain, fever beyond 3 days, eye pain or vision change.", "MoHFW"),
    ("Heat stroke & dehydration", "☀️", [3, 4, 5, 6], "high", "Heatwaves from March to June. Older adults, outdoor workers, children and pregnant women are most at risk.",
     ["Headache, dizziness, cramps, weakness", "Heat stroke: very hot skin, confusion, fainting, temperature above 40 °C"],
     ["Water, buttermilk, ORS through the day", "Stay indoors 12–4 pm; light cotton clothing", "Never leave children or pets in parked cars"],
     "Confusion, fainting or a temperature above 40 °C is an emergency: cool the person and call 108.", "NDMA heat action guidance"),
    ("Chickenpox & measles", "🔴", [2, 3, 4, 5], "medium", "Spring is the season for chickenpox and measles outbreaks among children and unvaccinated adults.",
     ["Fever followed by an itchy blister rash (chickenpox)", "Fever, cough, red eyes, then a blotchy rash (measles)"],
     ["Check MR / MMR and varicella vaccines are complete", "Keep children home until all blisters crust", "Pregnant women should avoid contact and tell their doctor about any exposure"],
     "Breathing difficulty, drowsiness, a rash in pregnancy or in a baby under 1 year.", "IAP / UIP schedule"),
    ("Influenza & H1N1", "🤒", [11, 12, 1, 2], "medium", "Flu circulates in the cold months; H1N1 clusters appear in some years.",
     ["Sudden fever, cough, sore throat, body ache", "Breathlessness is a danger sign"],
     ["Annual flu vaccine (ideally by October)", "Hand hygiene; cover coughs", "Rest and fluids; antivirals work best within 48 hours for high-risk people"],
     "Breathlessness, chest pain, confusion, or fever beyond 3 days — sooner in pregnancy, over 65 or with asthma/diabetes/heart disease.", "MoHFW seasonal influenza guidelines"),
    ("Asthma, COPD & air pollution", "🌫️", [10, 11, 12, 1], "high", "Winter inversion and Diwali smoke push AQI into the severe range in many cities; asthma and COPD attacks and heart problems rise.",
     ["Wheeze, tight chest, night cough", "More inhaler use than usual"],
     ["Check AQI; N95 mask outdoors when above 200", "Keep preventer inhalers regular; carry the reliever", "Avoid outdoor exercise on bad-air days; indoor air purifier if possible"],
     "Reliever needed more than every 4 hours, lips or nails turning blue, or difficulty speaking in sentences.", "CPCB AQI / GINA"),
    ("Winter heart & stroke risk", "❤️", [12, 1], "medium", "Cold mornings raise blood pressure and clotting; heart attacks and strokes peak in winter, especially in older adults.",
     ["Chest pressure, breathlessness, sweating (heart attack)", "Face drooping, arm weakness, speech trouble (stroke): act FAST"],
     ["Warm up before morning walks; walk later in the day", "Keep blood pressure medicines regular; check BP weekly", "Flu and pneumococcal vaccines protect the heart too"],
     "Chest pain or any FAST sign: call 108 at once; do not drive yourself.", "ICMR / WHO"),
    ("Scrub typhus", "🌾", [8, 9, 10, 11], "low", "Mite bites in bushes and fields after the rains, common in rural and peri-urban areas.",
     ["Fever, headache, a dark scab (eschar) at the bite site", "Rash, swollen glands"],
     ["Full-sleeved clothes and repellent in grass and fields", "Wash after fieldwork"],
     "Unexplained fever for more than 3 days after time outdoors: mention it to the doctor; it responds quickly to the right antibiotic.", "NCDC"),
]


def seed_seasonal(db):
    if db.scalar(select(Seasonal.id).limit(1)):
        return
    for d, e, months, risk, summ, sy, pv, see, src in SEASONAL:
        db.add(Seasonal(region="IN", months=months, disease=d, emoji=e, risk=risk, summary=summ, symptoms=sy, prevention=pv, see_doctor=see, source=src))


def seed_videos(db):
    if db.scalar(select(Video.id).limit(1)):
        return
    p = HERE / "data" / "videos.json"
    if not p.exists():
        return
    for i, v in enumerate(json.loads(p.read_text(encoding="utf-8"))):
        db.add(Video(topic=v["topic"], title=v["title"], channel=v["channel"], yt=v["yt"], source=v.get("source_page", ""), sort=i, lang=v.get("lang", "en")))


def seed_admin(db):
    email = os.getenv("ADMIN_EMAIL", "admin@thehealthtracker.com").strip().lower()
    pw = os.getenv("ADMIN_PASSWORD", "")
    a = db.scalar(select(Admin).where(Admin.email == email))
    if a is None:
        if not pw:  # never ship a known default password: make one and print it once to the deploy logs
            import secrets
            pw = secrets.token_urlsafe(12)
            print(f"[TheHealthTracker] First admin created: {email} / {pw}  (set ADMIN_PASSWORD to choose your own)", flush=True)
        a = Admin(email=email, pw_hash=hash_pw(pw), role="owner")
        db.add(a)
    elif pw:
        a.pw_hash = hash_pw(pw)


def seed_all(db):
    seed_partners(db)
    seed_plans(db)
    seed_seasonal(db)
    seed_videos(db)
    seed_admin(db)
