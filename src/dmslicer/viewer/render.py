"""Render an approved ViewerModel without reading any referenced artifact.

Phase 2A deliberately renders artifact/provenance URIs as plain text. Saved
resolution statuses are observations, not current file-existence guarantees.
No machine-specific href, filesystem lookup, or new model rule is introduced.
"""

from importlib.resources import files
import json

from .model import ViewerModel


def render_html(model: ViewerModel) -> str:
    """Return deterministic, self-contained HTML; never mutate the model.

    The JSON lives in a script raw-text element, so HTML entity escaping alone
    is insufficient. Escaping '<' prevents the HTML parser from recognizing a
    closing script tag. ensure_ascii also escapes Unicode line separators.
    All displayed contract values are subsequently assigned via textContent.
    """
    data = json.dumps(model, ensure_ascii=True, allow_nan=False, sort_keys=True, separators=(",", ":"))
    for char, escaped in (("<", "\\u003c"), (">", "\\u003e"), ("&", "\\u0026")):
        data = data.replace(char, escaped)
    template = files("dmslicer.viewer").joinpath("viewer.html").read_text(encoding="utf-8")
    return template.replace("__VIEWER_MODEL_JSON__", data)
