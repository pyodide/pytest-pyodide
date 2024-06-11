"""
Build test matrix for GitHub Actions
"""

import argparse
import dataclasses
import itertools
import json

DEFAULT_OS = "ubuntu-latest, macos-latest"
DEFAULT_RUNNER = "selenium"
DEFAULT_BROWSER = "chrome, firefox, node, safari, host"
DEFAULT_CHROME_VERSION = "latest"
DEFAULT_FIREFOX_VERSION = "latest"
DEFAULT_NODE_VERSION = "22"
DEFAULT_PLAYWRIGHT_VERSION = "1.44.0"


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

    # TODO: Node is actually a runner rather than a runtime, but we treat it as a runtime conventionally...
    if config.runner == "playwright" and config.runtime == "node":
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
            "safari": ["__IGNORED__"],  # This value will be ignored
            "host": ["__IGNORED__"],  # This value will be ignored
        }[config.runtime]
        key = "browser_version"

    return _inject_versions_inner(config, versions, key)


def remove_duplicate_configs(configs: list[TestConfig]) -> list[TestConfig]:
    """
    Remove duplicate configs.
    """
    _configs = []

    host_config = False
    for config in configs:
        if config in _configs:
            continue

        # If runtime is `host`, runner value will not be used. So we only need to keep one config
        if config.runtime == "host":
            if host_config:
                continue

            host_config = True

        _configs.append(config)

    return _configs


def build_configs(args: dict[str, list[str]]) -> list[TestConfig]:
    os = args["os"]
    pyodide_version = args["pyodide-version"]
    runner = args["runner"]
    browser = args["browser"]

    matrix = []
    for _os, _pyodide_version, _runner, _browser in itertools.product(
        os, pyodide_version, runner, browser
    ):
        config = TestConfig(_pyodide_version, _os, _runner, _browser)

        if not is_valid_config(config):
            continue

        config_with_versions = inject_versions(config, args)
        matrix.extend(config_with_versions)

    return remove_duplicate_configs(matrix)


def validate_args(args: dict[str, list[str]]):
    runners = args["runner"]
    for runner in runners:
        if runner not in ("selenium", "playwright"):
            raise ValueError(f"Invalid runner: {runner}")

    browsers = args["browser"]
    for browser in browsers:
        if browser not in ("chrome", "firefox", "node", "safari", "host"):
            raise ValueError(f"Invalid browser: {browser}")


def parse_args() -> dict[str, list[str]]:
    parser = argparse.ArgumentParser()

    parser.add_argument(
        "pyodide-version",
    )

    parser.add_argument(
        "--os",
    )
    parser.add_argument(
        "--runner",
    )
    parser.add_argument(
        "--browser",
    )
    parser.add_argument(
        "--chrome-version",
    )
    parser.add_argument(
        "--firefox-version",
    )
    parser.add_argument(
        "--node-version",
    )
    parser.add_argument(
        "--playwright-version",
    )

    defaults: dict[str, str] = {
        "os": DEFAULT_OS,
        "runner": DEFAULT_RUNNER,
        "browser": DEFAULT_BROWSER,
        "chrome_version": DEFAULT_CHROME_VERSION,
        "firefox_version": DEFAULT_FIREFOX_VERSION,
        "node_version": DEFAULT_NODE_VERSION,
        "playwright_version": DEFAULT_PLAYWRIGHT_VERSION,
    }

    args = parser.parse_args()
    args_dict: dict[str, list[str]] = {}
    for k, v in vars(args).items():
        if not v:
            v = defaults[k]

        args_dict[k] = [val.strip() for val in v.split(",")]

    validate_args(args_dict)
    return args_dict


def main():
    args = parse_args()

    configs: list[TestConfig] = build_configs(args)

    test_matrix = [dataclasses.asdict(config) for config in configs]
    print(json.dumps(test_matrix))


if __name__ == "__main__":
    main()
