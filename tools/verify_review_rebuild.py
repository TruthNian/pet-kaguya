"""Verify actual PNG pixels/JSON, not platform-specific PNG compression."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys

from PIL import Image
from canonical import load_canonical

ROOT = Path(__file__).resolve().parents[1]
FOLDERS = ['candidates/phase4/static', 'candidates/phase4/canonical-v3', 'candidates/phase5/idle',
           'candidates/phase5/waiting-art-v1', 'candidates/phase5/failed-art-v1', 'candidates/phase5/failed',
           'candidates/phase5/arm-backing-v1', 'candidates/phase5/jumping',
           'candidates/phase5/eye-backing-v1','candidates/phase5/look',
           'candidates/phase5/wave-art-v1','candidates/phase5/wave-art-v2',
           'candidates/phase5/wave-art-middle-v1','candidates/phase5/wave-art-middle-v2',
           'candidates/phase5/waving','candidates/phase5/processing-art-v1',
           'candidates/phase5/processing','candidates/phase5/waiting',
           'candidates/phase5/review-art-v1','candidates/phase5/review-art-v2','candidates/phase5/review',
           'candidates/phase5/leg-backing-v1','candidates/phase5/locomotion-inspection',
           'candidates/phase5/run_right','candidates/phase5/run_left','candidates/phase5/global']


def snapshot():
    logical, encoded = {}, {}
    for folder in FOLDERS:
        for path in sorted((ROOT/folder).iterdir()):
            key = path.relative_to(ROOT).as_posix()
            if path.suffix in ('.png', '.webp', '.gif'):
                with Image.open(path) as image:
                    frames = []
                    loop = image.info.get('loop')
                    for i in range(getattr(image, 'n_frames', 1)):
                        image.seek(i)
                        rgba = image.convert('RGBA')
                        frames.append((rgba.size, hashlib.sha256(rgba.tobytes()).hexdigest(), image.info.get('duration')))
                    logical[key] = (frames, loop)
                encoded[key] = hashlib.sha256(path.read_bytes()).hexdigest()
            elif path.suffix == '.json':
                logical[key] = json.loads(path.read_text(encoding='utf-8'))
    return logical, encoded


def main():
    before, encoded_before = snapshot()
    for script in ['identity.py', 'review_jaw.py', 'review_waiting.py', 'review_failed.py', 'review_arm_backing.py',
                   'build_idle.py', 'build_failed.py', 'build_jumping.py','build_gaze.py',
                   'guide_wave.py','review_wave.py','guide_wave_middle.py','build_waving.py',
                   'guide_processing.py','review_processing.py','build_processing.py','build_waiting.py',
                   'guide_review.py','review_review.py','review_review_v2.py','build_review.py',
                   'guide_legs.py','leg_material.py','review_locomotion.py','build_locomotion.py','build_global_review.py']:
        subprocess.run([sys.executable, str(ROOT/'tools'/script)], cwd=ROOT, check=True, capture_output=True)
    after, encoded_after = snapshot()
    load_canonical()  # Re-check the immutable selected source after all builds.
    changed = [key for key in before.keys() | after.keys() if before.get(key) != after.get(key)]
    if changed:
        for key in sorted(changed):
            if key.endswith('.json') and key in before and key in after:
                # Preserve exact comparison, but identify the divergent field
                # before fixing it. Do not mask raster or numeric differences.
                a,b = before[key],after[key]
                fields = {field:dict(saved=a.get(field),rebuilt=b.get(field))
                          for field in a.keys() | b.keys() if a.get(field)!=b.get(field)}
                print(json.dumps(dict(artifact=key,changedFields=fields),indent=2))
        raise SystemExit('Rebuilt content changed: '+', '.join(sorted(changed)))
    byte_changes = [key for key in encoded_before if encoded_before[key] != encoded_after[key]]
    print(json.dumps(dict(checkedLogicalArtifacts=len(before), decodedPixelsAndMetadataMatch=True,
                         encodedImageCompressionDifferences=len(byte_changes)), indent=2))


if __name__ == '__main__':
    main()
