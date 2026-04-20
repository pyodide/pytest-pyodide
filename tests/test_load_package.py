"""Tests for ``SeleniumBrowserRunner.load_package``.

Pyodide's ``pyodide.loadPackage`` does not raise when a package cannot be
loaded (e.g. the wheel URL 404s or the package name is unknown); it only
invokes the ``errorCallback`` option. Our ``load_package`` wrapper collects
those callback messages and turns them into a ``RuntimeError`` so that the
failure is reported at the call site rather than surfacing later as a
confusing ``ModuleNotFoundError`` inside Pyodide.
"""

import pytest


def test_load_package_succeeds(selenium):
    """Sanity check: loading a package that exists in the Pyodide dist
    must not raise, and the package must be importable afterwards."""
    selenium.load_package("micropip")
    # If the package is really loaded, importing it in Pyodide succeeds.
    selenium.run_js(
        "await pyodide.runPythonAsync('import micropip');"
    )


def test_load_package_bad_url_raises(selenium):
    """A URL that 404s must cause load_package to raise, and the error
    message must mention the failure reported by Pyodide."""
    bad_url = (
        f"http://{selenium.server_hostname}:{selenium.server_port}"
        "/does-not-exist-pytest_pyodide_test.whl"
    )
    with pytest.raises(RuntimeError) as exc_info:
        selenium.load_package(bad_url)

    msg = str(exc_info.value)
    assert "loadPackage" in msg
    assert bad_url in msg


def test_load_package_unknown_name_raises(selenium):
    """An unknown package name must also cause load_package to raise."""
    with pytest.raises(RuntimeError) as exc_info:
        selenium.load_package("definitely-not-a-real-package-xyz")

    msg = str(exc_info.value)
    assert "loadPackage" in msg
    assert "definitely-not-a-real-package-xyz" in msg


def test_load_package_partial_failure_raises(selenium):
    """If a list contains both a valid and an invalid package, the call
    must still raise so the failure is not silently swallowed."""
    with pytest.raises(RuntimeError) as exc_info:
        selenium.load_package(
            ["micropip", "definitely-not-a-real-package-xyz"]
        )

    msg = str(exc_info.value)
    assert "definitely-not-a-real-package-xyz" in msg
