"""Case 6 checks: property fits against handbook values, bubble levels against the case 2-5 numbers, and the
no-bubble H2 level against the hand formula c_floor = c_mouth + r L^2 / (W D) (independent route)."""
import math
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import plug as PL  # noqa: E402
from etchsim import props as P  # noqa: E402
from etchsim import window as WN  # noqa: E402


def test_water_properties_25C_and_60C():
    assert WN.mu_water(298.15) == pytest.approx(0.890e-3, rel=0.01)
    assert WN.mu_water(333.15) == pytest.approx(P.MU_L, rel=0.01)
    assert WN.gamma_water(298.15) == pytest.approx(0.07197, rel=0.002)
    assert WN.gamma_water(333.15) == pytest.approx(P.GAMMA_60C, rel=0.002)
    assert WN.p_vap_water(298.15) == pytest.approx(3169.0, rel=0.01)
    assert WN.p_vap_water(333.15) == pytest.approx(P.P_VAP_60C, rel=0.01)
    assert WN.rho_water(333.15) == pytest.approx(983.2, rel=1e-3)


def test_levels_match_earlier_cases():
    T = 333.15
    assert WN.c_need(T, P.W_SLIT) == pytest.approx(PL.C_BUB, rel=0.003)          # 9.71 mM = 13.9x
    assert WN.c_need(T, 50e-9) / P.H2_SAT == pytest.approx(27.0, rel=0.01)
    assert WN.c_need(T, 13.4e-9) / P.H2_SAT == pytest.approx(98.6, rel=0.01)
    # pressure only adds (p_amb - p_atm) / p_atm saturations
    assert (WN.c_need(T, P.W_SLIT, 3 * P.P_ATM) - WN.c_need(T, P.W_SLIT)) / P.H2_SAT == pytest.approx(2.0, rel=1e-9)


def test_floor_matches_hand_formula_60C():
    r = WN.slit_h2(n=1000)
    rsi = P.si_flux(r["er_top_nm_min"] / 6e10 * 0.98)           # ~mean rate along the slit
    hand = r["c_mouth"] + rsi * P.L_SLIT ** 2 / (P.W_SLIT * P.D["H2"])
    assert r["c_max"] == pytest.approx(hand, rel=0.03)
    assert r["S_mouth"] == pytest.approx(63.5, rel=0.02)


def test_concentration_rate_law():
    assert WN.c_oh_bulk(0.05) == pytest.approx(P.C_BULK, rel=1e-3)
    assert WN.er_ref_conc(0.05) == pytest.approx(P.ER_REF, rel=1e-12)
    # hand: 25 wt% vs 5 wt%: ([H2O] ratio)^4 * ([OH] ratio)^(1/4)
    h = (0.75 * 1018.2) / (0.95 * 990.2)
    o = (0.25 * 1018.2) / (0.05 * 990.2)
    assert WN.er_ref_conc(0.25) / P.ER_REF == pytest.approx(h ** 4 * o ** 0.25, rel=2e-3)
    assert WN.er_ref_conc(0.07) > WN.er_ref_conc(0.05) > WN.er_ref_conc(0.15) > WN.er_ref_conc(0.25)


def test_other_gas_lowers_h2_needed_by_its_pressure():
    T = 333.15
    d = (WN.c_need(T, P.W_SLIT) - WN.c_need(T, P.W_SLIT, p_other=P.P_ATM)) / P.H2_SAT
    assert d == pytest.approx(1.0, rel=1e-9)                       # 1 atm of N2/O2 = 1x saturation less H2


def test_mouth_scales_with_inverse_sqrt_rpm():
    a, b = WN.slit_h2(rpm=300, n=400), WN.slit_h2(rpm=1200, n=400)
    assert a["c_mouth"] / b["c_mouth"] == pytest.approx(2.0, rel=0.03)
    assert math.isclose(a["c_max"] - a["c_mouth"], b["c_max"] - b["c_mouth"], rel_tol=0.03)
