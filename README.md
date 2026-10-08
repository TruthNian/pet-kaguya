# Pet Kaguya

Local Kaguya sprite assets, reproducible animation tools, and an honest quality audit.

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
