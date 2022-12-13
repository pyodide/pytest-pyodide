import pytest


def test_dist_dir(pytester):

    dist_dir = "dist"

    pytester.makepyfile(
        f"""
        import pytest
        def test_option(request):
            assert request.config.getoption("--dist-dir") == {dist_dir!r}
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
    result.assert_outcomes(failed=1)


@pytest.mark.parametrize(
    "runtime",
    [
        "chrome",
        "firefox",
        "safari",
        "node",
        "chrome-no-host",
        "firefox-no-host",
        "safari-no-host",
        "node-no-host",
        "firefox chrome",
    ],
)
def test_runtime(pytester, runtime):

    runtimes = runtime.split()

    pytester.makepyfile(
        f"""
        import pytest
        def test_option(request):
            assert request.config.getoption("--runtime") == {runtimes!r}
        """
    )

    result = pytester.runpytest("--runtime", *runtimes)
    result.assert_outcomes(passed=1)


def test_invalid_runtime(pytester):

    runtimes = ["blah"]

    pytester.makepyfile(
        f"""
        import pytest
        def test_option(request):
            assert request.config.getoption("--runtime") == {runtimes!r}
        """
    )

    result = pytester.runpytest("--runtime", *runtimes)
    result.assert_outcomes(failed=1)
