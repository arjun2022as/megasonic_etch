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
| Status | B0_* (no sound) valid; **B_f1_I2_* (with sound) unreliable in 2D** | 1D: real gain ≈ 1–2 % less non-uniformity |

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
| Status | first run had two bugs (H₂ pinned by a zone-id clash; suspected OMEGA name clash); **rerun pending** | first look: bottom/top 0.9571–0.9574 vs 0.9576 |
