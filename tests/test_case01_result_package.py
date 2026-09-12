from pathlib import Path


def test_saved_case01_package_preserves_three_inputs_two_patches_and_absent_fusion(tmp_path):
    from dmslicer.prepare_case01_package import prepare
    from dmslicer.result_package import read_package
    root = Path(__file__).resolve().parents[1]
    path = prepare(root, tmp_path / 'package')
    value = read_package(path.read_bytes())['cases'][0]
    entities = value['scene']['entities']
    assert sum(e['scene_role'] == 'input' for e in entities) == 3
    assert sum(e['scene_role'] == 'common_interface' for e in entities) == 2
    assert not any(e['scene_role'] == 'fused_result' for e in entities)
    assert all(e['identity_status'] == 'STABLE_REFERENCE' for e in entities)
    assert value['provenance']['role_states']['fused_result'] == 'NOT_PRODUCED_IN_SUPPLIED_EVIDENCE'
    assert value['provenance']['computed_results']['operation']['packaging_geometry_computation'] == 'NONE'
