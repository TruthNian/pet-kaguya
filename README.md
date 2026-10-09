# Pet Kaguya

Local Kaguya sprite assets, reproducible animation tools, and an honest quality audit.

## Current work: locked mother pose and bounded action candidates

Current aggregate encoding uses offline lossless/exact method 6, quality 100: locally 1,017,692 bytes versus 1,098,260 at commit `5ca991b`, with **every decoded RGBA byte unchanged**, including hidden RGB. The 1536×2288 texture still decodes to 14,057,472 bytes; this is not a resolution, memory or FPS improvement. Single-run encoding was slower, so action/gaze strips retain their prior settings. [Frozen measurements and limits](qa/lossless-encoding-20261010.json); every actual aggregate encode is decoded and checked before saving.

The new [face-free hand edit](candidates/phase5/review-hands-pair-v1/detail.png) is **not adopted**: it redraws lines/shading without establishing better hand anatomy. I incorrectly called the partly occluded original waist crescent an extra cuff, despite that source fact already being recorded. That diagnosis and instruction are withdrawn; the [actual prompt](candidates/phase5/review-hands-pair-v1/prompt.txt) and [failed-study record](candidates/phase5/review-hands-pair-v1/build.json) are preserved. Current waiting v2/review v6 artwork and all motion cells remain unchanged this round; hand volume, cuffs and pose contact still need improvement. No installation or new host.

Current waiting uses composition **v2**: a [complete raised sleeve](candidates/phase5/waiting-sleeve-v1/detail.png) over the unchanged original held hand and face. A face-free fixed-square built-in image edit was cropped through inspected garment/cape/hand boundaries, not adopted as a full redraw. 53,583 source RGBA pixels change, including 12,314 alpha values; this is a whole garment plus limited contour-side backing, **not** a cloth-only RGB edit or clean recovered layer. The first cape mask accidentally retained 139 pink motif pixels, producing a stitched flower; the [exact failed composite](candidates/phase5/waiting-sleeve-v1/failed-cape-overlap.png) is retained. Corrected boundaries, actual six cels, unchanged 1010 ms × 3 held schedule, and the global atlas are synchronized. Only the waiting row changes from commit `3b1820d`; the other ten rows, mother and installed assets stay exact. Hard shadows, boundary integration, hand volume, small-size readability and complete motion remain unapproved. [Actual prompt](candidates/phase5/waiting-sleeve-v1/prompt.txt) and [raw/edit diagnostics](candidates/phase5/waiting-sleeve-v1/build.json) are archived.

The [current waiting GIMP project](sources/editor/waiting-sleeve/kaguya-waiting-sleeve.xcf) was genuinely saved/reopened/exported in GIMP 3.2.6. Visible RGBA matches exactly; 859 fully transparent hidden RGB values normalize to zero. Four real layers include editable garment/compensation masks, not an invented rig. [Editing constraints](sources/editor/waiting-sleeve/README.md) explain why mask edits require rebuilding base compensation. No installed-host or independent-host expansion is included.

Current jumping replaces the old grounded height field with **original-material two-link knees**. Anticipation/landing still descend only 0.8/0.25 native pixels; both shoe targets remain planted, while the body/dress translate rigidly. The three air cels are RGBA-identical to the prior renderer, with the same five native holds, 8 px apex and three-cycle fallback. No face redraw, new artwork, host change or inherited gait approval. The top viewer automatically synchronizes the [regenerated old-height-field comparison](candidates/phase5/jumping/contact-proof.json) at the same slot; [contact detail](candidates/phase5/jumping/contact-detail.png) and [113 px comparison](candidates/phase5/jumping/contact-comparison-113px.png) show the actual change. Estimated mattes/backing, moving edge colors, rigid clothing and held landing recovery remain limitations; naturalness is pending.

The preceding isolated [hair-boundary study](candidates/phase5/review-hair-boundary-v1/detail.png) retains the recorded v4 hands/sleeves/face/alpha and known mother pixels exactly while removing unobserved boundary constraints. Two unanchored pixel islands remain unchanged. **Not adopted:** numerical observation isolation does not repair clipping, flecks or missing strand topology. It does not replace an active row/global atlas/installed pet. The viewer separately shows [actual current idle/waiting/review cels](candidates/phase5/review-hair-boundary-v1/current-held-structure-224px.png); this contact is not the rejected hair candidate.

Current review uses composition **v6**, with [continuous sleeve interiors](candidates/phase5/review-sleeves-v2/detail.png) over the exact v5 hands/alpha/outer lines. Built-in image generation edited a face-free, fixed square crop; its 322,704 redrawn non-cloth pixels are rejected. Only 26,025 source RGB pixels in two connected cloth interiors change. Curved principal folds replace stiff shadow wedges; this is an observed visual improvement at 224 px, not a clean semantic matte, physical cloth model or full aesthetic approval. The v4 fingertip repair and v5 [12 observed hair-pixel restoration](candidates/phase5/review-art-v5/detail.png) remain exact. The six review cels and development atlas are synchronized; every other atlas row is unchanged, native resolution/timing/memory and installed assets remain unchanged. Earlier **v1** sleeve, compact-hand and RGB-boundary studies are still **not adopted**. [Corrections and remaining constraints](docs/PHASE5-STATES.zh-CN.md).

The current [GIMP sleeve project](sources/editor/review-sleeves-v2/kaguya-review-sleeves.xcf) was saved, really reopened and exported through GIMP 3.2.6's official batch API. Visible RGBA is exact; 859 fully transparent hidden RGB values normalize to zero. The locked v5 base and editable cloth masks use float base-mask compensation. This is not desktop brush painting or clean layer recovery; changing a mask requires rebuilding that compensation. CI checks the archived project/export evidence, not live GIMP execution.

GIMP 3.2.6 was actually used through its official batch API to create, save, reopen and export an [editable XCF project](sources/editor/review-hand/kaguya-review-hand.xcf). Its visible RGBA matches the controlled contour repair exactly; 859 fully transparent hidden RGB values are normalized, not a full-byte identity claim. The first normal-over alpha-stacking error was rejected. Editable masks need float base-mask compensation to avoid repeating that error. This is not desktop brush painting or a clean character rig; CI checks the archive hash and saved export evidence, not a live GIMP replay. Cross-platform animation rebuilds do not require GIMP. Hidden strand topology, sleeve/hand aesthetics and state transitions remain unresolved.

Phase 5 has **nine motion candidates and sixteen eye-only gaze cells**, sharing the locked v3 mother and camera. `candidates/phase5/global/` combines their exact decoded rows into a complete-coverage development atlas, **not an approved or installable release**. No `pet.json` or installer target is created. The user accepted frontal small steps, the restrained lateral amplitude and the cadence as a further-development basis, not finished motion quality. Current gait includes a bounded support-side root shift, pinned source shoes, rising/approach/contact poses and subtle root-driven ear/hair-tip lag. Current source-material neutral reconstruction is exact; the earlier non-lossless failure remains reproducible. Estimated layer edges, weak 80 px cues, clothing follow-through and arbitrary transitions remain unresolved. These rows are drag feedback, not autonomous locomotion: pointer displacement is independent of the sprite schedule, and release can interrupt any cel and restore the underlying state, not necessarily idle. No screen-world no-slip, live lag initialization, velocity synchronization, recovered physical mass, side-face redraw or artwork mirroring is claimed.

All action aesthetics remain pending. The user temporarily accepted held waiting/review timing and continued structural improvement, not the rendered hands or sleeves; no independent host expansion is authorized. Their entry/idle fallback lacks arm transitions; review's palm volumes and new fold-to-boundary integration still need review. The original sleeve/hand footprint was incompletely retired in v1 and corrected in v2; v3 further recovers known source hair without changing the held gesture. Earlier defects remain reproducible as evidence. Enlarged hair/plate seams remain unapproved; no hand redesign or clean-layer recovery is claimed. Additional whole-character redraws for gestures are not adopted; the explicitly selected complete AI mother v3 is retained. Backing plates are technical materials, never finished poses. This is not a complete arm/3-D rig or continuous native interpolation. Gaze's exact neutral reconstruction does not prove a perfect matte. [Current progress, failures and limits (中文)](docs/PHASE5-STATES.zh-CN.md), [idle/source work](docs/PHASE5.zh-CN.md).

The user selected **the earlier gently tapered AI-generated mother pose, v3**. The immutable source is `sources/canonical/artwork.png` with decision/hash in `sources/canonical/manifest.json`. Its face shape is locked; no fallback to rejected composites or procedural facial-geometry repairs. The viewer defaults to this source's idle and offers all nine current candidates and a global comparison. Motion acceptance is pending; the installed atlas remains untouched.

`candidates/phase4/static/` preserves a **rejected static prototype**, not an installable animation or approved foundation. The user agreed on the intended original front-idle proportions, restrained closed smile, mild failed expression, and chin-touching waiting gesture, but subsequently reported that many rendered images looked very bad. Direction agreement is not result approval.

The prototype mechanically shares a head/ears/ornament plate and restores foreground hands. This passes bounded pixel checks, **not** whole-character, head/neck, costume, seam, or aesthetic acceptance. It is not to be animated or promoted. A coherent complete-character source/layer model is still needed; copying a common head onto independent bodies is insufficient.

`baseline/phase3/` preserves the previous candidate, including its confirmed failed/waiting defects. **`pet/` is still that old Phase 3 candidate; do not mistake it for the Phase 4 repair.** The installed pet has not been replaced during this stage.

- [Full scope and outstanding acceptance gates (中文)](docs/REQUIREMENTS.zh-CN.md)
- [Static structure review and rejected experiments (中文)](docs/STATIC-REVIEW.zh-CN.md)

`candidates/phase4/canonical-v2/`, `canonical-v3/`, and `canonical-v4/` preserve generated mother-pose iterations and prompts, not animation atlases. These edits changed non-jaw pixels: they are not exact local edits or lossless upscales. The user subsequently chose v3 as the complete mother pose. `canonical-local-jaw/` is a rejected procedural experiment: its local fields kinked hair. It must not be used in production. `tools/review_jaw.py` preserves strict-edit diagnostics using a shared transform, not independent face fitting.

## Previous gentle-motion candidate (not visually accepted)

`pet/` contains the compatible old candidate. All nine animated states and sixteen look directions were rebuilt from per-row poses, but this did NOT establish cross-state identity or correct face compositing. No host patch or claimed native FPS/resolution upgrade.

The complete usable baseline is tagged **`baseline-phase2-complete-20261008`**. The earlier tag `baseline-phase2-20261008` contains only metadata due to an initial copy-path error; it is not an installable baseline.

- [First principles and five-step plan (中文)](docs/PLAN.zh-CN.md)
- [Real problems, fixes, remaining limitations (中文)](docs/ISSUES.zh-CN.md)
- [Validation and uncertainty (中文)](docs/VALIDATION.zh-CN.md)
- [Reproducible before/after metrics](qa/comparison.json)

![113 px nearest-neighbour simulation, old above / candidate below](qa/comparison-113px.png)

### Build / test / preview

Requires Python 3.12 and Node 22+:

```sh
python -m pip install -r requirements.txt
# Historical Phase 3 regression only; never promote it as the selected source:
python tools/build.py --historical-phase3 --out work/historical-rebuild
python tools/identity.py
python tools/review_jaw.py
python tools/build_idle.py
python tools/review_waiting.py
python tools/review_failed.py
python tools/build_failed.py
python tools/review_arm_backing.py
python tools/build_jumping.py
python tools/build_gaze.py
python tools/guide_wave.py
python tools/review_wave.py
python tools/guide_wave_middle.py
python tools/build_waving.py
python tools/guide_processing.py
python tools/review_processing.py
python tools/build_processing.py
python tools/build_waiting.py
python tools/guide_review.py
python tools/review_review.py
python tools/review_review_v2.py
python tools/review_review_v3.py
python tools/repair_review_hand_outline.py
python tools/review_review_v4.py
python tools/review_review_v5.py
python tools/build_review.py
python tools/review_hair_boundary.py
python tools/guide_legs.py
python tools/leg_material.py
python tools/review_locomotion.py
python tools/build_locomotion.py
python tools/build_global_review.py
python tools/verify_review_rebuild.py
python -m unittest discover -s tests -v
node --test tests/clock.test.mjs tests/review.test.mjs tests/idle-clock.test.mjs tests/candidate-clock.test.mjs tests/gaze-frame.test.mjs tests/cel-painter.test.mjs tests/comparison-reference.test.mjs
python -m http.server 8767 --bind 127.0.0.1
```

Open `http://127.0.0.1:8767/viewer/`. The top section offers all nine candidates at actual native holds, including left/right 1.06 s cycles. For both gait rows, the left side defaults to a frozen pre-follow-through reference from `d804cd5`; both sides share the **same clock, state and cel index**, including pause/manual/reduced motion and three-cycle idle fallback. Core source/camera/root/foot/focus/timing contracts must match before comparison. The original sixteen decoded reference cels match the historical cadence receipt; they are frozen source inputs, not regenerated assets, future candidate pixel locks or inherited full visual approval. A static idle reference remains available for identity inspection only. Its clock simulates uninterrupted row playback, not arbitrary live host drag release. Selected rows decode on demand; consecutive identical cels update time-slot status without redundant canvas paint. The global comparison shows representative poses at 113 px on dark/light backgrounds. The separate gaze section offers sixteen directions and an optional pointer preview. All gesture connections, sleeve folds, weak small-scale cues, transitions and motion aesthetics remain under review. Native interpolation, resolution, FPS and priority are unchanged.

### Windows install / rollback

**Normal installation is disabled:** complete development cell coverage is not an approved v3 release. `install.ps1` refuses to substitute the old Phase 3 atlas, a partial strip or the unapproved global QA artifact. The historical builder likewise requires explicit opt-in and can write only under repository `work/`. `tools/test_install.ps1` tests historical backup/recovery only in an isolated fixture, never the installed pet.

Explicit baseline recovery remains available if the user deliberately needs the archived baseline; it is not the new animation candidate:

```powershell
# Restore baseline only after checking the currently installed atlas hash:
./tools/install.ps1 -Baseline -ExpectedCurrentHash '<current atlas SHA-256>'
```

The installer backs up the two local pet files, rejects unexpected current hashes, and does not change app settings or binaries. Reselect/reload the local pet manually if the host caches it. A file install does not confirm that the live overlay is displaying it.

## Baseline

`baseline/phase2/` is the exact usable local version archived on 2026-10-08, **not** a claim that its animation is finished.

- Atlas: 1536 × 2288, RGBA, lossless WebP; 8 columns × 11 rows; cells 192 × 208.
- SHA-256: `71F7E36AD459D99C9DE1AC6033A968CDF4C125EB742FFD5FF19B8E81BBA56EF7`.
- File size: 2,013,616 bytes. Decoded RGBA texture: 14,057,472 bytes (13.41 MiB), unchanged by compression.
- `pet.json` and `spritesheet.webp` are archived without modification.

## Direction

Keep the existing golden hair, rabbit ears, moon ornament, coral dress, turquoise beads, and rabbit shoes. Gentle, restrained motion: breathing and slight ear/hair movement, no feature bloat.

The current host controls frame durations, nearest-neighbour scaling, state fallback, and pointer-look priority. An atlas cannot override those behaviours. We will not modify the installed application. A separate development viewer must not be presented as proof of native-host performance.

## Known problems / previous overclaims

- Idle: a 6.6 s native slow-idle cycle contains a 0.84 s fully closed-eye frame and a 2.34 s half/closed/half interval; this is not a natural short blink.
- Idle, waiting, and processing bodies are essentially frozen. Reduced differences came partly from freezing, not improved motion.
- Failed: only three distinct poses occupy eight cells. Repeated seated frames reduced average difference without repairing the standing-to-sitting jump.
- Other action rows retain independent-redraw inconsistency; pixel-change percentages alone are not perceptual quality scores.
- Processing has a small chest pulse and half-closed eyes that can read as sleepy; state legibility needs actual-size visual review.
- Pointer-look directions rotate the whole body in coarse steps. Visible-area differences alone are **not** proof of a defect: projection legitimately changes area.
- Compression does not increase frame rate, image resolution, or reduce decoded texture size. `requestAnimationFrame` does not invent missing poses.
- The native overlay's default action playback repeats three times then returns to idle; pointer-look can override some state animations. These remain host constraints.

## Provenance / rights

This is a user-requested archive and improvement of an existing local character asset. No third-party application bundles, credentials, private application state, or machine-specific paths are included. No licence grant is inferred for the character artwork; redistribution rights must be established separately. Tooling and artwork provenance will be documented as work proceeds.
