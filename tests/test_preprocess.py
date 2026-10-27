import numpy as np

from mtglc import preprocess


def test_standardize():
    out = preprocess.standardize(np.array([270.93, 270.93 + 25.9126]), 270.93, 25.9126)
    np.testing.assert_allclose(out, [0.0, 1.0], atol=1e-6)
