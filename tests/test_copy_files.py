from pathlib import Path

import pytest

from pytest_pyodide.decorator import copy_files_to_pyodide, run_in_pyodide


@copy_files_to_pyodide(
    [(Path(__file__).parent, "non_recursive_test")], recurse_directories=False
)
def test_non_recursive_decorator(selenium):
    should_exist = f"non_recursive_test/{Path(__file__).name}"
    should_not_exist = "non_recursive_test/datafiles/in_pyodide_tests.py"
    selenium.run(
        f"""
        with open("{should_exist}") as f:
            txt = f.read()
            assert(txt.find("test_non_recursive_decorator")!=-1)
        try:
            open("{should_not_exist}","r")
            assert("File {should_not_exist} was copied")
        except IOError:
            pass
        """
    )


@copy_files_to_pyodide(
    [(Path(__file__).parent, "recursive_test")], recurse_directories=True
)
def test_recursive_decorator(selenium):
    should_exist = f"recursive_test/{Path(__file__).name}"
    should_also_exist = "recursive_test/datafiles/in_pyodide_tests.py"
    selenium.run(
        f"""
        with open("{should_exist}") as f:
            assert(txt.find("test_non_recursive_decorator")!=-1)
        try:
            open("{should_also_exist}","r")
        except IOError:
            assert("File {should_also_exist} was not copied")
        """
    )


# possible test cases = list of a)tuple, b)path, c) folder name, d) glob pattern
@copy_files_to_pyodide(
    [
        (__file__, "test.py"),
        __file__,
        (Path(__file__).parent, "testfiles"),
        (str(Path(__file__).parent) + "/test*.py", "python_only"),
    ]
)
def test_copy_files_decorator(selenium):
    auto_target_path = Path(__file__).relative_to(Path.cwd())
    selenium.run(
        f"""
    with open("test.py") as f:
        txt = f.read()
    assert(txt.find("test_copy_files_decorator test 1")!=-1)

    with open("{auto_target_path}") as f:
        txt = f.read()
    assert(txt.find("test_copy_files_decorator test 2")!=-1)

    with open("testfiles/test_copy_files.py") as f:
        txt = f.read()
    assert(txt.find("test_copy_files_decorator test 3")!=-1)

    with open("python_only/test_copy_files.py") as f:
        txt = f.read()
    assert(txt.find("test_copy_files_decorator test 4")!=-1)
    """
    )


@copy_files_to_pyodide([(__file__, "test2.py")])
@run_in_pyodide
def test_copy_files_run_in_pyodide_decorator(selenium):
    with open("test2.py") as f:
        txt = f.read()
    assert txt.find("test_copy_files_decorator test 3") != -1


def test_bad_copy_files_decorator(selenium):
    try:
        # copy all files in bad folder
        @copy_files_to_pyodide([("/*.py", "test_folder")])
        def should_throw_fn(selenium):
            pass

        should_throw_fn(selenium)
        pytest.fail(
            "Copy files to pyodide should fail if source is above current directory"
        )
    except RuntimeError:
        pass
    try:
        # copy single bad file
        @copy_files_to_pyodide([("/test.py", "test.py")])
        def should_throw_fn2(selenium):
            pass

        should_throw_fn2(selenium)
        pytest.fail(
            "Copy files to pyodide should fail if source is above current directory"
        )
    except RuntimeError:
        pass


def test_copy_files_fails_if_no_selenium():
    with pytest.raises(RuntimeError):

        @copy_files_to_pyodide([(__file__, "test2.py")])
        def should_throw_fn():
            pass

        should_throw_fn()


def test_copy_files_run_install_wheel(selenium):
    wheel_path = (
        Path(__file__).parent
    ) / "datafiles/pyodide_http-0.2.0-py3-none-any.whl"

    @copy_files_to_pyodide([(wheel_path, "pyodide_http-0.2.0-py3-none-any.whl")])
    def install_package_and_try_import(selenium):
        selenium.run("""import pyodide_http""")

    install_package_and_try_import(selenium)
