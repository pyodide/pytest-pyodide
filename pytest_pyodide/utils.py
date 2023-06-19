import contextlib
import functools
import json
from pathlib import Path


@contextlib.contextmanager
def set_webdriver_script_timeout(selenium, script_timeout: float | None):
    """Set selenium script timeout

    Parameters
    ----------
    selenum : SeleniumWrapper
       a SeleniumWrapper wrapper instance
    script_timeout : int | float
       value of the timeout in seconds
    """
    if script_timeout is not None:
        selenium.set_script_timeout(script_timeout)
    yield
    # revert to the initial value
    if script_timeout is not None:
        selenium.set_script_timeout(selenium.script_timeout)


def parse_driver_timeout(node) -> float | None:
    """Parse driver timeout value from pytest request object"""
    mark = node.get_closest_marker("driver_timeout")
    if mark is None:
        return None
    else:
        return mark.args[0]


def parse_xfail_browsers(node) -> dict[str, str]:
    mark = node.get_closest_marker("xfail_browsers")
    if mark is None:
        return {}
    return mark.kwargs


@functools.cache
def built_packages(dist_dir: Path) -> list[str]:
    """Returns the list of built package names from repodata.json"""
    repodata_path = dist_dir / "pyodide-lock.json"
    if not repodata_path.exists():
        # Try again for backwards compatibility
        repodata_path = dist_dir / "repodata.json"
    if not repodata_path.exists():
        return []
    return list(json.loads(repodata_path.read_text())["packages"].keys())


def package_is_built(package_name: str, dist_dir: Path) -> bool:
    return package_name.lower() in built_packages(dist_dir)
