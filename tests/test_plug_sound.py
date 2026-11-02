"""Checks of the realistic-sound pieces of etchsim/plug.py: duty cycle, rectified diffusion term, early venting."""
import math
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import plug as PL  # noqa: E402

SURF = dict(OH=503.0931415, SIL=64.00191517, H2=44.42285922)


def test_duty_cycle():
    duty = (0.2, 0.2 / 6)
    t = np.linspace(0, 0.6, 60001)[:-1]
    frac = np.mean([PL.sound_on(x, duty) for x in t])
    assert frac == pytest.approx(1 / 6, abs=1e-3)
    assert PL.sound_on(0.123, None)


def test_rectified_term_is_mean_of_isothermal_pressure():
    """Second route: average p0 / (1 + eps cos wt) numerically over one cycle."""
    eps = PL.pulsation(1e6, 2.0)(9e-6, 1e-6)["eps"]
    wt = np.linspace(0, 2 * math.pi, 200001)[:-1]
    mean = np.mean(1 / (1 + eps * np.cos(wt)))
    assert mean == pytest.approx(1 / math.sqrt(1 - eps ** 2), rel=1e-9)
    assert mean - 1 < 2e-4                                  # rectified correction is tiny for a plug


def test_rectified_term_slightly_lowers_intake():
    fresh = {s: (np.array([0.0, 10e-6]), np.array([SURF[s]] * 2)) for s in ("OH", "SIL", "H2")}
    sv = PL.pulsation(1e6, 2.0)(9e-6, 1e-6)
    q0 = PL.PlugSlit(9e-6, SURF, fresh, 1e3, True, sv["D"]).solve()["N"]["H2"][-1]
    cb = PL.C_BUB / math.sqrt(1 - sv["eps"] ** 2)
    q1 = PL.PlugSlit(9e-6, SURF, fresh, 1e3, True, sv["D"], c_bub=cb).solve()["N"]["H2"][-1]
    assert q1 < q0 and (q0 - q1) / q0 < 1e-3


def test_swing_grows_toward_the_mouth():
    puls = PL.pulsation(1e6, 1.0)
    xs = [puls(b, 10e-6 - b)["xi"] for b in (9e-6, 4e-6, 1e-6, 0.3e-6)]
    assert all(a < b for a, b in zip(xs, xs[1:]))
    assert xs[0] < 20e-9 and xs[-1] > 100e-9
