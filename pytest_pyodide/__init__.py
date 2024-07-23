from importlib.metadata import PackageNotFoundError, version

from .config import get_global_config
from .decorator import copy_files_to_pyodide, run_in_pyodide
from .runner import (
    NodeRunner,
    PlaywrightChromeRunner,
    PlaywrightFirefoxRunner,
    SeleniumChromeRunner,
    SeleniumFirefoxRunner,
    SeleniumSafariRunner,
)
from .server import spawn_web_server
from .utils import parse_driver_timeout, set_webdriver_script_timeout

try:
    __version__ = version("pytest-pyodide")
except PackageNotFoundError:
    # package is not installed
    pass

__all__ = [
    "NodeRunner",
    "PlaywrightChromeRunner",
    "PlaywrightFirefoxRunner",
    "SeleniumChromeRunner",
    "SeleniumFirefoxRunner",
    "SeleniumSafariRunner",
    "set_webdriver_script_timeout",
    "parse_driver_timeout",
    "run_in_pyodide",
    "copy_files_to_pyodide",
    "spawn_web_server",
    "get_global_config",
]
