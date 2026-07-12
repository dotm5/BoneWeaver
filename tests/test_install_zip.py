"""Install a built extension ZIP into an isolated Blender user repository."""

from __future__ import annotations

import argparse
import importlib
import os
import sys
import traceback
from pathlib import Path

import bpy


def main() -> int:
    argv = sys.argv[sys.argv.index("--") + 1 :] if "--" in sys.argv else []
    parser = argparse.ArgumentParser()
    parser.add_argument("--zip", required=True)
    args = parser.parse_args(argv)
    archive = Path(args.zip).resolve(strict=True)
    repository_directory = Path(os.environ["BLENDER_USER_RESOURCES"]) / "extensions" / "user_default"
    repository_directory.mkdir(parents=True, exist_ok=True)
    repositories = bpy.context.preferences.extensions.repos
    repository = repositories.get("Local Test") or repositories.new(
        name="Local Test",
        module="user_default",
        custom_directory=str(repository_directory),
        source="USER",
    )
    result = bpy.ops.extensions.package_install_files(
        filepath=str(archive), repo=repository.module,
        enable_on_install=True, overwrite=True
    )
    if "FINISHED" not in result:
        raise RuntimeError(f"extension install returned {result!r}")
    module = importlib.import_module("bl_ext.user_default.boneweaver")
    if not hasattr(bpy.types.Scene, "boneweaver_settings"):
        module.register()
    for _ in range(3):
        module.unregister()
        if hasattr(bpy.types.Scene, "boneweaver_settings"):
            raise RuntimeError("Scene.boneweaver_settings leaked after unregister")
        module.register()
        if not hasattr(bpy.types.Scene, "boneweaver_settings"):
            raise RuntimeError("Scene.boneweaver_settings missing after register")
    module.unregister()
    print("BONEWEAVER_ZIP_INSTALL_OK", archive)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except SystemExit:
        raise
    except BaseException:
        traceback.print_exc()
        sys.stdout.flush()
        sys.stderr.flush()
        os._exit(1)
