from dataclasses import dataclass
from pathlib import Path

import numpy as np
import satpy

from mtglc import eumetsat

CHANNELS = ("vis_06", "nir_16", "ir_105", "ir_123")
GRID_FACTOR = {
    "vis_06": 2,
    "nir_16": 2,
    "ir_105": 1,
    "ir_123": 1,
}  # channels with 1km resolution get factor 2
SCALE = {
    "vis_06": 0.01,
    "nir_16": 0.01,
    "ir_105": 1.0,
    "ir_123": 1.0,
}  # Convert percentage to 0-1


@dataclass
class Window:
    row0: int
    row1: int
    col0: int
    col1: int

    def __post_init__(self):
        if self.row0 >= self.row1 or self.col0 >= self.col1:
            raise ValueError("Invalid window size.")
        h, w = self.shape
        if h % 4 or w % 4:
            raise ValueError("Window csannot be divided by 4")

    @property
    def shape(self):
        h = self.row1 - self.row0
        w = self.col1 - self.col0
        return (h, w)


EUROPE_WINDOW = Window(376, 1064, 2344, 4024)
EUROPE_CHUNKS = [33, 34, 35, 36, 37, 38]


def get_scene(filelist: list[Path], channels: list[str], reader="fci_l1c_nc"):
    if reader != "fci_l1c_nc":
        raise ValueError(f"reader {reader} has not been implemented yet")
    scn = satpy.Scene(filelist, reader)
    for ch in channels:
        scn.load([ch], upper_right_corner="NE")
    found_channels = [data_id._satpy_id["name"] for data_id in scn]
    eumetsat.check_channel_completeness(found_channels, channels)
    return scn


def window_slices(window: Window, factor: int) -> tuple[slice, slice]:
    return (
        slice(window.row0 * factor, window.row1 * factor),
        slice(window.col0 * factor, window.col1 * factor),
    )


def get_inputs(scn, window: Window) -> dict[str, np.ndarray]:
    # funciton that first slices the scene according to the window and then calls .values.
    # Values are converted from % to 0..1 range for vis_06 and nir_16
    # Returns np.float32 arrays. Raises ValueError in case of NaN in data
    # GRID_FACTOR is hardcoded as module constant
    inputs = {}
    for ch in CHANNELS:
        da = scn[ch][window_slices(window, GRID_FACTOR[ch])]
        arr = (da.values * SCALE[ch]).astype(np.float32)
        expected = tuple(GRID_FACTOR[ch] * n for n in window.shape)
        if arr.shape != expected:
            raise ValueError(f"{ch}: shape {arr.shape}, expected {expected}")
        n_nan = np.isnan(arr).sum()
        if n_nan:
            raise ValueError(f"{ch}: {n_nan} NaN pixels in window (missing chunk?)")
        inputs[ch] = arr
    return inputs
