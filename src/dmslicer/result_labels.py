"""Presentation labels for inspected sample runs; never infer material semantics.

C02's STEP products are Side_1_Bore / Side_2_Shaft; U05's are
Side_1_Sleeve / Side_2_Core. Their producer export order and inspected diagnostic
Solid1/2 locators underpin this bounded mapping, not display mesh measurements.
"""
import argparse
import io
import json
from pathlib import Path
import zipfile

from .result_package import read_package, write_package


def apply_sample_labels(entry):
    case = entry['case_id']
    if case not in ('CASE01', 'C02', 'U05'):
        return
    for entity in entry['scene']['entities']:
        source = entity.setdefault('source', {})
        source.setdefault('original_display_name', entity['display_name'])
        role = entity['scene_role']
        if case == 'CASE01':
            names = {'A / SOURCE': '输入 A：方块 A', 'G / GRADIENT': '输入 G：方块 G', 'B / SOURCE': '输入 B：方块 B',
                     'A-G common face': '公共接口补丁：A–G', 'G-B common face': '公共接口补丁：G–B'}
            entity['display_name'] = names[source['original_display_name']]
            source['label_basis'] = 'Saved CASE01 display labels; no new semantic binding'
        elif role in ('input', 'corrected'):
            locator = source.get('object_locator', '')
            prefix = '输入' if role == 'input' else '校正后输入'
            if locator.endswith('/Solid1'):
                entity['display_name'] = prefix + ' 1：外圆柱壳'
                source['label_basis'] = 'Saved producer Side_1_Bore (C02) / Side_1_Sleeve (U05); run-local export order'
            elif locator.endswith('/Solid2'):
                entity['display_name'] = prefix + ' 2：内圆柱芯'
                source['label_basis'] = 'Saved producer Side_2_Shaft (C02) / Side_2_Core (U05); run-local export order'
        else:
            entity['display_name'] = {'common_interface': '公共接口补丁', 'remaining': '剩余分区：外圆柱壳', 'fused_result': '融合结果'}[role]
            source['label_basis'] = 'Saved operation output role; original diagnostic name retained'
    entry['provenance']['semantic_analysis'] = '输入对象是从结果包读取的几何实体，不表示材料区域；未增加材料语义绑定。'


def relabel(package, output):
    data = package.read_bytes()
    read_package(data)
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        manifest = json.loads(archive.read('manifest.json'))
        assets = {a['path']: archive.read(a['path']) for a in manifest['assets'] if a['path'] in archive.namelist()}
        display = json.loads(assets[manifest['display']])
    for entry in display['cases']:
        apply_sample_labels(entry)
    assets[manifest['display']] = json.dumps(display, ensure_ascii=True).encode()
    manifest['presentation_revision'] = {'scope': 'LABELS_ONLY', 'geometry_change': 'NONE', 'source_package': package.name}
    output.mkdir(parents=True, exist_ok=False)
    target = output / package.name
    saved = write_package(target, manifest, assets)
    (output / 'manifest.json').write_text(json.dumps(saved, indent=2), encoding='utf-8')
    return target


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('package', type=Path)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    print(relabel(args.package, args.output))
