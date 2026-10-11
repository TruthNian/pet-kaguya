# Pet Kaguya

Local Kaguya artwork, native-compatible development sprites, and reproducible tools.

## Current version

The selected full AI mother is **canonical-v3**. Its face, identity and costume are locked; rejected Phase 3/4 composites and procedural jaw edits are not production sources.

On **2026-10-11**, the user accepted the current whole-review presentation: nine actions and sixteen gaze directions. The exact [visual receipt](sources/canonical/whole-review-acceptance-20261011.json) supersedes earlier pending visual status for this snapshot, not future artwork.

- [Current reviewed delivery](deliverables/kaguya-v3-reviewed-20261011.zip), 824,361 bytes; [current delivery index](deliverables/current.json).
- Local atlas installed after byte-verified backup; existing `pet.json` preserved exactly.
- The original local Kaguya had already migrated to a cloud pet. Updating local files alone did not update that cloud image. With separate authorization, the **original stable cloud ID** was updated and activated; the other same-name Kaguya was untouched.
- Downloaded stored cloud pixels match the reviewed atlas exactly. The user confirmed **“已显示新版，加载正常”** in the installed application.
- [Deployment evidence and limits](docs/DEPLOYMENT-20261011.json) separate local writing, cloud storage, active selection and user-observed loading. No application binaries or host rules were modified.
- Cloth lag and float sampling remain unadopted trials. No new artwork or image re-encoding was used for delivery.

Build metadata and older immutable ZIP manifests retain their **construction-time** pending/uninstalled status. Current acceptance and deployment belong to the separate hash-bound receipts; do not rewrite history or infer that every host transition or performance target is solved.

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
| Visual scope | The current whole presentation is accepted. This does not prove author-original anatomy/layers, every display size or every arbitrary interruption. No further speculative redraw is required. |
| Natural motion | Discrete holds, arbitrary state cuts, airborne interruptions and held-hand entry/exit remain within the agreed existing-host boundary. |
| Small-size expression | Several gestures and nearby gaze directions are weak at 80px. |
| Eye materials | Original-eye texture flow is accepted in the current whole presentation; subtle nearby directions and slight iris deformation remain documented tradeoffs. |
| Host capabilities | Known v2 format requires a 1536×2288 atlas with 192×208 cells. Display uses percentage sizing, not a hard 192×208 pixel crop; import/avatar generation validates exact known dimensions, and CSS requests pixelated scaling. Larger-density native compatibility is unproven. Fixed holds and pointer priority remain unchanged. |
| Measurement | Real app loading is user-confirmed, not an instrumented long-run CPU/GPU/FPS benchmark. No measured frame-rate or resolution improvement is claimed. |

The current atlas is 819,706 encoded bytes and decodes to 14,057,472 RGBA bytes.
Changed artwork is not a same-content compression result; file size does not prove FPS or texture-memory improvement.
The actual stored cloud download is a **5,011,836-byte PNG**, not the 819,706-byte upload WebP. It is 103,010 bytes (about 2.10%) larger than the backed-up old cloud PNG; those images have different pixels, so this is not a same-content encoder comparison or a measured loading regression.
The unchanged native schedule has six idle holds per 6.6 seconds and eight step holds per 1.06 seconds: roughly 0.91 and 7.55 scheduled content updates/second. These are **not measured display FPS**. Compressing or upscaling the atlas cannot by itself change hold timing, add interpolation or repair arbitrary state cuts.
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
A green engineering check is not aesthetic approval. This snapshot's aesthetic approval comes from the separate explicit user receipt.

## Reviewed delivery and historical frozen packages

- [Current visually accepted v3](deliverables/kaguya-v3-reviewed-20261011.zip): 824,361 bytes. Same exact atlas as f5eb77f, plus a normal Kaguya config, visual receipt and scope manifest. Its immutable manifest records loading as unverified **at packaging time**; the later [deployment receipt](docs/DEPLOYMENT-20261011.json) records successful cloud pixel readback, activation and user-confirmed application loading.

- [Earlier development snapshot f5eb77f](deliverables/kaguya-candidate-f5eb77f.zip): 823,480 bytes. Preserved unchanged; its pending acceptance description was accurate when created, before the 2026-10-11 whole-review decision.
- [Earlier v3 snapshot 0ac132c](deliverables/kaguya-candidate-0ac132c.zip): 1,007,149 bytes. Preserved unchanged for traceability; it precedes the calm failed-body change and is not the current download.
- [Original Phase 2 archive](deliverables/kaguya-baseline-phase2.zip): 2,016,380 bytes. Both runtime files are byte-exact to frozen Git commit 97ec2ab. This is not the current installed backup or the recommended new artwork.
- [Package hashes and frozen source commits](deliverables/index.json).

Historical archives retain their original approval boundaries. No ZIP contains an installer. The historical index remains unchanged; `deliverables/current.json` points to the reviewed delivery and its later deployment evidence. No old ZIP was overwritten.

The new [reviewed installer](tools/install_reviewed.ps1) requires the exact visual/installation receipt, source hash, existing target hashes and a verified backup; it preserves the existing config and atomically replaces only the atlas. The legacy installer is only for explicit historical recovery/regression. Cloud migration means local writing alone is insufficient for migrated pets; the actual cloud update used the official Pets connector and preserved the original ID. No GitHub Release or application patch was performed.

Build the reviewed archive with `python tools/deliver_reviewed.py`; use `--verify` for read-only checks. This does not rebuild artwork or perform installation. Current package: SHA-256 `B6669342853F3F93CBF10D740219C16CE1C17E454598C649EDAE88A20DDD2708`.

Build these frozen snapshots with `python tools/build_native_packages.py`; read-only source/archive verification uses `python tools/build_native_packages.py --verify`. Neither command rebuilds artwork or writes installed files. The source commits must exist locally; a normal full Git clone has them. The packages do not follow future art changes silently.
The local package/source round-trip check passed for all three saved files. The index accepts only its known two-package predecessor or the exact current three-package form; unknown entries are not discarded. No complete regression, installer test or native-host activation was run for this packaging change.

## Baseline and safety

The complete original usable baseline is tagged **baseline-phase2-complete-20261008**.
The earlier **baseline-phase2-20261008** tag contains metadata only; do not use it as an installable baseline.
`pet/` and `baseline/phase3/` are historical Phase 3 assets, including rejected defects—not the current recommendation.
Never install a single development strip or silently replace the locked mother.
Existing [GIMP projects](sources/editor) and archived generated inputs remain available for bounded editing and traceability.
