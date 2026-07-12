"""Blender factory-startup unittest entry point with reliable process status."""

from __future__ import annotations

import argparse
import os
import sys
import unittest
from pathlib import Path


def _arguments() -> argparse.Namespace:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser(add_help=False)
    parser.add_argument("--pattern", default="test_*.py")
    parser.add_argument("--verbose", action="store_true")
    return parser.parse_args(argv)


def main() -> None:
    args = _arguments()
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(root))
    suite = unittest.defaultTestLoader.discover(
        str(root / "tests"), pattern=args.pattern, top_level_dir=str(root)
    )
    result = unittest.TextTestRunner(verbosity=2 if args.verbose else 1).run(suite)
    print(
        "BONEWEAVER_TEST_RESULT",
        f"run={result.testsRun}",
        f"failures={len(result.failures)}",
        f"errors={len(result.errors)}",
        f"skipped={len(result.skipped)}",
    )
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if result.wasSuccessful() else 1)


if __name__ == "__main__":
    main()
