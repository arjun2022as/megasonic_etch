"""Independent checks of etchsim/plug.py (growing H2 plug)."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import plug as PL  # noqa: E402
from etchsim import props as P  # noqa: E402

SURF = dict(OH=503.0931415, SIL=64.00191517, H2=44.42285922)       # M0_none mouth (cases.csv)


def fresh(surf):
    return {s: (np.array([0.0, P.L_SLIT]), np.array([surf[s]] * 2)) for s in ("OH", "SIL", "H2")}


def steady(b, surf=SURF, er_ref=None):
    s = PL.PlugSlit(b, surf, fresh(surf), 1e3, True, dz=10e-9)       # dt = 1000 s: steady
    if er_ref is not None:
        s.er_ref = er_ref
    return s, s.solve()


def test_constants_match_fluent_header():
    assert PL.C_BUB == pytest.approx(9.709, rel=1e-3)               # C_H2_BUB in params.py
    assert PL.RHO_GAS == pytest.approx(507.36, rel=1e-3)            # RHO_GAS_PLUG
    assert PL.S_PLUG == pytest.approx(13.9, rel=5e-3)


def test_no_reaction_is_linear_diffusion():
    """Etching off: H2 runs from the mouth to the plug down a straight line, N = D (c_mouth - c*) / b."""
    b = 6e-6
    _, r = steady(b, er_ref=0.0)
    assert r["N"]["H2"][-1] == pytest.approx(P.D["H2"] * (SURF["H2"] - PL.C_BUB) / b, rel=1e-5)


def test_steady_h2_balance():
    """Steady fixed plug: H2 made on the walls = H2 into the plug + H2 out of the mouth."""
    s, r = steady(9e-6)
    made = 2 * r["si_consumed"]                                      # mol/s per m of slit, 2 H2 per Si
    into_plug = r["N"]["H2"][-1] * P.W_SLIT
    out_mouth = -r["N"]["H2"][0] * P.W_SLIT
    assert into_plug + out_mouth == pytest.approx(made, rel=1e-6)


def test_fixed_plug_matches_fluent():
    """2D Fluent B_f1_I2_floor (1 um plug, 90 deg) reported PLUG H2_in 7.254e-9 mol/s/m."""
    pump = PL.pump_fn(1e6, 2.0, 90.0)(9e-6, 1e-6)
    s = PL.PlugSlit(9e-6, SURF, fresh(SURF), 1e3, True, pump, dz=5e-9)
    q = s.solve()["N"]["H2"][-1] * P.W_SLIT
    assert q == pytest.approx(7.254e-9, rel=0.01)


def test_no_nucleation_control_is_steady_slit():
    """s_nuc = inf: no plug ever; the time-averaged etch tends to the steady bubble-free slit."""
    run = PL.simulate(SURF, t_end=0.2, s_nuc=np.inf)
    assert not run["events"]
    assert all(not h["plug"] for h in run["hist"])
