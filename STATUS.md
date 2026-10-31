# Project 1 status log (newest first)

Megasonic-assisted TMAH wet etching of poly-Si, 100 nm x 10 um slit (AR 100), alternating SiO2/poly-Si
50/50 nm, single-wafer spin tool with MegPie transducer. Formulas and sources: `docs/formulation.md`.

## Next steps (agreed with user 2026-10-30, in this order)
| # | Step | Check |
|---|---|---|
| 1 | Full `M0_none` (no megasonics), `bash submit_cases.sh M0_none` | bottom/top ~ 0.954 (1D) |
| 2 | Contour/movie script like 3d_nand `make_movies`: contours of OH-, silicate, H2, velocity, D_osc, etch rate along the slit, per case, from `<case>-final.cas.h5` | PNGs per case |
| 3 | FLAT WAFER first (normal incidence, how tools normally run): frequency 1/2/3 MHz x power 0.5/1/2 W/cm2 at 90 deg | case-by-case results |
| 4 | Then the ANGLE cases (A_*, F_*, P_* at 45 deg, R_*), then V_* checks | every case `done:` |
| 5 | `analyze_2d.py` figures + verification.md | 2D vs 1D |

Step 3 caveat: in the current model 90 deg gives u_t = 0, so A_f1_I2_t90 is IDENTICAL to M0_none (same
c_surf, same 1D 0.9575). A normal-incidence mechanism must be added first (candidates: acoustic
(Eckart) streaming thinning the wafer boundary layer -> mouth concentrations; compressional "breathing"
of the slit, xi = L|1+R|p0/(rho c^2), already in etchsim/acoustics.py), then flat-wafer cases added.
Every figure/summary: imposed oscillating flow + modelled mixing, NOT a full acoustic-streaming solution.

## Log
- 2026-10-30 M0_none rerun to 0.305 s: QUASI-STEADY by 0.1 s (0.105-0.305 s identical): top 292.06, bottom 274.45, bottom/top 0.9397, c_OH mouth 494.2 bottom 380.3, c_SIL bottom 82.7, c_H2 bottom 90.8 mM. vs 1D (mouth 503): OH drop 114 vs 85, H2 rise 46 vs 41 (ok), but silicate rise 19 vs 78 mM (4x too small). Hand estimate with zero TMA flux gives grad SIL/grad OH ~ 0.9, as the 1D has; 2D has ~0.17. Neutral H2 agrees, ions do not -> suspect the electromigration term in face_source. check_2d.py rebuilds the Nernst-Planck fluxes from the dump and compares them with the poly-Si consumption below each depth.
- 2026-10-30 M0_none full run (0.155 s): top 292.06, bottom 274.45 nm/min, bottom/top 0.9397, c_OH bottom  380.3 (1D: 293.57 / 281.09 / 0.9575 / OH min 418.5). OH drop along slit 40 % larger than 1D; quasi-steady  not checked (no report between 5 ms and 155 ms). Phase B extended to 0.305 s, reports every 50 ms with  c_OH mouth, c_SIL and c_H2 bottom (1D: mouth 503, SIL max 142 mM, H2 122x sat). Rerun M0_none --force.
- 2026-10-30: --discover ran on Puma, discover.txt read. Fluent 2024R1 paths coded in api.py (f5af647):
  no `setup.user_defined` (UDM/UDS count via TUI `/define/user-defined/...`); material is default `air`
  (properties overwritten); `uds_diffusivity.option` only 'defined-per-uds', then per
  `uds_diffusivities['uds-i']`; cell sources `source_terms.sources` + `source_terms.source_terms[eq]`;
  BC keys `uds.uds_bc['User Scalar i']` ('Specified Value') and `uds.uds['User Scalar i'].value`.
  Whether the UDF compile + UDS TUI steps succeeded is not yet confirmed (job log not seen).
- 2026-10-30: UDF compile fixed and confirmed on Puma (job 24474930, libudf.so linked): etch_params.h is
  inlined into etch.c (6022e1b; Fluent copies only listed files to libudf/src) and DEFINE_SOURCE bodies
  moved off the macro line (57094dd; udf_names.c generator copies the rest of that line). UDS TUI prints
  "You must select one of the solution zones!" but ends with "Solution zones:(2 3)" for all 3 scalars;
  etch.c now prints "HOOK <flux|diffusivity|source> uds-i active" on first call to prove each hookup.
- 2026-10-30 smoke tests (A_f1_I2_t45 --setup-only): mesh, UDM, compile/load, 3 UDS, early init all ok.
  uds-0 diffusivity: option 'user-defined' is allowed, but then `user_defined_function` reported "not
  active"; writing {"option","user_defined_function"} together SIGSEGV'd host + all nodes (Fluent itself,
  not our UDF). 2eeeb25: set option alone, log state + active children, write only an active child.
  Result: after option 'user-defined' ALL children inactive (24.1 settings bug). Decision: molecular rho D_i
  as constant per-UDS diffusivity; D_osc mixing moved into the source UDF as an implicit two-point face
  flux (dosc_source, docs/formulation.md); sources now in all fluid zones incl. bulk; D_osc averaging
  loops cover exterior cells so partitions agree. uds_diff removed.
- 2026-10-30 smoke test (job 24475471, abefc56): FULL SETUP WORKS. Diffusivities, sources in bulk+slit,
  inlet/top velocities, UDS values on inlet/top/outlet, init, patch, init_poly_area (1000 faces, 10 um as
  expected), phase A iterating and converging. HOOK source on all 4 nodes, but NO "HOOK flux": the UDS TUI
  never attached uds_flux, so electromigration was off. Fix: migration moved into face_source (same
  face loop as D_osc, central, conservative); uds_flux is now plain convection (no double count if it attaches).
- 2026-10-30 smoke test PASSED end to end (job 24475531, 9d31c10): phase A + B, dump/report, case written.
  HOOK source uds-0/1/2 on all 4 nodes. After only 0.0022 s (2 steps per stage, not quasi-steady):
  top 295.1 nm/min (1D 294.6), bottom 293.3, bottom/top 0.994 falling with time (1D 0.954).
  REPORT_OSC (45 deg, 1 MHz, 2 W/cm2, only 4 averaging steps so undersampled): D_osc_max 2.4e-10 m2/s
  = 2 % of D_OH 1.12e-8; mean speed max 0.124 m/s. Outlet has a benign recirculation (20 faces reversed).
  Next: full M0_none, compare bottom/top with 1D 0.954.
- 2026-10-31: first --discover job (24474108) failed before Fluent: no scipy in ~/venvs/pyfluent241.
  Fixed (c115fef): 1D mouth concentrations precomputed into cases.csv by make_cases.py. gcc 11.5 on nodes.

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
