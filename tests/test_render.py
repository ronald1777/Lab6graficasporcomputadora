"""Pruebas de restricciones y de efectos observables; unittest, sin pytest."""
import unittest
from pathlib import Path
import numpy as np
from src.mesh import load_obj
from src.renderer import rasterize
from src.shaders import SHADERS, PARAMS, cloud_mask, bump_normal, terrain, gas_coordinates
from src.noise import normalize

ROOT = Path(__file__).resolve().parents[1]

class RenderTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.vertices,cls.faces = load_obj(ROOT/'assets/sphere.obj')
        cls.g = rasterize(cls.vertices,cls.faces,100)

    def test_raster_geometry(self):
        self.assertGreater(self.g['mask'].sum(),4500)
        self.assertLess(self.g['mask'].sum(),5500)
        np.testing.assert_allclose(np.linalg.norm(self.g['p'],axis=1),1,atol=1e-8)

    def test_finite_distinct_materials_and_static_mesh(self):
        before = self.vertices.copy()
        p,v = self.g['p'],self.g['view']
        light = normalize(np.array([-.7,.2,.8]))
        results = [f(p,v,light,0.) for f in SHADERS.values()]
        for result in results:
            self.assertEqual(result.shape,p.shape)
            self.assertTrue(np.isfinite(result).all())
        for a,b in ((0,1),(1,2),(0,2)):
            self.assertGreater(np.abs(results[a]-results[b]).mean(),.04)
        np.testing.assert_array_equal(before,self.vertices)

    def test_star_is_emissive_and_animated(self):
        p,v = self.g['p'],self.g['view']
        l = normalize(np.array([-.7,.2,.8]))
        f = SHADERS['star']
        a = f(p,v,l,0.)
        np.testing.assert_array_equal(a,f(p,v,-l,0.))
        self.assertGreater(np.abs(a-f(p,v,l,3.)).mean(),.02)

    def test_cloud_advection_and_bump_normals(self):
        p,s = self.g['p'],PARAMS['rock']
        a,b = cloud_mask(p,0,s),cloud_mask(p,4,s)
        self.assertGreater(np.abs(a-b).mean(),.04)
        h = terrain(p,s)
        n = bump_normal(p,h,s)
        np.testing.assert_allclose(np.linalg.norm(n,axis=1),1,atol=1e-8)
        self.assertGreater(np.abs(n-p).mean(),.001)
        flat = dict(s,bump_strength=0)
        np.testing.assert_allclose(bump_normal(p,h,flat),p,atol=1e-8)

    def test_vortex_warps_surrounding_latitudes(self):
        p = normalize(np.array([[.30,-.2,.94],[.2,-.05,.97],[-.2,.2,.96]]))
        s = PARAMS['gas']
        warped,_,_ = gas_coordinates(p,0,s)
        flat,_,_ = gas_coordinates(p,0,dict(s,vortex_strength=0))
        self.assertGreater(np.max(np.abs(warped-flat)),.05)

if __name__=='__main__': unittest.main()
