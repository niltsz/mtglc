"""Prepare LightningCast inputs for one FCI repeat cycle over Europe and save them as .npz."""

import argparse
from datetime import UTC, datetime
from pathlib import Path

import numpy as np

from mtglc import eumetsat, fci, preprocess

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument(
    "cycle", help="start of the FCI repeat cycle in UTC, e.g. 2025-07-01T14:00"
)
parser.add_argument("output", type=Path, help=".npz with model inputs vis, nir, ir")
parser.add_argument("--raw-dir", type=Path, default=Path("data/raw"))
args = parser.parse_args()

cycle = datetime.fromisoformat(args.cycle).replace(tzinfo=UTC)
product_dir = eumetsat.get_product_dir(args.raw_dir, "fci_fdhsi", cycle)
product_filelist = eumetsat.get_product_filelist(product_dir)

chunks = eumetsat.select_chunk(product_filelist, fci.EUROPE_CHUNKS)
scn = fci.get_scene(chunks, channels=fci.CHANNELS)
inputs = fci.get_inputs(scn, fci.EUROPE_WINDOW)
vis, nir, ir = preprocess.to_model_inputs(inputs)

np.savez(args.output, vis=vis, nir=nir, ir=ir, ir105_k=inputs["ir_105"])
print(f"{args.output}: vis {vis.shape}, nir {nir.shape}, ir {ir.shape}")
