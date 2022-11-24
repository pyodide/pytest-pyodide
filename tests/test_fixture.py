import pytest

from pytest_pyodide.decorator import run_in_pyodide


@pytest.mark.parametrize("dummy", [1, 2, 3])
@run_in_pyodide
def test_selenium_standalone_refresh(selenium_standalone_refresh, dummy):
    import pathlib

    p = pathlib.Path("/hello")

    assert not p.exists()

    p.write_text("hello world")

    assert p.is_file()
