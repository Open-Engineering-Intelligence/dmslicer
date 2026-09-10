# Evidence Release upload inventory

This records the pre-upload gate and the verified post-publication inventory. Release/tag names are versioned and targets are implementation commits. Published assets are append-only by policy; a correction requires a new version and `supersedes` / `superseded_by` metadata.

## Approved upload candidates

### `goal-06a-evidence-aadf996`

Target: `aadf996a05bf87efee862964141b6aeb7f872baf`

| Asset | Bytes | SHA-256 | Source |
|---|---:|---|---|
| `goal-06a-canonical-evidence-aadf996.zip` | 63,249 | `2f0d7df9c19dde4acd4d1d445a265c1cbd5ee3960a25dd2c1a8b8b6ee63dc777` | curated Goal 06A custody copies |
| `goal-06a-evidence-manifest.json` | 26,146 | `6136247cc8a657f3eb558a9bafa527873ea70ace6228b1d5aa22503a6c5a8b55` | `manifests/goal-06a.json` published snapshot |
| `RELEASE_NOTES.md` | 591 | `5a2d9474f086503f542aec1f26a2cc08f6e5efb96d8732c440659b1c1583fd6c` | curated release notes |
| `UPLOAD_MANIFEST.json` | 1,489 | `8f997e28d841a8c2d7babe85057cec2909862b9a3971e302745a9a7c557f3082` | upload gate record |
| `SHA256SUMS.txt` | 378 | `eda101fb033122d8121f668acf7d1154a8920fc52cb866a2412bfded3e738e9e` | release control file |

Published: <https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06a-evidence-aadf996>

### `goal-06c-evidence-58ec93a`

Target: `58ec93a67d8214c69bc92d5710c60d91aa1fe30c`

| Asset | Bytes | SHA-256 | Source |
|---|---:|---|---|
| `goal-06c-canonical-evidence-58ec93a.zip` | 189,477 | `1bd135397e5624e772e0534ab75ab7a5dce19034562e805b8292b05558641f4b` | curated Goal 06C custody copies |
| `goal-06c-evidence-manifest.json` | 43,496 | `fb747fe2ecf554dacb033724733e0d023f8164a38ebc9db842a39ced70f8d545` | `manifests/goal-06c.json` published snapshot |
| `RELEASE_NOTES.md` | 635 | `53b88e0938f2cb7ef12edde550005ed098f9015b3bba2dd7419abbf123e7cfbc` | curated release notes |
| `UPLOAD_MANIFEST.json` | 1,490 | `f5af8f0c7f35d0bf746101d22bdb79c202c18353dc76f3ca642211fd95aff762` | upload gate record |
| `SHA256SUMS.txt` | 378 | `639599addd8ca991c24abb7e1d80c6f7fe53d6e7fd1b05976eeea435a7de9f62` | release control file |

Published: <https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06c-evidence-58ec93a>

### `goal-06d-evidence-b7054f3`

Target: geometry implementation `b7054f303896aa4a0762248a0b54686d8e733ead`. Policy-only commit `b42ba9e7b6efc6dd5a9dd9f7b1584b5a89066f8b` is not the Release target.

| Asset | Bytes | SHA-256 | Source |
|---|---:|---|---|
| `goal-06d-canonical-geometry-b7054f3.zip` | 342,458 | `f9be4d7170bccf9b7f949766751c9fbe9b43579b903b8cf6024d842d24839a1f` | curated Goal 06D geometry custody copies |
| `goal-06d-human-review-v2-b7054f3.zip` | 87,802 | `d412caba96a801f4331ac47425014638c647a766d2aea15e5346c1d267fc4675` | self-contained review package from verified custody copies |
| `goal-06d-evidence-manifest.json` | 65,482 | `81319e10b54c885efce0d644877c4486d52af78c9e2fa5c369f61cd6477c2e1f` | `manifests/goal-06d.json` published snapshot |
| `RELEASE_NOTES.md` | 880 | `97eb55ee772a8ec29a4b3df9931518738c7116877093d4fbad14a8975f593afd` | curated release notes |
| `UPLOAD_MANIFEST.json` | 1,759 | `10a68bb1c47d5f2e41996a3299beb05aa59d3ed256f747b810887666b336d493` | upload gate record |
| `SHA256SUMS.txt` | 482 | `bd3f254a13d089dffff829efaece683a7482f7ea164ec202adf77eca4df233d0` | release control file |

Published: <https://github.com/Open-Engineering-Intelligence/dmslicer/releases/tag/goal-06d-evidence-b7054f3>

GitHub's post-publication asset digest and size for every uploaded file matched this final local inventory. The 16 published assets total 826,192 bytes.

## Blocked or out of scope

| Goal | Status | Gate reason |
|---|---|---|
| 02C | `RELEASE_BLOCKED_PROVENANCE` | existing bundle embeds `79f60fa`; it cannot be rebound to `b646027` |
| 03A | `NOT_IN_P0_RELEASE_SCOPE` | manifest created; packaging commit is a sibling history not inherited downstream |
| 03B | `NOT_IN_P0_RELEASE_SCOPE` | manifest created; no selected P0 canonical output set |
| 03C | `RELEASE_BLOCKED_PROVENANCE` | pre-fix evidence binds `1c227cf`; post-fix execution does not explicitly bind `4a2aad8` |
| 04A | `RELEASE_BLOCKED_PROVENANCE` | A02/A08 custody is verified, but the historical run-to-`1935427` binding is unresolved |
| 04B | `NOT_IN_P0_RELEASE_SCOPE` | manifest created; no selected P0 canonical output set |
| 05A | `NOT_IN_P0_RELEASE_SCOPE` | manifest created; no selected P0 canonical output set |
| 05B | `RELEASE_BLOCKED_PROVENANCE` | 16/90 and 1/90 results are retained; output-to-`1de21fd` binding is not explicit |
| 05C | `RELEASE_BLOCKED_PROVENANCE` | preserved input-resolution evidence binds `0d681a9`, not final `fa4436a` |
| 06B | `RELEASE_BLOCKED_PROVENANCE` | operation evidence records validator source `aadf996`, not implementation `c23cc83` |

## Gate conclusion

06A, 06C, and 06D passed the source, size, SHA-256, sensitivity, duplication, failure-retention, and target-commit gates and were published. Blocked Goals must not be published until their provenance gaps are resolved without rerunning over historical outputs.
