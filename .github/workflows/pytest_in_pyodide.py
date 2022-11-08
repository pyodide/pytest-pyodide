import pytest

from pytest_pyodide.decorator import run_in_pyodide

def pytest_addoption(parser):
    parser.addoption("--extra_args", action="store")

@pytest.fixture(scope='session')
def name(request):
    name_value = request.config.option.extra_args
    if name_value is None:
        pytest.skip()
    return name_value


def _copy_files_to_pyodide(selenium):
     with spawn_web_server(".") as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"
        # fetch all files into the pyodide
        # n.b. this might be slow for big packages
        selenium.run(f"""
            from pyodide.http import pyfetch
            all_fetches=[]
            """)
        for file in Path(".").glob("**/*"):
            file_url=base_url+file.relative_to(".")
            if file.suffix==".whl":
                # wheel - install the wheel on the pyodide side
                selenium.run(
                    f"""
                    import micropip
                    await micropip.install("{file_url}")
                    """)

            selenium.run(
                f"""            
                all_fetches.append(pyfetch("{file_url}"))
                """)
        selenium.run(
            """
            import asyncio
            for response in asyncio.as_completed(all_fetches):
                bare_path="/".join(response.url.split("/")[3:])
                write_path="./test_files/"+bare_path
                with open(write_path,"wb") as fp:
                    byte_data=await response.bytes()
                    fp.write(byte_data)
            """)



def test_in_pyodide(selenium,request):
    # load any packages required
    _copy_files_to_pyodide(selenium)
    import pytest    
    extra_args=request.config.getoption("--extra_args")
    pytest.main(
            [
                "./test_files"
                "-vv",
                "-k",
                extra_args.split(" "),
            ]
        )
