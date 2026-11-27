"""Case 10 checks that need no Fluent: the row measurement of analyze_resolved.py and the run plan."""
import math

import analyze_resolved as AR
import run_resolved as RR
from etchsim import acoustics as A
from etchsim import props as P


def synthetic_rows(D_true, J_w=8.3e-3, H=10e-6, ny=200, nx=20, conv_frac=0.0):
    """linear profile c = c0 - (J_w / D_true) y; flux split into diffusion (D_H2) + convection remainder"""
    rows, dy, dx = [], H / ny, P.PITCH / nx
    for j in range(ny - 1):
        yf = (j + 1) * dy
        g = -J_w / D_true                                  # dc/dy
        for i in range(nx):
            jd = -P.D["H2"] * g * dx
            jc = J_w * dx - jd                             # whatever the flow carries on top of diffusion
            rows.append(dict(zone=2, x=i * dx, y=yf - dy / 2, dx=dx, y_face=yf, len=dx, jc=jc, jd=jd, grad=g * dx,
                             c_h2=1.0, n=10, d_osc=0.0))
    return rows


def test_pure_diffusion_gives_D():
    prof = AR.profile(synthetic_rows(P.D["H2"]))
    assert all(abs(r["D_eff"] / P.D["H2"] - 1) < 1e-12 for r in prof)


def test_enhanced_mixing_measured():
    prof = AR.profile(synthetic_rows(3 * P.D["H2"]))
    assert all(abs(r["D_eff"] / P.D["H2"] - 3) < 1e-9 for r in prof)


def test_mouth_prediction_linear():
    H, J_w, D = 10e-6, 8.3e-3, P.D["H2"]
    prof = AR.profile(synthetic_rows(D, J_w, H))
    c0, Jm, integ = AR.mouth_prediction(prof, c_top=30.0)
    y_last = prof[-1]["y"]
    assert abs(Jm - J_w) < 1e-12
    assert abs(c0 - (30.0 + J_w * y_last / D)) < 1e-9


def test_plan_values():
    p = RR.plan(RR.load("R15_flat", RR.CASES_CSV))
    wv = A.wall_velocities(2, 15)
    assert abs(p["u_t"] - 0.3106) < 1e-3 and abs(p["p_wall"] - wv["p_wall"]) < 1e-6
    p90 = RR.plan(RR.load("R90_flat", RR.CASES_CSV))
    assert p90["u_t"] == 0.0 and abs(p90["p_wall"] / 1e6 - 0.4584) < 1e-3
    assert abs(p["dt"] - 2.5e-8) < 1e-20


def test_top_values_between_mouth_and_bulk():
    tops, cs = RR.top_values(10e-6)
    assert 0 < tops["H2"] < cs["H2"]
    k = P.levich_km(P.D["H2"], P.omega_spin())
    assert abs(tops["H2"] - cs["H2"] * (1 - k * 10e-6 / P.D["H2"])) < 1e-12
