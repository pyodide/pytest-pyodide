import argparse
import itertools
import json

DEFAULT_PYODIDE_VERSION = "0.21.0, 0.21.3"
DEFAULT_OS = "ubuntu-20.04, macos-11"
DEFAULT_RUNNER = "selenium, playwright"
DEFAULT_BROWSER = "chrome, firefox, node, safari, host"
DEFAULT_CHROME_VERSION = "latest"
DEFAULT_FIREFOX_VERSION = "latest"
DEFAULT_NODE_VERSION = "14, 16, 18"


def is_valid(elem: dict[str, str]) -> bool:
    """
    Check if the test-config is valid
    """

    if "macos" not in elem["os"] and elem["browser"] == "safari":
        return False

    if "macos" in elem["os"] and elem["browser"] in ("chrome", "firefox", "node"):
        return False

    return True


def inject_versions(
    elem: dict[str, str], args: dict[str, list[str]]
) -> list[dict[str, str]]:
    """
    Add versions to test-config
    """

    keys = {
        "chrome": args["chrome_version"],
        "firefox": args["firefox_version"],
        "node": args["node_version"],
    }

    browser = elem["browser"]
    if browser not in keys:
        return [elem]

    elems = []
    for version in keys[browser]:
        _elem = elem.copy()
        _elem.update({f"{browser}-version": version})
        elems.append(_elem)

    return elems


def build_matrix(args: dict[str, list[str]]) -> list[dict[str, str]]:
    os = args["os"]
    pyodide_version = args["pyodide_version"]
    runner = args["runner"]
    browser = args["browser"]

    matrix = []
    for (_os, _pyodide_version, _runner, _browser) in itertools.product(
        os, pyodide_version, runner, browser
    ):
        elem = {
            "os": _os,
            "pyodide-version": _pyodide_version,
            "runner": _runner,
            "browser": _browser,
        }

        if not is_valid(elem):
            continue

        elems = inject_versions(elem, args)
        matrix.extend(elems)

    return matrix


def parse_args() -> dict[str, list[str]]:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "--pyodide-version",
        nargs="?",
        const=DEFAULT_PYODIDE_VERSION,
        default=DEFAULT_PYODIDE_VERSION,
    )
    parser.add_argument(
        "--os",
        nargs="?",
        const=DEFAULT_OS,
        default=DEFAULT_OS,
    )
    parser.add_argument(
        "--runner",
        nargs="?",
        const=DEFAULT_RUNNER,
        default=DEFAULT_RUNNER,
    )
    parser.add_argument(
        "--browser",
        nargs="?",
        const=DEFAULT_BROWSER,
        default=DEFAULT_BROWSER,
    )
    parser.add_argument(
        "--chrome-version",
        nargs="?",
        const=DEFAULT_CHROME_VERSION,
        default=DEFAULT_CHROME_VERSION,
    )
    parser.add_argument(
        "--firefox-version",
        nargs="?",
        const=DEFAULT_FIREFOX_VERSION,
        default=DEFAULT_FIREFOX_VERSION,
    )
    parser.add_argument(
        "--node-version",
        nargs="?",
        const=DEFAULT_NODE_VERSION,
        default=DEFAULT_NODE_VERSION,
    )

    args = parser.parse_args()
    args_dict: dict[str, list[str]] = {}
    for k, v in vars(args).items():
        args_dict[k] = [val.strip() for val in v.split(",")]

    return args_dict


def main():
    args = parse_args()

    matrix = build_matrix(args)

    print(f"matrix={json.dumps(matrix)}")


if __name__ == "__main__":
    main()
