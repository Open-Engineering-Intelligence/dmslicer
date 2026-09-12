from copy import deepcopy
import json
from pathlib import Path


def test_sample_labels_change_only_presentation_and_preserve_geometry_and_refs():
    from dmslicer.result_labels import apply_sample_labels
    from dmslicer.result_package import read_package
    root = Path(__file__).resolve().parents[1] / 'evidence/GEOMETRY-CASE-VIEWER-01'
    for case, relative in [('C02', 'c02-package-003/C02.dmslicer'), ('U05', 'u05-package-003/U05.dmslicer'), ('CASE01', 'case01-package-001/CASE01.dmslicer')]:
        entry = read_package((root / relative).read_bytes())['cases'][0]
        before = deepcopy(entry['scene']['entities'])
        apply_sample_labels(entry)
        after = entry['scene']['entities']
        assert [e['entity_ref'] for e in after] == [e['entity_ref'] for e in before]
        assert [e['mesh'] for e in after] == [e['mesh'] for e in before]
        assert all(not any(token in e['display_name'] for token in ('Export07A', 'Generator', 'common_1')) for e in after)
        assert all(e['source']['original_display_name'] == old['display_name'] for e, old in zip(after, before))
        if case != 'CASE01':
            inputs = [e['display_name'] for e in after if e['scene_role'] == 'input']
            assert inputs == ['输入 1：外圆柱壳', '输入 2：内圆柱芯']
        else:
            assert [e['display_name'] for e in after if e['scene_role'] == 'common_interface'] == ['公共接口补丁：A–G', '公共接口补丁：G–B']
