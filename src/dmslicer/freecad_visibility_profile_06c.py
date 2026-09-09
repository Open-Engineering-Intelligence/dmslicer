"""Apply and verify a persisted GUI visibility profile for a 06C FCStd."""

import json
import os
import traceback
from pathlib import Path

import FreeCAD
import FreeCADGui


def _main():
    request_path = Path(os.environ["DMSLICER_VISIBILITY_REQUEST"])
    response_path = Path(os.environ["DMSLICER_VISIBILITY_RESPONSE"])
    try:
        request = json.loads(request_path.read_text(encoding="utf-8"))
        document = FreeCAD.openDocument(request["fcstd_path"])
        try:
            visible_names = set(request["visible_objects"])
            for obj in document.Objects:
                if obj.ViewObject is not None:
                    obj.ViewObject.Visibility = obj.Name in visible_names
            document.recompute()
            document.save()
        finally:
            FreeCAD.closeDocument(document.Name)
        reopened = FreeCAD.openDocument(request["fcstd_path"])
        try:
            actual = sorted(
                obj.Name
                for obj in reopened.Objects
                if obj.ViewObject is not None and obj.ViewObject.Visibility
            )
            groups = sorted(
                obj.Name
                for obj in reopened.Objects
                if obj.TypeId == "App::DocumentObjectGroup"
            )
            response = {
                "status": "SUCCEEDED",
                "reopened": True,
                "gui_visibility_persisted": True,
                "groups": groups,
                "visible_objects": actual,
                "requested_visible_objects": sorted(visible_names),
                "profile_matches": actual == sorted(visible_names),
            }
        finally:
            FreeCAD.closeDocument(reopened.Name)
    except Exception:
        response = {"status": "FAILED", "traceback": traceback.format_exc()}
    response_path.write_text(json.dumps(response, sort_keys=True), encoding="utf-8")
    FreeCADGui.getMainWindow().close()


_main()
