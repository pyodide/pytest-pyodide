import pathlib

import pytest


def test_web_server_secondary(selenium, web_server_secondary):
    host, port, logs = web_server_secondary
    assert pathlib.Path(logs).exists()
    assert selenium.server_port != port


def test_host(request):
    runtime = request.config.option.runtime
    assert runtime == "host", "this test should only run when runtime is host"


def test_runtime(selenium, request):
    runtime = request.config.option.runtime
    assert runtime != "host", "this test should only run when runtime is not host"


def test_doctest():
    """
    >>> 1+1
    2
    """
    pass


def test_deprecated():
    import warnings

    warnings.simplefilter("always", DeprecationWarning)
    with pytest.warns(DeprecationWarning):
        import pytest_pyodide.browser  # noqa
