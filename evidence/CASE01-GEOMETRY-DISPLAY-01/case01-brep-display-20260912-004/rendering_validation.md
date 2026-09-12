# Rendering validation

`user-observation-003-unreadable.png` is preserved as `CHAT` evidence of the
previous display failure. It shows a single unshaded cyan silhouette even
though the corresponding B-rep tessellation test proves the Region mesh is
closed.

This run adds display-only flat shading using each tessellated triangle's
normal and a fixed light vector. It also draws only mesh edges whose adjacent
triangle normals are non-coplanar, excluding coplanar triangulation diagonals.
This makes the actual box facets legible without changing source geometry,
Snapshot contents, Patch identity, or mesh-to-entity references.

The next visual acceptance remains a user observation: browser automation is
blocked from opening local `file://` pages and no automated screenshot claim is
made.
