from pathlib import Path
from typing import Any

import pytest

from .server import spawn_web_server

_seleniums: dict[str, list[Any]] = {}
_copied_files = []
_playwright_browsers = None


# class to take a generator (e.g. a pytest fixture or something)
# and unwrap it so that it can be used for the whole of the module
class Degenerator:
    def __init__(self, gen):
        self.gen = gen
        self.value = gen.__enter__()

    def get_value(self):
        return self.value

    def __del__(self):
        self.close()

    def close(self):
        if self.gen is not None:
            self.gen.__exit__(None, None, None)
            self.value = None


def init_pyodide_runner(request, runtime):
    global _playwright_browsers
    from .fixture import playwright_browsers, selenium_common

    if request.config.option.runner.lower == "playwright":
        _playwright_browsers = playwright_browsers(request)
    if runtime in _seleniums:
        return _seleniums[runtime][0].get_value()
    web_server_main = Degenerator(spawn_web_server(request.config.option.dist_dir))
    # open pyodide
    _seleniums[runtime] = [
        Degenerator(
            selenium_common(
                request,
                runtime,
                web_server_main.get_value(),
                browsers=_playwright_browsers,
            )
        ),
        web_server_main,
    ]
    return _seleniums[runtime][0].get_value()


def copy_files_to_pyodide(file_list, request, runtime):
    new_files = []
    for x in file_list:
        if x.is_dir():
            continue
        if x not in _copied_files:
            new_files.append(x.resolve())
    if len(new_files) == 0:
        return
    base_path = Path.cwd()
    selenium = init_pyodide_runner(request, runtime)
    with spawn_web_server(base_path) as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"
        # fetch all files into the pyodide
        # n.b. this might be slow for big packages
        selenium.run(
            """
            from pyodide.http import pyfetch
            all_fetches=[]
            """
        )
        for file in new_files:
            _copied_files.append(file)
            file_url = base_url + str(file.relative_to(base_path))
            if file.suffix == ".whl":
                # wheel - install the wheel on the pyodide side before
                # any fetches
                selenium.run_async(
                    f"""
                    import micropip
                    await micropip.install("{file_url}")
                    """
                )
            else:
                # add file to fetches
                selenium.run_async(
                    f"""
                    all_fetches.append(pyfetch("{file_url}"))
                    """
                )
        # fetch everything all at once
        selenium.run_async(
            """
            import asyncio,os,os.path
            for coro in asyncio.as_completed(all_fetches):
                response=await coro
                bare_path="/".join(response.url.split("/")[3:])
                write_path="./test_files/"+bare_path
                #print("Writing: "+bare_path)
                os.makedirs(os.path.dirname(write_path),exist_ok=True)
                with open(write_path,"wb") as fp:
                    byte_data=await response.bytes()
                    fp.write(byte_data)
            """
        )


def run_test_in_pyodide(node_tree_id, runtime, ignore_fail=False):
    selenium = _seleniums[runtime][0].get_value()
    all_args = ["./test_files/" + node_tree_id, "--color=no"]
    #    all_args = ["./test_files/" + node_tree_id, "-q", "--color=no"]
    ret_error = selenium.run_async(
        f"""
        import pytest
        out_buf=""
        def write_out(line):
            global out_buf
            out_buf+=line
        import sys
        sys.stdout.write=write_out
        sys.stderr.write=write_out
        print("{all_args}")
        retcode=pytest.main({all_args})
        if retcode==0:
            out_buf=""
        out_buf

    """
    )
    if len(ret_error) != 0:
        print("ERR:", ret_error, "\n*******************")
        ret_error_lines = ret_error.splitlines()
        fail_error = []
        fail_stdout = []
        recording_error = False
        recording_stdout = False
        for line in ret_error_lines:
            if line.find(" FAILURES ") != -1:
                recording_error = True
            elif line.find("Captured stdout") != -1:
                recording_stdout = True
                recording_error = False
            elif line.find("========= short test summary") != -1:
                recording_error = False
                recording_stdout = False
            elif recording_error:
                fail_error.append(line)
            elif recording_stdout:
                fail_stdout.append(line)
        print("\n".join(fail_stdout))
        if not ignore_fail:
            pytest.fail("\n".join(fail_error[1:]), pytrace=False)
        return False
    return True


def close_test_in_pyodide_servers():
    global _seleniums
    for x in _seleniums.values():
        x[0].close()
    del _seleniums
