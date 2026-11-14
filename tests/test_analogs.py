import unittest
import numpy as np
from scipy.stats import chi2
from farm_analog.analogs import sigma_dissimilarity

class AnalogTests(unittest.TestCase):
    def test_matches_direct_covariance_distance(self):
        rng=np.random.default_rng(7)
        history=rng.normal(size=(60,4)) @ np.array([[1,0.4,0,0],[0,1,0,0],[0,0,3,0.6],[0,0,0,1]])
        target=np.array([0.5,1,2,3])
        candidates=np.vstack([target,target+1,target-2])
        differences=candidates-target
        d2=np.einsum('ij,jk,ik->i',differences,np.linalg.inv(np.cov(history,rowvar=False)),differences)
        expected=np.sqrt(chi2.isf(chi2.sf(d2,df=4),df=1))
        np.testing.assert_allclose(sigma_dissimilarity(target,history,candidates),expected,atol=1e-10)
        self.assertEqual(sigma_dissimilarity(target,history,candidates)[0],0)

    def test_rejects_missing_and_constant_features(self):
        for history in [np.ones((20,4)),np.full((20,4),np.nan)]:
            with self.assertRaises(ValueError): sigma_dissimilarity(np.ones(4),history,np.ones((2,4)))

if __name__=='__main__': unittest.main()
