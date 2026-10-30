# Project 1 status log (newest first)

Megasonic-assisted TMAH wet etching of poly-Si, 100 nm x 10 um slit (AR 100), alternating SiO2/poly-Si
50/50 nm, single-wafer spin tool with MegPie transducer. Formulas and sources: `docs/formulation.md`.

## Next step
- Puma: `cd ~/project1 && git pull && bash submit_cases.sh A_f1_I2_t45 --setup-only` (smoke test);
  send the log (`tail -n 100` per file; plain `tail -80` fails with two files) and fix what breaks.
- Then all 16 cases (`bash submit_cases.sh .`), then `analyze_2d.py`.

## Log
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
