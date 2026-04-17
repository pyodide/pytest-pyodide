"""End-to-end test for ``run_in_pyodide_coverage``.

Builds the dummy-pkg wheel from ``tests/coverage-test``, installs it into the
selenium pyodide environment, then calls ``add``, ``multiply`` and
``factorial`` each inside their own ``run_in_pyodide_coverage`` block. Finally,
the emitted ``.coverage.emscripten.*`` files are combined and a coverage
report is produced, which we assert contains the expected covered /
not-covered lines (and that the ``# pragma: no cover`` line is excluded).
"""

import json
import subprocess
import sys
from pathlib import Path
from pprint import pprint

from pytest_pyodide.decorator import run_in_pyodide_coverage
from pytest_pyodide.server import spawn_web_server

COVERAGE_TEST_DIR = Path(__file__).parent / "coverage-test"
DUMMY_PKG_FILE = COVERAGE_TEST_DIR / "dummy_pkg/__init__.py"
COVERAGE_TEST_PYPROJECT_TOML = COVERAGE_TEST_DIR / "pyproject.toml"


def _build_wheel(outdir: Path) -> Path:
    """Build the dummy-pkg wheel into ``outdir`` and return its path."""
    subprocess.run(
        [
            sys.executable,
            "-m",
            "build",
            "--wheel",
            "--outdir",
            str(outdir),
            str(COVERAGE_TEST_DIR),
        ],
        check=True,
    )
    wheels = list(outdir.glob("dummy_pkg-*.whl"))
    assert len(wheels) == 1, f"expected one wheel, got {wheels}"
    return wheels[0]


def test_run_in_pyodide_coverage(selenium, tmp_path, monkeypatch):
    # tmp_path = Path("/home/hood/Documents/programming/pytest-pyodide/tests/tmp_path")
    # Build the dummy-pkg wheel and install it into pyodide.
    wheel = _build_wheel(tmp_path)
    with spawn_web_server(tmp_path) as server:
        hostname, port, _ = server
        selenium.load_package(f"http://{hostname}:{port}/{wheel.name}")

    # Run everything from tmp_path so the `.coverage.emscripten.*` files
    # created by run_in_pyodide_coverage land in an isolated directory.
    monkeypatch.chdir(tmp_path)

    @run_in_pyodide_coverage(coverage_args={"source_pkgs": ["dummy_pkg"]})
    def exercise_add(selenium):
        from dummy_pkg import add

        assert add(2, 3) == 5

    @run_in_pyodide_coverage(coverage_args={"source_pkgs": ["dummy_pkg"]})
    def exercise_multiply(selenium):
        from dummy_pkg import multiply

        assert multiply(4, 5) == 20

    @run_in_pyodide_coverage(coverage_args={"source_pkgs": ["dummy_pkg"]})
    def exercise_factorial(selenium):
        from dummy_pkg import factorial

        assert factorial(5) == 120

    exercise_add(selenium)
    exercise_multiply(selenium)
    exercise_factorial(selenium)

    # Make sure coverage data files were actually written.
    coverage_files = list(tmp_path.glob(".coverage.emscripten.*"))
    assert len(coverage_files) == 3
    pyproject_toml = COVERAGE_TEST_PYPROJECT_TOML.read_text()
    pyproject_toml = pyproject_toml.format(
        COVERAGE_TEST_PATH=str(COVERAGE_TEST_DIR.absolute())
    )
    (tmp_path / "pyproject.toml").write_text(pyproject_toml)

    # Combine the per-run files into a single .coverage database.
    subprocess.run(
        [sys.executable, "-m", "coverage", "combine"],
        check=True,
        cwd=tmp_path,
    )

    # Produce a report restricted to dummy_pkg.
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "coverage",
            "json",
        ],
        cwd=tmp_path,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.returncode == 0
    assert result.stdout == "Wrote JSON report to coverage.json\n"

    coverage_json = json.loads((tmp_path / "coverage.json").read_text())
    file = coverage_json["files"][
        "/home/hood/Documents/programming/pytest-pyodide/tests/coverage-test/dummy_pkg/__init__.py"
    ]
    functions = file["functions"]
    pprint(functions)

    assert functions["add"]["missing_lines"] == []
    assert functions["add"]["excluded_lines"] == []
    assert functions["multiply"]["missing_lines"] == []
    assert functions["multiply"]["excluded_lines"] == []
    assert functions["factorial"]["missing_lines"] == [14]
    assert functions["factorial"]["excluded_lines"] == []
    assert functions["never_called"]["missing_lines"] == [24]
    assert functions["never_called"]["excluded_lines"] == []
    assert functions["unreachable"]["missing_lines"] == []
    assert functions["unreachable"]["excluded_lines"] == [30]
