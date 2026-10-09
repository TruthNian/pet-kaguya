# Review cloth study / GIMP 3.2.6

This is an independent **unadopted** cloth-surface candidate, based on the
current review composition v4 and previously archived face-free artwork.
The canonical v3 mother, current animation atlas, hands and installation are
unchanged. The actual XCF was saved, reopened, and exported with GIMP.

Four layers: locked v4 base, masked cloth artwork, hidden locked canonical
reference, hidden protected-foreground guide. Both visible layers have
masks. Normal-over uses a compensated base mask to avoid counting source
alpha twice. Editing the cloth mask requires recalculating that compensation.
The masks are not recovered original artist layers or a complete arm rig.

`gimp-export.png` and `gimp-reopened-export.png` are pixel-identical. Visible
RGBA exactly matches `candidates/phase5/review-sleeves-v1/pose.png`; 859
fully transparent hidden-RGB pixels are normalized to zero by GIMP.
CI checks the archived XCF hash and saved exports; it does not run GIMP.

Recreate the cloth inputs using `python tools/review_sleeves.py`. To create
a **fresh** GIMP project, use GIMP's `python-fu-eval` batch interpreter to run
`tools/gimp_sleeve_project.py`. Its default output is the ignored
`work/gimp-review-sleeves-v1`; an existing XCF there is deliberately not
overwritten. Supply a fresh `PROJECT_OUTPUT` through `runpy.run_path`'s
`init_globals` when needed. Native desktop painting is not claimed.

The first pointwise-green-mask attempt is retained as
`failed-pixel-selection.png` because its missed dark creases caused speckles.
The continuous-mask candidate remains pending visual review: preserved cuff
and outline geometry may still conflict with new folds. Smooth shading alone
does not establish cloth volume, correct anatomy or motion quality.
