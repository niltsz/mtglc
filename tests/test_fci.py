from pathlib import Path

import numpy as np
import pytest

from mtglc import eumetsat, fci

PATH_FILE = Path(__file__).resolve().parent.parent
RAW_DIR = PATH_FILE / "data" / "raw" / "fci_fdhsi" / "20250701" / "1400"
CHANNELS = ["vis_06", "nir_16", "ir_105", "ir_123"]


@pytest.fixture(scope="session")
def product_filelist():
    return eumetsat.get_product_filelist(RAW_DIR)


@pytest.fixture(scope="session")
def real_scene(product_filelist):
    return fci.get_scene(product_filelist, CHANNELS)


@pytest.mark.needs_data
def test_real_scene_calibration(real_scene):
    assert real_scene["vis_06"].attrs["calibration"] == "reflectance"
    assert real_scene["nir_16"].attrs["calibration"] == "reflectance"
    assert real_scene["ir_105"].attrs["calibration"] == "brightness_temperature"
    assert real_scene["ir_123"].attrs["calibration"] == "brightness_temperature"


@pytest.mark.needs_data
@pytest.mark.parametrize("channel", ["ir_105", "vis_06"])
def test_real_scene_northup_westleft(real_scene, channel):
    area = real_scene[channel].attrs["area"]
    n_row, n_col = area.shape
    mid_row = n_row // 2
    mid_col = n_col // 2
    edge_row = n_row // 50
    edge_col = n_col // 50

    _, lat_top = area.get_lonlat(edge_row, mid_col)
    _, lat_bottom = area.get_lonlat(n_row - 1 - edge_row, mid_col)
    lon_left, _ = area.get_lonlat(mid_row, edge_col)
    lon_right, _ = area.get_lonlat(mid_row, n_col - 1 - edge_col)

    assert np.isfinite([lat_top, lat_bottom, lon_left, lon_right]).all()
    assert lat_top > lat_bottom
    assert lon_left < lon_right
