from pathlib import Path

import pytest

from pytest_pyodide.pytest_in_pyodide import (
    close_test_in_pyodide_servers,
    copy_files_to_pyodide,
    run_test_in_pyodide,
)


# this fixture just makes sure that the servers for testing pyodide are
# closed at the end of the test run
@pytest.fixture(scope="module")
def pytest_in_pyodide_servers():
    try:
        yield
    finally:
        close_test_in_pyodide_servers()


def test_fail_test(pytest_in_pyodide_servers, request, runtime):
    in_pyodide_tests = (Path(__file__).parent / "in_pyodide_tests.py").resolve()
    in_pyodide_tests = in_pyodide_tests.relative_to(Path.cwd())
    copy_files_to_pyodide([in_pyodide_tests], request, runtime)
    success = run_test_in_pyodide(
        f"{in_pyodide_tests}::test_fail", runtime, ignore_fail=True
    )
    assert success is False


def test_succeed_test(pytest_in_pyodide_servers, request, runtime):
    in_pyodide_tests = (Path(__file__).parent / "in_pyodide_tests.py").resolve()
    in_pyodide_tests = in_pyodide_tests.relative_to(Path.cwd())
    copy_files_to_pyodide([in_pyodide_tests], request, runtime)
    run_test_in_pyodide(f"{in_pyodide_tests}::test_success", runtime, ignore_fail=False)


def test_running_in_pyodide(pytest_in_pyodide_servers, request, runtime):
    print(request.node.nodeid)
    in_pyodide_tests = (Path(__file__).parent / "in_pyodide_tests.py").resolve()
    in_pyodide_tests = in_pyodide_tests.relative_to(Path.cwd())
    copy_files_to_pyodide([in_pyodide_tests], request, runtime)
    run_test_in_pyodide(
        f"{in_pyodide_tests}::test_check_in_pyodide", runtime, ignore_fail=False
    )
