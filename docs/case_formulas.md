# Formulas and principles used in each case set

One table per case set, added when the set is finished. Details, sources and checks: `docs/formulation.md`.
Megasonics in this model = imposed oscillating flow and modelled mixing, not a full acoustic-streaming solution.

## 1. M0_none: baseline (used by every case)

| What | Formula / principle | Notes |
|---|---|---|
| Bulk etchant | C_OH = w ρ / M = 0.05 × 990 / 0.09115 = 543 mM | 5 wt% TMAH, ASSUMED |
| Liquid flow | Steady laminar, incompressible Navier–Stokes; Couette shear above the wafer u = G y, G = Ω r / gap = 785 s⁻¹ | 300 rpm, r = 50 mm, gap 2 mm (ASSUMED) |
| Diffusivities | Nernst–Einstein D = RTλ / (z²F²) at 25 °C; Stokes–Einstein D(T) = D₂₅ (T/298)(μ₂₅/μ) | OH⁻ 1.12, TMA⁺ 0.26, silicate 0.20, H₂ 0.96 (×10⁻⁸ m²/s, 60 °C) |
| Transport of ions | Nernst–Planck with zero current: N_i = −D_i ∇c_i + z_i D_i c_i S/Q, S = Σ z_j D_j ∇c_j, Q = Σ z_j² D_j c_j | electroneutrality c_TMA = c_OH + 2 c_SIL |
| Reaction | Si + 2 OH⁻ + 2 H₂O → SiO₂(OH)₂²⁻ + 2 H₂ | on poly-Si walls only; oxide inert |
| Rate law | r = K_Si (c_OH / C_bulk)^¼ · c/(c + εC_bulk), K_Si = ER_ref ρ_Si / M_Si | ER_ref = 300 nm/min, order ¼ (ASSUMED) |
| Source in a wall cell | S_i = ν_i r (wall length / cell area), ν = (−2, +1, +2) | OH⁻, silicate, H₂ |
| Etch rate and recess | ER = r M_Si / ρ_Si; recess = ER × t (quasi-steady) | |
| Mouth supply | From the 1D wafer-level model: spin-film mass transfer (Levich k_m) | OH⁻ 503, silicate 64, H₂ 44 mM |
| Time | 0.305 s with steps growing 0.1 µs → 1 ms; quasi-steady when unchanged between 50 ms reports | L²/D: OH⁻ 9 ms, silicate 51 ms |
| Fluent 24.1 workarounds | all species get D_OH in Fluent; D_i − D_OH (≤ 0) and migration added as face fluxes in the UDF (deferred correction) | |
| Checks | flux balance vs poly-Si consumption (check_2d.py); 1D model; stoichiometry | bottom/top 0.95758 vs 1D 0.95749 |
| Result metrics | bottom/top = ER_bottom / ER_top; non-uniformity 1 − U; recess difference (nm) | |

## 2. B cases: H₂ bubble (gas plug) in the slit, flat wafer (90°)

Everything in table 1, plus:

| What | Formula / principle | Notes |
|---|---|---|
| Bubble shape | Plug filling the 100 nm width, 1 µm or 200 nm long; poly-Si under it dry | cut out of the mesh; 2D = sheet along the trench (worst case for slits) |
| Gas pressure in the plug | Laplace: p_g = p_atm + 2γ/W − p_vap = 1.41 MPa | γ = 0.0662 N/m (ASSUMED for TMAH) |
| Bubble threshold | grows if c_H₂/c_sat > p_g/p_atm = 13.9 | below 13.9× it dissolves |
| H₂ uptake at the plug | Henry's law: c* = c_sat p_g/p_atm = 9.7 mM; sink −D_H₂ (c − c*) A/(dV) | OH⁻, silicate cannot cross; plug size fixed (ASSUMED) |
| Smallest growing seed | r* = 2γ / ((S − 1) p_atm) ≈ 10 nm at S = 130 | seeds become plugs in ~1 µs |
| Sound pressure at the wafer | p_a = |1 + R| √(2ρcI) = 229 / 324 / 458 kPa at 0.5 / 1 / 2 W/cm² | stable cavitation: p_a < p_g |
| Bubble pumping (lumped column) | p_a = (R + i(ωM − K/ω)) Q, R = 12μz/W³, M = ρz/W, K = κ p_g/(W l_b) | overdamped (ratio 7–30); viscous-limited when deep |
| Mixing from pumping | Taylor–Aris oscillatory dispersion: iωg − D g'' = −u′(x), D_pump = −½ Re⟨u′ g*⟩; slow limit ½·(2/105) U² h²/D | per species, ~1/D: silicate gains most |
| Zero current with pumping | S = Σ z_i (D_i + D_pump,i) ∇c_i | dispersion does not conduct (Q unchanged) |
| Status | B0_* (no sound) valid; B_f1_I2_* (with sound) had NOT settled at 0.305 s (0.9730 → 0.9675 and still falling): the apparent gain was a transient. Runs now continue until settled; rerun pending | 1D: real gain ≈ +0.0004 in bottom/top |

## 3. A cases: angle of incidence, 1 MHz, 2 W/cm², no bubble

Everything in table 1, plus:

| What | Formula / principle | Notes |
|---|---|---|
| Plane sound wave | p₀ = √(2ρcI), U₀ = p₀/(ρc) = 0.16 m/s at 2 W/cm² | c = 1551 m/s |
| Reflection from the Si wafer | Brekhovskikh fluid / elastic solid: R = (Z_L cos²2γ_S + Z_S sin²2γ_S − Z_f)/(… + Z_f), Snell's law for γ_L, γ_S | \|R\| → 1 beyond the critical angles |
| Sideways (tangential) speed | u_t = U₀ sin β \|1 + R\|, β = 90° − θ | 0 at 90°, 0.08–0.31 m/s at 75°–15° |
| Sticky (Stokes) layer | δ = √(2ν/ω) = 0.39 µm at 1 MHz | liquid speed 0 at the wafer |
| Imposed oscillating flow | u(y,t) = G y + u_t [cos ωt − e^(−y/δ) cos(ωt − y/δ)], v = 0 | on the inlet and top boundaries |
| Speed at the slit mouth | u_mouth = u_t \|1 − e^(−(1+i)(W/2)/δ)\| | 14–53 mm/s |
| Inside the slit | Womersley (W/2)√(ω/ν) ≈ 0.18 → quasi-steady Stokes flow, decays like e^(−4.21 z/W) | fades within a few nm |
| Mixing coefficient | D_osc = (var u + var v)/ω = \|u₁\|²/(2ω) (upper bound), same for every species | from 10 averaged cycles |
| Time, phase A | Δt = 1/(40 f) = 25 ns; 8 settle + 10 averaged cycles | then phase B as in table 1 |
| Mouth supply | 1D wafer-level model with the extra megasonic mixing | higher mouth OH⁻ than M0 |
| Results (rerun, 2026-11-01) | bottom/top t75 0.95718, t60 0.95713, t45 0.95725, t30 0.95740, t15 0.95738 (M0 0.95758); top rate 293.3–295.0 nm/min (M0 292.4) | faster overall, uniformity unchanged |
| Status | H₂ zone-id bug fixed (H₂ now rises with depth); OMEGA rename changed nothing. Settled (history flat), but the cell balance (residual_2d.py) still shows OH⁻ −6…−11 % and H₂ +4…+8 % off in A_t45, silicate exact: **small steady error, cause open** | conclusion (no uniformity gain) not affected |
| Comb walls (case 3, 2026-11-03) | poly-Si recessed R = 300 nm into 50 nm pockets (ASSUMED uniform R); settle test incl. silicate passed, no warnings | R_none_r300 + R/A_f1_I2_t75…t15_r300 |
| Comb result, no bubble | bottom/top none 0.96021, t75 0.95989, t60 0.95986, t45 0.95968, t30 0.95967, t15 0.95961 | angles give no uniformity gain on comb walls either (≤ −0.0006) |
| Comb result, floor plug 1 µm | growth = H₂_in/(ρ_g W): none 147.7, 90° 147.9, 60° 137.0, 45° 128.5, 15° 118.3 µm/s | 3 % above flat walls (143/133/125/115); same −20 % from 90° to 15° |
| Comb flux check (check_2d.py) | slit-centre flux vs consumption below: 4–6 % low mid-slit, 20 % in the last row; same for OH⁻, silicate and H₂, alternating with layer parity | geometric: in a comb part of the downward flux runs through the pockets, which a centre-line check does not see; not the migration term |
| **Case 3 status** | **COMPLETE (2026-11-03)** | conclusion: incidence angle does not change in-slit uniformity, flat or comb |

## 4. Growing H2 plug: nucleate -> grow -> vent -> refill (1D, etchsim/plug.py)

Everything in tables 1 and 2 (plug pressure, Henry uptake, pumping), plus:

| What | Formula / principle | Notes |
|---|---|---|
| Time-dependent transport | dc_i/dt = -dN_i/dz + nu_i r 2 f_poly / W, implicit Euler, 10 nm cells | same Nernst-Planck / zero current as the 1D slit |
| Plug growth | db/dt = -N_H2(b) / rho_g, rho_g = p_g/(RT) = 507 mol/m3 | N_H2 < 0 (dissolving) shrinks it |
| Displaced liquid | the column above moves out of the mouth at \|db/dt\| (plug flow), semi-Lagrangian shift each step | not in the fixed-plug Fluent cases |
| Nucleation | when max c_H2 > s_nuc c_sat: plug of 100 nm on the floor | s_nuc unknown: 13.9 / 27 / 70 / 100 / inf swept (ASSUMED floor) |
| Seed size vs threshold | S = 1 + 2 gamma/(r p_atm): 27x for a 50 nm sphere; 13.9x = plug-sized pocket already there | |
| Venting and refill | plug top within 100 nm of the mouth -> gas leaves; slit refills with mouth liquid (Washburn ~20 us, instant) | ASSUMED |
| Mouth | concentrations fixed from cases.csv (M0 or matching A case) | slit breathing does not change the wafer film (ASSUMED) |
| Sound | plug pumping D_pump(b, l_b) from cavitation.py every step; tilt via the A-case mouth values | rectified diffusion NOT yet included |
| Checks | fixed 1 um plug: intake = Fluent within 0.3-1.5 %; no reaction: N = D (c_mouth - c*)/b; H2 made = into plug + out of mouth | tests/test_plug.py |
| Results (0.3 s) | s_nuc 13.9/27: cycle 49 ms (none) .. 68 ms (15 deg), bottom 3-4 nm/min (0.01 of top); s_nuc 100: bottom 29 .. 55 nm/min; no bubbles: 281.5, max H2 122x (none) .. 102x (15 deg) | nucleation threshold is the key unknown |
| Fluent snapshots (flat) | B0_ / B_f1_I2_ / BA_f1_I2_t15_ floor_l3000, _l6000: growth none 145 / 175, 90 deg 146 / 176, 15 deg 111 / 129 um/s | 1D fixed-mouth within 3 % except 6 um no sound (+12 %: 2D drains the liquid above the mouth) |
| Realistic tool | flat MegPie 90 deg, 1 MHz, 1-2 W/cm2, sound on 33 of every 200 ms (300 rpm, 60 deg sector, ASSUMED) | run_realistic.py |
| Rectified diffusion (plug) | mean of p0/(1 + eps cos wt) = p0/sqrt(1 - eps^2), eps = dV/V; no area or shell effect for a plug | raises c* ~1e-4: slightly less intake |
| Early venting | vent when the meniscus swing xi (cavitation.pumping) reaches the mouth | xi ~10 nm deep, 90-450 nm near the mouth |
| Realistic result | all sound settings within 1 % of no sound (cycle 48-49 ms, bottom 3.0 nm/min at 13.9x; 29 nm/min at 100x) | the tool does not change the bubble cycle |
| Comb walls, sealed pockets | beside a plug each pocket etches on stored etchant: dc/dt = -2 r(c)/R; with r = K (c/C)^(1/4): c^(3/4) = c0^(3/4) - (3/4) 2K t/(R C^(1/4)) | 300 nm pocket empties in 247 ms (> 48 ms cycle); RK4 check |
| Pocket H2 | 2 r/R per pocket volume, all into the plug through the pocket mouth | cycle 49 -> 37 ms |
| Comb result | bottom 3 / 22 / 44 / 90 / 232 / 269 / 286 / 290 nm/min at R = 0 / 5 / 10 / 20 / 50 / 100 / 300 / 600 nm | refill tops pockets up with 503 mM liquid (ASSUMED instant) |
| Start-up delay | dR_bottom/dt = ER(R): from R0 = 0, 2, 5, 10, 20 nm -> 315 / 408 / 459 / 499 / 534 nm in 2 min (top 588, bubble-free 562) | uniform R along the slit ASSUMED |
| Fluent comb + plug | sealed pockets left out of the mesh (Fluent 24.1 mishandles closed liquid islands) | rerun 2026-11-03, settled |
| Comb snapshots vs 1D | growth µm/s, Fluent / 1D: 1 µm plug none 147.7/143.3, 90° 147.9/143.4, 15° 118.3/113.5; 3 µm none 151.0/149.2, 90° 151.3/149.6, 15° 115.2/111.0; 6 µm none 183.4/196.4, 90° 184.7/198.1, 15° 136.7/130.0 | agree within 1–5 %; 1D 7 % high only at 6 µm, no sound/90° (12 % on flat walls) |
| **Case 4 status** | **COMPLETE (2026-11-03)** | growth 115–185 µm/s for every plug length, angle and wall shape: the plug always fills the slit within ~50–60 ms |

## 5. Side view: finite bubbles along the trench (etchsim/sideview.py)

Everything in tables 1, 2 and 4, plus:

| What | Formula / principle | Notes |
|---|---|---|
| Domain | depth z (0..10 um) x trench length y (0..s/2), width-averaged; 100 nm x 200 nm cells | symmetry: half the spacing s between bubble sites |
| Transport | dc/dt = -div N + nu r 2 f_poly/W, Nernst-Planck + zero current on z and y faces, implicit Euler | poly smeared f = 1/2 (bottom/top -0.003 vs layered) |
| Bubble shape | half disc of radius R_b on the floor, fills the width; cells inside are gas, dry | pancake squeezed between the walls (ASSUMED isotropic growth) |
| Bubble surface | OH-, silicate no flux; H2 at c* = 9.7 mM (13.9x) | as in Fluent |
| Growth | dA/dt = (sum of H2 into the bubble per unit width) / rho_g; R_b from A (clipped by the domain) | R_b > s/2: neighbours merge into a sheet |
| Nucleation, venting | one site per s on the floor when max H2 > s_nuc c_sat; vent when the top is within 200 nm of the mouth; refill with mouth liquid | ASSUMED |
| Comb | front concentrations from pocket.front (recess R) | changes nothing measurable |
| Not included | displaced-liquid flow (Pe ~0.15), pumping, rectified diffusion, meniscus pinning | |
| Checks | no bubble = 1D slit (4e-7); bubble wider than the domain = 1D plug intake (exact) | tests/test_sideview.py |
| Results (13.9x) | sites 5 / 10 / 20 / 40 um: floor covered 91 / 81 / 55 / 26 %, bottom 24 / 53 / 128 / 211 nm/min (no bubbles 282) | spacing of bubble sites is the new key unknown |

## 6. Case 5 (user numbering): sub-plug H2 bubbles (etchsim/nanobubble.py)

Case numbering used with the user: 1 = M0 (table 1), 2 = fixed plugs (table 2), 3 = angles (table 3), 4 = growing
plug and side view (tables 4, 5), 5 = this table, 6 = bubble-free window (next).

| What | Formula / principle | Notes |
|---|---|---|
| Free round bubble | S_eq(r) = (p_atm + 2 gamma/r - p_vap)/p_atm (Laplace + Henry) | unstable: grows to a plug or dissolves |
| Pinned surface nanobubble | footprint radius L fixed by roughness/edges; cap curvature R_c = 2 gamma/((S - 1) p_atm + p_vap); height h = R_c - sqrt(R_c^2 - L^2) | Lohse & Zhang, PRE 91, 031003 (2015) |
| Stays small while | R_c >= L, i.e. S <= S_max(L) = 1 + (2 gamma/L - p_vap)/p_atm | above: cap passes a hemisphere, depins, grows to a plug |
| 50 nm condition | S_max(50 nm) = 26.9x | the user's "cannot reach 50 nm radius" |
| Largest stable footprint | L_max(S) = R_c(S) | 21 nm at 63x (mouth), 11 nm at 122x (floor) |
| H2 profile | 1D slit without plugs, mouth from cases.csv | no sound = 90 deg (flat MegPie) |
| Results | footprint 10 nm: stays small everywhere; 15 nm: runs away below 2.4 um (no sound) / 5.2 um (15 deg); >= 30 nm: runs away almost everywhere; all < 50 nm radius needs 74-78 % less H2 at the floor | gamma, c_sat ASSUMED; outflux and hysteresis not included (conservative) |
| Checks | sphere of W/2 feels exactly twice the plug's Laplace pressure; cap pressure from its own geometry = liquid S; no balance above S_max | tests/test_nanobubble.py |
| Etch effect (run_nanobubble_etch.py) | caps cover a fraction phi of the poly wall where S <= S_max(L); rate, OH use and H2 made x (1 - phi) there; covered region solved self-consistently | phi swept 0/10/30 % (ASSUMED) |
| Etch result | footprint 10 nm (stays small everywhere): rate -10 / -30 %, bottom/top 0.9575 -> 0.9615 / 0.9696 (less H2 and OH demand); 15 nm at 15 deg with 30 % cover also stays small (H2 drops to 85x < 88x); larger footprints run away to plugs below 0.2-5 um -> case 4 | small caps slow the etch, do not hurt uniformity |

## 7. Case 6: bubble-free window and the two-step recipe (etchsim/window.py, run_case6.py)

1D, laptop. 6A: no-bubble H2 vs spin speed (150-3000 rpm), temperature (20-60 C), chamber pressure (1-5 atm).
6B: bubble cycle vs spin speed against 15 deg sound. 6C: gentle bubble-free pre-recess, then the full etch.

| What | Formula / principle | Notes |
|---|---|---|
| Bubble-start level | c_need(r) = c_sat(T) (p_amb + 2 gamma(T)/r_eff - p_vap(T)) / p_atm; r_eff = W (plug), 50 nm, 13.4 nm (round seeds) | 9.71 mM = 13.9x / 27x / 100x at 60 C, 1 atm |
| Chamber pressure | only adds (p_amb - p_atm)/p_atm saturations to every level; the H2 present does not change | 5 atm: plug level 13.9x -> 17.9x |
| Temperature | ER_ref Arrhenius Ea 0.57 eV; D Stokes-Einstein with mu(T) Vogel fit; gamma IAPWS; p_vap Antoine; c_sat = 0.70 mM exp(530 K (1/T - 1/333.15)) | c_sat slope (Sander) ASSUMED for TMAH |
| Wafer film | k_m = 0.62 D^(2/3) nu^(-1/6) Omega^(1/2) (Levich) at every spin speed | thin-film limits not modelled (ASSUMED) |
| H2 present | c_floor ~ c_mouth + r L^2/(W D), c_mouth = 2 r L/(pitch k_m): mouth and in-slit parts each ~60x at 60 C / 300 rpm | in-slit part is untouched by spin or sound |
| Window margin | c_need / c_max (> 1 bubble-free) | grid must tile the 50 nm layers (n = 400 or 1000) |
| 6A result | seeds (13.9x): bubble-free only at 20 C >= 300 rpm (20 nm/min) or 25 C >= 1500 rpm (29 nm/min); 50 nm seed: <= 30-35 C; 13 nm seed (100x): 60 C >= 1000 rpm (floor 93x) or 55 C at 300 rpm | perfect film at 60 C still leaves 59x |
| 6B result (bubbles on, 60 C) | bottom etch, seeds / 100x: 300 rpm 3.0 / 28.7; 15 deg sound 3.8 / 54.5; 600 rpm 3.8 / 49.5; 1000 rpm 4.1 / 283.6 (bubble-free); 3000 rpm 5.7 / 284.5 nm/min | 600 rpm = 15 deg; 1000 rpm >> 15 deg if seeds are few |
| Two-step recipe | step 1 bubble-free (25 C, 2000 rpm: 29.1 top / 28.8 bottom nm/min) for t1, then dR_bottom/dt = ER_bottom(R) at 60 C / 300 rpm with seeds | uniform recess, instant temperature switch ASSUMED |
| 6C result | top recess 500 nm: bottom/top 0.46 (no step 1, 102 s) -> 0.79 / 0.87 / 0.93 / 0.96 with t1 = 15 / 30 / 60 / 120 s (116 / 129 / 156 / 210 s total) | ER_bottom(R) 3 / 11 / 23 / 44 / 90 / 140 / 232 / 269 / 286 nm/min at R = 0-300 nm |
| Checks | water mu, gamma, p_vap, rho vs handbook at 25 / 60 C; levels 13.9x / 27x / 98.6x; floor vs hand formula (3 %); mouth ~ rpm^(-1/2) | tests/test_window.py |

## 8. Lever study: megasonics vs TMAH concentration vs dissolved gas (run_levers.py; 60 C, 300 rpm, 1D)

| What | Formula / principle | Notes |
|---|---|---|
| Megasonics summary | existing results only: Fluent case 3 (flat, comb), 1D sweep (summary.csv), case 4 cycle (plug_cycle.csv, realistic.csv), case 6B (600 rpm) | levers_megasonics.png |
| Megasonics result | no bubbles: bottom/top never above no sound (flat 0.95713-0.95740 vs 0.95758; comb 0.95961-0.95989 vs 0.96021; 1D 0.9539-0.9575). Bubbles, seeds / 100x: no sound 2.98 / 28.81, real MegPie 2.98 / 28.85, 90 deg continuous 3.02 / 29.17, 15 deg continuous 3.83 / 54.47, 600 rpm 3.8 / 49.5 nm/min | 15 deg needs a tilt a meniscus-coupled MegPie cannot make |
| Concentration rate law | ER_ref(w) = 300 nm/min ([H2O](w)/[H2O](5 %))^4 ([OH](w)/[OH](5 %))^(1/4); [H2O] = (1-w) rho/M_w, [OH] = w rho/M_TMAH, rho = 983.2 + 140 w | Seidel law ASSUMED for TMAH; peak ~7 wt%; 2/5/10/15/25 wt% -> 265/300/296/269/196 nm/min |
| Concentration result | no bubbles bottom/top 0.918 / 0.958 / 0.977 / 0.986 / 0.993 at 2/5/10/15/25 wt%; floor H2 101/121/123/113/83x; bubbles, seeds: 2.6-3.0 nm/min at all; few seeds: 42/29/29/32/194 nm/min (25 wt% bubble-free) | water H2 solubility ASSUMED: salting-out (k_s 0.05-0.1 L/mol) would raise 25 wt% floor to ~115-160x and may close the window |
| Dissolved gas | bubble gas holds p_other of N2/O2: c_need = c_sat (p_amb + 2 gamma/r - p_vap - p_other)/p_atm; plug surface c* lowered the same way | equilibrium with the bubble ASSUMED (upper bound) |
| Gas result | plug level 13.9 / 12.9 / 11.9x and 13 nm level 98.4 / 97.4 / 96.4x for degassed / ~1 atm / ~2 atm; bottom etch seeds 3.01 / 2.96 / 2.85, few seeds 28.7 / 29.1 / 24.3 nm/min | degassing matters only if it removes seeds (not modelled; experiment) |
| Checks | rate-law ratio vs hand calculation (25 vs 5 wt%); 1 atm of other gas = 1x c_sat less H2 needed; 5 wt% reproduces the baseline | tests/test_window.py |
