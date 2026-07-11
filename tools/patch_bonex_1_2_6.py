"""Reversible local compatibility patch for BoneX 1.2.6 on Blender 5.2."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import tempfile
import tomllib


VULNERABLE_GETTER = '''def get_armature_soft_connections(armature_obj):
    """获取armature对象的soft_connections数据"""
    if not armature_obj.get(const.rigidbody_data_name):
        armature_obj[const.rigidbody_data_name] = {}

    armature_data = armature_obj[const.rigidbody_data_name]
    if const.soft_connections_key not in armature_data:
        armature_data[const.soft_connections_key] = []

    return armature_data[const.soft_connections_key]
'''


READ_ONLY_GETTER = '''def get_armature_soft_connections(armature_obj):
    """获取armature对象的soft_connections数据，不在读取路径初始化ID属性。"""
    armature_data = armature_obj.get(const.rigidbody_data_name)
    if not armature_data:
        return []

    return armature_data.get(const.soft_connections_key, [])
'''


class PatchError(RuntimeError):
    """Raised when an installation is not the exact supported BoneX release."""


@dataclass(frozen=True)
class PatchResult:
    changed: bool
    source_path: Path
    backup_path: Path
    before_sha256: str
    after_sha256: str


def patch_source(source: str) -> tuple[str, bool]:
    """Return the guarded BoneX source transformation and whether it changed."""
    if READ_ONLY_GETTER in source:
        return source, False
    if VULNERABLE_GETTER not in source:
        raise PatchError("BoneX 1.2.6 getter does not match the audited source")
    return source.replace(VULNERABLE_GETTER, READ_ONLY_GETTER, 1), True


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest().upper()


def _paths(root: str | Path) -> tuple[Path, Path]:
    root_path = Path(root).resolve()
    manifest_path = root_path / "blender_manifest.toml"
    if not manifest_path.is_file():
        raise PatchError(f"BoneX manifest not found: {manifest_path}")
    manifest = tomllib.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("id") != "bonex" or manifest.get("version") != "1.2.6":
        raise PatchError(
            "Only the audited BoneX id=bonex version=1.2.6 installation is supported"
        )
    source_path = root_path / "utils" / "utils.py"
    if not source_path.is_file():
        raise PatchError(f"BoneX utils source not found: {source_path}")
    backup_path = source_path.with_name("utils.py.uecp-bonex-1.2.6.bak")
    return source_path, backup_path


def _atomic_write(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="", dir=path.parent, delete=False
    ) as stream:
        stream.write(text)
        temporary = Path(stream.name)
    try:
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def apply_installation(root: str | Path) -> PatchResult:
    """Patch one exact BoneX 1.2.6 installation and retain its original source."""
    source_path, backup_path = _paths(root)
    source = source_path.read_text(encoding="utf-8")
    patched, changed = patch_source(source)
    if changed:
        if backup_path.exists():
            if backup_path.read_text(encoding="utf-8") != source:
                raise PatchError(f"Existing backup does not match current source: {backup_path}")
        else:
            backup_path.write_text(source, encoding="utf-8", newline="")
        _atomic_write(source_path, patched)
    return PatchResult(
        changed=changed,
        source_path=source_path,
        backup_path=backup_path,
        before_sha256=_sha256(source),
        after_sha256=_sha256(patched),
    )


def restore_installation(root: str | Path) -> PatchResult:
    """Restore the exact backup created by :func:`apply_installation`."""
    source_path, backup_path = _paths(root)
    if not backup_path.is_file():
        raise PatchError(f"BoneX compatibility backup not found: {backup_path}")
    current = source_path.read_text(encoding="utf-8")
    original = backup_path.read_text(encoding="utf-8")
    if current == original:
        return PatchResult(False, source_path, backup_path, _sha256(current), _sha256(current))
    expected_patched, _changed = patch_source(original)
    if current != expected_patched:
        raise PatchError("Current BoneX source diverged after patch; refusing to overwrite it")
    _atomic_write(source_path, original)
    return PatchResult(
        changed=True,
        source_path=source_path,
        backup_path=backup_path,
        before_sha256=_sha256(current),
        after_sha256=_sha256(original),
    )


def check_installation(root: str | Path) -> dict[str, object]:
    """Return a guarded, non-mutating status record for a BoneX installation."""
    source_path, backup_path = _paths(root)
    source = source_path.read_text(encoding="utf-8")
    if READ_ONLY_GETTER in source:
        status = "patched"
    elif VULNERABLE_GETTER in source:
        status = "vulnerable"
    else:
        raise PatchError("BoneX getter is neither the audited original nor patched form")
    return {
        "action": "check",
        "status": status,
        "source_path": str(source_path),
        "backup_path": str(backup_path),
        "backup_exists": backup_path.is_file(),
        "sha256": _sha256(source),
    }


def _result_record(action: str, result: PatchResult) -> dict[str, object]:
    return {
        "action": action,
        "changed": result.changed,
        "source_path": str(result.source_path),
        "backup_path": str(result.backup_path),
        "before_sha256": result.before_sha256,
        "after_sha256": result.after_sha256,
    }


def _default_root() -> Path:
    appdata = Path(os.environ.get("APPDATA", Path.home() / "AppData" / "Roaming"))
    return (
        appdata
        / "Blender Foundation"
        / "Blender"
        / "5.2"
        / "extensions"
        / "user_default"
        / "bonex"
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bonex-root", type=Path, default=_default_root())
    action = parser.add_mutually_exclusive_group(required=True)
    action.add_argument("--check", action="store_true")
    action.add_argument("--apply", action="store_true")
    action.add_argument("--restore", action="store_true")
    args = parser.parse_args(argv)
    try:
        if args.check:
            record = check_installation(args.bonex_root)
        elif args.apply:
            record = _result_record("apply", apply_installation(args.bonex_root))
        else:
            record = _result_record("restore", restore_installation(args.bonex_root))
    except PatchError as exc:
        print(json.dumps({"action": "error", "message": str(exc)}, ensure_ascii=False))
        return 2
    print(json.dumps(record, ensure_ascii=False, indent=2))
    if args.check and record["status"] == "vulnerable":
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
