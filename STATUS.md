# Project 1 status log (newest first)

Megasonic-assisted TMAH wet etching of poly-Si, 100 nm x 10 um slit (AR 100), alternating SiO2/poly-Si
50/50 nm, single-wafer spin tool with MegPie transducer. Formulas and sources: `docs/formulation.md`.

## Next steps (agreed with user 2026-10-30, in this order)
| # | Step | Check |
|---|---|---|
| 1 | Full `M0_none` (no megasonics), `bash submit_cases.sh M0_none` | bottom/top ~ 0.954 (1D) |
| 2 | `make_contours.py <cases>`: slit + mouth maps (OH-, silicate, H2/sat, speed, D_osc) and depth profiles; needs field_*.csv from dump_field (runs after 2026-10-31) | PNGs in results/<case>/plots |
| 3 | FLAT WAFER first (normal incidence, how tools normally run): frequency 1/2/3 MHz x power 0.5/1/2 W/cm2 at 90 deg | case-by-case results |
| 4 | Then the ANGLE cases (A_*, F_*, P_* at 45 deg, R_*), then V_* checks | every case `done:` |
| 4b | NEXT after the angle cases (user 2026-11-01): bubble-free window - conditions keeping H2 < 13.9x saturation everywhere (1D sweep of temperature, concentration, spin/flow, depth, pitch, gas, additives; then Fluent) | max H2/sat < 13.9 |
| 5 | `analyze_2d.py` figures + verification.md; FINAL comparison contours of every condition: `python make_contours.py --all` (maps_<q>_<view>.png one colour scale, diff_<q>_<view>.png vs M0_none, profiles.png) | results/compare |

Step 3 caveat: in the current model 90 deg gives u_t = 0, so A_f1_I2_t90 is IDENTICAL to M0_none (same
c_surf, same 1D 0.9575). A normal-incidence mechanism must be added first (candidates: acoustic
(Eckart) streaming thinning the wafer boundary layer -> mouth concentrations; compressional "breathing"
of the slit, xi = L|1+R|p0/(rho c^2), already in etchsim/acoustics.py), then flat-wafer cases added.
Every figure/summary: imposed oscillating flow + modelled mixing, NOT a full acoustic-streaming solution.

- 2026-11-01 BA runs FAILED to compile: the new PLUG report string had a literal newline (patch-script escaping). Fixed; every etch.c line now checked for balanced quotes before pushing. Resubmit BA.
- 2026-11-01 BA cases added (user: see how megasonics changes bubble growth): 1 um floor plug + 1 MHz 2 W/cm2 at 60/45/15 deg (phase A oscillation + plug pumping), mouth supply from the matching A case; compare with B0_floor (no sound) and B_f1_I2_floor (90 deg). UDF report now prints PLUG H2_in [mol/s/m] and growth [um/s] (RHO_GAS_PLUG = 507 mol/m3). Rectified diffusion (pulsation pumping gas into the plug) is NOT in Fluent (fixed plug): to be added as an analytic growth correction in the bubble-free study.
- 2026-11-01 ANGLE CASES (A t75..t15) done: bottom/top 0.9571-0.9574 (M0 0.9576), top rates +1..+2.6 nm/min (mouth refreshed, slit unchanged). check_2d A_f1_I2_t45 found 2 problems: (1) H2 pinned at 9.709 (= C_H2_BUB) in the whole slit: Fluent gave an interior face zone id 12 in a mesh without a plug, so init_poly_area treated it as the plug -> now requires a boundary thread and BUB_TOP > 0; (2) OH D_eff ~3 % high, N_TMA -6e-3, same signature as the B_f1 cases; common factor with B_f1 and not with M0/B0 is OMEGA != 1 -> suspected name clash of OMEGA with a Fluent macro; renamed OMEGA_AC. Rerun A_* and B_f1_* (11 cases).
## Log
- 2026-11-01 Pumping values in the B_f1 run are exactly as intended (etch.c defines, summary.json). B_f1 vs B0 headers differ only in DPUMP_* and OMEGA (unused in phase B). 1D with the 2D closure (pump in diffusion + S, not Q/drift): gain +0.0004 (bottom +0.12 nm/min); 2D +0.0025, and 2D raises OH (+4.8 mM) while silicate barely moves (-0.4), unlike 1D. => 2D B_f1_I2_* results UNRELIABLE (bug in how the UDF applies pumping; cause not found). Physical estimate: pumping cuts non-uniformity ~1-2 %. Deferred: cell-residual check of the 2D solution from field_*.csv. Moving on to the angle cases A_f1_I2_t75..t15.
- 2026-11-01 B0_floor check CLEAN (OH 1.124e-8, N_TMA ~1e-7) -> the error is in the PUMPING cases only. Independent 1D route (Slit L = 9 um, per-species D + pump, mouth = 2D values; run locally via uv, numpy/scipy cached on E:): B0_floor U 0.9651 (2D 0.9650), pumping gain +0.0007 (2D +0.0025); 1D with all pumps x3.5 gives +0.0023 -> 2D acts as if pumping ~3.5x too strong. Gain comes almost entirely from SILICATE pumping (via the field), OH pumping alone +0.00002. Corrected statement: floor-plug stable cavitation cuts non-uniformity by ~2 %, not 7 %. Next: compare DPUMP in results/B_f1_I2_floor/etch.c and summary.json with expected (1.717e-11, 6.114e-11, 1.998e-11, 5.590e-11).
- 2026-11-01 check after both fixes: B_f1_I2_floor and B_f1_I2_mid still show OH D_eff ~1.165e-8 (3.5 % above D + D_pump) and N_TMA -2e-3..-5e-4, nearly independent of the pump strength (1.7e-11 vs 5.5e-11) -> probably not the pumping; need check_2d on B0_floor to separate. No NaN in B_f1_I2_mid fields: the blank panel was a plotting bug (the case holding the global maximum sat exactly on the top contour level); fixed in make_contours.
- 2026-11-01 Bubble growth estimate: floor-plug H2 profiles fall monotonically to the plug, so it absorbs all slit H2 (~8.2e-9 mol/s/m) -> grows ~160 um/s at 507 mol/m3 gas; fixed 0.2/1 um plugs are snapshots. Hypothesis: grow-vent-refill cycle (self-breathing slit). Possible next model: time-dependent bubble cycle (1D first).
- 2026-11-01 B cases RERUN with both fixes (plots reviewed): H2 uptake works (sealed liquid at 13.9x, max anywhere 123x in M0). Sealed liquid below mid/mouth plugs: OH 0, silicate ~318 mM (= 64 + 503/2, stoichiometry closes). Floor plug is an H2 SINK: slit H2 falls from ~130x (M0) to <= ~64x at the mouth and 13.9x at the plug (the real plug would grow: not modelled). Pumping gain survives the zero-current fix: bottom/top B0_floor 0.9650 -> B_f1_I2_floor 0.9675 (NU 3.50 -> 3.25 %, -7 %), l200 0.9587 -> 0.9614 (-6.5 %). Conclusion at 90 deg: without a bubble megasonics does nothing in this model; a floor bubble + stable cavitation gives a small real gain; sealing bubbles dominate (nothing etches below them).
- 2026-11-01 H2 UPTAKE at the plug (user OK): first B runs had the sealed liquid below mid/mouth plugs at ~740x saturation (plug = no-flux wall). Now the meniscus holds H2 at 9.7 mM (13.9x, Henry at 1.41 MPa) via a cell source next to the bubble faces (UDM 9, user_memory 10); OH/SIL still blocked; plug size fixed (ASSUMED). check_2d skips the H2 balance for plug cases. Small (sub-width) bubbles: r* ~10 nm at S = 130, grow to a plug in ~1 us -> not modelled separately. Rerun ALL 12 B cases.
- 2026-11-01 12 BUBBLE CASES done. B0_floor 292.71/282.45 (0.9650, 10 dry layers), B_f1_I2_floor 292.80/283.24 (0.9673); B0_floor_l200 292.58/280.51 (0.9587), B_f1_I2_floor_l200 292.66/281.32 (0.9613); all mid/mouth plugs: everything below the plug stops (bottom 0, sealed liquid holds OH for only ~0.15 nm of etch), sound or not. check_2d on B_f1_I2_floor: SIL D_eff 2.02e-9 = D + D_pump (ok) but OH D_eff 4 % high and N_TMA -3e-3: per-ion pumping dispersion carried current. FIX: zero-current field now includes D_pump of OH, SIL and TMA (DPUMP_TMA added). Rerun the 6 B_f1_I2_* cases (B0 and M0 unaffected); post.slurm (checks + make_contours --all) as a job.
- 2026-11-01 +6 bubble cases with a 200 nm (nucleus-sized) plug: B0_/B_f1_I2_ floor_l200 (top 9.8 um), mid_l200 (5 um), mouth_l200 (1 um); 2 dry layers (980 poly faces). DPUMP_OH 1.4e-11 / 4.8e-11 / 2.8e-10 (stiffer short plug pumps less near the mouth: 2.5 % vs 11 % of D_OH). 2D caveat: a plug is a gas sheet along the whole trench length (seals the slit); right for holes, worst case for long slits.
- 2026-11-01 FLUENT BUBBLE CASES built (user OK): mesh2d --bubble-top/--bubble-len cuts a 1 um H2 plug out of the slit (wall zone "bubble", poly-Si under it dry; mesh checks pass: 26400 cells, 900 poly faces); params adds pump D per species from etchsim/cavitation.py (BUB_TOP, DPUMP_* in the header); etch.c face_source adds D_pump on axial slit faces between the mouth and the plug (in_pump); metrics report dry layers; check_2d.py checks only the liquid above the plug and includes D_pump; make_contours masks the plug. cases.csv +6: B0_floor/mid/mouth (plug, no sound), B_f1_I2_floor/mid/mouth (+1 MHz 2 W/cm2, 90 deg). DPUMP_OH = 1.7e-11 / 5.5e-11 / 1.2e-9 m2/s (floor/mid/mouth). Header change is inert for the other cases (all new defines 0).
- 2026-11-01 STABLE CAVITATION (user: at 90 deg the sound acts through cavitation, not streaming). etchsim/cavitation.py + tests/test_cavitation.py (6 checks pass locally: Python 3.14 via uv exists on the laptop) + run_cavitation.py -> results_1d/cavitation_table.csv. Trapped H2 bubble pulsates (stable, overdamped, p_a 229-458 kPa < p_gas 1.41 MPa) and pumps the column above it; Taylor-Aris dispersion: bubble at the floor -> OH 0.03-0.15 %, silicate 0.2-3 % of own D (negligible for etch); mid-depth OH <= 0.5 %; near the mouth OH up to 11 %, silicate up to 220 % but the liquid below is sealed. 1 MHz > 3 MHz, ~ power. Next (needs user OK): Fluent bubble cases (void in mesh + per-species pumping dispersion) B0 (bubble, no sound) vs B (bubble + sound) at floor / mid / near mouth.
- 2026-10-31 first M0_none plots (make_contours.py): profiles smooth (ER 293 -> 280 nm/min; OH 495 -> 412, SIL 69 -> 146 mM, H2 73 -> 131x sat), slit colours vary only with depth (1D picture valid), slit liquid stagnant (< 1e-9 m/s below ~0.3 um; spin flow ~1e-3 m/s at 1 um above the wafer), OH halo of ~0.25 um radius above the mouth and silicate/H2 plume out of it; wafer-level OH already ~497 at 1 um height (supply 503). Cosmetic: speed map shows noise below 1e-10 m/s; jagged wall edges from the triangulation mask.
- 2026-10-31 M0_none FINAL (job 24478676): top 292.41, bottom 280.01 nm/min, bottom/top 0.95758 vs 1D 0.95749 (agree to 0.01 %); both rates 0.4 % below 1D because the 2D mouth OH is 495 vs 503 ((495/503)^0.25 = 0.996). Recess after 2 min: 584.8 vs 560.0 nm (24.8 nm). VALID BASELINE. Step 2 started: dump_field UDF (whole-field CSV at the end of each run) + make_contours.py (slit and mouth maps, depth profiles, multi-case comparison; matplotlib).
- 2026-10-31 job 24478676 (95ac443): check_2d.py PASSES. D_eff = intended within 1 % at all interior depths (OH 1.124e-8, SIL 1.96e-9, H2 9.6e-9), N_TMA ~1e-6 (was 0.08), E_eff OH = E_eff SIL (one consistent field). Profile mouth->bottom: OH 495 -> 412 (1D 503 -> 418.5), SIL 69 -> 146 (1D max 142), H2 51 -> 91.6 mM (131x sat). 2D mouth is 8 mM below the 1D mouth value (2 um bulk layer above the slit). Expected bottom/top ~0.955 (from (412/495)^0.25); confirm with the done: line. M0_none = VALID baseline.
- 2026-10-31 job 24478379 (M0_none with d2b0bd5): c_OH 503.1 and c_H2 44.5 FROZEN for 0.3 s, bottom/top 1.0000, silicate D still D_H2. Two causes: (1) the run_case.py edit never saved, so Fluent still got (D_OH, D_SIL, D_H2) and used D_H2 for all; (2) the positive explicit remainder (D_i - D_SIL, up to 4.7x Fluent's implicit D) made OH/H2 Jacobi-slow: each iteration moved c_OH ~1e-4 mM. Fix: all UDS get rho*D_OH (largest) in Fluent, remainder D_i - D_OH <= 0 as deferred correction (no diag). Rerun M0_none.
- 2026-10-30 check_2d.py after the D_BASE fix (job state not yet confirmed): c_OH flat 503.0 and c_H2 flat 44.5 at every depth (= mouth values, no depletion at all), c_SIL 67 -> 88.5, silicate D_eff still 9.6e-9 (should be 1.96e-9). Not a valid steady state; need the job log (still running? crashed? stale header?). Living request document for the user: docs/make_inputs_doc.js -> Downloads/Project1_Inputs_Needed.docx (keep VERSION and the received log current).
- 2026-10-30 check_2d.py on M0_none: H2 balances (<1 %), OH/SIL off 36/68 %, implied TMA flux != 0. Effective D of ALL three species = 9.59e-9 = D_H2 (log shows per-UDS values 1.105e-5/1.928e-6/9.432e-6 set, but 24.1 uses the last one for every UDS). FIX: every UDS gets rho D_BASE (D_SIL) in Fluent, face_source adds rho (D_i - D_BASE) as a two-point flux. M0_none result above is INVALID; rerun.
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
