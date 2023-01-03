"""
Build test matrix for GitHub Actions
"""

import argparse
import dataclasses
import itertools
import json

DEFAULT_OS = "ubuntu-20.04, macos-11"
DEFAULT_RUNNER = "selenium, playwright"
DEFAULT_BROWSER = "chrome, firefox, node, safari, host"
DEFAULT_CHROME_VERSION = "latest"
DEFAULT_FIREFOX_VERSION = "latest"
DEFAULT_NODE_VERSION = "14, 16, 18"
DEFAULT_PLAYWRIGHT_VERSION = ""  # latest


@dataclasses.dataclass
class TestConfig:
    pyodide_version: str
    os: str
    runner: str
    browser: str
    browser_version: str = ""
    playwright_version: str = ""

    @property
    def runtime(self) -> str:
        # TODO: replace all "browser" wordings to "runtime"
        return self.browser

    @property
    def runtime_version(self) -> str:
        # TODO: replace all "browser" wordings to "runtime"
        return self.browser_version


def is_valid_config(config: TestConfig) -> bool:
    """
    Check if the test-config is valid
    """

    if "macos" not in config.os and config.runtime == "safari":
        return False

    # TODO: should we support running these runtimes in macos?
    if (
        "macos" in config.os
        and config.runner == "selenium"
        and config.runtime in ("chrome", "firefox", "node")
    ):
        return False

    # It is possible to run playwright in macos, but it is not tested yet
    if "macos" in config.os and config.runner == "playwright":
        return False

    return True


def _inject_versions_inner(
    config: TestConfig, versions: list[str], key: str
) -> list[TestConfig]:

    configs_with_versions = []
    for version in versions:
        _config = dataclasses.replace(config)
        setattr(_config, key, version)
        configs_with_versions.append(_config)

    return configs_with_versions


def inject_versions(config: TestConfig, args: dict[str, list[str]]):
    """
    Add corresponding versions to test-config
    """
    if config.runner == "playwright":
        versions = args.get("playwright_version", [])
        key = "playwright_version"
    else:
        versions = {
            "chrome": args.get("chrome_version", []),
            "firefox": args.get("firefox_version", []),
            "node": args.get("node_version", []),
            "safari": ["HOST_VERSION"],  # We just use host safari version
        }[config.runtime]
        key = "browser_version"

    return _inject_versions_inner(config, versions, key)


def build_configs(args: dict[str, list[str]]) -> list[TestConfig]:
    os = args["os"]
    pyodide_version = args["pyodide-version"]
    runner = args["runner"]
    browser = args["browser"]

    matrix = []
    for (_os, _pyodide_version, _runner, _browser) in itertools.product(
        os, pyodide_version, runner, browser
    ):
        config = TestConfig(_pyodide_version, _os, _runner, _browser)

        if not is_valid_config(config):
            continue

        config_with_versions = inject_versions(config, args)
        matrix.extend(config_with_versions)

    return matrix


def parse_args() -> dict[str, list[str]]:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "pyodide-version",
    )

    parser.add_argument(
        "--os",
        default=DEFAULT_OS,
    )
    parser.add_argument(
        "--runner",
        default=DEFAULT_RUNNER,
    )
    parser.add_argument(
        "--browser",
        default=DEFAULT_BROWSER,
    )
    parser.add_argument(
        "--chrome-version",
        default=DEFAULT_CHROME_VERSION,
    )
    parser.add_argument(
        "--firefox-version",
        default=DEFAULT_FIREFOX_VERSION,
    )
    parser.add_argument(
        "--node-version",
        default=DEFAULT_NODE_VERSION,
    )
    parser.add_argument(
        "--playwright-version",
        default=DEFAULT_PLAYWRIGHT_VERSION,
    )

    args = parser.parse_args()
    args_dict: dict[str, list[str]] = {}
    for k, v in vars(args).items():
        args_dict[k] = [val.strip() for val in v.split(",")]

    return args_dict


def main():
    args = parse_args()

    configs: list[TestConfig] = build_configs(args)

    test_matrix = [dataclasses.asdict(config) for config in configs]
    print(json.dumps(test_matrix, indent=2))


if __name__ == "__main__":
    main()
