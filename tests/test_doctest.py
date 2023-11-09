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


def test_doctest_run(pytester, request):
    pytester.makepyfile(DOCTESTS)
    from pathlib import Path

    result = pytester.runpytest(
        "--doctest-modules",
        "--dist-dir",
        Path(__file__).parents[1] / "pyodide",
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
            011     >>> from js import Object # doctest: +RUN_IN_PYODIDE
            012     >>> 1 == 2
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
