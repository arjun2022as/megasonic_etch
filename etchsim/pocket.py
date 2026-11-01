"""Lateral recess pockets and H2 bubble criteria.

Pocket: as a poly-Si layer is etched sideways it leaves a pocket of depth R (into the layer) and height equal to
the layer (50 nm), walled by SiO2 above and below, with the poly-Si etch front at its end. In the pocket the
fluxes are constant along its length (no reaction on the oxide walls), set by the front reaction r:
    N_OH = 2 r (towards the front), N_SIL = r, N_H2 = 2 r (back out), N_TMA = 0.
With Nernst-Planck + zero current, the gradients are g = r * h(c), h from a 2x2 linear system (same algebra
as the slit). The concentration change over the pocket is tiny (r R h / c ~ 1e-3 even for R = 1 um), so the
front concentrations are, to first order in R:
    c_front = c_mouth - r R h(c_mouth)          (checked against full RK4 integration in the tests)
and r solves r = rate(c_OH,front).

Bubbles: dissolved H2 above the pressure inside a bubble that fits the slit can feed it. For a slit of width
W filled with a wetting liquid (oxide, contact angle ~0) the meniscus has one curvature 2/W, so
    p_bubble = p_liquid + 2 gamma / W,   H2 partial pressure = p_bubble - p_vap,
    S_crit = (p_atm + 2 gamma / W - p_vap) / p_atm    (saturation H2_SAT defined at 1 atm H2)
Where S = c_H2 / H2_SAT > S_crit, bubbles confined in the slit can grow rather than dissolve.
"""
import numpy as np

from . import props as P

from .props import GAMMA_60C, P_ATM, P_VAP_60C  # noqa: E402,F401  (moved to props, kept importable here)


def h_vector(c_oh, c_sil, D=None):
    """d c / d x per unit front rate r (x from the pocket mouth toward the front), for OH and SIL.
    Fluxes toward the front: N_OH = +2 r, N_SIL = -r (silicate flows back out)."""
    D = D or P.D
    c_t = c_oh + 2 * c_sil
    Q = D["OH"] * c_oh + 4 * D["SIL"] * c_sil + D["TMA"] * c_t
    a1 = (-D["OH"] + D["TMA"]) / Q             # S = a1 g_oh + a2 g_sil
    a2 = (-2 * D["SIL"] + 2 * D["TMA"]) / Q
    # N_OH = -D_OH g_oh - D_OH c_oh S ; N_SIL = -D_SIL g_sil - 2 D_SIL c_sil S
    m11 = -D["OH"] - D["OH"] * c_oh * a1
    m12 = -D["OH"] * c_oh * a2
    m21 = -2 * D["SIL"] * c_sil * a1
    m22 = -D["SIL"] - 2 * D["SIL"] * c_sil * a2
    n1, n2 = 2.0, -1.0
    det = m11 * m22 - m12 * m21
    return (n1 * m22 - m12 * n2) / det, (m11 * n2 - m21 * n1) / det


def front(c_oh, c_sil, c_h2, R, rate_fn, iters=30):
    """Front concentrations and front rate for pockets of depth R (arrays). rate_fn(c_oh) -> mol/m2/s."""
    c_oh, c_sil, c_h2, R = (np.asarray(v, float) for v in (c_oh, c_sil, c_h2, R))
    hoh, hsil = h_vector(np.maximum(c_oh, 1e-12), np.maximum(c_sil, 0.0))
    r = rate_fn(c_oh)
    for _ in range(iters):                         # fixed point: front drop is tiny, converges fast
        r_new = rate_fn(np.maximum(c_oh + r * R * hoh, 0.0))
        if np.all(np.abs(r_new - r) <= 1e-12 * np.maximum(np.abs(r_new), 1e-300)):
            r = r_new
            break
        r = r_new
    return dict(r=r, c_oh=c_oh + r * R * hoh, c_sil=c_sil + r * R * hsil, c_h2=c_h2 + 2 * r * R / P.D["H2"])


def s_crit(W=P.W_SLIT, gamma=GAMMA_60C, p_vap=P_VAP_60C, p_atm=P_ATM):
    return (p_atm + 2 * gamma / W - p_vap) / p_atm
