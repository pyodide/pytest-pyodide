def test_run_webworker(selenium_webworker_standalone, script_type):
    selenium = selenium_webworker_standalone
    output = selenium.run_webworker(
        """
        import sys
        sys.version
        """
    )
    assert isinstance(output, str)
