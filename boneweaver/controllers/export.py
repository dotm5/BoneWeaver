"""Conversion-copy export orchestration outside operator adapters."""

from __future__ import annotations

import json
from pathlib import Path

import bpy

from ..core.export_contract import assert_export_ready, build_export_manifest, file_signature
from ..core.reopen_validation import launch_reopen_validation
from ..core.runtime_store import get_plan, has_plan
from ..core.runtime_store import get_report
from ..core.serialization import dumps


class ExportController:
    @staticmethod
    def export_report(context, filepath: str) -> set[str]:
        report = get_report()
        if report is None:
            return {"CANCELLED"}
        destination = Path(filepath)
        destination.write_text(dumps(report), encoding="utf-8", newline="\n")
        context.scene.boneweaver_settings.last_export_directory = str(destination.parent)
        return {"FINISHED"}

    @staticmethod
    def export_conversion(context, filepath: str) -> set[str]:
        runtime = context.window_manager.boneweaver_runtime
        if not runtime.plan_id or not has_plan(runtime.plan_id):
            runtime.last_error = "BONEWEAVER_EXPORT_PLAN_MISSING"
            return {"CANCELLED"}
        plan = get_plan(runtime.plan_id)
        try:
            _, snapshot = assert_export_ready(context, plan, runtime)
            source = Path(bpy.data.filepath)
            destination = Path(filepath)
            if not source.is_file():
                raise RuntimeError("BONEWEAVER_EXPORT_SOURCE_FILE_MISSING")
            if source.resolve() == destination.resolve():
                raise RuntimeError("BONEWEAVER_EXPORT_SOURCE_OVERWRITE_FORBIDDEN")
            source_signature = file_signature(source)
            destination.parent.mkdir(parents=True, exist_ok=True)
            bpy.ops.file.pack_all()
            packed_count = sum(bool(image.packed_file) for image in bpy.data.images)
            manifest = build_export_manifest(
                source, plan, snapshot,
                tolerance_mode=context.scene.boneweaver_settings.validation_tolerance_mode,
                packed_image_count=packed_count,
            )
            text = bpy.data.texts.get("BONEWEAVER_EXPORT_MANIFEST") or bpy.data.texts.new("BONEWEAVER_EXPORT_MANIFEST")
            text.clear()
            text.write(json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2))
            bpy.ops.wm.save_as_mainfile(filepath=str(destination), copy=True)
            if file_signature(source) != source_signature:
                raise RuntimeError("BONEWEAVER_EXPORT_SOURCE_FILE_CHANGED")
            report_path = destination.parent / "reopen-validation.json"
            return_code, reopen_payload, _stdout, stderr = launch_reopen_validation(
                bpy.app.binary_path, destination, report_path, Path(__file__).resolve().parents[2],
            )
            manifest["reopen_validation"] = {
                "result": "PASS" if return_code == 0 and reopen_payload and reopen_payload.get("success") else "FAILED",
                "report_path": str(report_path),
                "issues": (reopen_payload or {}).get("issues", []),
            }
            (destination.parent / "conversion-audit.json").write_text(
                json.dumps(manifest, ensure_ascii=False, sort_keys=True, indent=2) + "\n", encoding="utf-8",
            )
            if manifest["reopen_validation"]["result"] != "PASS":
                raise RuntimeError("BONEWEAVER_REOPEN_VALIDATION_FAILED: " + ", ".join(manifest["reopen_validation"]["issues"])
                                   + ("; " + stderr[-1000:] if stderr else ""))
            runtime.last_error = ""
            return {"FINISHED"}
        except Exception as error:
            runtime.last_error = str(error)
            return {"CANCELLED"}
