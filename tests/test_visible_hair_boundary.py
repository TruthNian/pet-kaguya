"""Visible hair anchors must not import garment color into hidden hair."""
import sys
from pathlib import Path
import unittest

import numpy as np

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
from visible_hair_boundary import solve
from refine_source_arm import slope_boundary


class VisibleBackgroundSolve(unittest.TestCase):
    def fixture(self):
        y,x=np.mgrid[:9,:9]
        material=np.zeros((9,9,4),dtype=np.uint8)
        material[...,:3]=np.stack([100+x*4,120+y*3,80+x+y],axis=-1)
        material[...,3]=253
        parent=material.copy()
        parent[...,:3]=(material[...,:3].astype(int)+[8,-7,5]).astype(np.uint8)
        domain=np.zeros((9,9),dtype=bool);domain[2:7,2:7]=True
        known=np.zeros_like(domain);known[2:7,1]=True
        return parent,material,domain,known

    def test_one_real_hair_boundary_fixes_offset_and_preserves_material_gradient(self):
        parent,material,domain,known=self.fixture()
        result,diagnostics=solve(parent,material,domain,known)
        np.testing.assert_array_equal(result,parent)
        self.assertEqual(diagnostics['anchors'],5)
        self.assertLessEqual(diagnostics['relativeResidual'],1.1e-8)
        unchanged,empty=solve(parent,material,np.zeros_like(domain),known)
        np.testing.assert_array_equal(unchanged,parent)
        self.assertEqual(empty,dict(iterations=0,relativeResidual=0.,anchors=0,clippedChannels=0))

    def test_occluder_color_and_unobserved_source_do_not_bleed_into_hair(self):
        parent,material,domain,known=self.fixture()
        expected,_=solve(parent,material,domain,known)
        parent[~known,:3]=[255,0,255]
        parent[...,3]=np.arange(81).reshape(9,9)
        result,_=solve(parent,material,domain,known)
        np.testing.assert_array_equal(result[domain,:3],expected[domain,:3])
        np.testing.assert_array_equal(result[~domain],parent[~domain])
        np.testing.assert_array_equal(result[...,3],parent[...,3])

    def test_unanchored_component_fails_even_with_zero_rhs_and_no_hidden_error(self):
        parent,material,domain,known=self.fixture()
        known[:]=False
        with self.assertRaises(ValueError):solve(material,material,domain,known)
        known[2:7,1]=True;domain[7,7]=True # second isolated component
        with self.assertRaises(ValueError):solve(parent,material,domain,known)

    def test_illegal_domains_and_unconverged_solution_are_not_silently_accepted(self):
        parent,material,domain,known=self.fixture()
        for kwargs in (dict(tolerance=True),dict(tolerance=0),dict(tolerance=np.nan),
                       dict(max_iterations=True),dict(max_iterations=0),dict(max_iterations=1)):
            with self.assertRaises(ValueError):solve(parent,material,domain,known,**kwargs)
        overlap=known.copy();overlap[2,2]=True
        with self.assertRaises(ValueError):solve(parent,material,domain,overlap)
        border=domain.copy();border[0,2]=True
        with self.assertRaises(ValueError):solve(parent,material,border,known)

    def test_inferred_inward_slope_is_not_taken_from_occluded_source_color(self):
        parent,material,domain,known=self.fixture()
        known[2:7,0]=True
        corrected=material.copy();corrected[~domain]=parent[~domain]
        parent[domain,:3]=[0,250,0] # foreground, never a hidden-hair observation
        result,inferred,diagnostics=slope_boundary(parent,corrected,domain,known)
        expected=material.copy()
        expected[...,:3]=(material[...,:3].astype(int)+[8,-7,5]).astype(np.uint8)
        np.testing.assert_array_equal(result,expected)
        self.assertEqual(int(inferred.sum()),5)
        self.assertEqual(diagnostics['clippedInferredChannels'],0)


if __name__=='__main__':unittest.main()
