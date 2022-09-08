import pathlib

import pytest


def test_web_server_secondary(selenium, web_server_secondary):
    host, port, logs = web_server_secondary
    assert pathlib.Path(logs).exists()
    assert selenium.server_port != port


def test_host():
    assert (
        pytest.pyodide_run_host_test
    ), "this test should only run when host test is enabled"


def test_runtime(selenium):
    assert (
        pytest.pyodide_runtimes
    ), "this test should only run when runtime is specified"


def test_doctest():
    """
    >>> 1+1
    2
    """
    pass
