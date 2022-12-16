# these tests are run using the run-in-pyodide option from test_run_in_pyodide.py
# test_fail is expected to fail obviously!


def test_success():
    print("WOOO")


def test_fail():
    print("Oh dear")
    assert 1 == 0


def test_check_in_pyodide():
    print("Check in pyodide")
    try:
        import pyodide

        dir(pyodide)
    except ImportError:
        assert "Not in pyodide" == 0