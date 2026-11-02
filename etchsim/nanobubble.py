"""Case 5: small H2 bubbles that stay smaller than a plug (sub-plug bubbles).

A FREE round bubble of radius r in liquid at saturation S (= c_H2 / c_sat) is in balance only when
    S_eq(r) = (p_atm + 2 gamma / r - p_vap) / p_atm                     (Laplace + Henry)
and that balance is unstable: slightly larger -> it needs less and runs away (to a plug in a 100 nm slit),
slightly smaller -> it dissolves. So free bubbles cannot stay small.

Bubbles that CAN stay small are PINNED surface nanobubbles (Lohse & Zhang, Phys. Rev. E 91, 031003, 2015): a gas
cap sitting on the wall whose footprint (contact radius L) is held by a rough spot or an edge. Adding gas cannot
widen the footprint, only bulge the cap, which shrinks its curvature radius R_c and raises its pressure until it
matches the liquid:
    R_c = 2 gamma / ((S - 1) p_atm + p_vap)            cap height h = R_c - sqrt(R_c^2 - L^2)
A balance exists only while the cap is at most a hemisphere, R_c >= L, i.e. while
    S <= S_max(L) = 1 + (2 gamma / L - p_vap) / p_atm   (= S_eq of a free bubble of radius L)
Above S_max(L) the cap bulges past a hemisphere, the contact line lets go and the bubble grows on into a plug.
L = 50 nm (half the slit width) gives S_max = 27x: the "cannot grow to 50 nm radius" condition.
ASSUMED: gamma of water at 60 C; caps on a sidewall, footprint set by roughness/pocket edges; gas outflux and
contact-angle hysteresis not included (they widen the stable range somewhat, so this is conservative).
"""
import math

from .props import GAMMA_60C, H2_SAT, P_ATM, P_VAP_60C, W_SLIT


def s_eq_free(r, gamma=GAMMA_60C):
    """Saturation in balance with a free round bubble of radius r (unstable balance)."""
    return (P_ATM + 2 * gamma / r - P_VAP_60C) / P_ATM


def s_max_pinned(L, gamma=GAMMA_60C):
    """Highest saturation at which a cap pinned on a footprint of radius L stays small (hemisphere limit)."""
    return s_eq_free(L, gamma)


def cap(S, L, gamma=GAMMA_60C):
    """Pinned cap in balance with liquid at saturation S: curvature radius, height, contact angle; None if it
    cannot stay small (S above S_max(L))."""
    Rc = 2 * gamma / ((S - 1) * P_ATM + P_VAP_60C)
    if Rc < L:
        return None
    h = Rc - math.sqrt(Rc * Rc - L * L)
    return dict(Rc=Rc, h=h, theta_deg=math.degrees(math.asin(L / Rc)), touches_far_wall=h >= W_SLIT)


def footprint_limit(S, gamma=GAMMA_60C):
    """Largest footprint radius that stays a small bubble at saturation S (= R_c)."""
    return 2 * gamma / ((S - 1) * P_ATM + P_VAP_60C)


def c_h2_limit(L):
    """Dissolved H2 [mM] above which a pinned bubble of footprint L runs away to a plug."""
    return s_max_pinned(L) * H2_SAT
