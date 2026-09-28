"""Run the generator's synthetic regression scripts from a fresh checkout.

Each script accepts coderprint.py as its sole required argument and replaces
GitHub responses with local fixtures. Keep the suite list explicit so a new
file cannot silently run as part of CI.
"""

from pathlib import Path
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


def main():
    if sys.version_info < (3, 12):
        print("Python 3.12 or later is required for the regression suite", flush=True)
        return 1
    for name in SCRIPTS:
        print("\n== %s ==" % name, flush=True)
        try:
            result = subprocess.run(
                [sys.executable, str(ROOT / "test" / "py" / name), str(SOURCE)],
                cwd=ROOT,
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
