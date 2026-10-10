"""Isolate terminal precision across the actual nine actions and 16 gazes.

Every baseline cel must reconstruct the current development atlas exactly.
No frame is reconstructed from a quantized native frame. No active file is
overwritten. Float64 is a numerical filter reference, not an aesthetic oracle.
"""
import hashlib
import json

import numpy as np
from PIL import Image, ImageDraw

from canonical import ROOT, ACCEPTED_SHA, load_canonical, clean_cutout, camera
import build_idle as idle
import build_failed as failed
import build_jumping as jumping
import hop_contact
import build_gaze as gaze
import locomotion_render as walking
import locomotion_follow as follow
from refine_leg_composition import inputs as leg_inputs
import build_locomotion
from material_support import ZERO
from protocol import DURATIONS
from terminal_sampling import METHOD, legacy, floating, filtered_float, reference64, composite_error

OUT = ROOT/'candidates/phase5/terminal-sampling-v1'
STATES = ['idle', 'run_right', 'run_left', 'waving', 'jumping', 'failed',
          'waiting', 'processing', 'review']


def digest(image):
    return hashlib.sha256(image.tobytes()).hexdigest().upper()


def metadata(state):
    return json.loads((ROOT/f'candidates/phase5/{state}/build.json').read_text(encoding='utf-8'))


def jobs():
    """Real original-source geometry, before its current terminal conversion."""
    mother = load_canonical()
    transform = camera(clean_cutout(mother)[0])
    regions, idle_motion = idle.specification()
    masks = idle.region_masks(regions)
    zero = dict(bodyY=0, earAngle=0, hairAngle=0)

    def ordinary(image, keys):
        source = clean_cutout(image)[0]
        return [lambda terminal, key=key: idle.render(source, key, transform, regions, masks,
                                                     terminal=terminal) for key in keys]

    result = {'idle': ordinary(mother, idle_motion['keyframes'])}
    image, _, _, _, _, motion = failed.inputs()
    result['failed'] = ordinary(image, motion['keyframes'])
    from build_waving import inputs as wave_inputs
    _,wave_motion,wave_sources,_ = wave_inputs()
    result['waving'] = [ordinary(wave_sources[kind], [zero])[0] for kind in wave_motion['sequence']]
    for state, pose_path in [('waiting', 'waiting-art-v2/pose.png'),
                             ('processing', 'processing/focused-pose.png'),
                             ('review', 'review/focused-pose.png')]:
        with Image.open(ROOT/f'candidates/phase5/{pose_path}') as saved:
            image = saved.convert('RGBA')
        motion = json.loads((ROOT/f'sources/canonical/{state}-motion.json').read_text(encoding='utf-8'))
        result[state] = ordinary(image, motion['keyframes'])

    _, _, _, _, _, _, poses = jumping.inputs()
    _, material = jumping.contact_inputs()
    result['jumping'] = [lambda terminal, key=key, material=material: hop_contact.render(
        material, key, transform, regions, masks, terminal=terminal) for key in poses]

    legs = leg_inputs()
    motion = json.loads((ROOT/'sources/canonical/locomotion-motion.json').read_text(encoding='utf-8'))
    build_locomotion.validate_motion(motion)
    response = follow.profile(motion)
    fields = follow.fields(regions, motion['followThrough'])
    eye_layers = gaze.layers(mother, gaze.load_generated(), gaze.specification())
    keys = [dict(key, followSourcePx={name: part['offsetsSourcePx'][i]
            for name, part in response.items()}) for i, key in enumerate(motion['keyframes'])]
    for state in motion['states']:
        direction = state['direction']
        focused = gaze.pose(mother, eye_layers, motion['focusOffsetSourcePx'][0]*direction, 0)
        material = walking.prepare(legs, focused, fields,local_support=ZERO)
        result[state['state']] = [lambda terminal, key=key, material=material, direction=direction:
            walking.render(material, key, direction, transform, terminal=terminal) for key in keys]
    gaze_spec = gaze.specification(corrected=True)
    eye_layers = gaze.layers(mother,gaze.load_generated(),gaze_spec)
    result['look'] = [ordinary(gaze.pose(mother, eye_layers, *gaze.offsets(i, gaze_spec)), [zero])[0]
                      for i in range(16)]
    return result, transform


def compare(name, index, job, baseline):
    record = {}
    def terminal(pixels):
        old = legacy(pixels)
        if digest(old) != baseline:
            raise ValueError(f'{name}/{index} does not reconstruct actual current cel')
        new = floating(pixels)
        oracle = reference64(pixels)
        raw_float = filtered_float(pixels)
        rounded = lambda evidence: {key: round(value, 9) for key, value in evidence.items()}
        record.update(index=index, legacyRGBAHash=digest(old), candidateRGBAHash=digest(new),
            changedPixels=int(np.any(np.asarray(old) != np.asarray(new), axis=2).sum()),
            legacyError=rounded(composite_error(old, oracle)), candidateError=rounded(composite_error(new, oracle)),
            float32FilterMaximumError=round(float(np.abs(raw_float-oracle).max()), 9),
            faceGeometryChanged=False, sourceArtworkRepainted=False)
        return new
    return job(terminal), record


def contacts(before, after, width):
    height = round(width*208/192)
    board = Image.new('RGB', (6*(width+12), 6*(height+28)), '#23252b')
    draw = ImageDraw.Draw(board)
    for bg_index, bg in enumerate(('#23252b', '#f1f0ee')):
        for i, name in enumerate(STATES):
            row, pair = divmod(i, 3)
            for variant, frame in enumerate((before[name][0], after[name][0])):
                x, y = (pair*2+variant)*(width+12), (row+3*bg_index)*(height+28)
                tile = Image.new('RGBA', frame.size, bg); tile.alpha_composite(frame)
                board.paste(tile.resize((width, height), Image.Resampling.NEAREST).convert('RGB'), (x+6, y+24))
                draw.text((x+3, y+3), f'{name}: {"old" if variant == 0 else "float"}', fill='white')
    return board


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    current = ROOT/'candidates/phase5/global/spritesheet.webp'
    original_bytes = current.read_bytes()
    with Image.open(current) as image:
        old_atlas = image.convert('RGBA')
    new_atlas = old_atlas.copy()
    jobs_by_state, transform = jobs()
    new_frames, old_frames, states = {}, {}, {}
    for name in STATES+['look']:
        spec = metadata(name)
        rows = [9, 10] if name == 'look' else [STATES.index(name)]
        frames, old, evidence = [], [], []
        for index, job in enumerate(jobs_by_state[name]):
            frame, record = compare(name, index, job, spec['frameHashes'][index])
            row = 9+index//8 if name == 'look' else rows[0]
            col = index%8
            previous = old_atlas.crop((col*192, row*208, (col+1)*192, (row+1)*208))
            if digest(previous) != record['legacyRGBAHash']:
                raise ValueError('Current global atlas and actual state cel disagree')
            pixels = np.asarray(frame)
            if pixels[0, :, 3].any() or pixels[-1, :, 3].any() or pixels[:, 0, 3].any() or pixels[:, -1, 3].any():
                raise ValueError('Precision study introduced a cell-edge mark')
            new_atlas.paste(frame, (col*192, row*208))
            frames.append(frame); old.append(previous); evidence.append(record)
        if name == 'idle':
            new_atlas.paste(frames[0], (6*192, 0))  # Actual legacy extra idle slot.
        new_frames[name], old_frames[name] = frames, old
        states[name] = dict(nativeRows=rows, camera=spec['camera'],
            durationsMs=spec.get('durationsMs'),
            legacyFrameHashes=spec['frameHashes'], candidateFrameHashes=[digest(f) for f in frames],
            cels=evidence)
        print(json.dumps(dict(state=name, cels=len(frames),
            meanLegacyError=float(np.mean([e['legacyError']['compositedMeanAbsoluteError'] for e in evidence])),
            meanCandidateError=float(np.mean([e['candidateError']['compositedMeanAbsoluteError'] for e in evidence])))), flush=True)
    new_atlas.save(OUT/'spritesheet.webp', lossless=True, exact=True, quality=100, method=6)
    with Image.open(OUT/'spritesheet.webp') as encoded:
        if encoded.convert('RGBA').tobytes() != new_atlas.tobytes():
            raise ValueError('Study encoder changed actual RGBA')
    for width in (80, 113, 192, 224):
        contacts(old_frames, new_frames, width).save(OUT/f'contact-{width}px.png')
    # Honest magnified native edge/face comparison, no contrast amplification.
    detail = Image.new('RGB', (960, 560), '#23252b'); draw = ImageDraw.Draw(detail)
    for row, bg in enumerate(('#23252b', '#f1f0ee')):
        for col, frame in enumerate((old_frames['idle'][0], new_frames['idle'][0])):
            tile = Image.new('RGBA', frame.size, bg); tile.alpha_composite(frame)
            detail.paste(tile.crop((25, 20, 145, 86)).resize((480, 264), Image.Resampling.NEAREST).convert('RGB'),
                        (col*480, row*280+16))
            draw.text((col*480+5, row*280), 'current' if col == 0 else 'float (not adopted)', fill='white')
    detail.save(OUT/'detail.png')
    records = [cel for state in states.values() for cel in state['cels']]
    report = dict(sourceSha256=ACCEPTED_SHA, method=METHOD, camera=transform,
        role='full-coverage-terminal-precision-study-not-an-active-pet',
        coverage=dict(actionStates=9, lookDirections=16, actualTimedActionCels=57, comparedCels=len(records)),
        atlasCanvas=[1536, 2288], decodedBytes=len(new_atlas.tobytes()),
        baselineAtlasRGBAHash=digest(old_atlas), candidateAtlasRGBAHash=digest(new_atlas),
        filter='same nonlinear-sRGB premultiplied Lanczos convention; not a linear-light change',
        oracle='independent NumPy float64 separable sinc(x)*sinc(x/3), same support, normalization and border crop',
        oracleIsAestheticProof=False, allLegacyCelsReconstructedExactly=True,
        measurementDecimalPlaces=9,
        measurementRoundingDoesNotRelaxPixelHashes=True,
        meanLegacyCompositedError=round(float(np.mean([e['legacyError']['compositedMeanAbsoluteError'] for e in records])), 9),
        meanCandidateCompositedError=round(float(np.mean([e['candidateError']['compositedMeanAbsoluteError'] for e in records])), 9),
        maximumFloat32FilterError=float(max(e['float32FilterMaximumError'] for e in records)),
        allCelsLowerMeanCompositedError=all(e['candidateError']['compositedMeanAbsoluteError'] <
            e['legacyError']['compositedMeanAbsoluteError'] for e in records),
        quantization='no uint8 straight/associated intermediate; float32 filter, float64 unassociation, final RGBA8 once',
        intermediateLanczosOvershootClamped=True, geometryAndSourcePixelsUnchanged=True,
        nativeTimingsChanged=False, hostResolutionChanged=False, hostFpsChanged=False,
        sourcePrecompositionRemoved=False, nativeUpscalingChanged=False, activeAtlasChanged=False,
        adopted=False, visualApproval='pending', installableFullAtlas=False, installed=False,
        states=states, limitations=[
            'Lower numerical filter error does not prove sharper, prettier or more legible artwork.',
            'Current source-space pose and iris/arm precompositions remain; this is not a whole-pipeline single sampling pass.',
            'Same 192x208 cells and discrete held schedules, same decoded texture memory; no new source detail, blink, FPS or host performance claim.',
            'Small-size state/gaze legibility, cuffs/hair seams, arbitrary interruptions and global naturalness remain unapproved.',
            'The float64 reference uses the same reconstruction kernel, not original continuous artwork or physical light truth.'])
    (OUT/'build.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8')
    if current.read_bytes() != original_bytes:
        raise ValueError('Study mutated active atlas')
    load_canonical()
    print(json.dumps({k: v for k, v in report.items() if k != 'states'}, indent=2))


if __name__ == '__main__':
    main()
