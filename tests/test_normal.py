"""Case 7 checks (etchsim/normal.py), each against an independent route."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import normal as N  # noqa: E402
from etchsim import props as P  # noqa: E402
from etchsim import window as WN  # noqa: E402

KL = P.levich_km(P.D["H2"], P.omega_spin())
DN = P.D["H2"] / KL


def test_near_wall_formula_reproduces_levich():
    assert N.k_rotating_disk(P.omega_spin(), P.D["H2"]) == pytest.approx(KL, rel=2e-3)   # 0.6204 vs 0.620


def test_homann_shooting_and_stagnation_coefficient():
    assert N.homann_fpp0() == pytest.approx(N.HOMANN_FPP0, abs=1e-4)
    assert N.k_stagnation(1.0, 1.0, 1.0) == pytest.approx(0.850, abs=1e-3)


def test_leveque_patch_mean_is_integral_of_local():
    # local k(x) = D / (Gamma(4/3) (9 D x / G)^(1/3)); mean over 0..L by quadrature
    D, G, L = 1e-9, 50.0, 1e-3
    x = np.linspace(L / 2e6, L, 2_000_001)
    local = D / (math.gamma(4 / 3) * (9 * D * x / G) ** (1 / 3))
    assert N.k_leveque_patch(G, L, D) == pytest.approx(np.trapezoid(local, x) / L, rel=2e-3)


def test_eckart_lubrication_profile():
    F, w_e, h = 0.27, 1.55e-3, N.GAP
    z, u = N.eckart_profile(F, w_e, h, n=20001)
    assert abs(np.trapezoid(u, z)) < 1e-9 * np.abs(u).max() * h       # no net sideways flux
    assert u[0] == 0 and abs(u[-1]) < 1e-15                            # no slip on both walls
    G_num = (u[1] - u[0]) / (z[1] - z[0])
    assert abs(G_num) == pytest.approx(F / w_e * h * h / (12 * P.MU_L), rel=1e-3)
    # force balance in the bulk: mu u'' = F' h / 2 - F' z
    mid = len(z) // 3
    u2 = (u[mid + 1] - 2 * u[mid] + u[mid - 1]) / (z[1] - z[0]) ** 2
    assert P.MU_L * u2 == pytest.approx(F / w_e * (h / 2 - z[mid]), rel=1e-4)


def test_minnaert_radius():
    # no surface tension / vapour: R = sqrt(3 kappa p0 / rho) / (2 pi f)
    R = N.resonance_radius(1e6, gamma=0.0, p_v=0.0)
    assert R == pytest.approx(math.sqrt(3 * P.P_ATM / P.RHO_L) / (2 * math.pi * 1e6), rel=1e-6)
    assert 2.5e-6 < N.resonance_radius(1e6) < 3.3e-6


def test_film_continuous_limits_are_analytic():
    # sound all the time: stirring a layer h -> c_wall = J (delta - h) / D; sink k -> c_wall = J / (k_L + k)
    r = N.film_cycle(duty=1.0, h_mix=0.4 * DN, revs=6)
    assert r["mean"] == pytest.approx(0.6, rel=0.01)
    r = N.film_cycle(duty=1.0, k_sink=0.5 * KL, revs=6)
    assert r["mean"] == pytest.approx(1 / 1.5, rel=0.01)
    r = N.film_cycle(revs=4)
    assert r["mean"] == pytest.approx(1.0, rel=1e-3)                    # no sound -> Levich


def test_film_recovery_after_full_renewal_matches_semi_infinite():
    # after the film is wiped, c_wall = 2 J sqrt(t / (pi D)) while sqrt(D t) << delta_N
    r = N.film_cycle(h_mix=1.0, revs=6)
    t_on = N.DUTY * N.T_REV
    i = np.searchsorted(r["t"], t_on + 0.005)
    tt = r["t"][i] - t_on
    hand = 2 * math.sqrt(P.D["H2"] * tt / math.pi) / DN
    assert r["c_wall"][i] == pytest.approx(hand, rel=0.05)


def test_mouth_side_cannot_remove_the_in_slit_rise():
    a = WN.slit_h2(n=400)
    b = WN.slit_h2(n=400, km_scale=1e6)
    assert b["S_mouth"] < 0.1
    assert 55 < b["S_max"] < 65                                         # > 27x and > 13.9x even with perfect renewal
    assert b["S_max"] == pytest.approx(a["S_max"] - a["S_mouth"], rel=0.05)


def test_h2_only_scale_leaves_oh_mouth():
    a = WN.slit_h2(n=400)
    b = WN.slit_h2(n=400, km_scale=2.0, h2_only=True)
    assert b["surf"]["OH"] == pytest.approx(a["surf"]["OH"], rel=1e-9)
    assert b["S_mouth"] == pytest.approx(a["S_mouth"] / 2, rel=0.01)
