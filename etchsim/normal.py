"""Case 7: what a flat MegPie (normal incidence, 90 deg) can do ABOVE the wafer, i.e. to the liquid renewal at
the slit mouths (k_m), with the mechanisms the earlier model left out.

Why the earlier cases gave exactly zero at 90 deg: the only wafer-level sound effect in the model was the sideways
oscillation of the liquid along the wafer, u_t = U0 sin(beta) |1 + R| (acoustics.py), which adds D_osc = u_t^2/(2 w)
to the Levich film (run_1d.km_spin). At normal incidence beta = 0, so u_t = 0 and the mouth stays at 63x. The
in-slit 90 deg effects (compression breathing ~2 nm, plug pumping, rectified diffusion, early venting) were already
in case 4 and change the bottom etch by < 0.1 nm/min. What was missing is second-order (streaming) flow and the
bubbles in the gap, which need either a nonlinear acoustic solution of the mm-scale gap or bubble data.

Mechanisms estimated here (each an UPPER BOUND unless stated; numbers checked in tests/test_normal.py):
  1. Eckart (bulk-absorption) streaming. Force density F = 2 alpha I / c (alpha = amplitude absorption, ~f^2).
     In a gap h much thinner than the beam, a force normal to the walls is balanced by pressure; flow appears
     only where F changes sideways (beam edge, width w_e). Lubrication solution, wafer z = 0, transducer z = h:
         mu u'' = p0'(x) - F'(x) z,  u(0) = u(h) = 0,  no net sideways flux  ->  p0' = F' h / 2,
         u = (F'/mu) [ (h/4)(z^2 - h z) - (z^3 - h^2 z)/6 ],  wall shear G = F' h^2 / (12 mu),  F' = F / w_e.
  2. Beam-edge tangential oscillation. Where the wafer pressure p_w = |1 + R| p0 drops to 0 over w_e, the liquid
     oscillates sideways with U_e = p_w / (rho w w_e) (rho du/dt = -dp/dx). Treated exactly like oblique sound in
     the model (film D -> D + U_e^2 / (2 w)), plus its Rayleigh streaming u_R = 3 U_e^2 / (4 w w_e).
     Both act only on two edge strips of width w_e: a fraction 2 w_e / (2 pi r) of each revolution.
  3. Stable-cavitation bubbles at the wafer. Bubbles smaller than resonance (Minnaert, ~3 um at 1 MHz) are driven
     to the pressure antinode, which is the wafer (R = 0.86). Two effects, bubble numbers UNKNOWN (swept):
       a. microstreaming stirs a layer h_mix (a few bubble radii) next to the wafer;
       b. the bubbles take up dissolved H2 (they sit near 1x saturation): a sink k_sink = n_A 4 pi R D (Sh = 2,
          quiescent; microstreaming raises it) per wafer area, acting on H2 only.
     Sound only under the MegPie sector (duty 1/6 of a revolution, ASSUMED as in case 4). The film above the
     wafer is modelled as its Nernst layer delta_N = D / k_Levich (pure diffusion, c = 0 at delta_N), solved in time
     over many revolutions (film_cycle) so that the 0.3 s film memory against the 0.2 s revolution is resolved.
Result form: k multiplier m = (mouth H2 without sound) / (mouth H2 with sound), as time mean and as worst moment.

Near-wall formula used to put any wall flow on the Levich scale (high Schmidt number, Leveque):
    u_z ~ -C z^2 near the wall  ->  k = D^(2/3) C^(1/3) / (3^(1/3) Gamma(4/3))
rotating disk C = 0.51023 Omega^1.5 nu^-0.5 gives 0.6206 D^(2/3) nu^(-1/6) Omega^(1/2) (Levich's 0.620).
Imposed / estimated flows, not a full acoustic-streaming solution.
"""
import math

import numpy as np

from . import acoustics as A
from . import props as P

GAP = 2e-3                     # m, MegPie-to-wafer liquid gap, ASSUMED (same as fluent2d/params.py)
ALPHA_F2 = 10.5e-15            # s2/m, amplitude absorption / f^2 of water at 60 C, ASSUMED from Pinkerton (1949)
                               # (25.3e-15 at 20 C, falls with T); 5 wt% TMAH taken as water
T_REV = 60.0 / P.SPIN_RPM      # 0.2 s per revolution at 300 rpm
DUTY = 60.0 / 360.0            # MegPie sector 60 deg, ASSUMED (as case 4)
LEVEQUE = 3 ** (1 / 3) * math.gamma(4 / 3)      # 1.2879
C_KARMAN = 0.51023             # von Karman rotating disk, -H(zeta) ~ 0.51023 zeta^2 near the wall
HOMANN_FPP0 = 1.3119           # axisymmetric stagnation flow f''(0) (Homann 1936); checked by shooting in tests


def k_from_wall_curvature(C, d):
    """Mass-transfer coefficient for a wall flow with u_z = -C z^2 near the wall (Sc >> 1)."""
    return d ** (2 / 3) * C ** (1 / 3) / LEVEQUE


def k_rotating_disk(omega, d, nu=P.NU_L):
    return k_from_wall_curvature(C_KARMAN * omega ** 1.5 / math.sqrt(nu), d)


def k_stagnation(a, d, nu=P.NU_L, fpp0=HOMANN_FPP0):
    """Axisymmetric stagnation flow u_r = a r: near wall u_z = -fpp0 a^1.5 nu^-0.5 z^2 -> 0.850 D^2/3 nu^-1/6 a^1/2."""
    return k_from_wall_curvature(fpp0 * a ** 1.5 / math.sqrt(nu), d)


def k_leveque_patch(G, length, d):
    """Mean k over a patch of given length with wall shear rate G (Leveque, mean = 3/2 x local at the end)."""
    return 1.5 / math.gamma(4 / 3) / 9 ** (1 / 3) * (d * d * G / length) ** (1 / 3)


def homann_fpp0(eta_max=8.0):
    """Shooting solution of f''' + 2 f f'' - f'^2 + 1 = 0, f(0) = f'(0) = 0, f'(inf) = 1 (independent check)."""
    from scipy.integrate import solve_ivp
    from scipy.optimize import brentq

    def miss(s):
        sol = solve_ivp(lambda e, y: [y[1], y[2], -2 * y[0] * y[2] + y[1] ** 2 - 1], (0, eta_max), [0, 0, s],
                        rtol=1e-10, atol=1e-12)
        return sol.y[1, -1] - 1.0
    return brentq(miss, 1.0, 1.6, xtol=1e-10)


# ------------------------------------------------------------------------------------------- 1. Eckart streaming
def eckart(f, I_w_cm2, h=GAP, w_e=None, d=P.D["H2"], r=P.R_PROBE):
    """Edge-cell Eckart streaming in the gap and its effect on k at the wafer (upper bound: no reflection loss)."""
    w_e = w_e or P.C_SOUND / f
    I = I_w_cm2 * 1e4
    alpha = ALPHA_F2 * f * f
    F = 2 * alpha * I / P.C_SOUND                       # N/m3, travelling wave (standing wave: x (1 - R^2), less)
    dF = F / w_e
    G = dF * h * h / (12 * P.MU_L)
    z = np.linspace(0, h, 401)
    u = dF / P.MU_L * ((h / 4) * (z * z - h * z) - (z ** 3 - h * h * z) / 6)
    k_patch = k_leveque_patch(G, w_e, d)
    k_l = P.levich_km(d, P.omega_spin())
    frac = 2 * w_e / (2 * math.pi * r)                 # two edges per revolution, edge strip w_e wide
    return dict(f=f, I=I_w_cm2, alpha=alpha, F=F, w_e=w_e, G_wall=G, u_max=float(np.abs(u).max()),
                k_patch=k_patch, k_patch_over_levich=k_patch / k_l, time_fraction=frac,
                m_mean=1 + frac * k_patch / k_l)


def eckart_profile(F, w_e, h=GAP, n=401):
    dF = F / w_e
    z = np.linspace(0, h, n)
    return z, dF / P.MU_L * ((h / 4) * (z * z - h * z) - (z ** 3 - h * h * z) / 6)


# ------------------------------------------------------------------------------------------- 2. beam edge
def beam_edge(f, I_w_cm2, w_e=None, d=P.D["H2"], r=P.R_PROBE):
    """Sideways oscillation where the wafer pressure drops at the beam edge, used like oblique sound."""
    w_e = w_e or P.C_SOUND / f
    om = 2 * math.pi * f
    p_w = A.wall_velocities(I_w_cm2, 90.0)["p_wall"]
    U_e = p_w / (P.RHO_L * om * w_e)
    d_osc = U_e ** 2 / (2 * om)
    k_mult_local = ((d + d_osc) / d) ** (2 / 3)        # same rule as run_1d.km_spin (Levich with D + D_osc)
    u_R = 3 * U_e ** 2 / (4 * om * w_e)                 # Rayleigh streaming outside the Stokes layer
    G_R = u_R / A.stokes_delta(f)                       # upper bound: all of it as wall shear
    k_R = k_leveque_patch(G_R, w_e, d)
    k_l = P.levich_km(d, P.omega_spin())
    frac = 2 * w_e / (2 * math.pi * r)
    U_15 = A.wall_velocities(I_w_cm2, 15.0)["u_t"]
    return dict(f=f, I=I_w_cm2, w_e=w_e, p_wall=p_w, U_edge=U_e, U_t_15deg=U_15, D_osc=d_osc,
                k_mult_local=k_mult_local, u_rayleigh=u_R, k_rayleigh_over_levich=k_R / k_l, time_fraction=frac,
                m_mean=1 + frac * (k_mult_local - 1 + k_R / k_l))


# ------------------------------------------------------------------------------------------- 3. bubbles
def resonance_radius(f, gamma=P.GAMMA_60C, p0=P.P_ATM, p_v=P.P_VAP_60C, rho=P.RHO_L, kappa=1.0):
    """Minnaert radius with surface tension (isothermal kappa = 1 for um bubbles at MHz, ASSUMED):
    (2 pi f R)^2 rho = 3 kappa (p0 - p_v + 2 gamma / R) - 2 gamma / R."""
    from scipy.optimize import brentq
    om = 2 * math.pi * f
    g = lambda R: (om * R) ** 2 * rho - (3 * kappa * (p0 - p_v + 2 * gamma / R) - 2 * gamma / R)  # noqa: E731
    return brentq(g, 1e-8, 1e-3)


def bubble_sink_k(n_per_mm2, R, d=P.D["H2"], sh=2.0):
    """H2 uptake by n bubbles per mm2 of wafer, radius R: k_sink = n 4 pi R D (Sh / 2)."""
    return n_per_mm2 * 1e6 * 4 * math.pi * R * d * sh / 2


def bubble_level(R, gamma=P.GAMMA_60C):
    """H2 saturation a free bubble of radius R holds (Laplace + Henry), ~1.5x at 3 um."""
    return (P.P_ATM + 2 * gamma / R - P.P_VAP_60C) / P.P_ATM


def microstreaming_speed(f, R, eps):
    """Order of the steady microstreaming speed next to a bubble pulsating by eps R (Nyborg): u ~ eps^2 w R."""
    return eps * eps * 2 * math.pi * f * R


def seed_pulsation(R, I_w_cm2, f=1e6):
    """Relative radius swing of a small seed (far below resonance, isothermal): eps = p_a / (3 p_g)."""
    p_a = A.wall_velocities(I_w_cm2, 90.0)["p_wall"]
    p_g = P.P_ATM + 2 * P.GAMMA_60C / R - P.P_VAP_60C
    return dict(R=R, p_a=p_a, p_g=p_g, eps=p_a / (3 * p_g), stable=p_a < p_g)


# ------------------------------------------------------------------------------------------- film over the wafer
def film_cycle(duty=DUTY, t_rev=T_REV, h_mix=0.0, k_sink=0.0, s_bub=0.0, d=P.D["H2"], km=None, n=270, revs=12,
               steps=2400, mix=1e3):
    """Time-periodic H2 in the Nernst layer above the wafer (unit source J = 1 at the wafer, c = 0 at delta_N).

    While under the MegPie (first duty x t_rev of each revolution): D x mix in 0 < y < h_mix (bubble stirring) and
    a wall sink k_sink (c_wall - s_bub c0), c0 = J delta_N / D the no-sound wall value. Implicit Euler, cell-centred.
    Returns the wall value over the last revolution relative to c0, and the multipliers m = c0 / c_wall.
    """
    from scipy.sparse import diags
    from scipy.sparse.linalg import splu
    km = km or P.levich_km(d, P.omega_spin())
    dn = d / km
    dy = dn / n
    yf = np.arange(n + 1) * dy
    dt = t_rev / steps
    c0 = dn / d

    def matrix(on):
        Df = np.where((yf < h_mix) & on, d * mix, d)
        lo, di, up = np.zeros(n), np.zeros(n), np.zeros(n)
        for i in range(n):
            if i > 0:
                a = Df[i] / dy ** 2
                di[i] += a
                lo[i] = -a
            if i < n - 1:
                a = Df[i + 1] / dy ** 2
                di[i] += a
                up[i] = -a
            else:
                di[i] += Df[n] / (dy * dy / 2)                   # c = 0 at y = delta_N (half cell)
        # wall sink through the half cell next to the wall: flux k (c_w - c_b), c_w ~ c[0] (dy small vs delta)
        ks = k_sink if on else 0.0
        di[0] += ks / dy
        A_ = diags([lo[1:], 1 / dt + di, up[:-1]], [-1, 0, 1], format="csc")
        return splu(A_), Df[0], ks

    on_m, off_m = matrix(True), matrix(False)
    c = (dn - (np.arange(n) + 0.5) * dy) / d                    # start from the steady no-sound (Levich) profile
    rec_t, rec_c = [], []
    for k in range(revs * steps):
        t = (k % steps) * dt
        on = t < duty * t_rev
        lu, D0, ks = on_m if on else off_m
        rhs = c / dt
        rhs[0] += (1.0 + ks * s_bub * c0) / dy
        c = lu.solve(rhs)
        if k >= (revs - 1) * steps:
            cw = c[0] + (1.0 - ks * (c[0] - s_bub * c0)) * (dy / 2) / D0
            rec_t.append(t)
            rec_c.append(cw / c0)
    rc = np.array(rec_c)
    return dict(t=np.array(rec_t), c_wall=rc, mean=float(rc.mean()), max=float(rc.max()), min=float(rc.min()),
                m_mean=1 / float(rc.mean()), m_worst=1 / float(rc.max()), delta_N=dn, t_film=dn * dn / d)
