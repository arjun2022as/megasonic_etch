"""Stable cavitation of an H2 bubble trapped in the slit ("bubble pumping"), normal incidence (flat wafer).

At 90 deg the sound only moves the liquid along the wafer normal, so a slit full of liquid just breathes by
compression (~2 nm, acoustics.compression_pumping). A gas bubble trapped in the slit is a soft spring:
the acoustic pressure at the wafer makes it pulsate (stable cavitation, below the transient threshold),
and the pulsation pumps the liquid column between the bubble and the mouth up and down.

Chain of formulas (each checked in tests/test_cavitation.py by an independent route):
  1. Acoustic pressure at the wafer: p_a = |1 + R| sqrt(2 rho c I) (acoustics.wall_velocities). The
     wavelength (1.5 mm at 1 MHz) >> slit depth, so the whole slit sees the same p_a.
  2. Gas in a bubble filling the slit width W_b: p_g = p_atm + 2 gamma / W_b - p_vap (Laplace pressure of a
     cylindrical meniscus of radius W_b / 2; vapour taken out). Pulsation is isothermal (thermal diffusion
     length in the gas at MHz ~1 um >> bubble), kappa = 1. Stable if p_a < p_g (gas never in tension).
  3. Lumped column, per metre of slit length (2D): the pressure p_a at the mouth drives the volume flux Q
     against Poiseuille resistance R = 12 mu z / W^3, inertance M = rho z / W and the bubble spring
     K = kappa p_g / A_b (A_b = W l_b, bubble area in the plane):  p_a = (R + i(omega M - K/omega)) Q.
     Mean velocity U = Q / W, displacement xi = U / omega.
  4. Mixing by the oscillating Poiseuille flow (Womersley (W/2) sqrt(omega/nu) = 0.2-0.3: quasi-steady
     profile u = 1.5 U (1 - x^2/h^2) cos(omega t), h = W/2): Taylor-Aris dispersion of an oscillating flow
     (Watson 1983 method). The cross-channel deviation g solves  i omega g - D g'' = -u'(x),  g'(+-h) = 0,
     and D_disp = -1/2 Re <u' conj(g)>  (time and cross-section average). Closed form below; in the
     slow limit omega h^2 / D -> 0 it tends to 1/2 (2/105) U^2 h^2 / D (half the steady Taylor value).
     D_disp depends on the species (~1/D): the slow silicate gains most. Unlike D_osc it is not equal for
     all species, so strictly it carries a small current; ignored here (ASSUMED small).
The column moves only between the mouth and the bubble top; the liquid below a bubble that fills the
width is sealed off from the mouth (ASSUMED: no wetting film past the bubble).
"""
import cmath
import math

from . import acoustics as A
from .props import GAMMA_60C, P_ATM, P_VAP_60C
from .props import D, MU_L, RHO_L, W_SLIT

KAPPA = 1.0                 # isothermal pulsation


def gas_pressure(W_b=W_SLIT, gamma=GAMMA_60C, p_atm=P_ATM, p_vap=P_VAP_60C):
    return p_atm + 2 * gamma / W_b - p_vap


def pumping(f, I_w_cm2, z_top, l_b, W=W_SLIT, theta=90.0, mu=MU_L, rho=RHO_L, kappa=KAPPA):
    """Liquid motion driven by a bubble of length l_b whose top is at depth z_top below the mouth."""
    om = 2 * math.pi * f
    p_a = A.wall_velocities(I_w_cm2, theta)["p_wall"]
    p_g = gas_pressure(W)
    R = 12 * mu * z_top / W ** 3
    M = rho * z_top / W
    K = kappa * p_g / (W * l_b)
    Q = p_a / abs(complex(R, om * M - K / om))
    U = Q / W
    return dict(f=f, I=I_w_cm2, z_top=z_top, l_b=l_b, p_a=p_a, p_gas=p_g, stable=p_a < p_g, R=R, M=M, K=K,
                Q=Q, U=U, xi=U / om, dV_over_V=Q / (om * W * l_b), womersley=A.womersley(W, f),
                f_res=math.sqrt(K / M) / (2 * math.pi), damping_ratio=R / (2 * math.sqrt(K * M)))


def taylor_steady(U, W=W_SLIT, Dm=D["OH"]):
    """Steady plane-Poiseuille Taylor-Aris dispersion, mean velocity U, half-width h = W/2."""
    h = W / 2
    return 2.0 / 105.0 * U * U * h * h / Dm


def oscillatory_dispersion(U, f, W=W_SLIT, Dm=D["OH"]):
    """Time-averaged extra axial dispersion of u = 1.5 U (1 - x^2/h^2) cos(omega t) in a channel of width W."""
    h, om = W / 2, 2 * math.pi * f
    if om * h * h / Dm < 1e-3:                       # closed form loses digits (1/k^3 cancellation)
        return 0.5 * taylor_steady(U, W, Dm)
    a, b = U / 2, -1.5 * U / (h * h)                 # u' = u - mean = a + b x^2
    k = cmath.sqrt(1j * om / Dm)
    B = -b / (Dm * k * k)                            # g = A0 + B x^2 + C cosh(k x)
    A0 = (2 * B - a / Dm) / (k * k)
    C = -2 * B * h / (k * cmath.sinh(k * h))
    Ac, Bc, Cc, kc = A0.conjugate(), B.conjugate(), C.conjugate(), k.conjugate()
    s, c = cmath.sinh(kc * h), cmath.cosh(kc * h)
    i1 = Ac * (a * h + b * h ** 3 / 3)               # = 0: <u'> = 0
    i2 = Bc * (a * h ** 3 / 3 + b * h ** 5 / 5)
    i3 = Cc * (a * s / kc + b * (h * h * s / kc - 2 * h * c / kc ** 2 + 2 * s / kc ** 3))
    return -0.5 * ((i1 + i2 + i3) / h).real


def table(freqs=(1e6, 2e6, 3e6), powers=(0.5, 1.0, 2.0), bubbles=((9e-6, 1e-6), (5e-6, 1e-6), (1e-6, 1e-6),
                                                                    (9.5e-6, 0.5e-6), (8e-6, 2e-6))):
    """Rows for every frequency x power x (z_top, l_b): pumping and the dispersion of each species."""
    rows = []
    for z_top, l_b in bubbles:
        for f in freqs:
            for I in powers:
                r = pumping(f, I, z_top, l_b)
                for sp in ("OH", "SIL", "H2"):
                    dd = oscillatory_dispersion(r["U"], f, Dm=D[sp])
                    r[f"D_disp_{sp}"] = dd
                    r[f"D_disp_over_D_{sp}"] = dd / D[sp]
                rows.append(r)
    return rows
