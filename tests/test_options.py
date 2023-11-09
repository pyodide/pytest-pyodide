from pathlib import Path
from textwrap import dedent

import pytest

from pytest_pyodide.hook import _filter_runtimes


def test_dist_dir(pytester):
    dist_dir = str(Path("dist").resolve())

    pytester.makepyfile(
        f"""
        import pytest
        def test_option(request):
            assert str(request.config.getoption("--dist-dir", "")) == {dist_dir!r}
        """
    )

    result = pytester.runpytest("--dist-dir", "dist")
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("runner", ["selenium", "playwright"])
def test_runner(pytester, runner):
    pytester.makepyfile(
        f"""
        import pytest
        def test_option(request):
            assert request.config.getoption("--runner") == {runner!r}
        """
    )

    result = pytester.runpytest("--runner", runner)
    result.assert_outcomes(passed=1)


def test_invalid_runner(pytester):
    runner = "blah"

    pytester.makepyfile(
        f"""
        import pytest
        def test_option(request):
            assert request.config.getoption("--runner") == {runner!r}
        """
    )

    result = pytester.runpytest("--runner", runner)

    # pytest: error argument --runner: invalid choice ...
    assert result.ret == 4


@pytest.mark.parametrize(
    "_runtime",
    [
        "invalid",
    ],
)
def test_invalid_runtime(pytester, _runtime):
    _runtime.split(",")

    pytester.makepyfile(
        """
        import pytest
        def test_option():
            assert True
        """
    )

    # TODO: catch internal errors directly?
    with pytest.raises(ValueError, match="Pytest terminal summary report not found"):
        result = pytester.runpytest("--runtime", _runtime)
        result.assert_outcomes(errors=1)


@pytest.mark.parametrize(
    "_runtime,expected",
    [
        ("chrome", (True, {"chrome"})),
        ("firefox", (True, {"firefox"})),
        ("node", (True, {"node"})),
        ("chrome,firefox", (True, {"chrome", "firefox"})),
        ("chrome-no-host,firefox", (False, {"chrome", "firefox"})),
        ("host", (True, set())),
        ("chrome-no-host,host", (True, {"chrome"})),
    ],
)
def test_filter_runtimes(_runtime, expected):
    assert _filter_runtimes(_runtime) == expected


def test_options_pytester(pytester):
    pytester.makepyfile(
        dedent(
            """
            import pytest
            from pathlib import Path

            def test_options_pytester():
                assert pytest.pyodide_run_host_test == True
                assert pytest.pyodide_runtimes == set(["chrome","firefox","safari","node"])
                assert pytest.pyodide_dist_dir == Path("some_weird_dir").resolve()
            """
        )
    )
    run_host = pytest.pyodide_run_host_test
    runtimes = pytest.pyodide_runtimes
    dist_dir = pytest.pyodide_dist_dir

    result = pytester.runpytest(
        "--dist-dir",
        Path(__file__).parents[1] / "pyodide",
        "--rt",
        "chrome,firefox,safari,node",
        "--dist-dir",
        "some_weird_dir",
    )
    result.assert_outcomes(passed=1)

    assert run_host == pytest.pyodide_run_host_test
    assert runtimes == pytest.pyodide_runtimes
    assert dist_dir == pytest.pyodide_dist_dir
