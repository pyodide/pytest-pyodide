import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "utils"))

from build_test_matrix import (
    TestConfig,
    build_configs,
    inject_versions,
    is_valid_config,
    remove_duplicate_configs,
)


@pytest.mark.parametrize(
    "config, expected",
    [
        (TestConfig("0.21.0", "ubuntu-latest", "selenium", "firefox"), True),
        (TestConfig("0.21.0", "ubuntu-latest", "playwright", "firefox"), True),
        (TestConfig("0.21.0", "macos-latest", "selenium", "firefox"), False),
        (TestConfig("0.21.0", "macos-latest", "selenium", "chrome"), False),
        (TestConfig("0.21.0", "macos-latest", "selenium", "node"), False),
        (TestConfig("0.21.0", "macos-latest", "selenium", "safari"), True),
    ],
)
def test_build_matrix_is_valid(config, expected):
    assert is_valid_config(config) == expected


def test_build_matrix_inject_versions():
    configs = inject_versions(
        TestConfig("0.21.0", "ubuntu-latest", "selenium", "firefox"),
        {"chrome_version": ["1.0", "2.0"], "firefox_version": ["3.0", "4.0"]},
    )

    assert len(configs) == 2
    assert configs[0].browser_version == "3.0"
    assert configs[1].browser_version == "4.0"

    configs = inject_versions(
        TestConfig("0.21.0", "ubuntu-latest", "selenium", "chrome"),
        {"chrome_version": ["1.0", "2.0", "3.0"], "firefox_version": ["3.0", "4.0"]},
    )

    assert len(configs) == 3
    assert configs[0].browser_version == "1.0"
    assert configs[1].browser_version == "2.0"
    assert configs[2].browser_version == "3.0"

    configs = inject_versions(
        TestConfig("0.21.0", "ubuntu-latest", "playwright", "firefox"),
        {
            "chrome_version": ["1.0", "2.0"],
            "firefox_version": ["3.0", "4.0"],
            "playwright_version": ["5.0", "6.0"],
        },
    )

    assert len(configs) == 2
    assert configs[0].playwright_version == "5.0"
    assert configs[1].playwright_version == "6.0"


def test_remove_duplicate_configs():
    configs = [
        TestConfig("0.21.0", "ubuntu-latest", "selenium", "firefox"),
        TestConfig("0.21.0", "ubuntu-latest", "selenium", "firefox"),
    ]

    assert len(remove_duplicate_configs(configs)) == 1

    configs = [
        TestConfig("0.21.0", "ubuntu-latest", "selenium", "firefox"),
        TestConfig("0.21.0", "ubuntu-latest", "selenium", "chrome"),
    ]

    assert len(remove_duplicate_configs(configs)) == 2

    configs = [
        TestConfig("0.21.0", "ubuntu-latest", "selenium", "host"),
        TestConfig("0.21.0", "ubuntu-latest", "playwright", "host"),
    ]

    assert len(remove_duplicate_configs(configs)) == 1


def test_build_configs():
    configs = build_configs(
        {
            "os": ["ubuntu-latest", "macos-latest"],
            "pyodide-version": ["0.21.0"],
            "runner": ["selenium", "playwright"],
            "browser": ["firefox", "chrome", "node", "safari", "host"],
            "chrome_version": ["1.0", "2.0"],
            "firefox_version": ["3.0", "4.0"],
            "node_version": ["5.0", "6.0"],
            "playwright_version": ["7.0", "8.0"],
        }
    )

    for config in configs:
        assert is_valid_config(config)

        print(config)
