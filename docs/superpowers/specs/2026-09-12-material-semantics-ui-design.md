# Material and semantics UI design

## Purpose

Bring the useful interaction structure of the local slicer reference into the
09B material-and-semantics prototype without copying its AMF import path,
PyVista renderer, or implementation. The prototype continues to use
`.dmslicer` result packages. The proven 56810 geometry viewer is a protected
reference and remains unchanged.

## Boundaries

- The 56810 service, page, and protected baseline are not modified by this Goal.
- STEP/B-rep remains geometry authority; displayed mesh remains display-only.
- Material and semantic choices are explicit workspace annotations. They do
  not create geometry relations or activate a volumetric field.
- The reference application's code, AMF assumptions, and rendering stack are
  outside scope.

## Prototype pages and context

The 09B prototype provides the following material workflow:

1. **Object assignments** lists stable input objects and opens the material and
   semantics dialog for an explicit selection.
2. **Material library** lists definitions and opens the material-property
   dialog for add or edit.

The prototype may borrow spacing, hierarchy, and interaction ideas from 56810,
but it must not embed, copy wholesale, or replace 56810. A later integration
decision requires a separate user-reviewed Goal after this prototype is shown.

## Material library

The library is the stable list of material definitions. It exposes an
**Add material** action. Add and Edit open the same dialog; Edit starts from a
copy and never removes the original record before a validated replacement is
accepted. Closing or cancelling the dialog leaves the library unchanged.

Color is a first-class material field with a visible, clickable swatch in both
the library row and the dialog. It is not represented as a generic property.
Composition uses its own structured editor and state, so changing the selected
property cannot reuse a prior color or numeric value as composition input.

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
  evidence drawer remain untouched.
- Material-library add/edit/restore are covered by unit and browser checks.
- Object dialog is checked for Source, Gradient, Isolator, Unassigned, one
  object, and multiple objects.
- Browser review confirms 09B has no copied 56810 page, no AMF import route,
  and no copied PyVista component.
- Every saved annotation includes case id, stable object references, material
  library version, explicit semantic decision, and display override when one
  exists.

## Reference interaction audit

The local Streamlit reference was exercised before implementation. Its useful
layout is the object list plus a contextual editor and a separate material
library. The following behaviors are defects and must not be copied:

- Edit removes a material from the library before the user saves the edited
  copy.
- Initialize can discard the loaded-model session when all objects are
  selected; the 09B reset action changes annotation drafts only.
- Completed objects disappear from the Process selector and cannot be edited
  again without reinitialization; 09B keeps every stable object editable.
- Apply and Save are not clearly separated; 09B uses Apply for an atomic draft
  update and Save for persistence of the complete configuration.
- Color is hidden inside the generic property selector and object ID swatches
  are not interactive.
- Switching from color to composition can leak the previous color value into
  the composition editor.

The 09B object list is therefore the selection and navigation surface. It does
not add a second Process selector. Reset affects only selected assignments and
must retain the active case and geometry state; Show remains a display-only
operation.
