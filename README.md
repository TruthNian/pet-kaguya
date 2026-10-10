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
- Failed now holds canonical body height instead of dipping/rebounding every 1.22 seconds. Accepted mouth source and tiny ear/hair poses remain exact; rendered pixels/alpha can change with the projection. This is developer-selected, not full-motion acceptance; 80px expression remains weak.
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
| Host capabilities | Known v2 format requires a 1536×2288 atlas with 192×208 cells. Display uses percentage sizing, not a hard 192×208 pixel crop; import/avatar generation validates exact known dimensions, and CSS requests pixelated scaling. Larger-density native compatibility is unproven. Fixed holds and pointer priority remain unchanged. |
| Delivery and measurement | Complete aesthetic acceptance, native-host loading of the new atlas, final release and real CPU/GPU/FPS measurements are not established. |

The current atlas is 819,706 encoded bytes and decodes to 14,057,472 RGBA bytes.
Changed artwork is not a same-content compression result; file size does not prove FPS or texture-memory improvement.
See the [full scope/acceptance ledger](docs/REQUIREMENTS.zh-CN.md) and [chronological work record](docs/PHASE5-STATES.zh-CN.md).
The [read-only installed render facts](docs/HOST-RENDER-FACTS.json) distinguish accepted file geometry from display capability. Percentage rendering alone is not proof that a larger atlas will import, appear in settings, load correctly or improve real performance.
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
Failed compares frozen body oscillation against the current calm hold. Old mouth/precision comparisons are disabled for the changed body, rather than mislabelled as same-pose references.
The detailed player loads only the selected reference. An unconditional retired-eye gait reference previously blocked both current step actions; this page-loading regression is fixed without relaxing historical-source validation. Hop contact reference is loaded only when chosen, not alongside the default height comparison.
Three whole-scene research tests have been removed. Small filter arithmetic checks remain, but are not part of the daily visual loop.
The default CI uses fast current-asset/core-logic checks. Full archived regressions and installer audits require explicit manual `full_audit`; they do not block daily visual iteration.
Pushes that change only documentation, frozen downloads or their packaging tool do not rerun animation QA. Artwork, source, player, tests, dependencies and workflow changes still trigger the fast checks; pull requests retain verification.
A green engineering check is not aesthetic approval.

## Compact frozen packages

- [Current v3 development candidate, snapshot f5eb77f](deliverables/kaguya-candidate-f5eb77f.zip): 823,480 bytes. Exact current nine-state/sixteen-look atlas, including the calm failed body; local-v2 `pet.json`, manifest and acceptance limits. Waving middle/review hands/failed body are developer-selected, not human-approved.
- [Earlier v3 snapshot 0ac132c](deliverables/kaguya-candidate-0ac132c.zip): 1,007,149 bytes. Preserved unchanged for traceability; it precedes the calm failed-body change and is not the current download.
- [Original Phase 2 archive](deliverables/kaguya-baseline-phase2.zip): 2,016,380 bytes. Both runtime files are byte-exact to frozen Git commit 97ec2ab. This is not the current installed backup or the recommended new artwork.
- [Package hashes and frozen source commits](deliverables/index.json).

These are file-layout-checked archives, **not approved releases or verified native-host installations**. No install script is included. Do not overwrite the installed pet; a separate explicit decision and a backup of the actual installation are still required.
The index explicitly points to snapshot f5eb77f. Both earlier ZIPs remain byte-exact; no old archive is silently replaced. The package freezes resources, not the comparison viewer, and contains no installer.
The existing installer continues to refuse unapproved development installation. No GitHub Release or application change is performed.

Build these frozen snapshots with `python tools/build_native_packages.py`; read-only source/archive verification uses `python tools/build_native_packages.py --verify`. Neither command rebuilds artwork or writes installed files. The source commits must exist locally; a normal full Git clone has them. The packages do not follow future art changes silently.
The local package/source round-trip check passed for all three saved files. The index accepts only its known two-package predecessor or the exact current three-package form; unknown entries are not discarded. No complete regression, installer test or native-host activation was run for this packaging change.

## Baseline and safety

The complete original usable baseline is tagged **baseline-phase2-complete-20261008**.
The earlier **baseline-phase2-20261008** tag contains metadata only; do not use it as an installable baseline.
`pet/` and `baseline/phase3/` are historical Phase 3 assets, including rejected defects—not the current recommendation.
Never install a single development strip or silently replace the locked mother.
Existing [GIMP projects](sources/editor) and archived generated inputs remain available for bounded editing and traceability.
