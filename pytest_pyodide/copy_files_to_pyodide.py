from collections.abc import MutableSequence, Sequence
from pathlib import Path
from typing import Any

from .server import spawn_web_server

_copied_files: dict[Any, MutableSequence[tuple[Path, str]]] = {}


def copy_files_to_emscripten_fs(
    file_list: Sequence[Path | str | tuple[Path | str, Path | str]],
    selenium: Any,
    install_wheels=True,
    recurse_directories=True,
):
    """
    Copies files in file_list to the emscripten file system. Files
    are passed as a list of source Path / install Path pairs.


    Parameters:
        file_list (Sequence[Path|str|tuple[Path | str, Path | str]]): A list of files, directories or glob patterns to copy as (src,destination) pairs. Destination is relative to the current
        directory on pyodide. If a single filename is passed for an entry, the destination is chosen relative to the current working directory.

        selenium : The pytest selenium fixture which hosts the pyodide to copy to.

        install_wheels (bool): If True, any wheels in the copy list are installed instead of copied.

        recurse_directories (bool): If this is True, subdirectories of directories in file_list will be copied.
    """
    if selenium not in _copied_files:
        _copied_files[selenium] = []
    new_files = []
    for list_entry in file_list:
        if isinstance(list_entry, tuple):
            src, dest_path = Path(list_entry[0]), Path(list_entry[1])
        else:
            src = Path(list_entry).resolve()
            dest_path = Path(list_entry).relative_to(Path.cwd())
        # check if it is a glob
        last_folder = ""
        last_remaining = str(src)
        glob_pattern = None
        glob_base = None
        for i, c in enumerate(str(src)):
            if c in ["*", "[", "]"]:
                glob_pattern = str(last_remaining)
                glob_base = Path(last_folder)
                print(glob_pattern)
                break
            if c == "/":
                last_folder = str(src)[: i + 1]
                last_remaining = str(src)[i + 1 :]
        if src.is_dir():
            # copy all files in directory
            if recurse_directories:
                glob_pattern = "**/*"
                glob_base = src
            else:
                glob_pattern = "./*"
                glob_base = src
        if glob_base and glob_pattern:
            # Multiple files to copy
            print(glob_base, glob_base.resolve())
            glob_base = glob_base.resolve()
            if not glob_base.is_relative_to(Path.cwd()):
                raise RuntimeError(
                    "Can only copy directories to pyodide that are below the current directory"
                )
            for f in glob_base.glob(glob_pattern):
                if f.is_dir():
                    continue
                relative_path = f.relative_to(glob_base)
                file_dest = Path(dest_path, relative_path)
                if (f, str(file_dest)) not in _copied_files[selenium]:
                    new_files.append((f, str(file_dest)))
        else:
            # Single file to copy
            src = src.resolve()
            if not src.is_relative_to(Path.cwd()):
                raise RuntimeError(
                    "Can only copy files to pyodide that are below the current directory"
                )
            if (src, str(dest_path)) not in _copied_files[selenium]:
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
            _copied_files[selenium].append((file, dest))
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
