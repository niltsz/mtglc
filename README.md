# mtglc



**Status:** work in progress.
This projects aims to provide a ML ready dataset for lightning nowcasting over Europe, combining the MTG FCI data with the MTG LI as a target. 
Furthermore, the zero shot performance of LightningCast model, developed by CIMSS/SSEC on GOES-16 ABI data over the USA, for this data will be evaluated. 

The state of this repo is work in progress. So far, this code is able to connect to the EUMDAC datastore and download MTG data (credentials required, see below).
This data is then lazily filtered for the correct chunks and channels to create a scene, on which the original LightningCast model is run.

First plots of a zero shot run of LightningCast on 2025-07-01T14:00 - 2025-07-01T14:10 looks plausible, however a deeper analysis is still tbd. 

Next steps: Use LI as labels, store data as Zarr instead of npz, evaluate performance of LC

## Setup

Project is setup with the package manager uv (https://docs.astral.sh/uv/)
Within the folder of this repo (after cloning):

    uv sync
    uv run pytest -m "not needs_data"

Most of the tests do not require data to run. For those tests that need data place it in `data/raw`

To obtain access to the EUMETSAT datastore, register at their website and accept their licences / terms and conditions. Create credentials (key, secret) and export them or
store them separated by a comma in `Path.home() / .eumdac / credentials`.
The file scripts/download.py can be used to modified to download the data point used for the first look.
`uv run scripts/download.py`

The model is not included. For this repo, the CSPP Geo LightningCast 1.0beta2 version is used, downloaded from the SSEC website. Place `fit_conv_model.h5` and `model_config.pkl` found in `libexec/python_runtime/lib/python3.10/site-packages/lightningcast/static/waf22` in the folder `external/lc_model`

For one cycle, run 

    uv run scripts/prepare_sample.py 2025-07-01T14:00 data/sample.npz
    uv run --python 3.11 scripts/predict_lightningcast.py data/sample.npz data/sample_prob.npy

To keep TensorFlow out of the main package, this script brings its own python version (see header of predict_lightningcast.py)

## Notes 

The area is hardcoded in fci.py, based on the indices for 2km resolution. Indices for 1km resolution is derrived by multiplying by 2. Checks are implemented so that the 
size of the window is divisible by 4 in each direction which is a requirement for the U-Net of LightningCast. Reflectances are satpy's `reflectance` divided by 100 (no solar zenith correction), as in the LightningCast training data.
NaN in the data are not filled but the entire sample is rejected instead.


## Credits

Thanks to John Cintineo and colleagues at CIMSS/SSEC (University of
Wisconsin–Madison) for LightningCast and for releasing it through CSPP Geo.
The model is described in Cintineo et al. (2022). I use the released version
as is; this project is not affiliated with CIMSS in any way.

## License

MIT for the code in this repository. EUMETSAT data and the LightningCast model
are subject to their own terms.