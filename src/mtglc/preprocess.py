import numpy as np

# scaling values (mean, std) taken from CSPP 1.0beta2 static/wav22/model_config.pkl
SCALING_VALUES = {
    "vis_06": (0.08713, 0.15314),  # CH02
    "nir_16": (0.047332, 0.0834376),  # CH05
    "ir_105": (270.93, 25.9126),  # CH13
    "ir_123": (273.168, 19.9895),  # CH15
}


def standardize(data: np.ndarray, mean: float, std: float) -> np.ndarray:
    if np.isnan(data).any():
        raise ValueError("input contains NaN")
    return ((data - mean) / std).astype(np.float32)


def to_model_inputs(inputs: dict[str, np.ndarray]) -> list[np.ndarray]:
    """Output of fci.get_inputs -> [vis 0.5 km, nir 1 km, ir 2 km (2 ch)] with batch dim."""
    s = {ch: standardize(a, *SCALING_VALUES[ch]) for ch, a in inputs.items()}
    vis = s["vis_06"].repeat(2, axis=0).repeat(2, axis=1)  # 1 km -> 0.5 km, nearest
    ir = np.stack([s["ir_105"], s["ir_123"]], axis=-1)
    return [vis[None, ..., None], s["nir_16"][None, ..., None], ir[None]]
