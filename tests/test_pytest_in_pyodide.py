def test_success():
    print("WOOO")

def test_fail():
    print("Oh dear")
    assert(1==0)    

def test_check_in_pyodide():
    print("Check in pyodide")
    try:
        import pyodide
    except ImportError:
        assert("Not in pyodide"==0)
