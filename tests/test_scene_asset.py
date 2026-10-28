import importlib.util
from pathlib import Path

import pytest

spec=importlib.util.spec_from_file_location('scene_asset',
    Path(__file__).resolve().parents[1]/'tools/inspect_scene_asset.py')
module=importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)


def test_scene_missing_mesh_is_not_passed(tmp_path):
    (tmp_path/'scene.urdf').write_text('<robot><link><visual><mesh filename="missing.obj"/></visual></link></robot>')
    assert not module.inspect_urdf(tmp_path)['mesh_references_resolve']


def test_scene_rejects_escaping_mesh(tmp_path):
    (tmp_path/'scene.urdf').write_text('<robot><mesh filename="../outside.obj"/></robot>')
    with pytest.raises(ValueError):module.inspect_urdf(tmp_path)
