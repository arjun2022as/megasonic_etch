"""Case 10 checks that need no Fluent: the row measurement of analyze_resolved.py and the run plan."""
import cmath
import math

import analyze_resolved as AR
import run_resolved as RR
from etchsim import acoustics as A
from etchsim import props as P

DH2 = P.D["H2"]


def synthetic(D_true, J_w=8.3e-3, H=10e-6, ny=200, nx=20, c_top=30.0, slit_excess=2.0):
    """exact linear profile c(y) = c_top + J_w (H - y) / D_true on a uniform grid (cell centres at (j+1/2) dy), the
    flux split into molecular diffusion (D_H2) + a convective remainder; slit-top cells slit_excess above row 0"""
    rows, dy, dx = [], H / ny, P.PITCH / nx
    c = lambda y: c_top + J_w * (H - y) / D_true                     # noqa: E731
    g = -J_w / D_true
    for j in range(ny):
        yc = (j + 0.5) * dy
        for i in range(nx):
            has_face = j < ny - 1
            jd = -DH2 * g * dx if has_face else 0.0
            rows.append(dict(zone=2, x=-0.45e-6 + i * dx, y=yc, dx=dx, y_face=(j + 1) * dy if has_face else 0.0,
                             len=dx if has_face else 0.0, jc=(J_w * dx - jd) if has_face else 0.0, jd=jd,
                             grad=g * dx if has_face else 0.0, c_h2=c(yc), n=10, d_osc=0.0, u_amp=0.0,
                             shear_mean=0.0, shear_amp=0.0))
    for i in range(4):                                                # slit-top row, 10 nm tall, centroid -5 nm
        rows.append(dict(zone=3, x=12.5e-9 + i * 25e-9, y=-5e-9, dx=25e-9, y_face=0.0, len=0.0, jc=0, jd=0, grad=0,
                         c_h2=c(0.5 * dy) + slit_excess, n=10, d_osc=0, u_amp=0, shear_mean=0, shear_amp=0))
    return rows


def test_pure_diffusion_gives_D():
    prof = AR.profile(synthetic(DH2))
    assert all(abs(r["D_eff"] / DH2 - 1) < 1e-12 for r in prof)


def test_enhanced_mixing_measured():
    prof = AR.profile(synthetic(3 * DH2))
    assert all(abs(r["D_eff"] / DH2 - 3) < 1e-9 for r in prof)


def test_resistances_reproduce_the_profile():
    """film + last half cell must give back the first-row value exactly; R_m the slit-top excess"""
    J_w, H = 8.3e-3, 10e-6
    for D_true in (DH2, 2 * DH2):
        rows = synthetic(D_true, J_w, H)
        r = AR.resistances(rows, AR.profile(rows), dict(H=H, c_top={"H2": 30.0}), J_w)
        if D_true == DH2:              # the last half cell is plain D_H2 by design: exact only when D_true = D_H2
            assert abs(r["c_row_pred"] - r["c_row_meas"]) < 1e-9
        assert abs(r["R_m"] * J_w - 2.0) < 1e-9
        assert abs(r["c_mouth_pred"] - (r["c_row_pred"] + 2.0)) < 1e-9


def test_production_matches_hand_value():
    assert abs(AR.production(dict(result_B=dict(er_mean_nm_min=300.0))) - 8.2959e-3) < 1e-6


def test_layer_thickness_found_from_data():
    """a Stokes-like decay exp(-y/delta) must give the 1 % thickness delta ln(100) from the rows alone"""
    delta = 0.39e-6
    rows = [dict(y=j * 0.025e-6, shear_amp=math.exp(-j * 0.025e-6 / delta)) for j in range(1, 400)]
    assert abs(AR.first_below_rows(rows, "shear_amp", 0.01) - delta * math.log(100)) < 0.03e-6
    pairs = [(r["y"], r["shear_amp"]) for r in rows]
    assert abs(AR.first_below(pairs, 0.01) - delta * math.log(100)) < 0.06e-6


def test_extra_mix_absolute_threshold():
    prof = [dict(y=1e-7, D_eff=DH2 * 1.005), dict(y=2e-7, D_eff=DH2 * 1.2), dict(y=3e-7, D_eff=DH2)]
    assert AR.extra_mix_height(prof) == 2e-7
    assert math.isnan(AR.extra_mix_height([dict(y=1e-7, D_eff=DH2 * 1.001)]))


def test_stokes_check_exact_profile_is_zero():
    u_t, delta = 0.31, 0.389e-6
    rows = [dict(x=-0.45e-6, y=j * 20e-9, u_amp=u_t * abs(1 - cmath.exp(-(1 + 1j) * j * 20e-9 / delta)))
            for j in range(1, 100)]
    assert AR.stokes_check(rows, dict(u_t=u_t, delta=delta)) < 1e-12


def test_plan_values():
    p = RR.plan(RR.load("R15_flat", RR.CASES_CSV))
    wv = A.wall_velocities(2, 15)
    assert abs(p["u_t"] - 0.3106) < 1e-3 and abs(p["p_wall"] - wv["p_wall"]) < 1e-6
    p90 = RR.plan(RR.load("R90_flat", RR.CASES_CSV))
    assert p90["u_t"] == 0.0 and abs(p90["p_wall"] / 1e6 - 0.4584) < 1e-3
    assert abs(p["dt"] - 2.5e-8) < 1e-20
    pf = RR.plan(RR.load("R15_flat_fine", RR.CASES_CSV))
    assert abs(pf["dt"] - 1.25e-8) < 1e-20 and abs(pf["mesh"]["dx"] - 2.5e-9) < 1e-20 and pf["sample_every"] == 8


def test_top_values_between_mouth_and_bulk():
    tops, cs = RR.top_values(10e-6)
    assert 0 < tops["H2"] < cs["H2"]
    k = P.levich_km(DH2, P.omega_spin())
    assert abs(tops["H2"] - cs["H2"] * (1 - k * 10e-6 / DH2)) < 1e-12


def _stokes_rows(u_t, delta, H, amp=1.0, ny=400):
    """mid-pitch column with the exact Stokes amplitude (scaled by amp) and its face shear on a uniform grid"""
    dy, rows = H / ny, []
    for j in range(ny):
        y = (j + 0.5) * dy
        yf = (j + 1) * dy
        rows.append(dict(x=-0.4475e-6, y=y, y_face=yf, len=5e-9,
                         u_amp=amp * u_t * abs(1 - cmath.exp(-(1 + 1j) * y / delta)),
                         shear_amp=amp * u_t * math.sqrt(2) / delta * math.exp(-yf / delta)))
    return rows


def test_stokes_metrics_exact_and_deficit():
    """exact layer scores 1 / 1 / ~1; the first set's 20 % deficit is caught"""
    u_t, delta, H = 0.3106, 0.3886e-6, 10e-6
    m = AR.stokes_metrics(_stokes_rows(u_t, delta, H), u_t, delta, H)
    assert abs(m["bulk"] - 1) < 1e-3 and abs(m["wall_shear"] - 1) < 1e-9 and abs(m["layer"] - 1) < 0.02
    assert m["profile_err"] < 1e-12
    bad = AR.stokes_metrics(_stokes_rows(u_t, delta, H, amp=0.8), u_t, delta, H)
    assert abs(bad["bulk"] - 0.8) < 1e-3 and abs(bad["wall_shear"] - 0.8) < 1e-9


def test_production_same_in_driver_and_analysis():
    assert abs(RR.production(300.0) / P.PITCH - AR.production(dict(result_B=dict(er_mean_nm_min=300.0)))) < 1e-15


def test_pin_top_values_and_header():
    p = RR.plan(RR.load("R15_flat", RR.CASES_CSV))
    p["mesh_info"] = dict(y_top_cell=9.95e-6, h_top_cell=0.1e-6)
    RR.pin_top(p)
    tops, _ = RR.top_values(9.95e-6)
    assert p["H_bc"] == 9.95e-6 and p["c_top"] == tops
    assert abs(p["top_pin_k"] - 100 * max(P.D[k] for k in ("OH", "SIL", "H2")) / 1e-14) < 1e-3
    h = RR.header_resolved(p)
    for k in ("TOP_ID 8", "TOP_PIN_K", "PIN_C_OH", "PIN_C_SIL", "PIN_C_H2"):
        assert f"#define {k}" in h


def test_bdf2_amplitude_and_pass_rule():
    """converged BDF2 gives 0.9919 u_t at 40 steps/cycle (independent route: Richardson-like small-step limit -> 1)"""
    assert abs(RR.bdf2_amp(40) - 0.991912) < 1e-6 and abs(RR.bdf2_amp(80) - 0.997952) < 1e-6
    assert abs(RR.bdf2_amp(100000) - 1) < 1e-8          # error ~ (w dt)^2 / 3 ~ 1.3e-9
    assert RR.stokes_pass(dict(bulk=0.9919, wall_shear=0.99), 40)
    assert not RR.stokes_pass(dict(bulk=0.801, wall_shear=0.893), 40)
