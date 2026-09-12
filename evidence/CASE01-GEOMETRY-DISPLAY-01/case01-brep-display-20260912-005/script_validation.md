# Script validation

The preceding display artifact (004) failed before initialization: the user
observed an empty canvas plus static sidebar text, with no generated controls.
`user-observation-004-script-failure.png` preserves that `CHAT` evidence.

Root cause: the generated `facetEdges` JavaScript contained malformed nested
array syntax in its triangle-edge loop. The browser consequently rejected the
entire script, so no entity controls or rendering could start.

This run rewrites that loop using explicit `edge` records. The regression test
now extracts the generated `<script>` and runs `node --check -`; it passes.
This proves parseability, not a claimed automated browser interaction. Local
`file://` browser automation remains unavailable under the URL policy.
