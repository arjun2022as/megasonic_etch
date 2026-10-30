# Project 1 status log (newest first)

Megasonic-assisted TMAH wet etching of poly-Si, 100 nm x 10 um slit (AR 100), alternating SiO2/poly-Si
50/50 nm, single-wafer spin tool with MegPie transducer. Formulas and sources: `docs/formulation.md`.

## Next step
- Puma: `cd ~ && git clone https://github.com/arjun2022as/megasonic_etch.git project1`, then
  `cd ~/project1 && bash submit_cases.sh M0_none --discover`; send `tail -60 logs/M0_none_*.out` and
  `results/M0_none_discover/discover.txt`. Fix the UDS/UDF hookups in `fluent2d/api.py` from it.
- Then: smoke test `bash submit_cases.sh A_f1_I2_t45 --setup-only`, then all 16 cases, then `analyze_2d.py`.

## Decisions (user)
- Software: Fluent 2024R1 + compiled UDFs (not COMSOL). Etchant 5 wt% TMAH, 60 C (Micron conditions pending).
- Megasonics 1/2/3 MHz, 0.5-2 W/cm2; H2 tracked as dissolved species. Wet etch only (dry etch done before).
- Formulas checked twice; assumptions labelled.

## Assumptions to replace with real data
- Poly-Si etch rate at 5 wt%, 60 C: 300 nm/min (calibrate with Project 1 SEM). Rate order in OH-: 1/4.
- Silicate diffusivity ~ carbonate; H2 solubility 0.7 mM; slit pitch 1 um; slit floor inert; oxide on top.
- Spin 300 rpm, MegPie gap 2 mm, r = 50 mm.

## Results so far
- 2026-10-30 1D model (`run_1d.py`, `run_evolution.py`): bottom/top etch rate 0.96 (294 vs 281 nm/min);
  electromigration doubles OH- depletion; dissolved H2 ~120x saturation, above the slit bubble threshold
  13.9x everywhere -> H2 bubbles likely control uniformity (90 % blocking -> bottom/top 0.65).
  Megasonic oscillating flow reaches only ~5 nm into the slit; MegPie normal incidence gives no tangential
  flow. Acoustic pressure 230-460 kPa < Laplace 1.32 MPa holding a confined bubble.
  Recess after 2 min: 587 nm top vs 562 nm bottom.
- 2026-10-30 2D Fluent model written and pushed (commit 4e0cd88), not yet run.
