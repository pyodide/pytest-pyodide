from pathlib import Path

import pytest

from pytest_pyodide.copy_files_to_pyodide import copy_files_to_emscripten_fs
from pytest_pyodide.run_tests_inside_pyodide import (
    close_pyodide_browsers,
    get_browser_pyodide,
    run_test_in_pyodide,
)


# fixture to copy the test file across
@pytest.fixture(scope="module")
def remote_test_file(request, runtime):
    try:
        datafile_path = (
            Path(__file__).parent / "datafiles/in_pyodide_tests.py"
        ).resolve()
        datafile_path = datafile_path.relative_to(Path.cwd())
        dest_path = Path("test_files", datafile_path)
        print(dest_path, datafile_path)
        selenium = get_browser_pyodide(request, runtime)
        copy_files_to_emscripten_fs(
            [(datafile_path, dest_path)], selenium, install_wheels=False
        )
        yield dest_path
    finally:
        close_pyodide_browsers()


def test_fail_test(remote_test_file, runtime):
    success = run_test_in_pyodide(
        f"{remote_test_file}::test_fail", runtime, ignore_fail=True
    )
    assert success is False


def test_succeed_test(remote_test_file, runtime):
    run_test_in_pyodide(f"{remote_test_file}::test_success", runtime, ignore_fail=False)


def test_running_in_pyodide(remote_test_file, runtime):
    run_test_in_pyodide(
        f"{remote_test_file}::test_check_in_pyodide", runtime, ignore_fail=False
    )


def test_pyodide_tests_skipped_inside_pyodide(remote_test_file, runtime):
    run_test_in_pyodide(
        f"{remote_test_file}::test_this_doesnt_run", runtime, ignore_fail=False
    )
