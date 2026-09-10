# P2-MVP Local Acceptance Summary

- Goal: `P2-MVP`
- Run: `p2-mvp-acceptance-001`
- Branch: `feat/evidence-promotion-semantic-snapshot`
- Implementation commit: `219e893392e80766469790e3bc1b99d3d39fd345`
- Parent and merge base: `ea617b6b6fa8d074c1c89d6f61513fe4d892cef3`
- Test command: `py -3.12 -m pytest -q --junitxml=outputs/p2-mvp-acceptance-001/pytest.xml`
- Software result: 58 passed, 0 failed, 0 errors, 0 skipped
- Request and manifest schema: `2.0.0`
- SHA-256 role: file/copy integrity, custody, acquisition provenance, off-host verification, and reproducibility lookup only
- Failure retention: negative policy evidence is explicitly allowlisted with retention role `FAILURE`

Expected local promotion state:

- Local package: `LOCAL_PACKAGE_CREATED`
- Recoverable copy count: `2`
- Copy policy: `LOCAL_TWO_PATHS_NOT_OFF_HOST_REDUNDANCY`
- Preservation: `NOT_FULLY_PRESERVED`
- Publication: `PUBLICATION_NOT_AUTHORIZED`

P2-MVP does not evaluate CAD geometry, engineering semantic equivalence, or UI
state. Geometry therefore remains `GEOMETRIC_EQUIVALENCE_NOT_PROVEN`.
FreeCAD/OCCT comparison, CAD fixtures, Human Inspection artifacts, push, pull
request, Release, and off-host storage are deferred or not authorized.
