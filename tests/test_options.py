import pytest

from pytest_pyodide.hook import _filter_runtimes


def test_dist_dir(pytester):
    dist_dir = "dist"

    pytester.makepyfile(
        f"""
        import pytest
        def test_option(request):
            assert str(request.config.getoption("--dist-dir", "")) == {dist_dir!r}
        """
    )

    result = pytester.runpytest("--dist-dir", dist_dir)
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
