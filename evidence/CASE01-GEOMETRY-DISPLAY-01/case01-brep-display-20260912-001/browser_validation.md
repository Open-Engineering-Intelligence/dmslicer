# Browser validation

The generated `case01_3d.html` was queued for opening in the Codex panel.

Automated interactive validation was blocked before page load: the available
browser automation policy refuses local `file://` URLs. No policy bypass or
alternate browser-control mechanism was attempted. Therefore this package does
not claim a browser screenshot, console-clean result, or executed selection /
visibility interaction.

The deterministic artifact-level test in `tests/test_case01_display.py` does
verify the emitted canvas, visibility-checkbox, selection-traceability markup,
three Region mesh entities, two Patch mesh entities, and their stable entity
references. It is not a substitute for the blocked browser interaction.
