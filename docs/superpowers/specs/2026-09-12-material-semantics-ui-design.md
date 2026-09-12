# Material and semantics UI design

## Purpose

Bring the useful interaction structure of the local slicer reference into the
DM-Slicer workbench without copying its AMF import path, PyVista renderer, or
implementation. The workbench continues to use `.dmslicer` result packages
and the proven 56810 geometry viewer.

## Boundaries

- The geometry page remains the only page with a 3D canvas.
- STEP/B-rep remains geometry authority; displayed mesh remains display-only.
- Material and semantic choices are explicit workspace annotations. They do
  not create geometry relations or activate a volumetric field.
- The reference application's code, AMF assumptions, and rendering stack are
  outside scope.

## Pages and shared context

The workbench has two peer pages under one shared shell:

1. **Geometry** keeps the current 56810 import, scene, camera, visibility,
   hit-selection, and evidence experience.
2. **Material and semantics** is a full page without a geometry canvas. It
   receives the active case id and stable object references from the shared
   workbench context, then reads and writes only annotation state.

Changing page does not reload the result package, discard the selected object,
or silently drop an unsaved annotation draft.

## Material library

The library is a table of named material records. It has a primary **Add
material** action. Add and edit open the same material-property dialog, with
name, display color, description, and extensible properties. Selecting a
library row enables Edit. Material records are definitions only; adding one
does not assign it to an object.

Initial records include PLA, ABS, PETG, and TPO. New records must have a
stable key, valid display color, and an explicit user-provided name.

## Object assignment flow

The page shows an object table containing stable object reference, display
name, geometry role, semantic type, material, group, and save state. Users
select one or more rows and invoke **Edit material and semantics**. The dialog
states the selected-object count and applies fields only to that explicit set.

The dialog uses conditional fields:

| Semantic type | Required fields | Prohibited automatic inference |
| --- | --- | --- |
| Source | Material selection | Material or semantics from color/geometry contact |
| Gradient | Group `G`, `G1`, `G2`, or a user-created group | Direct material assignment |
| Isolator | Object-scoped isolation properties | Cross-object merge or self-association |
| Unassigned | None | Any material or semantic activation |

Material color is the default display color. A separate, recorded display
override may be set in the dialog, but it must not change the material record.

## Interaction decisions

- A dialog, rather than inline table editing, concentrates the conditional
  settings and makes a multi-object operation visible before save.
- The library dialog and object-assignment dialog are separate. The assignment
  dialog offers **Add material** as a secondary action; it opens the library
  dialog and returns to the assignment draft after the material is created.
- Evidence stays in the existing collapsed drawer. It records annotation
  decisions and stable object references, separately from geometry evidence.

## Errors and validation

- Saving a Source without material fails without mutating prior persisted
  annotation state.
- Saving a Gradient with a material fails.
- An annotation for an unknown case or unstable object reference fails without
  altering the current page.
- Leaving a dialog with unsaved changes asks the user to keep editing,
  discard, or save.

## Verification

- Existing 56810 geometry controls, rendering, camera, Fit, boundaries, and
  evidence drawer keep their behavior.
- Material-library add/edit/restore are covered by unit and browser checks.
- Object dialog is checked for Source, Gradient, Isolator, Unassigned, one
  object, and multiple objects.
- Browser review confirms no second geometry canvas, no AMF import route, and
  no copied PyVista component.
- Every saved annotation includes case id, stable object references, material
  library version, explicit semantic decision, and display override when one
  exists.
