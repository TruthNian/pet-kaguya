"""Versioned local texture support; no source paint or geometry changes."""
import hashlib
import json

import numpy as np
from PIL import Image

from build_idle import sample
from canonical import ROOT

LEGACY='clipped-local-v1'
ZERO='zero-extended-local-v2'
REFERENCE=ROOT/'sources/reference/material-support-v1'


def sample_local(array,x,y,support):
    if support==LEGACY:
        return sample(array,x,y)
    if support!=ZERO:
        raise ValueError('Unknown local texture support version')
    if array.ndim not in (2,3) or not all(array.shape[:2]):
        raise ValueError('Local texture must have nonempty 2-D support')
    # Extend the discrete texture by zero, not the continuous sample result.
    # Keep the same bilinear arithmetic as the legacy sampler in the interior.
    height,width=array.shape[:2]
    x,y=np.asarray(x,dtype=float),np.asarray(y,dtype=float)
    if not np.isfinite(x).all() or not np.isfinite(y).all():
        raise ValueError('Local texture coordinates must be finite')
    cx,cy=np.clip(x,-1,width),np.clip(y,-1,height)
    ix,iy=np.floor(cx).astype(int),np.floor(cy).astype(int)
    nx,ny=ix+1,iy+1
    fx,fy=cx-ix,cy-iy
    def corner(xx,yy):
        inside=(xx>=0)&(yy>=0)&(xx<width)&(yy<height)
        values=array[np.clip(yy,0,height-1),np.clip(xx,0,width-1)]
        return values*(inside[...,None] if array.ndim==3 else inside)
    if array.ndim==3:
        fx,fy=fx[...,None],fy[...,None]
    return ((corner(ix,iy)*(1-fx)+corner(nx,iy)*fx)*(1-fy)
            +(corner(ix,ny)*(1-fx)+corner(nx,ny)*fx)*fy)


def repair_receipt(state,frames):
    manifest=json.loads((REFERENCE/'manifest.json').read_text(encoding='utf-8'))
    if state not in ('jumping','run_left','run_right'):
        raise ValueError('No frozen support input for this state')
    for suffix in ('json','webp'):
        name=f'{state}.{suffix}'
        if hashlib.sha256((REFERENCE/name).read_bytes()).hexdigest().upper()!=manifest['files'][name]:
            raise ValueError('Frozen local-support input changed')
    baseline=json.loads((REFERENCE/f'{state}.json').read_text(encoding='utf-8'))
    if len(frames)!=len(baseline['frameHashes']):
        raise ValueError('Local support repair cannot change cel count')
    with Image.open(REFERENCE/f'{state}.webp') as strip:
        if strip.size!=(1536,208) or strip.crop((len(frames)*192,0,1536,208)).getbbox():
            raise ValueError('Frozen support strip shape or blank columns changed')
        old=[strip.crop((i*192,0,(i+1)*192,208)).convert('RGBA') for i in range(len(frames))]
    hashes=lambda images:[hashlib.sha256(f.tobytes()).hexdigest().upper() for f in images]
    if hashes(old)!=baseline['frameHashes']:
        raise ValueError('Frozen support-v1 cels disagree with their contract')
    changes=[]
    for before,after in zip(old,frames):
        diff=np.abs(np.asarray(after,dtype=int)-np.asarray(before,dtype=int))
        yy,xx=np.where(np.any(diff,axis=2))
        if diff[...,3].any() or diff[:140].any() or diff[164:].any() or diff.max()>1:
            raise ValueError('Local support repair changed alpha, protected art or exceeded one channel unit')
        changes.append(dict(changedPixels=int(len(yy)),maximumChannelDifference=int(diff.max()),
            bounds=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)] if len(yy) else None))
    return dict(baselineCommit='7f58246889fbbcfef788606067a95cf9251e1a87',
        reference=f'sources/reference/material-support-v1/{state}.webp',
        baselineFrameHashes=hashes(old),currentFrameHashes=hashes(frames),changes=changes,
        scope='local-bilinear-support-only',sourceArtworkChanged=False,geometryChanged=False,
        timingChanged=False,nativeAlphaPreservedExactly=True,fullMotionApproved=False)
