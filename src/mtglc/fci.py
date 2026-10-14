from pathlib import Path

import satpy

from mtglc import eumetsat


def get_scene(filelist: list[Path], channels: list[str], reader="fci_l1c_nc"):
    if reader != "fci_l1c_nc":
        raise ValueError(f"reader {reader} has not been implemented yet")
    scn = satpy.Scene(filelist, reader)
    for ch in channels:
        scn.load([ch], upper_right_corner="NE")
    found_channels = [data_id._satpy_id["name"] for data_id in scn]
    eumetsat.check_channel_completeness(found_channels, channels)
    return scn
