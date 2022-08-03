import pytest

from pytest_pyodide import run_in_pyodide


@pytest.mark.xfail_browsers(
    node="Should xfail",
    firefox="Should xfail",
    chrome="Should xfail",
    safari="Should xfail",
)
@run_in_pyodide
def test_xfail_browser(selenium):
    raise AssertionError("This test should xfail")
