"""Checks of the sealed-pocket formula (etchsim/plug.py) and of the comb option of the cycle model."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import plug as PL  # noqa: E402
from etchsim import props as P  # noqa: E402

SURF = dict(OH=503.0931415, SIL=64.00191517, H2=44.42285922)


def test_exact_formula_matches_rk4():
    R, c, dt = 300e-9, 503.0, 1e-5
    f = lambda x: -2 * PL.pocket_rate(x) / R                  # noqa: E731
    for _ in range(int(0.048 / dt)):
        k1 = f(c)
        k2 = f(c + dt / 2 * k1)
        k3 = f(c + dt / 2 * k2)
        k4 = f(c + dt * k3)
        c += dt / 6 * (k1 + 2 * k2 + 2 * k3 + k4)
    assert float(PL.sealed_pocket(503.0, R, 0.048)) == pytest.approx(c, rel=1e-9)


def test_empty_time_scales_with_recess():
    t = lambda R: 503.0 ** 0.75 / (0.75 * 2 * P.si_flux(P.ER_REF) / (R * P.C_BULK ** 0.25))   # noqa: E731
    assert t(300e-9) == pytest.approx(0.247, rel=0.01)
    assert t(600e-9) / t(300e-9) == pytest.approx(2.0, rel=1e-12)
    assert float(PL.sealed_pocket(503.0, 300e-9, 0.3)) == 0.0


def test_zero_recess_is_the_flat_model():
    a = PL.summarise(PL.simulate(SURF, t_end=0.06))
    b = PL.summarise(PL.simulate(SURF, t_end=0.06, recess=0.0))
    assert a["er_bottom_nm_min"] == b["er_bottom_nm_min"]
