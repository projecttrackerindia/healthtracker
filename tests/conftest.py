import pytest


@pytest.fixture(autouse=True)
def _reset_rate_limits():
    from api import auth
    auth._HITS.clear()
    yield
    auth._HITS.clear()
