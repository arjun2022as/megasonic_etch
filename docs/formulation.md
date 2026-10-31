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

## 6. Recess growth and H₂ bubbles (`etchsim/pocket.py`, `run_evolution.py`)

**Pockets.** An etched poly-Si layer leaves a pocket of depth R and height 50 nm, with oxide walls and the etch front at its end. Inside the pocket the fluxes are constant: N_OH = 2r inward, N_SIL = r and N_H₂ = 2r outward. With the same zero-current Nernst–Planck algebra, the gradients are r·h(c), where h comes from a 2×2 linear system. The concentration change over the pocket is about 10⁻³ of bulk even for R = 1 µm, so

  c_front = c_mouth − r R h(c_mouth),  r = rate(c_OH,front),  c_H₂,front = c_H₂,mouth + 2rR/D_H₂.

Check: this matches a full RK4 integration along the pocket to within 1 % of the concentration drop and 10⁻⁶ of the concentration.
Time stepping: quasi-steady at each time; the recess advances by the front etch velocity with explicit dt = 5 s.

**Bubble criterion.** A bubble that fills the slit width has a meniscus with one curvature 2/W (wetting oxide):

  S_crit = (p_atm + 2γ/W − p_vap)/p_atm = 13.9 for W = 100 nm (γ = 0.0662 N/m, p_vap = 19.9 kPa at 60 °C)

Where the dissolved-H₂ supersaturation S > S_crit, confined bubbles can grow (check: recomputed by hand).

**Bubble blocking, a parametric scenario.** No bubble dynamics are solved. Where S > S_crit, bubbles take a fraction α of the slit cross-section: the transport area shrinks and the walls stay wetted. α is swept from 0 to 0.9 and the bubble region is found self-consistently.
Check: a uniform liquid fraction ε reproduces the cosh solution with D → εD.

**Indicator for megasonic action on confined bubbles:** the pressure amplitude at the wafer, |1+R|p₀, compared with the Laplace pressure 2γ/W = 1.32 MPa.

## 7. Stage 2: 2D Fluent model (`fluent2d/`, `run_case.py`)

**Geometry (`fluent2d/mesh2d.py`).**
- Slit 100 nm × 10 µm, plus pockets of depth R in every poly-Si layer.
- Above it, 1 µm of wafer (one pitch) and 2 µm of liquid.
- Cells: 5 nm across, 10 nm along the depth (5 rows per layer), graded from 5 nm above the wafer. That gives 28 k cells at R = 0 and 88 k at R = 300 nm.
- Zones: `poly` (etch front), `oxide`, `wafer-top`, `inlet`, `top`, `outlet`.

**Equations (UDF `fluent2d/udf/etch.c`, constants generated into `etch_params.h`).**
- Three user-defined scalars: φ_i = c_i/ρ for OH⁻, silicate and H₂.
- Diffusivity: Γ = ρ(D_i + D_osc). Fluent 2024 R1 applies ONE constant diffusivity to all UDS even with defined-per-uds (M0_none 2026-10-30: check_2d.py showed all three species diffusing with uds-2's D_H2), so every UDS gets ρD_BASE (D_BASE = smallest D_i = D_SIL) and the remainder ρ(D_i − D_BASE) is added to the face-source term below. ASSUMED: at the inlet/outlet/top boundary faces only D_BASE acts (half a cell, 2 µm above the slit, convection-dominated). The D_osc part is a cell source ∇·(ρD_osc∇φ_i) = (1/V) Σ_f k_f (φ_nb − φ_c), k_f = ρ D_osc,f A·A/|A·dr|, D_osc,f = mean of the two cells, implicit part −Σk_f/V. This is the same two-point flux Fluent would use; it is needed because the 2024 R1 settings API cannot attach a per-UDS user-defined diffusivity. ASSUMED: no D_osc flux through the inlet/outlet/top boundaries, which are far from the slit.
- Electromigration (ions only): outward face flux J = z_i D_i c_f (S·A_out)/Q_f with c_f and Q_f from the mean of the two cells, added to the cell as the source −(1/V) Σ_f J (`face_source` in etch.c, together with the D_osc term). On this orthogonal mesh S·A comes exactly from the two cell values, so each face flux is the same seen from both sides (conservative across zones and parallel partitions). Central rather than upwind, because migration is diffusion-like (cell Péclet ≪ 1). It is a source and not a UDS flux UDF because Fluent 2024 R1's TUI never attached the flux hook (no call seen on Puma, 2026-10-30). ASSUMED: no migration flux through the inlet/outlet/top boundaries (uniform specified values, far from the slit).
- Reaction: a source term in the cells next to poly-Si faces, ν_i r × (poly length / cell area), implicit for OH⁻.
- These are the same equations as the 1D model; `tests/test_fluent2d.py` checks the C electromigration term against `slit1d` algebraically.

**Flow.**
- Laminar and incompressible.
- Inlet and top: u = G y + amp·u_t[cos ωt − e^{−y/δ} cos(ωt − y/δ)], v = 0. This is the exact Stokes-layer solution over a flat wall plus the steady Couette shear between the spinning wafer and the MegPie face, G = Ωr/gap (300 rpm, r = 50 mm, gap 2 mm ASSUMED → 785 s⁻¹).
- u_t comes from §5 for each incidence angle θ. θ = 90° (MegPie) gives u_t = 0.

**Two phases.**
- **A:** only when u_t > 0. The oscillating flow runs 8 cycles to settle, then 10 cycles are sampled at 40 steps per cycle. The variance of u and v gives D_osc = (var u + var v)/ω, i.e. |u₁|²/2ω, the upper bound.
- **B:** amp = 0. TMAH transport with D_osc is advanced with time steps of 10⁻⁷ up to 10⁻³ s to about 0.305 s (6 silicate diffusion times L²/D_SIL = 51 ms; OH⁻ needs 9 ms), reported every 50 ms at the end so the quasi-steady state can be checked.
- **Boundary conditions:** inlet, top and outlet backflow use the mouth concentrations from the 1D model (wafer-level boundary layer).

**Outputs.** Each process writes `dump_<id>.csv` (poly-Si cells and the centre column). `run_case.py` turns these into the etch rate per layer, top/bottom and bottom/top. `analyze_2d.py` makes the angle, mixing, frequency/power and verification figures.

**Cases (`make_cases.py`, 16).**
- M0: no megasonic.
- A: incidence 90/75/60/45/30/15° at 1 MHz and 2 W/cm².
- F: 2 and 3 MHz at 45°.
- P: 0.5 and 1 W/cm² at 45°.
- R: 300 nm recess, with and without megasonics.
- V: checks (no electromigration, first-order rate, mesh refined 2×).

The 2D model resolves the mouth region: the oscillating Stokes flow over the slit, the steady spin shear, and the lateral recess pockets as the etch advances. It uses user-defined scalars for OH⁻, silicate and H₂ with the same Nernst–Planck / zero-current flux (DEFINE_UDS_FLUX) and a reaction-flux wall condition on poly-Si faces only. The 1D model is its reference.
