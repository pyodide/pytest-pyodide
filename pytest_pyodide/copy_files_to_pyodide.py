from pathlib import Path
from typing import Any

from .server import spawn_web_server

_copied_files: dict[Any, list[Path]] = {}


def copy_files_to_emscripten_fs(
    file_list: list[tuple[Path, Path]], selenium: Any, install_wheels=True
):
    """
    Copies files in file_list to the emscripten file system. Files
    are passed as a list of source Path / install Path pairs.

    If install_wheels is True, any wheels copied are installed.
    """
    if selenium not in _copied_files:
        _copied_files[selenium] = []
    new_files = []
    for src, dest_path in file_list:
        if src.is_dir():
            continue
        src = src.resolve()
        if not src.is_relative_to(Path.cwd()):
            raise RuntimeError(
                "Can only copy files to pyodide that are below the current directory"
            )
        if src not in _copied_files[selenium]:
            new_files.append((src, str(dest_path)))
    if len(new_files) == 0:
        return
    base_path = Path.cwd()
    with spawn_web_server(base_path) as server:
        server_hostname, server_port, _ = server
        base_url = f"http://{server_hostname}:{server_port}/"
        # fetch all files into the pyodide
        # n.b. this might be slow for big packages

        selenium.run(
            """
            import os
            from pathlib import Path
            from pyodide.http import pyfetch
            all_fetches = []
            all_wheels = []

            async def _fetch_file(src,dest):
                response = await pyfetch(src)
                dest.parent.mkdir(parents=True,exist_ok=True)
                with open(dest, "wb") as fp:
                    byte_data = await response.bytes()
                    fp.write(byte_data)

            """
        )
        for file, dest in new_files:
            _copied_files[selenium].append(file)
            file_url = base_url + str(file.relative_to(base_path))
            if file.suffix == ".whl" and install_wheels:
                # wheel - install the wheel on the pyodide side before
                # any fetches (and don't copy it)
                selenium.run_async(
                    f"""
                    all_wheels.append("{file_url}")
                    """
                )
            else:
                # add file to fetches
                selenium.run_async(
                    f"""
                    all_fetches.append(_fetch_file("{file_url}",Path("{dest}")))
                    """
                )
        # install all wheels with micropip
        selenium.run_async(
            """
            import micropip
            await micropip.install(all_wheels)
            """
        )
        # fetch everything all at once
        selenium.run_async(
            """
            import asyncio, os, os.path
            await asyncio.gather(*all_fetches)
            """
        )
