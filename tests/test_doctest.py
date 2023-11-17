from pathlib import Path
from textwrap import dedent

import pytest

from pytest_pyodide import run_in_pyodide

DOCTESTS = """\
def pyodide_fail():
    '''
    >>> from js import Object # doctest: +RUN_IN_PYODIDE
    >>> 1 == 2
    True
    '''

def host_success():
    '''
    >>> import sys
    >>> sys.platform == "emscripten"
    False
    '''

def pyodide_success():
    '''
    >>> pyodide_success() # doctest: +RUN_IN_PYODIDE
    7
    >>> from js import Object
    >>> import sys
    >>> sys.platform == "emscripten"
    True
    '''
    return 7
"""


def test_doctest_run(pytester, selenium, request, playwright_browsers, capsys):
    file = pytester.makepyfile(DOCTESTS)
    config = pytester.parseconfigure(file)

    config.playwright_browsers = playwright_browsers

    @run_in_pyodide
    def write_file(selenium, path, contents):
        path.parent.mkdir(exist_ok=True)
        import sys

        sys.path.append(str(path.parent))
        path.write_text(contents)

    write_file(selenium, Path("/test_files/test_doctest_run.py"), DOCTESTS)

    class MyPlugin:
        """Copy a couple of fixtures into the inner pytest

        If we instantiate playwright_browsers twice it breaks playwright
        If we instantiate safari twice it breaks safari
        """

        def pytest_fixture_setup(self, fixturedef, request):
            vals = {"selenium": selenium, "playwright_browsers": playwright_browsers}
            if fixturedef.argname in vals:
                val = vals[fixturedef.argname]
                cache_key = fixturedef.cache_key(request)
                fixturedef.cached_result = (val, cache_key, None)
                return val

    result = pytester.inline_run(
        file,
        "--doctest-modules",
        "--dist-dir",
        request.config.getoption("--dist-dir"),
        "--rt",
        ",".join(pytest.pyodide_runtimes),
        "--runner",
        request.config.option.runner,
        "--rootdir",
        str(file.parent),
        plugins=(MyPlugin(),),
    )
    if not pytest.pyodide_runtimes:
        result.assertoutcome(passed=1)
        return
    result.assertoutcome(passed=2, failed=1)
    result.getfailures()[0]
    captured = capsys.readouterr()
    expected = dedent(
        """
        003     >>> from js import Object # doctest: +RUN_IN_PYODIDE
        004     >>> 1 == 2
        Expected:
            True
        Got:
            False
        """
    ).strip()
    print(captured.out)
    assert expected in captured.out


def test_doctest_collect(pytester):
    BROWSERS = ["chrome", "firefox", "node", "safari"]
    BROWSER_TESTS = []
    for b in BROWSERS:
        BROWSER_TESTS.append(f"pyodide_fail[{b}]"),
        BROWSER_TESTS.append(f"pyodide_success[{b}]"),
    HOST_TESTS = ["host_success"]

    def check(rt, expected):
        path = pytester.makepyfile(DOCTESTS)
        items, reprec = pytester.inline_genitems(
            path, "--doctest-modules", "--rt", ",".join(rt)
        )
        assert sorted(
            [i.name.removeprefix("test_doctest_collect.") for i in items]
        ) == sorted(expected)

    check(BROWSERS + ["chrome-no-host"], BROWSER_TESTS)
    check(["host"], HOST_TESTS)
    check(BROWSERS + ["host"], BROWSER_TESTS + HOST_TESTS)
