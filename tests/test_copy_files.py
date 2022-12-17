from pytest_pyodide.decorator import copy_files_to_pyodide, run_in_pyodide


@copy_files_to_pyodide([(__file__, "test.py")])
def test_copy_files_decorator(selenium_standalone):
    selenium_standalone.run(
        """
    with open("test.py") as f:
        txt=f.read()
    assert(txt.find("test_copy_files_decorator")!=-1)
    """
    )


@copy_files_to_pyodide([(__file__, "test2.py")])
@run_in_pyodide
def test_copy_files_run_in_pyodide_decorator(selenium_standalone):
    with open("test2.py") as f:
        txt = f.read()
    assert txt.find("test_copy_files_decorator") != -1
