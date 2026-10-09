"""Specific sleeve-edge/background improvements, not full pet acceptance."""
import json
import sys
from pathlib import Path
import unittest

import numpy as np
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'tools'))
import review_source_arm as arm
import refine_source_arm as refinement
from review_source_backing import load_projected


class RefinedSourceArm(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.original=arm.materials(background_override=load_projected())
        cls.expanded=arm.materials(background_override=load_projected(),follow_cloth_edges=True)
        cls.data,cls.domain,cls.known,cls.solve,cls.inferred,cls.slope=refinement.refine(cls.expanded)
        cls.rendered=[arm.pose(cls.data,angle) for angle in arm.ANGLES]

    def test_actual_connected_green_sleeve_is_not_mislabeled_visible_hair(self):
        x0,y0,x1,y1=arm.BOX
        np.testing.assert_array_equal(self.expanded['allowed'],self.original['allowed'])
        np.testing.assert_array_equal(self.expanded['protected'],self.original['protected'])
        added=(self.expanded['beta']>0)&(self.original['beta']==0)
        self.assertEqual(int(added.sum()),221)
        for x,y in [(427,903),(426,905),(425,908),(423,913),(422,915)]:
            self.assertEqual(self.original['beta'][y,x],0)
            self.assertGreater(self.expanded['beta'][y,x],0)
            self.assertFalse(self.known[y-y0,x-x0])
            r,g,b,_=np.asarray(self.rendered[1][0])[y,x]
            self.assertFalse(int(g)-int(r)>=-8 and int(g)-int(b)>16 and g>75)
        source=np.asarray(self.data['mother'])[y0:y1,x0:x1,:3].astype(int)
        r,g,b=np.moveaxis(source,-1,0)
        self.assertFalse(np.any(self.known&(g-r>=-8)&(g-b>16)&(g>75)))

    def test_hidden_color_changes_only_in_unknown_area_and_alpha_is_source(self):
        x0,y0,x1,y1=arm.BOX
        source=np.asarray(self.data['mother']);background=np.asarray(self.data['background'])
        full=np.zeros(source.shape[:2],dtype=bool);full[y0:y1,x0:x1]=self.domain
        np.testing.assert_array_equal(source[~full],background[~full])
        np.testing.assert_array_equal(source[...,3],background[...,3])
        self.assertFalse(np.any(self.domain&self.known))
        self.assertFalse(np.any(self.known&self.expanded['protected'][y0:y1,x0:x1]))
        self.assertLessEqual(self.solve['relativeResidual'],1.1e-8)
        self.assertLessEqual(self.slope['relativeResidual'],1.1e-8)
        self.assertEqual(self.slope['inferredPixels'],771)
        self.assertTrue(np.all(self.inferred<=self.domain))

    def test_neutral_and_nonzero_protection_are_not_conflated_with_visual_approval(self):
        source=np.asarray(self.data['mother'])
        beta=self.data['beta'][...,None]
        self.assertTrue((self.data['foreground']>=-1e-9).all())
        self.assertTrue((self.data['foreground']<=255*beta+1e-9).all())
        for i,(image,measurement) in enumerate(self.rendered):
            actual=np.asarray(image)
            np.testing.assert_array_equal(actual[~self.data['allowed']],source[~self.data['allowed']])
            np.testing.assert_array_equal(actual[...,3],source[...,3])
            self.assertEqual(measurement['changedOutsidePermission'],0)
            with Image.open(refinement.OUT/f'pose-{i}.png') as saved:
                self.assertEqual(saved.convert('RGBA').tobytes(),image.tobytes())
        self.assertEqual(self.rendered[0][0].tobytes(),self.data['mother'].tobytes())
        self.assertEqual(self.rendered[-1][0].tobytes(),self.data['mother'].tobytes())
        for name in ('protected', 'allowed'):
            with Image.open(refinement.OUT/(name+'-mask.png')) as mask:
                np.testing.assert_array_equal(np.asarray(mask),self.data[name].astype(np.uint8)*255)
        metadata=json.loads((refinement.OUT/'build.json').read_text(encoding='utf-8'))
        self.assertTrue(metadata['inferredBoundaryIsNotSourceObservation'])
        self.assertTrue(metadata['foregroundMatteStillEstimated'])
        self.assertFalse(metadata['foregroundMaterialDomainPreserved'])
        for key in ('adopted','activeAtlasChanged','installableFullAtlas','installed',
                    'facialGeometryRepair','cleanLayerRecoveryClaimed','articulatedArmBuilt','nativeInterpolation'):
            self.assertFalse(metadata[key])
        self.assertEqual(metadata['visualMotionApproval'],'pending')
        self.assertEqual(metadata['durationsMs'],[140,140,140,280])
        self.assertEqual(metadata['repeatBeforeIdle'],3)


if __name__=='__main__':unittest.main()
