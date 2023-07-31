import pytest

from pytest_pyodide.decorator import run_in_pyodide


@pytest.mark.parametrize("dummy", [1, 2, 3])
@run_in_pyodide
def test_selenium_standalone_refresh(selenium_standalone_refresh, dummy):
    import pathlib

    p = pathlib.Path("/hello")

    assert not p.exists()

    p.write_text("hello world")

    assert p.is_file()


def test_playwright_browsers(playwright_browsers, request):
    if request.config.option.runner.lower() != "playwright":
        pytest.skip("this test should only run when playwright is specified")

    runtimes = pytest.pyodide_runtimes

    assert set(playwright_browsers.keys()) == set(runtimes)


@run_in_pyodide
def test_jspi(selenium_jspi):
    from js import WebAssembly

    assert hasattr(WebAssembly, "Suspender")
