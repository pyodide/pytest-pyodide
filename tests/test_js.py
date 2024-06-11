from pytest_pyodide import run_in_pyodide


@run_in_pyodide()
def test_js_globals(selenium_standalone):
    import js

    hasattr(js, "fetch")
    hasattr(js, "Object")
    hasattr(js, "AbortController")
    hasattr(js, "AbortSignal")
    hasattr(js, "setTimeout")
    hasattr(js, "clearTimeout")
    hasattr(js, "setInterval")
