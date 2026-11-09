"""Case 6, bubble-free window: temperature-dependent liquid properties, bubble-start levels, and the no-bubble
H2 level in the slit for a given spin speed / temperature (1D steady slit, etchsim/slit1d.py).

Bubble-start level for a gas surface of curvature radius r (Laplace + Henry), as an absolute concentration:
    c_need(r) = c_sat(T) (p_amb + 2 gamma(T) / r_eff - p_vap(T)) / p_atm
r_eff = W for the slit-wide plug (one curvature W/2 -> 2 gamma / W), r_eff = r for a round seed of radius r.
Raising the chamber pressure p_amb raises every level; nothing changes the H2 actually present (made by the
etch, removed by diffusion), so p_amb only moves the thresholds.
"""
import math

from . import props as P
from .slit1d import Slit

T60 = P.T


def mu_water(T):
    """Pa s, Vogel fit (0-100 C): 2.414e-5 * 10^(247.8/(T - 140))."""
    return 2.414e-5 * 10 ** (247.8 / (T - 140.0))


def rho_water(T):
    """kg/m3, Thiesen-type fit (0-100 C)."""
    tc = T - 273.15
    return 1000.0 * (1 - (tc + 288.9414) / (508929.2 * (tc + 68.12963)) * (tc - 3.9863) ** 2)


def gamma_water(T):
    """N/m, IAPWS 1994: 235.8 (1 - T/Tc)^1.256 (1 - 0.625 (1 - T/Tc)) mN/m."""
    tau = 1 - T / 647.096
    return 0.2358 * tau ** 1.256 * (1 - 0.625 * tau)


def p_vap_water(T):
    """Pa, Antoine (1-100 C): log10(p / mmHg) = 8.07131 - 1730.63 / (233.426 + T_C)."""
    return 133.322 * 10 ** (8.07131 - 1730.63 / (233.426 + T - 273.15))


VANT_HOFF_H2 = 530.0         # K, d ln(k_H) / d(1/T) for H2 in water (Sander 2015 compilation); ASSUMED for TMAH


def c_sat(T):
    """mol/m3 of H2 under 1 atm H2: H2_SAT (0.70 mM at 60 C, ASSUMED) scaled with the van 't Hoff slope."""
    return P.H2_SAT * math.exp(VANT_HOFF_H2 * (1 / T - 1 / T60))


def c_need(T, r_eff, p_amb=P.P_ATM, p_other=0.0):
    """Dissolved H2 [mol/m3] that holds a gas surface of effective radius r_eff steady (see module doc).
    p_other: partial pressure of other dissolved gases (N2, O2, Ar) that the bubble also holds at equilibrium;
    0 = fully degassed."""
    return c_sat(T) * (p_amb + 2 * gamma_water(T) / r_eff - p_vap_water(T) - p_other) / P.P_ATM


# ---------------------------------------------------------------- TMAH concentration
M_WATER = 0.018015


def rho_soln(w):
    """kg/m3 at 60 C: 983.2 + 140 w (ASSUMED linear; 990 at 5 wt%, ~1018 at 25 wt%)."""
    return P.RHO_L + 140.0 * w


def c_oh_bulk(w):
    return w * rho_soln(w) / P.M_TMAH


def er_ref_conc(w):
    """Bulk etch rate at w (mass fraction), from the model's own rate law r ~ [H2O]^4 [OH-]^(1/4) (Seidel 1990),
    scaled to ER_ref = 300 nm/min at 5 wt% (ASSUMED). Peaks near 7 wt%, about half at 25 wt%."""
    h2o = lambda x: (1 - x) * rho_soln(x) / M_WATER          # noqa: E731
    return P.ER_REF * (h2o(w) / h2o(P.WT_TMAH)) ** 4 * (c_oh_bulk(w) / c_oh_bulk(P.WT_TMAH)) ** P.ORDER_OH


# bubble-start levels (round seeds: 2 gamma / r, plug: 2 gamma / W)
LEVELS = {"plug (seeds that span the slit)": P.W_SLIT, "50 nm seed": 50e-9, "13 nm seed (few seeds, ~100x)": 13.4e-9}


def props_at(T):
    mu = mu_water(T)
    D = {k: P.d_at(T, mu, v) for k, v in P.D25.items()}
    return dict(T=T, mu=mu, nu=mu / rho_water(T), D=D, er_ref=P.arrhenius(P.ER_REF, T60, T), c_sat=c_sat(T),
                gamma=gamma_water(T), p_vap=p_vap_water(T))


def slit_h2(T=T60, rpm=P.SPIN_RPM, km_scale=1.0, er_scale=1.0, n=800, L=P.L_SLIT, pitch=P.PITCH, w=P.WT_TMAH,
            h2_only=False):
    """No-bubble quasi-steady slit at temperature T and spin rpm. km_scale multiplies the wafer-level k (e.g. extra
    film mixing; h2_only: only for H2, e.g. bubbles taking up H2); er_scale multiplies the reference etch rate (any
    chemistry change). Returns H2 at mouth/floor."""
    if abs((P.LAYER / (L / n)) - round(P.LAYER / (L / n))) > 1e-9:
        raise ValueError(f"n = {n}: cells must tile the {P.LAYER * 1e9:g} nm layers")
    pr = props_at(T)
    om = P.omega_spin(rpm)
    km = {s: (km_scale if (s == "H2" or not h2_only) else 1.0) * P.levich_km(pr["D"][s], om, pr["nu"])
          for s in ("OH", "SIL", "H2")}
    s = Slit(n=n, D=pr["D"], er_ref=pr["er_ref"] * er_scale * er_ref_conc(w) / P.ER_REF, km=km, L=L, pitch=pitch,
             c_bulk=c_oh_bulk(w))
    r = s.solve()
    h2_max = r["h2_supersat"] * P.H2_SAT                     # mol/m3 (slit1d normalises by the 60 C value)
    return dict(T_C=T - 273.15, rpm=rpm, km_scale=km_scale, er_scale=er_scale,
                er_top_nm_min=r["er_top"] * 6e10, er_bottom_nm_min=r["er_bottom"] * 6e10, uniformity=r["uniformity"],
                c_mouth=r["surf"]["H2"], c_max=h2_max, surf=r["surf"], c_sat=pr["c_sat"],
                S_mouth=r["surf"]["H2"] / pr["c_sat"], S_max=h2_max / pr["c_sat"])
