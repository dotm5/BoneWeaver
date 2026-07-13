"""Factory-startup acceptance from a raw UEFormat .uemodel import."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import traceback
from pathlib import Path

import bpy


def main():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", required=True)
    parser.add_argument("--output", required=True)
    parser.add_argument("--module-root", required=True)
    args = parser.parse_args(argv)
    source = Path(args.input).resolve(strict=True)
    root = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(Path(args.module_root).resolve(strict=True)))
    sys.path.insert(0, str(root))

    extension = importlib.import_module("io_scene_ueformat")
    extension.register()
    import boneweaver
    from tools.run_quick_reorient_real import run_loaded_scene
    boneweaver.register()
    try:
        result = bpy.ops.uf.import_uemodel(
            directory=str(source.parent), files=[{"name": source.name}]
        )
        if result != {"FINISHED"}:
            raise RuntimeError(f"UEFormat import failed: {result}")
        return run_loaded_scene(
            source, Path(args.output).resolve(), expected_adapter="UEFORMAT_METADATA"
        )
    finally:
        boneweaver.unregister()
        extension.unregister()


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit as error:
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(int(error.code or 0))
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
