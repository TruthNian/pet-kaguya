"""Gradient-guided hidden RGB with visible-background-only constraints.

Foreground occluders are not observations of the hidden background. Across
their boundaries the color-offset field has a natural zero-normal condition,
not a copied garment color. This does not recover missing strand topology.
"""
import numpy as np


def solve(parent, material, domain, known_background, tolerance=1e-8, max_iterations=1600):
    parent,material = np.asarray(parent),np.asarray(material)
    domain,known = np.asarray(domain),np.asarray(known_background)
    if (parent.dtype!=np.uint8 or parent.shape!=material.shape or material.dtype!=np.uint8
            or parent.ndim!=3 or parent.shape[2]!=4 or min(parent.shape[:2])<3
            or domain.dtype!=np.bool_ or known.dtype!=np.bool_
            or domain.shape!=parent.shape[:2] or known.shape!=domain.shape
            or np.any(domain&known) or any(np.any(edge) for edge in
                (domain[0],domain[-1],domain[:,0],domain[:,-1]))
            or isinstance(tolerance,bool) or not np.isfinite(tolerance) or not 0<tolerance<1
            or isinstance(max_iterations,bool) or not isinstance(max_iterations,int) or max_iterations<1):
        raise ValueError('Hidden RGB solve requires disjoint interior unknowns and visible-background observations')
    if not domain.any(): return parent.copy(),dict(iterations=0,relativeResidual=0.,anchors=0,clippedChannels=0)
    y,x = np.nonzero(domain)
    lookup = np.full(domain.shape,-1,dtype=np.int32);lookup[y,x]=np.arange(len(y))
    ny,nx = np.stack([y-1,y+1,y,y]),np.stack([x,x,x-1,x+1])
    neighbors = lookup[ny,nx].T
    present = neighbors>=0
    observed = known[ny,nx].T
    diagonal = np.sum(present|observed,axis=1).astype(float)
    # Every connected unknown component must reach a real background anchor;
    # zero RHS alone cannot prove uniqueness of an unanchored Neumann system.
    seen = np.zeros(len(y),dtype=bool)
    anchored = np.any(observed,axis=1)
    for seed in range(len(y)):
        if seen[seed]: continue
        stack=[seed];seen[seed]=True;has_anchor=False
        while stack:
            i=stack.pop();has_anchor |= bool(anchored[i])
            for j in neighbors[i]:
                if j>=0 and not seen[j]: seen[j]=True;stack.append(int(j))
        if not has_anchor: raise ValueError('A hidden component has no visible-background anchor')
    delta = parent[...,:3].astype(float)-material[...,:3].astype(float)
    rhs = np.sum(delta[ny,nx].transpose(1,0,2)*observed[...,None],axis=1)
    safe = np.maximum(neighbors,0)

    def operator(values):
        return diagonal[:,None]*values-np.sum(values[safe]*present[...,None],axis=1)

    offset=np.zeros_like(rhs);residual=rhs.copy();direction=residual.copy()
    norm0=float(np.sum(rhs*rhs));norm=norm0;iterations=0
    while norm>norm0*tolerance*tolerance and iterations<max_iterations:
        applied=operator(direction);denominator=float(np.sum(direction*applied))
        if denominator<=0 or not np.isfinite(denominator): raise ValueError('Invalid anchored RGB operator')
        step=norm/denominator;offset+=step*direction;residual-=step*applied
        next_norm=float(np.sum(residual*residual))
        direction=residual+(next_norm/norm)*direction;norm=next_norm;iterations+=1
    actual=operator(offset)-rhs
    relative=np.sqrt(float(np.sum(actual*actual))/norm0) if norm0 else 0.
    if not np.isfinite(relative) or relative>1.1*tolerance: raise ValueError('Visible-background RGB solve did not converge')
    result=parent.copy()
    colors=material[y,x,:3].astype(float)+offset
    result[y,x,:3]=np.clip(np.rint(colors),0,255).astype(np.uint8)
    return result,dict(iterations=iterations,relativeResidual=float(relative),anchors=int(observed.sum()),
                       clippedChannels=int(((colors<0)|(colors>255)).sum()))
