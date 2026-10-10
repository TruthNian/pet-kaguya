# Pet Kaguya

Local Kaguya artwork, native-compatible development sprites, and reproducible tools.

## Current version

The selected full AI mother is **canonical-v3**. Its face, identity and costume are locked; rejected Phase 3/4 composites and procedural jaw edits are not production sources.

- Current development atlas: [candidates/phase5/global](candidates/phase5/global/build.json), nine action rows and sixteen gaze cells.
- Accepted as development bases only: restrained frontal steps, the new failed mouth, 4px hop and lowered waving peak.
- Original-eye texture flow is now an accepted eye-motion development basis. Sixteen looks reuse the exact approved pixels; frontal steps, processing and review share the same quieter model. Iris texture can deform slightly; the face/eye outline stays fixed.
- Waiting/review held timing is temporarily accepted, not their hand/sleeve anatomy.
- The turning-palm waving middle cel is now a developer-selected continuity improvement, preserving the accepted peak and canonical rest. Its hand/clothing and full motion still lack human acceptance.
- Review now uses developer-selected relaxed overlapping hands over its v6 base, with the same accepted eye flow, alpha and held timing. Hand/cuff anatomy and full motion still lack human acceptance.
- Cloth lag and float sampling remain **unadopted trials**. The old-eye overlapping-hand animation is historical, not the current review.
- This is **not an approved release**. Installed pet resources and the installed application have not been changed.

### Watch the actual current version once

Start the local server, then open [the 55-second whole review](viewer/whole-review.html).
It presents the same current cel at 113px/224px on light/dark backgrounds.
All nine actions use their native hold schedules; non-idle actions repeat three times, then show idle.
Sixteen pointer directions follow, held 600ms each **as an observation setting**, not native animation timing.
No artwork regeneration, interpolation, video codec or extra dependency is required.

Use [the detailed comparison page](viewer/index.html) only when investigating a particular defect.
The whole review excludes all unadopted candidates, so they cannot be confused with the current version.

## Real remaining issues

| Area | Still incomplete |
| --- | --- |
| Hands and clothing | Waiting/review hand volume, wrist/cuff joins, sleeve edges and hidden-hair integration need visual judgement and refinement. |
| Natural motion | Discrete holds, arbitrary state cuts, airborne interruptions and held-hand entry/exit remain; current prototypes are not finished motion. |
| Small-size expression | Several gestures and nearby gaze directions are weak at 80px. |
| Eye materials | Accepted original-eye texture flow reduces observed duplicate pale rims without iris extraction or generated eye-white backing. Complete naturalness, small-size direction legibility and slight iris deformation still need judgement. |
| Host capabilities | Native 192×208 cells, fixed hold times, pixelated scaling and pointer priority are unchanged. Atlas edits cannot remove these constraints. |
| Delivery and measurement | Complete aesthetic acceptance, native-host loading of the new atlas, final release and real CPU/GPU/FPS measurements are not established. |

The current atlas is 1,003,424 encoded bytes and decodes to 14,057,472 RGBA bytes.
Changed artwork is not a same-content compression result; file size does not prove FPS or texture-memory improvement.
See the [full scope/acceptance ledger](docs/REQUIREMENTS.zh-CN.md) and [chronological work record](docs/PHASE5-STATES.zh-CN.md).
Old long-form README notes remain in [Git history](https://github.com/TruthNian/pet-kaguya/blob/165d52c1050cef67c6cd7d01098587e972adb343/README.md), not as misleading current status.

## Build / verify / preview

Requires Python 3.12+ and Node 22+.

```sh
python -m pip install -r requirements.txt
python tools/verify_fast.py
python -m http.server 8767 --bind 127.0.0.1
```

Use http://127.0.0.1:8767/viewer/whole-review.html for the whole review.
The fast check reads current pixels/contracts; it does not rerender historical studies.
Build only the action being edited and check only affected playback logic.
Unadopted float-sampling and sleeve studies are frozen research, not required artwork rebuilds. Comparisons whose eye-material baseline is now stale are disabled rather than silently regenerated.
The eye section offers an explicitly frozen pre-adoption gaze comparison. The original proposal retains its pending-at-creation receipt; the separate [user adoption decision](sources/canonical/gaze-surface-adoption-20261010.json) approves only this development basis, not full motion or installation.
The main waving comparison uses the frozen pre-middle version on the left and current wave on the right. The former high-peak and float-study comparisons are disabled for the changed wave rather than silently rebuilt or mislabelled as single-factor evidence.
The current review comparison uses an exact frozen pre-hand strip with the same accepted eye model. It does not compare the new eyes against the archived rigid-eye hand study. The existing GIMP project remains the static hand source, not a claim that the new animated eye flow has been edited in GIMP.
Three whole-scene research tests have been removed. Small filter arithmetic checks remain, but are not part of the daily visual loop.
The default CI uses fast current-asset/core-logic checks. Full archived regressions and installer audits require explicit manual `full_audit`; they do not block daily visual iteration.
A green engineering check is not aesthetic approval.

## Baseline and safety

The complete original usable baseline is tagged **baseline-phase2-complete-20261008**.
The earlier **baseline-phase2-20261008** tag contains metadata only; do not use it as an installable baseline.
`pet/` and `baseline/phase3/` are historical Phase 3 assets, including rejected defects—not the current recommendation.
Never install a single development strip or silently replace the locked mother.
Existing [GIMP projects](sources/editor) and archived generated inputs remain available for bounded editing and traceability.
