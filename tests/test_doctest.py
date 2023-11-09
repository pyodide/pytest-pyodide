import os
from pathlib import Path
from textwrap import dedent

import pytest

from pytest_pyodide import run_in_pyodide
from pytest_pyodide.run_tests_inside_pyodide import (
    close_pyodide_browsers,
    get_browser_pyodide,
)

DOCTESTS = """\
def pyodide_success():
    '''
    >>> from js import Object # doctest: +RUN_IN_PYODIDE
    >>> pyodide_success()
    7
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


def test_doctest_run(pytester, request):
    # Help playwright find the cache
    os.environ["XDG_CACHE_HOME"] = str(Path(ORIG_HOME) / ".cache")
    pytester.makepyfile(DOCTESTS)

    @run_in_pyodide
    def write_file(selenium, path, contents):
        path.parent.mkdir(exist_ok=True)
        import sys

        sys.path.append(str(path.parent))
        path.write_text(contents)

    for runtime in pytest.pyodide_runtimes:
        selenium = get_browser_pyodide(request, runtime)
        write_file(selenium, Path("/test_files/test_doctest_run.py"), DOCTESTS)

    result = pytester.runpytest(
        "--doctest-modules",
        "--dist-dir",
        request.config.getoption("--dist-dir"),
        "--rt",
        request.config.option.runtime,
    )
    if not pytest.pyodide_runtimes:
        result.assert_outcomes(passed=1)
        return
    result.assert_outcomes(passed=2, failed=1)
    result.stdout.fnmatch_lines(
        dedent(
            """
            014     >>> from js import Object # doctest: +RUN_IN_PYODIDE
            015     >>> 1 == 2
            Expected:
                True
            Got:
                False
            """
        )
        .strip()
        .splitlines(),
        consecutive=True,
    )
    close_pyodide_browsers()


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
