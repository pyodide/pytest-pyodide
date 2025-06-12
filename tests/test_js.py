from pytest_pyodide import run_in_pyodide


@run_in_pyodide()
def test_js_globals(selenium_standalone):
    import js

    assert hasattr(js, "fetch")
    assert hasattr(js, "Object")
    assert hasattr(js, "AbortController")
    assert hasattr(js, "AbortSignal")
    assert hasattr(js, "setTimeout")
    assert hasattr(js, "clearTimeout")
    assert hasattr(js, "setInterval")
    assert hasattr(js, "Request")
    assert hasattr(js, "Response")
