"""The launch period: every plan is free until 31 March 2027.

Families are what we need first, so nothing in the app is sold to them for now — the money comes from lab bookings,
medicine orders and the shop. The subscription machinery (plans, invoices, Razorpay, UPI, settlements) stays exactly
where it is, switched off behind one check: `free_now()`. Every quota, gate and price surface reads it, so turning
paid plans back on is one environment variable (`FREE_UNTIL=`) and a restart, not a release.

    FREE_UNTIL=2027-03-31   (default; the last day everything is free, IST)
    FREE_UNTIL=             (empty: the launch period is over, stored plans apply again)
"""
from __future__ import annotations

import os
import time
from datetime import date, datetime, timedelta, timezone

IST = timezone(timedelta(hours=5, minutes=30))
PLAN = "plus"                 # what every family gets while the launch period runs
DEFAULT = "2027-03-31"


def _raw() -> str:
    return os.getenv("FREE_UNTIL", DEFAULT).strip()


def until() -> date | None:
    """The last day on which everything is free, or None when the launch period is switched off."""
    s = _raw()
    if not s:
        return None
    try:
        return date.fromisoformat(s)
    except ValueError:
        print(f"[launch] FREE_UNTIL={s!r} is not a YYYY-MM-DD date; the launch period is off", flush=True)
        return None


def until_ts() -> int | None:
    """End of that day in IST, as a unix timestamp — what the app shows and counts down to."""
    d = until()
    if not d:
        return None
    return int(datetime(d.year, d.month, d.day, 23, 59, 59, tzinfo=IST).timestamp())


def free_now() -> bool:
    ts = until_ts()
    return bool(ts and time.time() <= ts)


def label() -> str:
    """'31 March 2027' — for sentences the family reads."""
    d = until()
    return d.strftime("%d %B %Y").lstrip("0") if d else ""


def plan_of(h) -> str:
    """The plan a family's quotas should be read against: everything while the launch period runs, else what they pay for."""
    return PLAN if free_now() else getattr(h, "plan", "free")


def state() -> dict:
    """What the app and the site need to say it: {free, until, label}."""
    return {"free": free_now(), "until": until_ts(), "label": label()}
