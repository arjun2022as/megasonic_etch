"""Megasonic field at the wafer and what reaches a 100 nm slit (linear acoustics, plane waves).

Conventions: theta = incidence angle measured from the wafer SURFACE (90 deg = normal, as under a
MegPie transducer parallel to the wafer). beta = 90 - theta is the angle from the surface normal.

Chain of formulas (each checked in tests/test_formulas.py against an independent route):
  1. Plane travelling wave of intensity I:  p0 = sqrt(2 rho c I),  U0 = p0 / (rho c).
  2. Reflection from the silicon wafer (fluid / isotropic elastic solid, Brekhovskikh):
        Z_f = rho c / cos(beta);  sin(g_L) = cL sin(beta) / c,  sin(g_S) = cS sin(beta) / c
        Z_L = rho_s cL / cos(g_L),  Z_S = rho_s cS / cos(g_S)
        R   = (Z_L cos^2(2 g_S) + Z_S sin^2(2 g_S) - Z_f) / (same + Z_f)
     Beyond a critical angle cos(g) is imaginary (evanescent wave in the solid) and |R| = 1.
  3. Velocity just outside the viscous layer (incident + reflected):
        tangential  u_t = U0 sin(beta) |1 + R|,   normal  u_n = U0 cos(beta) |1 - R|  (-> 0 at a rigid wall)
  4. Stokes layer: delta = sqrt(2 nu / omega); oscillating tangential flow over a wall
        u(y, t) = u_t Re{ (1 - exp(-(1 + i) y / delta)) exp(i omega t) }.
  5. Into the slit (width W): Womersley number a = (W/2) sqrt(omega / nu) < 1 -> quasi-steady Stokes flow;
     a flow driven across the mouth decays with depth like the slowest Stokes (Moffatt / Papkovich-Fadle)
     mode of a channel, |u| ~ u_mouth exp(-K y / W), K = 4.2124 (= 2 x 2.1062 for the half-width).
     u_mouth = |Stokes profile| at y = W/2 above the wall.
  6. Mixing by the oscillation: a particle displaced +-xi = |u|/omega each cycle while diffusing gives
     at most D_osc = |u|^2 / (2 omega) (upper bound of oscillatory dispersion). It is added to every
     species equally (mechanical dispersion carries no current).
  7. Compression pumping: the pressure antinode at the wafer (|1+R| p0) compresses the liquid in the slit;
     the volume breathed through the mouth per cycle gives a displacement L |1+R| p0 / (rho c^2).
"""
import cmath
import math

from .props import C_SOUND, NU_L, RHO_L

RHO_SI, CL_SI, CS_SI = 2330.0, 8433.0, 5843.0   # silicon (Si [100] longitudinal / shear speeds)
K_SLOT = 4.2124                                  # decay rate per width of the slowest Stokes channel mode


def plane_wave(I_w_cm2, rho=RHO_L, c=C_SOUND):
    I = I_w_cm2 * 1e4
    p0 = math.sqrt(2 * rho * c * I)
    return p0, p0 / (rho * c)


def _cos_from_sin(s):
    """cos of a possibly complex refraction angle, branch with an evanescent (decaying) solid wave."""
    c2 = 1 - s * s
    if c2 >= 0:
        return complex(math.sqrt(c2), 0.0)
    return complex(0.0, -math.sqrt(-c2))


def reflection(theta_deg, rho=RHO_L, c=C_SOUND, rho_s=RHO_SI, cl=CL_SI, cs=CS_SI):
    """Complex pressure reflection coefficient of a plane wave on an elastic half-space."""
    beta = math.radians(90.0 - theta_deg)
    sb, cb = math.sin(beta), math.cos(beta)
    zf = rho * c / cb if cb > 1e-12 else float("inf")
    if zf == float("inf"):
        return complex(-1.0, 0.0)            # grazing limit
    gl_s, gs_s = cl * sb / c, cs * sb / c
    cos_gl, cos_gs = _cos_from_sin(gl_s), _cos_from_sin(gs_s)
    zl = rho_s * cl / cos_gl
    zs = rho_s * cs / cos_gs if abs(cos_gs) > 1e-15 else complex(float("inf"))
    sin2gs = 2 * gs_s * cos_gs
    cos2gs = 1 - 2 * gs_s * gs_s
    ztot = zl * cos2gs ** 2 + (zs * sin2gs ** 2 if sin2gs != 0 else 0)
    return (ztot - zf) / (ztot + zf)


def wall_velocities(I_w_cm2, theta_deg):
    p0, U0 = plane_wave(I_w_cm2)
    R = reflection(theta_deg)
    beta = math.radians(90.0 - theta_deg)
    return dict(p0=p0, U0=U0, R=R, u_t=U0 * math.sin(beta) * abs(1 + R),
                u_n=U0 * math.cos(beta) * abs(1 - R), p_wall=p0 * abs(1 + R))


def stokes_delta(f, nu=NU_L):
    return math.sqrt(2 * nu / (2 * math.pi * f))


def stokes_amp(y, delta):
    """|1 - exp(-(1+i) y / delta)|: amplitude of the oscillating tangential flow at height y."""
    return abs(1 - cmath.exp(-(1 + 1j) * y / delta))


def womersley(W, f, nu=NU_L):
    return (W / 2) * math.sqrt(2 * math.pi * f / nu)


def slit_oscillation(I_w_cm2, theta_deg, f, W):
    """Megasonic quantities at a slit of width W: mouth velocity and the depth-decay of mixing."""
    wv = wall_velocities(I_w_cm2, theta_deg)
    delta = stokes_delta(f)
    u_mouth = wv["u_t"] * stokes_amp(W / 2, delta)
    omega = 2 * math.pi * f
    return dict(wv, f=f, delta=delta, womersley=womersley(W, f), u_mouth=u_mouth,
                d_osc_mouth=u_mouth ** 2 / (2 * omega), xi_mouth=u_mouth / omega,
                decay_length=W / K_SLOT)


def d_osc(y, osc, W):
    """Upper-bound oscillatory dispersion at depth y below the mouth."""
    u = osc["u_mouth"] * math.exp(-K_SLOT * y / W)
    return u * u / (2 * 2 * math.pi * osc["f"])


def compression_pumping(I_w_cm2, theta_deg, L, rho=RHO_L, c=C_SOUND):
    """Displacement amplitude at the mouth from compressing the liquid column of depth L."""
    p_wall = wall_velocities(I_w_cm2, theta_deg)["p_wall"]
    return L * p_wall / (rho * c * c)
