"""Inspect a local static URDF/USD scene without executing bundled code or simulation."""
from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def inspect_urdf(root):
    root = Path(root).resolve()
    urdfs = sorted(root.glob('*.urdf'))
    if len(urdfs) != 1:
        raise ValueError('Choose a directory with exactly one top-level URDF')
    raw = urdfs[0].read_bytes()
    if b'<!DOCTYPE' in raw or b'<!ENTITY' in raw:
        raise ValueError('XML entities are not supported')
    tree = ET.fromstring(raw)
    meshes = []
    for element in tree.findall('.//mesh'):
        name = element.attrib['filename']
        path = (root/name).resolve()
        if not path.is_relative_to(root):
            raise ValueError('Mesh path escapes the selected asset root')
        meshes.append(dict(file=name, exists=path.is_file(),
            bytes=path.stat().st_size if path.is_file() else None,
            sha256=hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None))
    return dict(urdf=urdfs[0].name, urdf_sha256=hashlib.sha256(raw).hexdigest(),
        links=len(tree.findall('link')), joints=len(tree.findall('joint')),
        visual_elements=len(tree.findall('.//visual')),
        collision_elements=len(tree.findall('.//collision')), meshes=meshes,
        mesh_references_resolve=bool(meshes) and all(row['exists'] for row in meshes))


def inspect_usd(entry):
    from pxr import Usd, UsdGeom, UsdUtils
    stage = Usd.Stage.Open(str(entry))
    if not stage:
        raise ValueError('USD stage did not open')
    layers, assets, unresolved = UsdUtils.ComputeAllDependencies(str(entry))
    bbox = UsdGeom.BBoxCache(Usd.TimeCode.Default(), ['default','render','proxy'])
    bounds = bbox.ComputeWorldBound(stage.GetPseudoRoot()).ComputeAlignedRange()
    return dict(stage_opened=True, up_axis=str(UsdGeom.GetStageUpAxis(stage)),
        meters_per_unit=UsdGeom.GetStageMetersPerUnit(stage),
        layer_count=len(layers), asset_dependency_count=len(assets),
        unresolved_dependencies=[str(value) for value in unresolved],
        bbox_min=list(bounds.GetMin()), bbox_max=list(bounds.GetMax()),
        note='OpenUSD composition only; no Isaac Sim runtime, dynamics, rendering or policy training')


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('asset_root',type=Path)
    parser.add_argument('output',type=Path)
    parser.add_argument('--usd-entry',default='HalfCubicCourse_Isaac.usda')
    args=parser.parse_args()
    if args.output.exists():parser.error('Use a new output directory')
    root=args.asset_root.resolve()
    entry=(root/args.usd_entry).resolve()
    if not entry.is_relative_to(root):parser.error('USD entry must remain in asset root')
    report=dict(asset_root_local=str(root), urdf=inspect_urdf(root),
        provider='SKAI Intelligence, as identified by project owner',
        redistribution_permission='not_established_by_this_inspection',
        simulator_run=False, physical_trials=0, motor_commands_sent=0)
    if entry.exists():
        report['usd']=inspect_usd(entry)
    else:
        report['usd']=dict(stage_opened=False,reason='entry_missing')
    args.output.mkdir(parents=True)
    (args.output/'scene_inspection.json').write_text(json.dumps(report,indent=2)+'\n')
    print(json.dumps({'urdf_meshes_resolve':report['urdf']['mesh_references_resolve'],
        'usd_stage_opened':report['usd']['stage_opened'],'output':str(args.output)}))


if __name__=='__main__':main()
