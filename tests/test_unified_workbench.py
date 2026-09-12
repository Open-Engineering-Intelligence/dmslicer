import json
from pathlib import Path
import subprocess

import pytest

from dmslicer.geometry_case_viewer import render_catalog
from test_geometry_case_viewer import catalog


def test_comparison_layout_handles_sparse_six_slots_without_mutating_entities():
    source = Path(__file__).resolve().parents[1] / 'src/dmslicer/viewer_layout.js'
    assert source.is_file(), 'Shared comparison layout is not implemented'
    script = source.read_text(encoding='utf-8') + '''
const entities=[0,1,2,3,4,9].map((s,i)=>({entity_ref:'e'+i,comparison_slot:s,display_name:'object '+i}));
const before=JSON.stringify(entities), layout=makePanelLayout(entities,true,1000,900);
if(layout.panels.length!==6||layout.rows!==3)throw Error('six slots must fit three rows');
for(const panel of layout.panels)if(panel.y+panel.h>900||panel.x+panel.w>1000)throw Error('clipped');
if(JSON.stringify(entities)!==before)throw Error('mutated evidence');
const common=makePanelLayout(entities,false,1000,900);
if(common.panels.length!==1)throw Error('overlay must share coordinates');
const fallback=makePanelLayout(entities.map(({comparison_slot,...e})=>e),true,1000,900);
if(fallback.panels.length!==6)throw Error('legacy package needs automatic panels');
console.log('PASS');
'''
    completed = subprocess.run(['node', '-'], input=script, capture_output=True, text=True)
    assert completed.returncode == 0, completed.stderr


def test_page_exposes_one_import_and_three_modes():
    html = render_catalog(catalog(), import_enabled=True)
    assert 'DM-Slicer 几何结果工作台' in html
    for mode in ('overlay', 'comparison', 'evidence'):
        assert f'value="{mode}"' in html
    assert 'id="package-file"' in html
    assert 'id="model-file"' not in html
