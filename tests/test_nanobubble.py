"""Independent checks of etchsim/nanobubble.py (case 5, sub-plug bubbles)."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import nanobubble as NB  # noqa: E402
from etchsim import plug as PL  # noqa: E402
from etchsim.props import GAMMA_60C, P_ATM, P_VAP_60C, W_SLIT  # noqa: E402


def test_fifty_nm_limit_is_27x():
    assert NB.s_max_pinned(50e-9) == pytest.approx(26.9, abs=0.05)


def test_sphere_of_half_width_feels_twice_the_plug_curvature():
    """Round bubble of radius W/2: 2 gamma/(W/2) = 4 gamma/W, twice the plug's 2 gamma/W."""
    excess = lambda s: s * P_ATM - P_ATM + P_VAP_60C          # noqa: E731  (= Laplace pressure)
    assert excess(NB.s_eq_free(W_SLIT / 2)) == pytest.approx(2 * excess(PL.S_PLUG), rel=1e-9)


def test_cap_geometry_second_route():
    """Pressure of the cap from its own height and footprint (R = (h^2 + L^2) / 2h) matches the liquid."""
    S, L = 60.0, 15e-9
    c = NB.cap(S, L)
    R = (c["h"] ** 2 + L ** 2) / (2 * c["h"])
    assert (P_ATM + 2 * GAMMA_60C / R - P_VAP_60C) / P_ATM == pytest.approx(S, rel=1e-9)
    assert c["theta_deg"] < 90 and not c["touches_far_wall"]


def test_no_balance_above_the_limit():
    L = 20e-9
    smax = NB.s_max_pinned(L)
    assert NB.cap(smax * 0.999, L) is not None
    assert NB.cap(smax * 1.001, L) is None
    assert NB.cap(smax * 0.999999, L)["h"] == pytest.approx(L, rel=2e-3)   # hemisphere at the limit
    assert NB.footprint_limit(smax) == pytest.approx(L, rel=1e-9)
    assert math.isclose(NB.c_h2_limit(L), smax * 0.70)
