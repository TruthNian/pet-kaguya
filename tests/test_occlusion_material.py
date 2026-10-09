"""Paint-alpha is not an occlusion mask or proof of recovered artist layers."""
from pathlib import Path
import sys
import unittest
import numpy as np

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'tools'))
from occlusion_material import condition,over
from build_idle import sample


class OcclusionMaterial(unittest.TestCase):
    def fixture(self):
        source=np.zeros((5,7,4),dtype=float)
        source[...]=[80.,40.,20.,128.]
        background=source.copy();background[1:4,2:5]=[50.,90.,120.,180.]
        hint=np.zeros((5,7),dtype=float);hint[1:4,2:5]=.25
        return source,background,hint

    def test_fractional_source_alpha_is_reconstructed_not_source_over_twice(self):
        s,b,h=self.fixture();p,beta=condition(s,b,h)
        np.testing.assert_allclose(over(p,beta,b),s,rtol=0,atol=3e-14)
        wrong=s*h[...,None]+b*(1-s[...,3:4]*h[...,None]/255)
        self.assertGreater(np.max(np.abs(wrong-s)),10)
        self.assertTrue(np.any(beta>h))

    def test_conditioned_color_and_alpha_are_valid_without_gamut_clipping(self):
        s,b,h=self.fixture();s[2,3]=[0.,0.,0.,128.]
        p,beta=condition(s,b,h)
        self.assertEqual(beta[2,3],1)
        self.assertTrue((p>=0).all())
        self.assertTrue((p[...,:3]<=p[...,3:4]+1e-10).all())
        self.assertTrue((p[...,3]<=255*beta+1e-10).all())
        np.testing.assert_allclose(over(p,beta,b),s,rtol=0,atol=3e-14)

    def test_known_source_outside_material_is_exact_and_inputs_not_mutated(self):
        s,b,h=self.fixture();copies=[a.copy() for a in (s,b,h)]
        p,beta=condition(s,b,h)
        np.testing.assert_array_equal(p[h==0],0)
        np.testing.assert_array_equal(beta[h==0],0)
        for a,c in zip((s,b,h),copies):np.testing.assert_array_equal(a,c)
        np.testing.assert_array_equal(over(p,beta,b)[h==0],s[h==0])
        b[0,0,0]+=1
        with self.assertRaises(ValueError):condition(s,b,h)

    def test_moving_paint_and_occlusion_reveals_backing_instead_of_double_alpha(self):
        s,b,h=self.fixture();p,beta=condition(s,b,h)
        y,x=np.mgrid[:5,:7].astype(float)
        moved=over(sample(p,x-1,y),sample(beta,x-1,y),b)
        np.testing.assert_array_equal(moved[1:4,2],b[1:4,2])
        self.assertGreater(np.max(np.abs(moved-s)),10)
        self.assertTrue((moved[...,:3]<=moved[...,3:4]+1e-10).all())
        self.assertTrue((moved[...,3]<=255+1e-10).all())

    def test_invalid_premultiplied_data_shape_weights_and_nonfinite_values_fail(self):
        s,b,h=self.fixture()
        for value in (-.1,1.1,np.nan):
            bad=h.copy();bad[2,3]=value
            with self.assertRaises(ValueError):condition(s,b,bad)
        for bad in (s.astype(np.uint8),s[...,:3],s[:3],s*np.nan):
            with self.assertRaises(ValueError):condition(bad,b,h)
        bad=s.copy();bad[1,1,0]=200
        with self.assertRaises(ValueError):condition(bad,b,h)
        bad=s.copy();bad[1,1,3]=300
        with self.assertRaises(ValueError):condition(bad,b,h)

    def test_no_material_has_the_same_composition_contract(self):
        s,b,h=self.fixture();h[:]=0
        p,beta=condition(s,s,h)
        np.testing.assert_array_equal(p,0);np.testing.assert_array_equal(beta,0)
        np.testing.assert_array_equal(over(p,beta,s),s)


if __name__=='__main__':unittest.main()
