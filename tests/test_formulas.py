"""Second, independent checks of every formula and of the 1D solver.
Run: uv run --no-project --with pytest --with numpy --with scipy pytest -q"""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import acoustics as A  # noqa: E402
from etchsim import props as P  # noqa: E402
from etchsim.slit1d import Slit, layer_mask  # noqa: E402


# ---------------------------------------------------------------- properties
def test_bulk_concentration_by_hand():
    # 5 g TMAH per 100 g solution; 1 L of solution weighs 990 g -> 49.5 g -> 49.5 / 91.15 mol
    assert P.C_BULK == pytest.approx(49.5 / 91.15 * 1000, rel=1e-9)
    assert 530 < P.C_BULK < 560


def test_ion_diffusivities_from_limiting_conductivity():
    # independent route: D = R T lambda / (z^2 F^2), lambda in S m2/mol (CRC table)
    for ion, lam, z in (("OH", 198.0e-4, 1), ("TMA", 44.9e-4, 1)):
        d = P.R_GAS * 298.15 * lam / (z * z * P.F_FARADAY ** 2)
        assert P.D25[ion] == pytest.approx(d, rel=3e-3)


def test_stokes_einstein_factor():
    assert P.D["OH"] / P.D25["OH"] == pytest.approx((333.15 / 298.15) * (0.8900 / 0.4665), rel=1e-12)
    assert 2.0 < P.D["OH"] / P.D25["OH"] < 2.3


def test_etch_rate_units_and_arrhenius():
    assert P.etch_rate(P.C_BULK) * 60 * 1e9 == pytest.approx(300.0)          # 300 nm/min at bulk
    assert P.si_flux(5e-9) == pytest.approx(5e-9 * 2330 / 0.028086)           # mol/m2/s
    # 0.57 eV: ~ x2 per ~10.6 C near 60 C (independent: d ln r / dT = Ea / (k T^2))
    r70 = P.arrhenius(1.0, 333.15, 343.15)
    assert math.log(r70) == pytest.approx(0.57 / P.K_B_EV * (1 / 333.15 - 1 / 343.15), rel=1e-12)


def test_spin_film_by_integrating_velocity_profile():
    om, r, Q = P.omega_spin(300), 0.05, 1e-3 / 60
    h, G = P.spin_film(Q, om, r)
    z = np.linspace(0, h, 20001)
    u = om ** 2 * r / P.NU_L * (h * z - z * z / 2)                           # spin-off film profile
    assert 2 * math.pi * r * np.trapezoid(u, z) == pytest.approx(Q, rel=1e-6)
    assert G == pytest.approx((u[1] - u[0]) / (z[1] - z[0]), rel=1e-3)


def test_levich_by_hand():
    k = P.levich_km(1e-9, 10.0, 1e-6)
    assert k == pytest.approx(0.620 * 1e-6 * 10 * math.sqrt(10), rel=1e-12)


# ---------------------------------------------------------------- acoustics
def test_plane_wave_intensity_round_trip():
    p0, U0 = A.plane_wave(1.0)
    assert p0 ** 2 / (2 * P.RHO_L * P.C_SOUND) == pytest.approx(1e4)
    assert U0 == pytest.approx(p0 / (P.RHO_L * P.C_SOUND))
    assert 0.10 < U0 < 0.13                                                  # ~0.115 m/s at 1 W/cm2


def test_reflection_normal_incidence_and_limits():
    z1, z2 = P.RHO_L * P.C_SOUND, A.RHO_SI * A.CL_SI
    assert A.reflection(90.0) == pytest.approx((z2 - z1) / (z2 + z1), abs=1e-12)
    rigid = A.reflection(60.0, rho_s=1e12)
    assert rigid == pytest.approx(1.0, abs=1e-6)                             # rigid wall
    for th in (10, 30, 45, 60, 70):                                          # beyond both critical angles
        assert abs(A.reflection(th)) == pytest.approx(1.0, abs=1e-9)
    for th in (85, 88):                                                      # before them: energy goes in
        assert abs(A.reflection(th)) < 1.0


def test_wall_velocities_rigid_limit():
    th = 30.0
    p0, U0 = A.plane_wave(1.0)
    beta = math.radians(60)
    R = A.reflection(th, rho_s=1e12)
    assert U0 * math.sin(beta) * abs(1 + R) == pytest.approx(2 * U0 * math.cos(math.radians(th)), rel=1e-6)
    assert A.wall_velocities(1.0, 90.0)["u_t"] == pytest.approx(0.0, abs=1e-12)   # normal incidence


def test_stokes_layer():
    d = A.stokes_delta(1e6)
    assert d == pytest.approx(math.sqrt(2 * P.NU_L / (2 * math.pi * 1e6)))
    assert 0.35e-6 < d < 0.42e-6
    assert A.stokes_amp(0.0, d) == 0.0 and A.stokes_amp(20 * d, d) == pytest.approx(1.0, abs=1e-6)
    assert A.stokes_amp(0.05e-6, d) == pytest.approx(math.sqrt(2) * 0.05e-6 / d, rel=0.15)   # small y


def test_slit_is_quasi_steady_stokes():
    for f in (1e6, 2e6, 3e6):
        assert A.womersley(P.W_SLIT, f) < 0.4


# ---------------------------------------------------------------- 1D slit solver
def test_layer_mask_alternates_from_oxide():
    z = (np.arange(8) + 0.5) * P.LAYER
    assert list(layer_mask(z)) == [0, 1, 0, 1, 0, 1, 0, 1]


def test_solver_matches_cosh_solution_first_order_no_migration():
    er = 3e-9 / 60                                  # slow etch: OH not depleted to zero
    s = Slit(n=1000, order=1.0, er_ref=er, poly=np.ones(1000), migration=False)
    res = s.solve()
    k = P.si_flux(er) / P.C_BULK                    # r = k c
    m = math.sqrt(2 * k * 2 / (P.W_SLIT * P.D["OH"]))
    exact = P.C_BULK * np.cosh(m * (P.L_SLIT - s.zc)) / math.cosh(m * P.L_SLIT)
    assert np.max(np.abs(res["c"]["OH"] - exact)) / P.C_BULK < 2e-3


def test_zero_current_and_cation_conservation():
    s = Slit(n=800)
    res = s.solve()
    c, N, ratio = res["c"], res["N"], res["phi_grad_ratio"]
    # rebuild the cation flux independently from its own Nernst-Planck expression
    ext = np.concatenate(([s.surf["OH"] + 2 * s.surf["SIL"]], c["OH"] + 2 * c["SIL"]))
    zpos = np.concatenate(([0.0], s.zc))
    grad = np.diff(ext) / np.diff(zpos)
    mid = 0.5 * (ext[:-1] + ext[1:])
    n_tma = -P.D["TMA"] * grad + P.D["TMA"] * mid * ratio[:-1]
    assert np.max(np.abs(n_tma)) < 1e-6 * np.max(np.abs(N["OH"]))           # cation not consumed
    current = -N["OH"][:-1] - 2 * N["SIL"][:-1] + n_tma
    assert np.max(np.abs(current)) < 1e-6 * np.max(np.abs(N["OH"]))


def test_stoichiometry_at_the_mouth():
    s = Slit(n=800)
    res = s.solve()
    si = res["si_consumed"] / s.W                   # Si etched per s (both walls, whole depth) / mouth width
    assert -res["N"]["SIL"][0] == pytest.approx(si, rel=1e-6)          # silicate leaves
    assert res["N"]["OH"][0] == pytest.approx(2 * si, rel=1e-6)        # OH- enters, 2 per Si
    assert -res["N"]["H2"][0] == pytest.approx(2 * si, rel=1e-6)       # H2 leaves, 2 per Si


def test_independent_bvp_solver_with_migration():
    """Same physics by a different method: scipy solve_bvp on the ODE system (c, N) with a smeared
    poly fraction of 0.5; must agree with the finite-volume Newton solver."""
    from scipy.integrate import solve_bvp
    er, order = 30e-9 / 60, 1.0
    D = P.D
    k = P.si_flux(er) / P.C_BULK

    def rhs(z, y):
        c_oh, c_si, c_h, n_oh, n_si, n_h = y
        c_t = c_oh + 2 * c_si
        Q = D["OH"] * c_oh + 4 * D["SIL"] * c_si + D["TMA"] * c_t
        # unknown gradients g from N_i = -D_i g_i + z_i D_i c_i S/Q with S = sum z D g: a 2x2 linear
        # system per point (independent of how the finite-volume solver writes the migration term)
        g_oh, g_si = np.zeros_like(z), np.zeros_like(z)
        for j in range(z.size):
            M = np.zeros((2, 2))
            b = np.array([n_oh[j], n_si[j]])
            # S = -D_OH g_oh - 2 D_SIL g_si + D_TMA (g_oh + 2 g_si)
            sc = np.array([-D["OH"] + D["TMA"], -2 * D["SIL"] + 2 * D["TMA"]]) / Q[j]
            M[0] = np.array([-D["OH"], 0.0]) + (-1) * D["OH"] * c_oh[j] * sc
            M[1] = np.array([0.0, -D["SIL"]]) + (-2) * D["SIL"] * c_si[j] * sc
            g_oh[j], g_si[j] = np.linalg.solve(M, b)
        g_h = -n_h / D["H2"]
        r = k * np.maximum(c_oh, 0) * 2 * 0.5 / P.W_SLIT
        return np.vstack([g_oh, g_si, g_h, -2 * r, r, 2 * r])

    def bc(ya, yb):
        return np.array([ya[0] - P.C_BULK, ya[1], ya[2], yb[3], yb[4], yb[5]])

    z = np.linspace(0, P.L_SLIT, 400)
    y0 = np.vstack([np.full_like(z, P.C_BULK), np.zeros_like(z), np.zeros_like(z),
                    np.zeros_like(z), np.zeros_like(z), np.zeros_like(z)])
    sol = solve_bvp(rhs, bc, z, y0, tol=1e-6, max_nodes=200000)
    assert sol.success
    s = Slit(n=1000, order=order, er_ref=er, poly=np.full(1000, 0.5))
    res = s.solve()
    ref = sol.sol(s.zc)
    assert np.max(np.abs(res["c"]["OH"] - ref[0])) / P.C_BULK < 3e-3
    assert np.max(np.abs(res["c"]["SIL"] - ref[1])) / P.C_BULK < 3e-3


def test_pocket_linear_front_matches_full_integration():
    from etchsim.pocket import front, h_vector
    s = Slit(n=10)
    c_oh, c_sil, R = np.array([500.0, 300.0]), np.array([10.0, 60.0]), np.array([1e-6, 1e-6])
    lin = front(c_oh, c_sil, np.zeros(2), R, s.rate)
    for k in range(2):                       # RK4 along the pocket with the front rate from the linear model
        r, y, nst = lin["r"][k], np.array([c_oh[k], c_sil[k]]), 2000
        dx = R[k] / nst
        for _ in range(nst):
            def f(v):
                return r * np.array(h_vector(v[0], v[1]))
            k1 = f(y)
            k2 = f(y + dx / 2 * k1)
            k3 = f(y + dx / 2 * k2)
            k4 = f(y + dx * k3)
            y = y + dx / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
        assert c_oh[k] - y[0] == pytest.approx(c_oh[k] - lin["c_oh"][k], rel=1e-2)   # drop along pocket
        assert y[1] - c_sil[k] == pytest.approx(lin["c_sil"][k] - c_sil[k], rel=1e-2)
        assert y[0] == pytest.approx(lin["c_oh"][k], rel=1e-6)
    assert np.allclose(front(c_oh, c_sil, np.zeros(2), np.zeros(2), s.rate)["r"], s.rate(c_oh))   # R = 0


def test_bubble_criterion_by_hand():
    from etchsim.pocket import s_crit
    assert s_crit() == pytest.approx((101325 + 2 * 0.0662 / 100e-9 - 19946) / 101325)
    assert 13 < s_crit() < 15


def test_liquid_fraction_matches_cosh_with_reduced_area():
    er, eps = 3e-9 / 60, 0.4
    s = Slit(n=1000, order=1.0, er_ref=er, poly=np.ones(1000), migration=False)
    s.liquid[:] = eps
    res = s.solve()
    k = P.si_flux(er) / P.C_BULK
    m = math.sqrt(4 * k / (P.W_SLIT * P.D["OH"] * eps))
    exact = P.C_BULK * np.cosh(m * (P.L_SLIT - s.zc)) / math.cosh(m * P.L_SLIT)
    assert np.max(np.abs(res["c"]["OH"] - exact)) / P.C_BULK < 2e-3


def test_grid_convergence_layered():
    a = Slit(n=1000).solve()
    b = Slit(n=2000).solve()
    assert a["uniformity"] == pytest.approx(b["uniformity"], abs=0.01)
    assert a["er_mean"] == pytest.approx(b["er_mean"], rel=0.01)
