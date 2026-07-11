"""Blender entry point for independent UECP reopen validation."""

from __future__ import annotations

import argparse
import dataclasses
import json
import os
import sys
from pathlib import Path


def main():
    arguments = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--report", required=True)
    parser.add_argument("--project-root", required=True)
    args = parser.parse_args(arguments)
    sys.path.insert(0, args.project_root)
    from ue_chain_prep.core.reopen_validation import validate_reopened_file

    report = validate_reopened_file()
    Path(args.report).write_text(
        json.dumps(dataclasses.asdict(report), ensure_ascii=False, sort_keys=True, indent=2) + "\n",
        encoding="utf-8",
    )
    print("UECP_REOPEN_RESULT", "PASS" if report.success else "FAIL", ",".join(report.issues))
    sys.stdout.flush()
    sys.stderr.flush()
    os._exit(0 if report.success else 1)


if __name__ == "__main__":
    main()
