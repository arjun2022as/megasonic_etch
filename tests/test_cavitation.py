"""Independent checks of etchsim/cavitation.py (pure Python; runs with pytest or as a script)."""
import math
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import cavitation as CV  # noqa: E402
from etchsim import props as P  # noqa: E402


def close(a, b, rel):
    assert abs(a - b) <= rel * abs(b), f"{a} vs {b} (rel {abs(a - b) / abs(b):.2e} > {rel})"


def fd_dispersion(U, f, W, Dm, n=2000):
    """Second route: finite differences on 0 <= x <= h (g even), i omega g - D g'' = -u', g'(0) = g'(h) = 0,
    complex Thomas solve, then D_disp = -1/2 Re <u' conj(g)> by the trapezoid rule."""
    h, om = W / 2, 2 * math.pi * f
    dx = h / n
    x = [i * dx for i in range(n + 1)]
    up = [U / 2 - 1.5 * U * xi * xi / (h * h) for xi in x]
    s = Dm / (dx * dx)
    lo, di, hi, rhs = [0j] * (n + 1), [0j] * (n + 1), [0j] * (n + 1), [0j] * (n + 1)
    for i in range(n + 1):
        di[i] = 1j * om + 2 * s
        lo[i] = -s
        hi[i] = -s
        rhs[i] = -up[i]
    hi[0] = -2 * s                                   # ghost node g[-1] = g[1]
    lo[n] = -2 * s                                   # ghost node g[n+1] = g[n-1]
    for i in range(1, n + 1):                        # Thomas
        m = lo[i] / di[i - 1]
        di[i] -= m * hi[i - 1]
        rhs[i] -= m * rhs[i - 1]
    g = [0j] * (n + 1)
    g[n] = rhs[n] / di[n]
    for i in range(n - 1, -1, -1):
        g[i] = (rhs[i] - hi[i] * g[i + 1]) / di[i]
    vals = [up[i] * g[i].conjugate() for i in range(n + 1)]
    integral = dx * (sum(vals) - 0.5 * (vals[0] + vals[-1]))
    return -0.5 * (integral / h).real


def test_gas_pressure_by_hand():
    close(CV.gas_pressure(100e-9), 101325 + 2 * 0.0662 / 100e-9 - 19946, 1e-12)
    assert 1.3e6 < CV.gas_pressure() < 1.5e6


def test_steady_taylor_by_hand_integration():
    # steady: D g'' = u', g'(h) = 0 -> g = (a x^2/2 + b x^4/12)/D; <u' g> = (1/24 - 7/80 + 3/112) U^2 h^2 / D
    U, W, Dm = 0.1, 100e-9, P.D["OH"]
    h = W / 2
    by_hand = -(1 / 24 - 7 / 80 + 3 / 112) * U * U * h * h / Dm
    close(CV.taylor_steady(U, W, Dm), by_hand, 1e-12)


def test_slow_oscillation_is_half_of_steady_taylor():
    U, W, Dm = 0.1, 100e-9, P.D["OH"]
    for lam in (1e-2, 1e-5):                         # omega h^2 / D (closed form, then the guard)
        f = lam * Dm / (2 * math.pi * (W / 2) ** 2)
        close(CV.oscillatory_dispersion(U, f, W, Dm), 0.5 * CV.taylor_steady(U, W, Dm), 1e-3)
    close(fd_dispersion(U, 1e-2 * Dm / (2 * math.pi * (W / 2) ** 2), W, Dm), 0.5 * CV.taylor_steady(U, W, Dm), 1e-3)


def test_closed_form_matches_finite_differences():
    for f in (1e6, 3e6):
        for sp in ("OH", "SIL"):
            close(CV.oscillatory_dispersion(0.1, f, 100e-9, P.D[sp]), fd_dispersion(0.1, f, 100e-9, P.D[sp]), 2e-3)


def test_viscous_limit_is_poiseuille_by_hand():
    # a long column over a short bubble: resistance dominates, U = p_a W^2 / (12 mu z)
    r = CV.pumping(1e6, 2.0, 9e-6, 1e-6)
    assert r["R"] > 10 * abs(r["K"] / (2 * math.pi * 1e6) - 2 * math.pi * 1e6 * r["M"])
    close(r["U"], r["p_a"] * (100e-9) ** 2 / (12 * P.MU_L * 9e-6), 1e-2)
    assert r["stable"]


def test_spring_limit_volume_change():
    # very soft column (shallow, long bubble) cannot exceed the isothermal compression p_a / p_g
    r = CV.pumping(1e6, 2.0, 1e-8, 5e-6)
    assert r["dV_over_V"] <= r["p_a"] / r["p_gas"] * 1.0001


if __name__ == "__main__":
    for name, fn in list(globals().items()):
        if name.startswith("test_"):
            fn()
            print("ok", name)
