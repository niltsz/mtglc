# Decision log

Short entries: date, decision, reason, rejected alternatives.

## 2026-10-04 — Project initialised
Repository created with a bootstrap script: uv (src layout), ruff, pytest, GitHub Actions CI.
Third-party software and data live in `external/` and `data/` and are not version-controlled.

## 2026-10-07 eumetsat.py
All datetimes are now in UTC.

## 2026-10-09 - Pin satpy < 1.0, calibration reflectance without SZA normalization
Upstream satpy marks calibration "reflectance" as deprecated, one should use "unnormalized_reflectance" instead while underlying data remains unchanged.
Installed version satpy 0.60 only provides "reflectance". SatPy version pinned
to < 1.0 as changes might occur in future


## 2026-10-12
Shift the focus of this repo to provide a recipe for an ML ready dataset taht includes MTG FCI and lightning data over Europe.
Use MTG LI Accumulated Flash Area as target for ML. Time Window [t0, t0 + 60 min), with the start time taken from the file ("accumulation start times") instead of file name. Bc one pixel could occur multiple times, it needs to be summed per pixel instead of bool flash/no flash. Indices start at 1. LI runs from negative to positive in direction west to east (caution), and from south to north for negative to positive (standard definition of elevation),. i.e. (1, 1) is south-west corner. Compare MTG LI Level 2 data guide, page 40. 
For the start time of the labels (LI), the start time + 10 min of the scan cycle in which europe is fully scanned is used (example: europe is fully scanned at 14:07:45. The label will then be [14:10 : 15:10). This ensures that no flashes will be recorded before europe is scanned. For the example day 01.07.2025 14:00, the full disk was scanned from 14:00:07 until 14:09:34.
Note: CIMSS LightningCast uses the same dt for both the FCI scene and the LI window, derived from the trailer file name. Bc Europe is scanned at the end of the cycle, this means that the label starts several minutes before the actual scan.  
The orientation of FCI will be flipped by satpy, with the defautl argument upper_right_corner = "NE". Test cases written, test passes for "NE" and turns red for "NW", "SE" and "NW". 
