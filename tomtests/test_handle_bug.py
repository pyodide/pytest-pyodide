import pytest

from pytest_pyodide import run_in_pyodide


@pytest.fixture
@run_in_pyodide
def macguffin(selenium):
    from pytest_pyodide.decorator import PyodideHandle

    s = {"a": 1}
    return PyodideHandle(s)


@run_in_pyodide
def test_macguffin(selenium, macguffin):
    assert macguffin["a"] == 1
