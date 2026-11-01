"""Factory-startup acceptance on a supplied blend or imported UEFormat asset."""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import sys
import time

import bpy


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--input', required=True)
    parser.add_argument('--output', required=True)
    parser.add_argument('--ueformat-root')
    parser.add_argument('--restore', action='store_true')
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:])
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
    import boneweaver
    from boneweaver.core.auto_cleanup import (
        build_cleanup_plan, apply_cleanup_plan, restore_cleanup_snapshot,
        latest_cleanup_snapshot, _data_signature,
    )
    boneweaver.register()
    source, output = Path(args.input), Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    source_hash = hashlib.sha256(source.read_bytes()).hexdigest()
    if source.suffix == '.blend':
        bpy.ops.wm.open_mainfile(filepath=str(source), load_ui=False)
    else:
        sys.path.insert(0, args.ueformat_root)
        extension = importlib.import_module('io_scene_ueformat')
        extension.register()
        bpy.ops.uf.import_uemodel(directory=str(source.parent), files=[{'name': source.name}])
    if bpy.context.object and bpy.context.object.mode != 'OBJECT':
        bpy.ops.object.mode_set(mode='OBJECT')
    bpy.ops.object.select_all(action='DESELECT')
    rig = next(o for o in bpy.context.scene.objects if o.type=='ARMATURE')
    rig.select_set(True)
    bpy.context.view_layer.objects.active = rig
    if args.restore:
        name = latest_cleanup_snapshot(rig)
        assert name and restore_cleanup_snapshot(bpy.context, name), 'reopened restore failed'
        report = {'reopen_restore': True, 'bones': len(rig.data.bones), 'source_unchanged': source_hash == hashlib.sha256(source.read_bytes()).hexdigest()}
    else:
        started = time.perf_counter()
        signature, count = _data_signature(rig.data), len(rig.data.bones)
        plan = build_cleanup_plan(bpy.context)
        print('PLAN', len(plan.delete_names), flush=True)
        name, result = apply_cleanup_plan(bpy.context, plan)
        report = {k: result[k] for k in ('status','reoriented','deleted')}
        report.update(source=str(source), before_bones=count, after_bones=len(rig.data.bones),
                      deleted_names=plan.delete_names, decisions=plan.decisions,
                      mesh_checks=result.get('mesh_checks', []), elapsed=time.perf_counter()-started)
        # Deterministic repeat is a no-op and retains the first recovery point.
        second_name, second = apply_cleanup_plan(bpy.context, build_cleanup_plan(bpy.context))
        assert second['status']=='NOOP' and second_name==name, 'not idempotent'
        report['idempotent'] = True
        bpy.ops.wm.save_as_mainfile(filepath=str(output/'converted.blend'))
        assert name and restore_cleanup_snapshot(bpy.context, name), 'restore failed'
        assert _data_signature(rig.data)==signature, 'original bone data mismatch'
        report['exact_restore'] = True
        report['source_unchanged'] = source_hash == hashlib.sha256(source.read_bytes()).hexdigest()
    (output/('reopen.json' if args.restore else 'acceptance.json')).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print('ACCEPTANCE', json.dumps({k:v for k,v in report.items() if k not in ('decisions','deleted_names')},ensure_ascii=False), flush=True)


if __name__ == '__main__':
    try:
        main()
    except Exception:
        import traceback
        traceback.print_exc()
        sys.stdout.flush(); sys.stderr.flush()
        os._exit(1)
