"""Task-local manifest assembly; all text reads explicit UTF-8 on Windows."""
from pathlib import Path
import datetime
import hashlib
import json
import platform
import subprocess

root = Path(__file__).resolve().parents[3]
goal = root / 'evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01'
final = goal / 'final-001'
read = lambda p: json.loads(p.read_text(encoding='utf-8'))
git = lambda *args: subprocess.check_output(['git', *args], cwd=root, text=True).strip()
commit, baseline, branch = git('rev-parse', 'HEAD'), git('rev-parse', '91e4d98'), git('branch', '--show-current')
inputs = read(final / 'samples.json')['samples']
for item in inputs:
    item['input_fixture'] = item['path']
    item['input_sha256'] = hashlib.sha256((final / item['path']).read_bytes()).hexdigest()
    assert item['input_sha256'] == item['sha256']
    item['geometry_validation'] = 'NOT_RERUN_SOURCE_RESULT_ONLY'
browser = read(final / 'browser-live-001/checks.json')
assert browser['status'] == 'PASS'
failures = []
for path in sorted(goal.glob('*/checks.json')):
    data = read(path)
    if data.get('status') == 'FAIL':
        failures.append({'path': path.relative_to(goal).as_posix(), 'failure': data.get('failure'), 'status': 'PRESERVED', 'provenance': 'L'})
manifest = {
    'goal_id': 'WORKBENCH-MATERIAL-SEMANTIC-UI-01', 'run_id': 'final-001',
    'task_title': 'DM-Slicer｜09B 材料与语义配置工作区', 'branch': branch,
    'implementation_commit': commit, 'policy_commit': baseline, 'parent_baseline': baseline,
    'merge_base': git('merge-base', commit, 'main'),
    'evidence_identity': 'WORKBENCH-MATERIAL-SEMANTIC-UI-01+' + commit + '+final-001',
    'scope': '09B material library, semantic_type, gradient_group_id, object-scoped Isolator, independent persistence',
    'acceptance_criteria': '../scope-002/SEMANTIC_TYPES_V2.md',
    'stop_conditions': ['No push/merge/release', 'No docs/research_v2 edits', 'No CAD rerun or semantic activation', 'Geometry bulk controls/drawer redesign removed from 09B to09A'],
    'inputs': inputs,
    'environment': {'Python': platform.python_version(), 'pytest': subprocess.check_output(['py', '-3.12', '-m', 'pytest', '--version'], text=True).strip(),
                    'Node': subprocess.check_output(['node', '--version'], text=True).strip(), 'FreeCAD': 'NOT_INVOKED', 'OCCT': 'NOT_INVOKED',
                    'browser': browser['browser'], 'viewports': browser['viewports']},
    'commands': [
        {'command': 'node --test --test-reporter=spec --test-reporter-destination=evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/final-001/model-tests.txt --test-reporter=junit --test-reporter-destination=evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/final-001/model.junit.xml tests/workspace_annotations.test.cjs', 'exit_code': 0, 'result': '11 PASS'},
        {'command': 'py -3.12 -m pytest tests/test_geometry_case_viewer.py tests/test_result_package.py tests/test_geometry_import.py tests/test_case01_result_package.py tests/test_result_labels.py tests/test_unified_workbench.py -q --junitxml=evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/final-001/regression.xml', 'exit_code': 0, 'result': '22 PASS after exact restoration of 3 omitted local test fixtures'},
        {'command': 'node tests/material_workspace_browser.cjs', 'environment': {'DMS_WORKBENCH_URL': 'http://127.0.0.1:56811/', 'DMS_BROWSER_OUTPUT': 'evidence/WORKBENCH-MATERIAL-SEMANTIC-UI-01/final-001/browser-live-001', 'NODE_PATH': 'bundled workspace dependency node_modules'}, 'exit_code': 0, 'result': str(len(browser['checks'])) + ' browser checks PASS'},
        {'command': 'git diff --quiet 91e4d98 -- docs/research_v2', 'exit_code': 0, 'result': 'Frozen research contract unchanged'},
    ],
    'execution_timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    'tolerances': [],
    'tolerance_note': 'No geometry tolerance applied. Display deflections are retained inside unmodified package bytes. Synthetic policy predicates perform no geometry comparison.',
    'JUnit': ['model.junit.xml', 'regression.xml'],
    'validator': ['browser-live-001/checks.json', 'policy-decisions.json', 'custody-script-checks.json', 'custody-verification.json'],
    'STEP_BREP_FCStd': 'Original assets inside five allowlisted .dmslicer packages; no CAD file opened or resaved',
    'VIEW_INDEX': 'VIEW_INDEX.md', 'HUMAN_REVIEW': 'HUMAN_REVIEW.md',
    'failure_commit': 'aa6f76babffd5c6f7335b1fe476a235cc97ad179', 'initial_red_commit': 'abc532d', 'fix_commit': commit,
    'reviewer_finding': 'Independent reviewer found dirty-draft overwrite and async case-binding race. Both fixed and independently rechecked; no remaining important finding.',
    'known_mismatch_or_failure_mode': [
        'Only CASE01 provides stable editable input references; other four samples remain domain-read-only',
        'Isolator material requirement remains UNDECIDED', 'Ambiguous v1 annotations rejected; no silent migration',
        'Source/boundary relation editing, composition derivation, domain merge, state propagation and field activation not implemented',
        'Browser storage is origin-specific and is not a backup; export files required for portability',
        'Original geometry controls retained; batch selection/transparency/drawer work moved to09A',
        'QA numeric material data explicitly marked synthetic TEST ONLY with source/unit/evidence',
        'Broader regression first failed on three untracked fixture packages; exact byte copies restored and failure preserved',
    ],
    'actual_geometry_validation_criteria': 'NOT_APPLICABLE_UI_ONLY. Connectivity policy is conditional on upstream confirmed geometry and is not a geometry validator.',
    'results': {'model_tests': 'PASS', 'python_regression': 'PASS', 'browser_checks': 'PASS', 'package_byte_integrity': 'PASS', 'scientific_experiment': 'NOT_RERUN', 'geometry_equivalence': 'NOT_ASSESSED', 'human_visual_acceptance': 'PENDING'},
    'failures': failures, 'evidence_confidence': 'L', 'hash_semantics': 'BYTE_INTEGRITY_ONLY',
    'custody': {'verification': 'custody-verification.json', 'copy_plan': 'copy-plan.json', 'independent_disaster_recovery': 'NOT_ESTABLISHED', 'external_actions': 'NONE'},
    'model_configuration_request': {'requested_phase': 'Terra / Medium UI implementation; Astra / High for substantive boundary conflict', 'actual_runtime_switch': 'NOT_INDEPENDENTLY_VERIFIED'},
}
with (final / 'manifest.json').open('x', encoding='utf-8') as stream:
    json.dump(manifest, stream, ensure_ascii=False, indent=2)
print(json.dumps({'implementation_commit': commit, 'inputs': len(inputs), 'browser_checks': len(browser['checks']), 'preserved_browser_failures': len(failures)}))
