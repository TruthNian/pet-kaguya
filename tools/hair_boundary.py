"""Dirichlet RGB correction; no image blur, new alpha or exterior edits.

The missing interior gets its strand gradients from a generated material,
but its color boundary is inherited from the existing pose. A harmonic
offset reconciles those two constraints. This cannot repair strand topology.
Only NumPy is needed; the solve is over the explicitly allowed pixels.
"""
import numpy as np


def harmonic_rgb(parent, material, permission, tolerance=1e-8, max_iterations=1600):
    parent, material = np.asarray(parent), np.asarray(material)
    domain = np.asarray(permission)
    if (isinstance(tolerance,bool) or not np.isfinite(tolerance) or not 0 < tolerance < 1
            or isinstance(max_iterations,bool) or not isinstance(max_iterations,int) or max_iterations < 1
            or parent.dtype != np.uint8 or material.dtype != np.uint8
            or parent.shape != material.shape or parent.ndim != 3 or parent.shape[2] != 4
            or min(parent.shape[:2]) < 3
            or domain.shape != parent.shape[:2] or domain.dtype != np.bool_
            or np.any(domain[0]) or np.any(domain[-1]) or np.any(domain[:,0]) or np.any(domain[:,-1])):
        raise ValueError('RGB boundary solve needs an interior boolean domain and matching uint8 RGBA')
    if not np.any(domain):
        return parent.copy(), dict(iterations=0, relativeResidual=0.0)
    y,x = np.nonzero(domain)
    indices = np.full(domain.shape,-1,dtype=np.int32)
    indices[y,x] = np.arange(len(y))
    neighbors = np.stack([indices[y-1,x],indices[y+1,x],indices[y,x-1],indices[y,x+1]],axis=1)
    present = neighbors >= 0
    safe = np.maximum(neighbors,0)
    boundary_delta = parent[...,:3].astype(np.float64)-material[...,:3].astype(np.float64)
    deltas = np.stack([boundary_delta[y-1,x],boundary_delta[y+1,x],
                       boundary_delta[y,x-1],boundary_delta[y,x+1]],axis=1)
    rhs = np.sum(deltas*(~present)[...,None],axis=1)

    def operator(values):
        return 4*values-np.sum(values[safe]*present[...,None],axis=1)

    # Solve all three independent channels; shared scalar CG is equivalent
    # to a block-diagonal system. Never accept a silently unconverged solve.
    offset = np.zeros_like(rhs)
    residual = rhs.copy()
    direction = residual.copy()
    norm0 = float(np.sum(rhs*rhs))
    norm = norm0
    iterations = 0
    while norm > norm0*tolerance*tolerance and iterations < max_iterations:
        applied = operator(direction)
        denominator = float(np.sum(direction*applied))
        if denominator <= 0 or not np.isfinite(denominator):
            raise ValueError('Invalid RGB boundary operator')
        step = norm/denominator
        offset += step*direction
        residual -= step*applied
        next_norm = float(np.sum(residual*residual))
        direction = residual+(next_norm/norm)*direction
        norm = next_norm
        iterations += 1
    relative = np.sqrt(norm/norm0) if norm0 else 0.0
    # Check the actual equation, not only the recurrent CG residual.
    actual = operator(offset)-rhs
    actual_relative = np.sqrt(float(np.sum(actual*actual))/norm0) if norm0 else 0.0
    if not np.isfinite(actual_relative) or actual_relative > tolerance*1.1:
        raise ValueError('RGB boundary solve did not converge')
    result = parent.copy()
    result[y,x,:3] = np.clip(np.rint(material[y,x,:3].astype(float)+offset),0,255).astype(np.uint8)
    return result, dict(iterations=iterations,relativeResidual=float(max(relative,actual_relative)))
