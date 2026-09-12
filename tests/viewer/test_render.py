"""Static document and real-browser tests for the model-only renderer.

Browser tests use an existing Node/Playwright installation (NODE_PATH may point
to a bundled installation). No browser or package is downloaded by these tests.
"""

from copy import deepcopy
from html.parser import HTMLParser
import importlib
import json
import os
from pathlib import Path
import subprocess

import pytest

from contract_consumers.slicer_mock import decide
from dmslicer.viewer import build_viewer_model


ROOT = Path(__file__).resolve().parents[2]


def model(name, group="geometry", decision=True):
    snapshot = json.loads((ROOT / "contract_examples/v0.1" / group / f"{name}.json").read_text(encoding="utf-8"))
    return build_viewer_model(snapshot, decide(snapshot, ROOT) if decision else None, repository_root=ROOT)


def render(view):
    try:
        module = importlib.import_module("dmslicer.viewer.render")
    except ModuleNotFoundError as error:
        if error.name == "dmslicer.viewer.render":
            pytest.fail("HTML renderer is not implemented")
        raise
    return module.render_html(view)


class Document(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.scripts = []
        self.resources = []
        self.current = None
        self.feed(html)

    def handle_starttag(self, tag, attrs):
        attrs = dict(attrs)
        if tag == "script":
            self.current = {"attrs": attrs, "text": ""}
            self.scripts.append(self.current)
        if "src" in attrs or (tag in {"link", "base"} and "href" in attrs):
            self.resources.append((tag, attrs))

    def handle_data(self, data):
        if self.current is not None:
            self.current["text"] += data

    def handle_endtag(self, tag):
        if tag == "script":
            self.current = None


@pytest.mark.parametrize("name,group", [
    ("planar_full", "geometry"), ("planar_partial", "geometry"),
    ("planar_multipatch", "geometry"), ("ambiguous_relation", "negative"),
    ("unresolved_artifact", "negative"),
])
def test_document_contains_exact_model_and_only_self_contained_resources(name, group):
    view = model(name, group)
    parsed = Document(render(view))
    data = [s for s in parsed.scripts if s["attrs"].get("type") == "application/json"]
    assert len(data) == 1
    assert json.loads(data[0]["text"]) == view
    assert len(parsed.scripts) == 2
    assert parsed.resources == []


def test_html_is_deterministic_without_mutating_model_or_adding_local_paths():
    view = model("planar_partial")
    before = deepcopy(view)
    first = render(view)
    assert first == render(view)
    assert view == before
    assert str(ROOT) not in first and ROOT.as_posix() not in first
    assert "file:///" not in first


def test_hostile_payload_stays_json_data_not_executable_script():
    view = model("planar_partial")
    payload = '</script><script>alert(1)</script><img src=x onerror=alert(2)> & \u2028\u2029'
    view["metadata"]["label"] = payload
    parsed = Document(render(view))
    assert len(parsed.scripts) == 2
    data = next(s for s in parsed.scripts if s["attrs"].get("type") == "application/json")
    assert json.loads(data["text"])["metadata"]["label"] == payload
    assert "</script>" not in data["text"]
    assert parsed.resources == []


@pytest.fixture(scope="module")
def browser_results(tmp_path_factory):
    directory = tmp_path_factory.mktemp("viewer-render")
    views = {
        "full": model("planar_full"),
        "partial": model("planar_partial"),
        "multi": model("planar_multipatch"),
        "ambiguous": model("ambiguous_relation", "negative"),
        "invalid": model("unresolved_artifact", "negative"),
        "no_decision": model("planar_partial", decision=False),
    }
    views["unavailable"] = deepcopy(views["invalid"])
    views["unavailable"]["validation"]["snapshot"] = {
        "status": "UNAVAILABLE", "issues": [{"code": "VALIDATION_UNAVAILABLE", "path": "$", "message": "Path check unavailable"}],
    }
    # Defense at the rendering boundary: invalid status must suppress even
    # stale entity records from a saved model.
    views["unavailable"]["regions"] = deepcopy(views["partial"]["regions"])
    hostile = deepcopy(views["partial"])
    payload = '</script><script>alert(1)</script><img src=x onerror=alert(2)>'
    hostile["metadata"]["label"] = payload
    hostile["regions"][0]["label"] = payload
    hostile["artifact_links"][0]["uri"] = "javascript:alert(3)"
    hostile["artifact_links"][0]["resolution"] = "RESOLVED"
    views["hostile"] = hostile
    views["surrogate_id"] = deepcopy(views["partial"])
    views["surrogate_id"]["semantic_bindings"][0]["binding_id"] = "binding:\ud800"
    for name, view in views.items():
        (directory / f"{name}.html").write_text(render(view), encoding="utf-8")
    script = r'''
const {chromium} = require('playwright');
const {pathToFileURL} = require('node:url');
const path = require('node:path');
(async () => {
  const browser = await chromium.launch({headless:true});
  const context = await browser.newContext({viewport:{width:1360,height:900}});
  const result = {};
  for (const name of ['full','partial','multi','ambiguous','invalid','unavailable','no_decision','hostile','surrogate_id']) {
    const page = await context.newPage();
    page.setDefaultTimeout(5000);
    const errors = [], requests = [], dialogs = [];
    page.on('pageerror', e => errors.push(String(e)));
    page.on('console', m => {if (m.type()==='error') errors.push(m.text());});
    page.on('request', r => {if (!r.url().startsWith('file:')) requests.push(r.url());});
    page.on('dialog', async d => {dialogs.push(d.message()); await d.dismiss();});
    await page.goto(pathToFileURL(path.join(process.argv[2],name+'.html')).href);
    await page.waitForFunction(() => document.documentElement.dataset.ready === 'true');
    result[name] = {
      title:await page.title(), text:await page.locator('body').innerText(),
      navCount:await page.locator('nav a[data-entity-id]').count(),
      selected:await page.locator('nav .selection-mark').allTextContents(),
      partitionRows:await page.locator('#partition-summary > tbody > tr').allTextContents(),
      externalAnchors:await page.locator('a:not([href^="#"])').count(),
      errors,requests,dialogs
    };
    async function follow(locator) {
      const id=await locator.getAttribute('data-entity-id');
      await locator.click();
      await page.waitForFunction(id => document.querySelector('#entity-detail').dataset.entityId === id, id);
    }
    if (name==='full') {
      await follow(page.locator('nav a[data-entity-id="region:e0-a"]'));
      result.full.regionDetail = await page.locator('#entity-detail').innerText();
      await follow(page.locator('#entity-detail .backreferences a[data-entity-id^="relation:"]').first());
      result.full.relationDetail = await page.locator('#entity-detail').innerText();
      await follow(page.locator('#entity-detail a[data-entity-id="region:e0-a"]').first());
      result.full.returnDetail = await page.locator('#entity-detail').innerText();
    }
    if (name==='partial') {
      await follow(page.locator('nav a[data-entity-id="patch:e1-common"]'));
      result.partial.patchDetail = await page.locator('#entity-detail').innerText();
      await follow(page.locator('#entity-detail a[data-entity-id^="component:"]').first());
      result.partial.componentDetail = await page.locator('#entity-detail').innerText();
    }
    if (name==='hostile') {
      await follow(page.locator('nav a[data-entity-id="region:e1-side-1"]'));
      result.hostile.detail = await page.locator('#entity-detail').innerText();
      result.hostile.injectedElements = await page.locator('img,script:not(#viewer-model):not(#viewer-code)').count();
    }
    if (name==='surrogate_id') {
      await page.evaluate(() => Array.from(document.querySelectorAll('nav a[data-entity-id]')).find(a=>a.dataset.entityId==='binding:\ud800').click());
      await page.waitForFunction(() => document.querySelector('#entity-detail').dataset.entityId==='binding:\ud800');
      result.surrogate_id.detail = await page.locator('#entity-detail').innerText();
    }
    await page.close();
  }
  await browser.close();
  console.log(JSON.stringify(result));
})().catch(e=>{console.error(e);process.exit(1)});
'''
    runner = directory / "check.cjs"
    runner.write_text(script, encoding="utf-8")
    result = subprocess.run(
        [os.environ.get("DMSLICER_TEST_NODE", "node"), str(runner), str(directory)],
        capture_output=True, text=True, encoding="utf-8", check=False, timeout=90,
    )
    assert result.returncode == 0, result.stderr
    return json.loads(result.stdout)


@pytest.mark.parametrize("name", ["full", "partial", "multi", "ambiguous", "invalid", "unavailable", "no_decision", "hostile"])
def test_browser_pages_have_identity_banner_and_no_runtime_or_network_errors(browser_results, name):
    result = browser_results[name]
    assert result["title"] == "DM-Slicer Geometry Snapshot Viewer"
    assert "CONTRACT TOPOLOGY / NON-GEOMETRIC VIEW" in result["text"]
    assert result["errors"] == result["requests"] == result["dialogs"] == []
    assert result["externalAnchors"] == 0


def test_full_page_separates_taxonomy_and_confirmation(browser_results):
    text = browser_results["full"]["text"]
    assert "Taxonomy" in text and "Confirmation" in text
    assert "Confirmed to be disjoint" in text
    assert "FULL_FACE_OVERLAP" in text
    assert browser_results["full"]["selected"] == []


def test_partial_page_shows_three_distinct_partitions_and_decision_selection(browser_results):
    result = browser_results["partial"]
    assert len(result["partitionRows"]) == 3
    assert sum("REMAINING" in row and "320 mm2" in row for row in result["partitionRows"]) == 2
    assert sum("COMMON" in row and "480 mm2" in row for row in result["partitionRows"]) == 1
    assert sorted(result["selected"]) == ["Selected interface", "Selected patch", "Target region"]
    for value in ("PLANAR_INTERFACE_PARTITION", "partition_direction", "local_frame_ref", "SPLIT_COMMON_AND_REMAINING", "Expected / NOT_EXECUTED"):
        assert value in result["text"]


def test_multipatch_preserves_separate_entities_absence_and_invalid_decision(browser_results):
    result = browser_results["multi"]
    assert "patch:e2-one" in result["text"] and "patch:e2-two" in result["text"]
    assert "Components (2)" in result["text"] and "Patches (2)" in result["text"]
    assert "Boundaries — ABSENT" in result["text"]
    assert "Surface Partitions — ABSENT" in result["text"]
    assert "expected_partition_refs" in result["text"] and "INVALID_DECISION" in result["text"]
    assert result["selected"] == [] and result["navCount"] > 0


def test_ambiguous_relation_is_visible_without_interface(browser_results):
    result = browser_results["ambiguous"]
    assert "AMBIGUOUS" in result["text"]
    assert "Interfaces — ABSENT" in result["text"]
    assert result["selected"] == []


@pytest.mark.parametrize("name,code", [("invalid", "UNRESOLVED_ARTIFACT"), ("unavailable", "VALIDATION_UNAVAILABLE")])
def test_invalid_snapshot_has_diagnostics_without_authoritative_navigation(browser_results, name, code):
    result = browser_results[name]
    assert code in result["text"]
    assert result["navCount"] == 0 and result["selected"] == []


def test_cross_references_navigate_both_directions(browser_results):
    full = browser_results["full"]
    assert "Referenced by" in full["regionDetail"]
    assert "taxonomy" in full["relationDetail"]
    assert "region:e0-a" in full["returnDetail"] and "validity_state" in full["returnDetail"]
    partial = browser_results["partial"]
    assert "Selected patch" in partial["patchDetail"]
    assert "patch:e1-common" in partial["componentDetail"]


def test_hostile_strings_render_as_text_and_saved_resolved_status_creates_no_link(browser_results):
    hostile = browser_results["hostile"]
    assert "</script><script>alert(1)</script>" in hostile["detail"]
    assert hostile["injectedElements"] == 0
    assert hostile["externalAnchors"] == 0


def test_optional_decision_can_be_absent(browser_results):
    assert "NOT_PROVIDED" in browser_results["no_decision"]["text"]
    assert browser_results["no_decision"]["selected"] == []


def test_json_identifier_with_lone_surrogate_does_not_abort_navigation(browser_results):
    result = browser_results["surrogate_id"]
    assert result["errors"] == []
    assert "semantic_role" in result["detail"]
