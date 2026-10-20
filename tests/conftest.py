import os
import glob as _glob
for _old in _glob.glob("./data/test_*.db*"):  # every run starts from an empty store (fixed UTRs, stock counts and the like must not carry over)
    try:
        os.remove(_old)
    except OSError:
        pass
os.environ.setdefault("APP_ENV", "test")   # demo one-time codes are refused in production

import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from api import auth
    auth._HITS.clear()
    yield
    auth._HITS.clear()
