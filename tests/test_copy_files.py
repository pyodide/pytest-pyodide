from pathlib import Path

from pytest_pyodide.decorator import copy_files_to_pyodide, run_in_pyodide


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
        txt=f.read()
    assert(txt.find("test_copy_files_decorator test 1")!=-1)
    with open("{auto_target_path}") as f:
        txt=f.read()
    assert(txt.find("test_copy_files_decorator test 2")!=-1)
    with open("testfiles/test_copy_files.py") as f:
        txt=f.read()
    assert(txt.find("test_copy_files_decorator test 3")!=-1)
    with open("python_only/test_copy_files.py") as f:
        txt=f.read()
    assert(txt.find("test_copy_files_decorator test 4")!=-1)
    """
    )


@copy_files_to_pyodide([(__file__, "test2.py")])
@run_in_pyodide
def test_copy_files_run_in_pyodide_decorator(selenium):
    with open("test2.py") as f:
        txt = f.read()
    assert txt.find("test_copy_files_decorator test 3") != -1
