import pytest

from pytest_pyodide.decorator import run_in_pyodide
from pytest_pyodide.fixture import rename_fixture


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


@rename_fixture("myfixture", "myfixture_variant")
def myfunc(a, myfixture):
    return [a, myfixture]


def test_rename_fixture1():
    assert myfunc(2, 3) == [2, 3]
    assert myfunc(2, myfixture_variant=3) == [2, 3]
    assert myfunc(a=2, myfixture_variant=3) == [2, 3]


@pytest.fixture
def myfixture():
    yield 27


@pytest.fixture
def myfixture_variant():
    yield 99


@rename_fixture("myfixture", "myfixture_variant")
def test_rename_fixture2(myfixture):
    assert myfixture == 99
