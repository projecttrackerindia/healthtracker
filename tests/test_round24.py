"""Round 24: medicine refills. Run: python -m pytest -q tests/test_round24.py"""
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

from api import reminders

ROOT = Path(__file__).resolve().parents[1]


def test_days_left_counts_daily_and_weekly_doses():
    assert reminders.doses_per_day({"when": ["Morning", "Night"]}) == 2
    assert abs(reminders.doses_per_day({"when": ["Monday"]}) - 1 / 7) < 1e-9
    assert reminders.days_left({"when": ["Morning", "Night"], "left": 7}) == 3.5
    assert reminders.days_left({"when": ["Morning"], "left": None}) is None
    assert reminders.days_left({"when": [], "left": 5}) is None
    state = {"meds": {"d3": [{"id": "md1", "n": "Metformin 500 mg", "when": ["Morning", "Night"], "left": 5}, {"id": "md9", "n": "Vitamin D", "when": ["Sunday"], "left": 4}, {"id": "md8", "n": "Amlodipine", "when": ["Morning"], "left": 30}]}}
    low = reminders.low_meds(state, {"id": "d3"})
    assert [x["id"] for x in low] == ["md1"] and low[0]["days"] == 2
    assert reminders.refill_text(low) == "Metformin 500 mg — about 2 days left"
    assert reminders.refill_text([{"n": "X", "days": 0, "left": 0}]) == "X — none left"
    assert reminders.refill_text([{"n": "X", "days": 0, "left": 1}]) == "X — today"


def test_tick_sends_one_refill_push_per_day(monkeypatch):
    """A household with a low medicine gets one 'Refill soon' push in the 09:00 window, and not a second one."""
    import os
    os.environ["DATABASE_URL"] = "sqlite:///./data/test_round24.db"
    from api import push as PUSH
    from api.db import SessionLocal, engine  # the job uses api.db.session (a contextmanager) against the same engine
    from api.models import Base, HouseholdState, PushSub, ReminderSent, User
    from api.family import encrypt as seal_state
    Base.metadata.create_all(engine)
    sent = []
    monkeypatch.setattr(PUSH, "ready", lambda: True)
    monkeypatch.setattr(PUSH, "send", lambda sub, msg, ttl=3600: (sent.append(msg) or (True, 201, "")))
    hid = "h_refill_test"
    state = {"members": [{"id": "d3", "name": "Kamala Devi"}], "meds": {"d3": [{"id": "md1", "n": "Metformin 500 mg", "when": ["Morning", "Night"], "left": 4}]}, "rem": {"on": True}}
    with SessionLocal() as db:
        db.query(ReminderSent).delete()
        db.query(PushSub).filter(PushSub.household_id == hid).delete()
        db.query(HouseholdState).filter(HouseholdState.household_id == hid).delete()
        db.add(HouseholdState(household_id=hid, blob=seal_state(state)))
        db.add(PushSub(user_id="u_none", household_id=hid, endpoint="https://push.test/1", sub={"endpoint": "https://push.test/1", "keys": {}}))
        db.commit()
    try:
        _refill_flow(sent, hid, SessionLocal)
    finally:   # the engine is shared by every test module, so leave nothing behind for the other reminder tests
        with SessionLocal() as db:
            db.query(PushSub).filter(PushSub.household_id == hid).delete()
            db.query(HouseholdState).filter(HouseholdState.household_id == hid).delete()
            db.query(ReminderSent).filter(ReminderSent.key.like(f"{hid}:%")).delete()
            db.commit()


def _refill_flow(sent, hid, SessionLocal):
    at = datetime(2026, 10, 21, 9, 5, tzinfo=reminders.IST)
    n = reminders.tick(at)
    refills = [m for m in sent if m["tag"] == "refill-d3"]
    assert n >= 1 and len(refills) == 1, sent
    assert refills[0]["title"] == "Kamala: refill soon" and "Metformin 500 mg — about 2 days left" in refills[0]["body"] and refills[0]["url"] == "/app#refill=md1"
    sent.clear()
    reminders.tick(datetime(2026, 10, 21, 9, 20, tzinfo=reminders.IST))
    assert not [m for m in sent if m["tag"] == "refill-d3"]          # same day: no repeat
    reminders.tick(datetime(2026, 10, 21, 15, 0, tzinfo=reminders.IST))
    assert not [m for m in sent if m["tag"] == "refill-d3"]          # outside the window


def test_page_carries_layer_24():
    html = (ROOT / "web" / "index.html").read_text(encoding="utf-8")
    assert "/*live-p24*/" in html and "SX.medDaysLeft=" in html and "#refill=" in html and "lv24-low" in html
    if not shutil.which("node"):
        return
    js = r"""
const fs=require('fs');const html=fs.readFileSync(process.argv[process.argv.length-1],'utf8');
const i=html.indexOf('/*live-p24*/');const nxt=html.indexOf('/*live-p',i+10);const j=nxt>0?nxt:html.indexOf('SX.boot();\n})();',i);const src=html.slice(i,j);
global.location={hash:'',pathname:'/app'};global.history={replaceState(){}};global.window=global;global.setTimeout=()=>0;
const S={members:[{id:'d3',name:'Kamala Devi',rel:'Mother'}],meds:{d3:[{id:'md1',n:'Metformin 500 mg',when:['Morning','Night'],left:4},{id:'md2',n:'Amlodipine',when:['Morning'],left:30},{id:'md3',n:'Thyronorm',when:['Morning']}]}};
const SX={p:s=>s,S,extend(){},me:()=>S.members[0],save(){},act:{},ico:n=>'<svg/>'};
new Function('SX','S','E','P',src)(SX,S,s=>String(s),SX.p);
const low=SX.lv24.low(S.members[0]);if(low.length!==1||low[0].x.id!=='md1'||low[0].d!==2)throw new Error('low '+JSON.stringify(low.map(o=>[o.x.id,o.d])));
if(SX.lv24.when(0.5)!=='runs out today'||SX.lv24.when(1.5)!=='1 day left'||SX.lv24.when(4.9)!=='4 days left')throw new Error('when');
if(SX.medDaysLeft({when:['Morning'],left:undefined})!==null)throw new Error('uncounted');
console.log('ok');
"""
    r = subprocess.run(["node", "-e", js, "--", str(ROOT / "web" / "index.html")], capture_output=True, text=True, timeout=60)
    assert r.returncode == 0 and "ok" in r.stdout, r.stdout + r.stderr
