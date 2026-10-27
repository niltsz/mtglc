# /// script
# requires-python = "==3.11.*"
# dependencies = ["tensorflow==2.15.*", "numpy<2"]
# ///
"""Run the CSPP LightningCast waf22 model on prepared inputs (.npz) and save probabilities."""

import argparse
from pathlib import Path

import numpy as np
import tensorflow as tf

parser = argparse.ArgumentParser()
parser.add_argument("inputs", type=Path, help=".npz with vis, nir, ir")
parser.add_argument("output", type=Path, help=".npy with probabilities (H, W)")
parser.add_argument(
    "--model", type=Path, default=Path("external/lc_model/fit_conv_model.h5")
)
args = parser.parse_args()

model = tf.keras.models.load_model(args.model, compile=False)
d = np.load(args.inputs)
prob = model.predict([d["vis"], d["nir"], d["ir"]], verbose=0)[0]
np.save(args.output, prob.astype(np.float32))
print(
    f"{args.output}: {prob.shape}, max {prob.max():.3f}, >0.5: {(prob > 0.5).mean():.2%}"
)
