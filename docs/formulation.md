# Megasonic-assisted TMAH etching of poly-Si in a high-aspect-ratio slit: formulation

Project 1 of the UA proposal "Megasonics for Improved Wet Processing of Materials in High Aspect Ratio
Structures". Every formula below is implemented in `etchsim/` and checked a second time by an independent
route in `tests/test_formulas.py` (column "Check").

## 1. Conditions

| Item | Value | Source / status |
|---|---|---|
| Etchant | 5 wt% TMAH, 60 °C | chosen with the user (Micron conditions pending) |
| Feature | slit, W = 100 nm, depth L = 10 µm (AR 100) | user |
| Sidewall | alternating SiO₂ / poly-Si, 50 nm / 50 nm, oxide at the top; slit floor inert | ASSUMED thicknesses, top layer and floor |
| Tool | single-wafer spin tool + megasonic transducer (MegPie), 300 rpm, 1 L/min, r = 50 mm | proposal; rpm, flow, radius ASSUMED |
| Megasonics | 1, 2, 3 MHz; 0.5, 1, 2 W/cm²; incidence θ = 90° (MegPie, normal) and 60/45/30° | user / proposal |
| Slit pitch | 1 µm | ASSUMED (sets wafer-level consumption) |

## 2. Properties at 60 °C

| Quantity | Value | Source | Check |
|---|---|---|---|
| ρ, μ water | 983.2 kg/m³, 0.4665 mPa·s | IAPWS | – |
| c (sound) | 1551 m/s | water, 60 °C | – |
| c_bulk TMA⁺ = OH⁻ | 0.05·ρ_soln/M = 543 mol/m³ (ρ_soln 990 kg/m³ ASSUMED) | definition | by hand |
| D (25 °C) OH⁻, TMA⁺ | 5.273e-9, 1.196e-9 m²/s | CRC (Vanýsek), λ° = 198.0, 44.9 S cm²/mol | D = RTλ/(z²F²) recomputed |
| D (25 °C) SiO₂(OH)₂²⁻ | 0.92e-9 m²/s | ASSUMED ≈ CO₃²⁻ (published silicate conductivities inconsistent) | – |
| D (25 °C) H₂ | 4.5e-9 m²/s | Cussler, *Diffusion* | – |
| D(60 °C) | D₂₅ · (T/298.15) · (μ₂₅/μ₆₀) = ×2.13 (Stokes–Einstein) | standard | factor recomputed |
| H₂ solubility | 0.70 mol/m³ | ASSUMED (0.78 mM at 25 °C) | – |

Dilute-limit diffusivities are used at 0.54 M; activity and concentration corrections (~10–20 %) are neglected.

## 3. Chemistry

Overall reaction (Seidel et al., *J. Electrochem. Soc.* 137, 3612 (1990); same for TMAH):

  Si + 2 OH⁻ + 2 H₂O → SiO₂(OH)₂²⁻ + 2 H₂

Rate per unit poly-Si area: r = (ER_ref ρ_Si / M_Si) · (c_OH / c_bulk)ⁿ, with n = 1/4 (Seidel: rate ∝ [H₂O]⁴[OH⁻]^¼,
water nearly constant) and n = 1 as a sensitivity case. ER_ref = 300 nm/min at 5 wt%, 60 °C is ASSUMED from
Si(100) data spanning 148–734 nm/min over 5–25 wt% and 60–90 °C. **It is the main number to calibrate with
the proposal's SEM etch rates.** Temperature: Arrhenius, E_a = 0.57 eV (TMAH, Si(100), 28–80 °C). SiO₂ etches
at ~0.2 nm/min (selectivity > 1000) and is treated as inert. Etch velocity = r·M_Si/ρ_Si.
Numerical cut-off: below 10⁻⁶ c_bulk the rate goes smoothly to zero (factor c/(c + 10⁻⁶ c_bulk)).

## 4. Transport in the slit: diffusion + electromigration (Nernst–Planck)

Width averaging (1D in depth z) is justified because W²/D ≈ 10⁻⁶ s ≪ L²/D ≈ 10⁻² s; quasi-steady because
L²/D ≪ the minutes the etch front takes to move.

  N_i = −(D_i + D_osc) dc_i/dz + z_i D_i c_i (−F/RT) dφ/dz,  i ∈ {OH⁻, SiO₂(OH)₂²⁻, TMA⁺}; H₂ neutral.

- **Electroneutrality:** c_TMA = c_OH + 2 c_SIL. The Debye length at 0.54 M is about 0.4 nm, much smaller than W, so the double layer is not resolved.
- **Zero current:** Σ z_i N_i = 0. No external circuit, and the reaction consumes two negative charges and releases two, so it carries no charge. This gives the diffusion potential

  −(F/RT) dφ/dz = S/Q, S = Σ z_j D_j dc_j/dz, Q = Σ z_j² D_j c_j

  so ion i migrates with velocity z_i D_i S/Q.
- **D_osc:** megasonic mixing (§5). It is mechanical dispersion, equal for every species, and carries no current because Σ z_i c_i = 0.
- **Conservation:** dN_i/dz = ν_i r(c_OH) · 2 f_poly(z)/W, with ν = (−2, +1, +2) for (OH⁻, silicate, H₂) and f_poly = 1 in poly-Si layers.
- **Boundaries:** at the floor z = L, N_i = 0. At the mouth, c_i = c_i,bulk + J_i/k_i, where J_i is the slit flux spread over one pitch of wafer and k_i = 0.620 D_i^{2/3} ν^{-1/6} Ω^{1/2} (Levich, spinning wafer).
- **Order of magnitude:** depletion number φ² = 2r(2/W)f_poly L²/(D_OH c_bulk) = 0.14 with D_OH. Electromigration ties OH⁻ to the slower TMA⁺ (ambipolar D ≈ 4×10⁻⁹ m²/s), which raises it to about 0.4.

| Check | Result |
|---|---|
| First order, no migration, uniform wall | matches c = c₀ cosh(m(L−z))/cosh(mL), m² = 4k/(W D), within 0.2 % |
| Same physics by a different method (scipy `solve_bvp` on the (c, N) ODE system, with migration) | agrees within 0.3 % |
| Cation flux rebuilt from its own Nernst–Planck expression | ≈ 0, and the net current ≈ 0 (< 10⁻⁶ of the OH⁻ flux) |
| Stoichiometry at the mouth | silicate out = Si etched; OH⁻ in = H₂ out = 2 × Si etched |
| Grid 1000 vs 2000 cells | bottom/top ratio within 0.01 |

## 5. Megasonic field (linear acoustics, plane waves)

| Step | Formula | Check |
|---|---|---|
| Amplitude | p₀ = √(2ρcI), U₀ = p₀/(ρc); 1 W/cm² → 1.75×10⁵ Pa, 0.115 m/s | I = p₀²/(2ρc) round trip |
| Reflection at the Si wafer | R = (Z_L cos²2γ_S + Z_S sin²2γ_S − Z_f)/(… + Z_f) (Brekhovskikh, fluid/elastic solid), with Z_f = ρc/cos β, Z_L,S = ρ_s c_L,S / cos γ_L,S and Snell's law | normal incidence → (Z_Si − Z_w)/(Z_Si + Z_w) = 0.856; rigid wall → 1; \|R\| = 1 beyond the critical angles |
| Velocity outside the viscous layer | tangential u_t = U₀ sin β \|1 + R\|, normal u_n = U₀ cos β \|1 − R\|, β = 90° − θ | rigid limit → 2U₀ cos θ; normal incidence → u_t = 0 |
| Stokes layer | δ = √(2ν/ω): 0.39, 0.28, 0.22 µm at 1, 2, 3 MHz; u(y) = u_t \|1 − e^{−(1+i)y/δ}\| | limits y → 0 and y ≫ δ |
| In the slit | Womersley (W/2)√(ω/ν) = 0.13–0.23 < 1, so quasi-steady Stokes flow; it decays as e^{−4.21 z/W} (slowest channel Stokes mode; consecutive Moffatt eddies are ~1/350 weaker) | – |
| Mixing | upper bound D_osc = \|u\|²/(2ω), with u = u_t \|Stokes(W/2)\| e^{−4.21 z/W} | – |
| Outside the slit | the wafer-level mass transfer uses D + u_t²/(2ω) in the Levich formula (upper bound) | – |
| Compression pumping | ξ = L \|1+R\| p₀/(ρc²): about 2 nm per cycle at 2 W/cm² | – |

**Not modelled:** cavitation, bubble microstreaming, Eckart bulk streaming (estimated 10⁻⁴–10⁻³ m/s in a mm-scale gap, below the spin-film flow), and H₂ bubble nucleation (reported as dissolved-H₂ supersaturation instead).

## 6. Stage 2 (Fluent 2D, UDFs), planned

The 2D model resolves the mouth region: the oscillating Stokes flow over the slit, the steady spin shear, and the lateral recess pockets as the etch advances. It uses user-defined scalars for OH⁻, silicate and H₂ with the same Nernst–Planck / zero-current flux (DEFINE_UDS_FLUX) and a reaction-flux wall condition on poly-Si faces only. The 1D model is its reference.
