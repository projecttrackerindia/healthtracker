import os
import glob as _glob

# Every test writes sqlite:///./data/test_<name>.db, and /data/ is git-ignored — so it does not exist in a
# fresh clone and SQLite cannot create a file inside a directory that is not there. The suite passed for
# everyone who had run the app locally and failed for everyone who had not, which is the worst way for a test
# suite to behave: green on the machine that wrote it, red on CI and on a new contributor's first morning.
os.makedirs("./data", exist_ok=True)

for _old in _glob.glob("./data/test_*.db*"):  # every run starts from an empty store (fixed UTRs, stock counts and the like must not carry over)
    try:
        os.remove(_old)
    except OSError:
        pass
os.environ.setdefault("APP_ENV", "test")   # demo one-time codes are refused in production

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    """Both layers of the limiter, between every test.

    The in-process deque is not the whole story any more: the counter is also kept in the database so that it
    holds across containers, and that half survives everything the test harness does to memory. Left alone, a
    full suite run spends the signup budget somewhere around the ninth test that signs anybody up, and every
    test after that gets a 429 from a limiter that is working exactly as intended."""
    from api import auth
    auth._HITS.clear()
    _clear_shared()
    yield
    auth._HITS.clear()
    _clear_shared()


def _clear_shared():
    try:
        from api.db import session
        from api.models import RateHit
        with session() as db:
            db.query(RateHit).delete()
    except Exception:
        pass        # the table does not exist yet on the very first test to touch the database
