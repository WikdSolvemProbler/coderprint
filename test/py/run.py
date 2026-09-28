"""Run the generator's synthetic regression scripts from a fresh checkout.

Each script accepts coderprint.py as its sole required argument and replaces
GitHub responses with local fixtures. Keep the suite list explicit so a new
file cannot silently run as part of CI.
"""

from pathlib import Path
import os
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "coderprint.py"
SCRIPTS = (
    "test_lines.py",
    "test_tests.py",
    "test_history.py",
    "test_identity.py",
    "test_in_use.py",
    "main_test.py",
    "test_B1_panel.py",
    "test_B2_ops.py",
    "test_B3_data_file.py",
    "test_collection.py",
)
PER_SCRIPT_SECONDS = 300
TEST_SETTINGS = {
    "GH_TOKEN", "GITHUB_TOKEN", "GITHUB_REPOSITORY", "CLONE_CACHE", "FORCE",
    "GIT_DIR", "GIT_WORK_TREE", "GIT_INDEX_FILE", "GIT_DIFF_OPTS",
    "GIT_EXTERNAL_DIFF", "GIT_ATTR_NOSYSTEM", "GIT_TEMPLATE_DIR",
}


def test_environment():
    # An Action sets GITHUB_REPOSITORY to this project, while these suites draw
    # synthetic cards for owner1. Keep PATH and the system runtime settings.
    return {name: value for name, value in os.environ.items()
            if name not in TEST_SETTINGS and not name.startswith(("CARDS_", "GIT_CONFIG_"))}


def main():
    if sys.version_info < (3, 12):
        print("Python 3.12 or later is required for the regression suite", flush=True)
        return 1
    env = test_environment()
    for name in SCRIPTS:
        print("\n== %s ==" % name, flush=True)
        try:
            result = subprocess.run(
                [sys.executable, "-u", str(ROOT / "test" / "py" / name), str(SOURCE)],
                cwd=ROOT,
                env=env,
                timeout=PER_SCRIPT_SECONDS,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print("FAIL %s exceeded %d seconds" % (name, PER_SCRIPT_SECONDS), flush=True)
            return 1
        if result.returncode:
            print("FAIL %s exited %d" % (name, result.returncode), flush=True)
            return 1
    print("\nAll generator regression scripts passed", flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
