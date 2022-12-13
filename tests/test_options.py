def test_dist_dir(pytester):

    dist_dir = "dist"

    pytester.makepyfile(
        f"""
        def test_dist_dir():
            assert pytest.pyodide_dist_dir == {dist_dir!r}
        """
    )

    result = pytester.runpytest("--dist-dir", dist_dir)
    result.assert_outcomes(passed=1)
