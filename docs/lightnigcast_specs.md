# LightningCast model: what we use and how

All model facts below refer to the CSPP Geo LightningCast 1.0beta2 download
(CIMSS/SSEC), model directory `static/waf22/`. The CIMSS source repository
contains other models and configurations that do not apply here.
The model file is not redistributed; copy it to `external/lc_model/`.

## Model file and runtime
- Files in the CSPP package, under
  `libexec/python_runtime/lib/python3.10/site-packages/lightningcast/static/waf22/`:
  `fit_conv_model.h5` and `model_config.pkl`
- SHA-256 of `fit_conv_model.h5`: `687ee1ed86785a9cb00e460acf53c4ca7513141dd0fb9ab1e902ac7bcde95c2`8
- Loads with `tf.keras.models.load_model(path, compile=False)` under TensorFlow 2.15
  (Keras 2, Python ≤ 3.11). 

## Inputs
| Model input | ABI channel | FCI channel | Grid fed to model | mean | std |
|---|---|---|---|---|---|
| `input_1` | CH02 (0.64 µm) | `vis_06` | 0.5 km (FCI 1 km, pixel-doubled) | 0.08713 | 0.15314 |
| `input_2` | CH05 (1.6 µm)  | `nir_16` | 1 km | 0.047332 | 0.0834376 |
| `input_3` | CH13 (10.3 µm) | `ir_105` | 2 km | 270.93 K | 25.9126 K |
|           | CH15 (12.3 µm) | `ir_123` | 2 km | 273.168 K | 19.9895 K |

- Standardization per channel in native units, `(x − mean) / std`, no clipping.
  Values from `scaling_vals` in `model_config.pkl`. The config has no
  `minmax_scaling_vals`, so CSPP uses this branch as well
  (`predict_ltg.py`, "Normal mean/std scaling using native-unit data", line 3413).
- Reflectance as a fraction (0–1), consistent with the means above, without
  solar-zenith correction (satpy `reflectance` ÷ 100).
- CSPP fills missing values before scaling; this pipeline instead rejects
  samples with NaN in the domain.

## Architecture (from the loaded model)
- `input_2` is upsampled ×2 and `input_3` ×4 to 0.5 km; all inputs are
  concatenated (4 channels).
- U-Net at 0.5 km: 5 levels with 16/32/64/128/256 feature maps, two 3×3
  convolutions + ReLU per level, 4 × MaxPooling 2×2 (down to 8 km),
  4 × Conv2DTranspose stride 2 with skip connections at every level
  (back to 0.5 km). No batch normalization or dropout.
- Output: 1×1 convolution + sigmoid, then MaxPooling 4×4 to the 2 km grid and
  squeeze to `(batch, H, W)`. Each 2 km value is the maximum over 4×4 sub-pixels.
- 3×3 convolutions use same padding, so the output covers exactly the 2 km input grid.
- 2.16 M parameters. Theoretical receptive field ≈ 230 px at 0.5 km (≈ 115 km),
  computed from the layer configuration.

## Input size
Training patches were 2944 × 3328 / 1472 × 1664 / 736 × 832 px (0.5 / 1 / 2 km).
The network is fully convolutional: any size works if the 2 km height and width
are divisible by 4 (bottleneck at H/4). Verified: 784 × 1692 runs in ~7 s on
Apple MacBook Air (M4, 16GB RAM); a width of 1690 fails at the first skip-connection concatenate.

## Output
Probability of lightning in the next 60 min per 2 km pixel.
Training target: GLM flash extent density accumulated over 60 min
(`FED_accum_60min_2km`), binarized at 0.1, i.e. at least one flash.

## Training (from `model_config.pkl`)
Binary cross-entropy, Adam (learning rate 3e-4), batch size 1, up to 100 epochs
with early stopping (patience 4), GOES-16 ABI channels CH02, CH05, CH13, CH15.
Sample lists and training period are not included in the package.

## References
- CSPP Geo LightningCast Software User's Guide, v1.0beta2.
- Cintineo, J. L., et al. (2022): LightningCast: A deep-learning model for
  lightning nowcasting. Weather and Forecasting. https://doi.org/10.1175/WAF-D-22-0019.1