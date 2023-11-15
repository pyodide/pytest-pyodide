import os
from pathlib import Path
from textwrap import dedent

import pytest

DOCTESTS = """\
def pyodide_success():
    '''
    >>> from js import Object # doctest: +RUN_IN_PYODIDE
    >>> import sys
    >>> sys.platform == "emscripten"
    True
    '''
    return 7

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
"""

ORIG_HOME = os.environ.get("HOME", None)


def test_doctest_run(pytester, request, runtime, playwright_browsers, capsys):
    # Help playwright find the cache
    os.environ["XDG_CACHE_HOME"] = str(Path(ORIG_HOME) / ".cache")
    file = pytester.makepyfile(DOCTESTS)
    config = pytester.parseconfigure(file)

    config.playwright_browsers = playwright_browsers

    class MyPlugin:
        def pytest_fixture_setup(self, fixturedef, request):
            if fixturedef.argname == "playwright_browsers":
                my_cache_key = fixturedef.cache_key(request)
                fixturedef.cached_result = (playwright_browsers, my_cache_key, None)
                return playwright_browsers

    result = pytester.inline_run(
        file,
        "--doctest-modules",
        "--dist-dir",
        request.config.getoption("--dist-dir"),
        "--rt",
        runtime,
        "--runner",
        request.config.option.runner,
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
        012     >>> from js import Object # doctest: +RUN_IN_PYODIDE
        013     >>> 1 == 2
        Expected:
            True
        Got:
            False
        """
    ).strip()
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
