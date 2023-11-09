from textwrap import dedent


def test_doctest1(pytester):
    pytester.makepyfile(
        dedent(
            """
            def doctest_pyodide_success():
                '''
                >>> from js import Object # doctest: +RUN_IN_PYODIDE
                >>> import sys
                >>> sys.platform == "emscripten"
                True
                '''

            def doctest_pyodide_fail():
                '''
                >>> from js import Object # doctest: +RUN_IN_PYODIDE
                >>> 1 == 2
                True
                '''

            def doctest_host_success():
                '''
                >>> import sys
                >>> sys.platform == "emscripten"
                False
                '''
            """
        )
    )
    from pathlib import Path

    result = pytester.runpytest(
        "--doctest-modules", "--dist-dir", Path(__file__).parents[1] / "pyodide"
    )
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
