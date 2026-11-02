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
| Fluent snapshots | B0_ / B_f1_I2_ / BA_f1_I2_t15_ floor_l3000, _l6000 (fixed 3 and 6 um plugs) | pending |
