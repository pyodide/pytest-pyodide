"""
Stores the global runtime configuration related to the pytest_pyodide package.
"""

from collections.abc import Iterable, Sequence
from typing import Literal

RUNTIMES = Literal["chrome", "firefox", "node", "safari"]

_global_load_pyodide_script = """
let pyodide = await loadPyodide({ fullStdLib: false, jsglobals : self });
"""


class Config:
    def __init__(self):
        # Flags to be passed to the browser or runtime.
        self.flags: dict[RUNTIMES, list[str]] = {
            "chrome": ["--js-flags=--expose-gc"],
            "firefox": [],
            "node": [],
            "safari": [],
        }

        # The script to be executed to load the Pyodide.
        self.load_pyodide_script: dict[RUNTIMES, str] = {
            "chrome": _global_load_pyodide_script,
            "firefox": _global_load_pyodide_script,
            "node": _global_load_pyodide_script,
            "safari": _global_load_pyodide_script,
        }

        # The script to be executed to initialize the runtime.
        self.initialize_script: str = "pyodide.runPython('');"
        self.node_extra_globals = []

    def set_flags(self, runtime: RUNTIMES, flags: list[str]):
        self.flags[runtime] = flags

    def get_flags(self, runtime: RUNTIMES) -> list[str]:
        return self.flags[runtime]

    def set_load_pyodide_script(self, runtime: RUNTIMES, load_pyodide_script: str):
        self.load_pyodide_script[runtime] = load_pyodide_script

    def get_load_pyodide_script(self, runtime: RUNTIMES) -> str:
        return self.load_pyodide_script[runtime]

    def set_initialize_script(self, initialize_script: str):
        self.initialize_script = initialize_script

    def get_initialize_script(self) -> str:
        return self.initialize_script

    def add_node_extra_globals(self, l: Iterable[str]):
        self.node_extra_globals.extend(l)

    def get_node_extra_globals(self) -> Sequence[str]:
        return self.node_extra_globals


SINGLETON = Config()


def get_global_config() -> Config:
    """
    Return the singleton config object.
    """
    return SINGLETON
