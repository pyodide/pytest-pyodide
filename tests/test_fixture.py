import pytest

from pytest_pyodide.decorator import run_in_pyodide
from pytest_pyodide.fixture import rename_fixture
from pytest_pyodide.hook import _has_standalone_fixture


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


@run_in_pyodide
def test_also_jspi(selenium_also_with_jspi):
    pass


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


def test_has_standalone_fixture(pytester):
    from textwrap import dedent

    pytester.makepyfile(
        dedent(
            """
            from pytest_pyodide.fixture import rename_fixture

            @rename_fixture("selenium", "selenium_standalone")
            def test_example1(selenium):
                pass

            @rename_fixture("selenium_standalone", "selenium_standalone1")
            def test_example2(selenium_standalone):
                pass
            """
        )
    )
    node = pytester.getpathnode("test_has_standalone_fixture.py")
    r = node.collect()
    t1, t2 = r
    assert "test_example1" in t1.name
    assert "test_example2" in t2.name
    assert _has_standalone_fixture(t1)
    assert not _has_standalone_fixture(t2)
