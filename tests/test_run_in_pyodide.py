from pathlib import Path

import pytest

from pytest_pyodide.copy_files_to_pyodide import copy_files_to_emscripten_fs
from pytest_pyodide.run_tests_inside_pyodide import run_test_in_pyodide


# fixture to copy the test file across
@pytest.fixture(scope="function")
def remote_test_file(selenium):
    datafile_path = (Path(__file__).parent / "datafiles/in_pyodide_tests.py").resolve()
    datafile_path = datafile_path.relative_to(Path.cwd())
    dest_path = Path("test_files", datafile_path)
    copy_files_to_emscripten_fs(
        [(datafile_path, dest_path)], selenium, install_wheels=False
    )
    yield dest_path


def test_fail_test(remote_test_file, selenium):
    success = run_test_in_pyodide(
        f"{remote_test_file}::test_fail", selenium, ignore_fail=True
    )
    assert success is False


@pytest.mark.xfail
def test_xfail_test(remote_test_file, selenium):
    run_test_in_pyodide(f"{remote_test_file}::test_fail", selenium, ignore_fail=False)


def test_succeed_test(remote_test_file, selenium):
    run_test_in_pyodide(
        f"{remote_test_file}::test_success", selenium, ignore_fail=False
    )


def test_running_in_pyodide(remote_test_file, selenium):
    run_test_in_pyodide(
        f"{remote_test_file}::test_check_in_pyodide", selenium, ignore_fail=False
    )


def test_pyodide_tests_skipped_inside_pyodide(remote_test_file, selenium):
    run_test_in_pyodide(
        f"{remote_test_file}::test_this_doesnt_run", selenium, ignore_fail=False
    )
