"""Condition flattened RGBA against an estimated backing, not artist layers.

S = P + (1 - beta) B in premultiplied RGBA. beta is visibility/occlusion,
not necessarily P's alpha: flattened paint coverage is a separate quantity.
Moving P and beta together avoids both double-alpha and neutral shortcuts.
"""
import numpy as np


def condition(source, background, hint):
    s,b,h = np.asarray(source),np.asarray(background),np.asarray(hint)
    if (s.shape!=b.shape or s.ndim!=3 or s.shape[-1]!=4 or h.shape!=s.shape[:2]
            or not all(np.issubdtype(x.dtype,np.floating) for x in (s,b,h))
            or not all(np.isfinite(x).all() for x in (s,b,h))
            or np.any(h<0) or np.any(h>1)):
        raise ValueError('Use finite premultiplied RGBA and bounded occlusion hints')
    for rgba in (s,b):
        if (np.any(rgba<-1e-9) or np.any(rgba[...,3]>255+1e-9)
                or np.any(rgba[...,:3]>rgba[...,3:4]+1e-9)):
            raise ValueError('Material inputs must be valid premultiplied RGBA')
    active=h>0
    if not np.array_equal(s[~active],b[~active]):
        raise ValueError('Known background outside material must be exact source')
    minimum=np.zeros(h.shape,dtype=float)
    # P channels >= 0, and P alpha - each color >= 0.
    for observed,backing in ((s,b),(s[...,3:4]-s[...,:3],b[...,3:4]-b[...,:3])):
        needed=np.zeros_like(observed,dtype=float)
        np.divide(backing-observed,backing,out=needed,where=backing>0)
        minimum=np.maximum(minimum,np.max(needed,axis=-1))
    # P alpha <= beta*255, needed for a valid masked foreground and for
    # (1-beta)/(1-P_alpha) to be a bounded normal-over base compensation.
    bound=np.zeros(h.shape,dtype=float)
    np.divide(s[...,3]-b[...,3],255-b[...,3],out=bound,where=b[...,3]<255)
    minimum=np.maximum(minimum,bound)
    beta=np.where(active,np.maximum(h,np.clip(minimum,0,1)),0)
    p=s-(1-beta[...,None])*b
    p[~active]=0
    if (np.any(p<-1e-8) or np.any(p[...,3]>255*beta+1e-8)
            or np.any(p[...,:3]>p[...,3:4]+1e-8)):
        raise ValueError('Conditioned paint is not a valid premultiplied material')
    # Remove only roundoff at gamut endpoints, not quantize/clamp bad input.
    p=np.maximum(p,0)
    p[...,:3]=np.minimum(p[...,:3],p[...,3:4])
    return p,beta


def over(material, occlusion, background):
    return material+(1-occlusion[...,None])*background
