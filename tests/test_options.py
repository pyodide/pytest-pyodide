import pytest


def test_dist_dir(pytester):

    dist_dir = "dist"

    pytester.makepyfile(
        f"""
        import pytest
        def test_dist_dir(request):
            assert request.config.option.getoption("--dist-dir") == {dist_dir!r}
        """
    )

    result = pytester.runpytest("--dist-dir", dist_dir)
    result.assert_outcomes(passed=1)


@pytest.mark.parametrize("runner", ["selenium", "playwright"])
def test_runner(pytester, runner):
    pytester.makepyfile(
        f"""
        import pytest
        def test_dist_dir(request):
            assert request.config.option.getoption("--runner") == {runner!r}
        """
    )

    result = pytester.runpytest("--runner", runner)
    result.assert_outcomes(passed=1)


def test_invalid_runner(pytester):

    runner = "blah"

    pytester.makepyfile(
        f"""
        import pytest
        def test_dist_dir(request):
            assert request.config.option.getoption("--runner") == {runner!r}
        """
    )

    result = pytester.runpytest("--runner", runner)
    result.assert_outcomes(failed=1)
