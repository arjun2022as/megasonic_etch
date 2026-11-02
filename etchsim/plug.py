"""Growing H2 plug on the slit floor: nucleate -> grow -> vent at the mouth -> refill -> nucleate again (1D, transient).

The 2D Fluent bubble cases hold the plug at a fixed size and only report how fast it would grow. Here the plug
really grows. Same physics as the 1D slit model (etchsim/slit1d.py: Nernst-Planck with zero current, power-law
wall reaction), plus:
  * time-dependent:  dc_i/dt = -dN_i/dz + nu_i r 2 f_poly / W   (implicit Euler)
  * the plug fills the width from its top at depth b(t) down to the floor (L); the poly-Si under it is dry.
  * plug top: OH-, silicate no flux; H2 held at c* = c_sat p_g/p_atm (Henry, 13.9x sat), as in the Fluent UDF.
  * growth: the gas taken up, N_H2(b) [mol/m2/s], adds volume at the gas density rho_g = p_g/(R T):
        db/dt = -N_H2(b) / rho_g                     (N_H2 < 0, i.e. a dissolving plug, shrinks it)
    The growing plug pushes the liquid above it out of the mouth at speed |db/dt| (plug flow); handled by
    moving the liquid with the plug top each step (semi-Lagrangian shift, exact for uniform speed).
  * nucleation: when the dissolved H2 anywhere exceeds s_nuc x saturation, a plug of length l0 forms on the
    floor (ASSUMED: floor = where H2 is highest; s_nuc = 13.9 means a gas pocket of plug size is available,
    e.g. in a crevice; seeds smaller than the width need more, ~27x for a 50 nm sphere).
  * venting: when the plug top comes within b_vent = 100 nm of the mouth the meniscus touches the film above the wafer
    and the gas leaves (ASSUMED); the slit refills with liquid of mouth composition (capillary refill ~20 us,
    treated as instant).
  * mouth: concentrations fixed at the values from the 1D wafer-level model (same as the 2D cases; ASSUMED
    unaffected by the slit's own breathing).
  * sound (optional): the pulsating plug pumps the liquid column above it (etchsim/cavitation.py), recomputed
    every step for the current plug top and length (a longer plug is softer and pumps more).
  * realistic tool (optional): sound only while the slit is under the MegPie sector (duty = (T_rev, T_on)).
  * rectified diffusion (optional, rect=True): for a plug it reduces to one term. The gas meets the liquid only at
    its end meniscus, whose area does not change as the plug pulses (no "area effect"), and the liquid column
    moves rigidly with the meniscus, so the meniscus does not slide through the liquid (no "shell effect"; the
    flow-profile mixing is the pumping dispersion above). Left: the gas pressure p = p0 / (1 + eps cos wt)
    (isothermal, eps = dV/V) averages to p0 / sqrt(1 - eps^2), so the mean H2 at the meniscus is raised by that
    factor: slightly LESS intake (eps ~ 0.4-1.5 %: ~1e-4 relative).
  * early venting (optional, xi_vent=True): with sound on, the meniscus swings by xi (cavitation.pumping); once
    the swing reaches the mouth (b <= xi) the plug vents.
  * comb walls (optional, recess = R > 0): the poly-Si sits at the end of 50 nm pockets of depth R. Beside the
    plug the pockets stay full of liquid (gas cannot enter a gap narrower than the slit) and are cut off from the
    mouth: each keeps etching on its stored etchant, dc/dt = -2 r(c) / R (front area / pocket volume = 1/R), which
    for r = K (c/C)^n (n = 1/4) integrates exactly: c^(1-n) = c0^(1-n) - (1-n) 2 K / (R C^n) t
    (sealed_pocket()). Its H2 (2 r / R) goes into the plug through the pocket mouth (liquid there held at 13.9x).
    Open pockets exchange with the slit in ~R^2/D ~ 10 us, so they follow the local slit liquid (ASSUMED instant).
Not included (yet): the plug's Laplace pressure changing as it nears the mouth, plugs nucleating away from the
floor, wetting films past the plug.
Imposed oscillating flow and modelled mixing, not a full acoustic-streaming solution.
"""
import math

import numpy as np

from . import cavitation as CV
from . import props as P
from .slit1d import IONS, SPECIES, Slit, layer_mask

P_GAS = CV.gas_pressure(P.W_SLIT)
C_BUB = P.H2_SAT * P_GAS / P.P_ATM                 # 9.709 mol/m3, H2 at the plug surface
RHO_GAS = P_GAS / (P.R_GAS * P.T)                  # 507 mol/m3
S_PLUG = P_GAS / P.P_ATM                           # 13.9


def pump_fn(f, I, theta=90.0):
    """D_pump per species for a plug whose top is at b and length l_b (None: no sound)."""
    if not (f and I):
        return None

    def pump(b, l_b):
        U = CV.pumping(f, I, b, l_b, theta=theta)["U"]
        return {k: CV.oscillatory_dispersion(U, f, Dm=P.D[k]) for k in ("OH", "SIL", "H2", "TMA")}
    return pump


def pulsation(f, I, theta=90.0):
    """Pumping dispersion, meniscus swing xi and volume amplitude eps of a plug (top at b, length l_b)."""
    if not (f and I):
        return None

    def puls(b, l_b):
        r = CV.pumping(f, I, b, l_b, theta=theta)
        return dict(D={k: CV.oscillatory_dispersion(r["U"], f, Dm=P.D[k]) for k in ("OH", "SIL", "H2", "TMA")},
                    xi=r["xi"], eps=r["dV_over_V"])
    return puls


def sealed_pocket(c0, R, dt, er_ref=P.ER_REF, order=P.ORDER_OH, cb=P.C_BULK):
    """OH- left in a sealed pocket of depth R after time dt, starting from c0 (exact for the power-law rate)."""
    k = (1 - order) * 2 * P.si_flux(er_ref) / (R * cb ** order)
    return np.maximum(np.asarray(c0, float) ** (1 - order) - k * dt, 0.0) ** (1 / (1 - order))


def pocket_rate(c, er_ref=P.ER_REF, order=P.ORDER_OH, cb=P.C_BULK):
    """Front etch rate [mol Si/m2/s] in a pocket holding OH- at c (same law as the slit walls)."""
    return P.si_flux(er_ref) * (np.maximum(c, 0.0) / cb) ** order


def sound_on(t, duty):
    """duty = (T_rev, T_on): sound only during the first T_on of every revolution; None = always on."""
    return duty is None or (t % duty[0]) < duty[1]


class PlugSlit(Slit):
    """Liquid column between the mouth (z = 0) and the plug top or the floor (z = b), one implicit time step."""

    def __init__(self, b, surf, c_old, dt, plug, pump=None, dz=10e-9, c_bub=C_BUB):
        n = max(4, int(round(b / dz)))
        super().__init__(n=n, L=b, km=None)
        self.poly = layer_mask(self.zc)              # walls do not move: same layers at the same depth
        self.bulk = dict(surf)
        self.plug, self.dt, self.c_bub = plug, dt, c_bub
        self.pump = pump or {k: 0.0 for k in ("OH", "SIL", "H2", "TMA")}
        self.c_old = {s: np.interp(self.zc, *c_old[s]) for s in SPECIES}    # c_old[s] = (z, c)

    def fluxes(self, c, surf):
        ext = {s: np.concatenate(([surf[s]], c[s])) for s in SPECIES}
        zpos = np.concatenate(([0.0], self.zc))
        grad, mid = {}, {}
        for s in SPECIES:
            grad[s] = np.concatenate((np.diff(ext[s]) / np.diff(zpos), [0.0]))
            mid[s] = np.concatenate((0.5 * (ext[s][:-1] + ext[s][1:]), ext[s][-1:]))
        grad["TMA"] = grad["OH"] + 2 * grad["SIL"]
        mid["TMA"] = mid["OH"] + 2 * mid["SIL"]
        if self.migration:                           # zero current incl. pumping dispersion (as in etch.c)
            S = sum(P.Z[i] * (self.D[i] + self.pump[i]) * grad[i] for i in IONS)
            Q = sum(P.Z[i] ** 2 * self.D[i] * np.maximum(mid[i], 1e-12) for i in IONS)
            ratio = S / Q
        else:
            ratio = np.zeros(self.n + 1)
        N = {}
        for s in SPECIES:
            N[s] = -(self.D[s] + self.pump[s]) * grad[s] + P.Z[s] * self.D[s] * mid[s] * ratio
            N[s][-1] = 0.0
        if self.plug:                                # H2 into the plug across the half cell next to it
            N["H2"][-1] = -(self.D["H2"] + self.pump["H2"]) * (self.c_bub - c["H2"][-1]) / (0.5 * self.dz)
        return N, ratio

    def residual(self, x, surf):
        c = self._unpack(x)
        acc = np.concatenate([(c[s] - self.c_old[s]) / self.dt for s in SPECIES])
        return super().residual(x, surf) + acc


def layer_rates(z, er, L=P.L_SLIT):
    """Mean of a per-cell etch rate over each poly-Si layer (depth order)."""
    k = np.floor(z / P.LAYER).astype(int)
    poly = layer_mask(z) > 0
    ks = np.unique(k[poly])
    return (ks + 0.5) * P.LAYER, np.array([er[(k == kk) & poly].mean() for kk in ks])


def simulate(surf, pump=None, t_end=0.3, s_nuc=S_PLUG, l0=P.W_SLIT, b_vent=2 * P.LAYER, dz=10e-9, dt_max=1e-3,
             max_move=2.0, L=P.L_SLIT, log=None, sound=None, duty=None, rect=False, xi_vent=False, recess=0.0):
    """Run the nucleate-grow-vent cycle from a freshly refilled slit (liquid = mouth composition) at t = 0.

    s_nuc = inf: no bubbles (control). max_move: largest plug-top step per time step, in cells.
    sound = pulsation(f, I, theta) replaces `pump` and enables duty (intermittent sound), rect and xi_vent.
    recess > 0: comb walls; pockets beside the plug keep etching on stored etchant (sealed_pocket).
    Returns the plug history, events and the time-averaged etch rate of every poly-Si layer.
    """
    zref = (np.arange(int(round(L / dz))) + 0.5) * dz             # fixed reference grid for averages
    fresh = {s: (np.array([0.0, L]), np.array([surf[s], surf[s]])) for s in SPECIES}
    state, b, plug, t, dt = fresh, L, False, 0.0, 1e-6
    hist, events, vents = [], [], []
    er_int = np.zeros_like(zref)
    poly_ref = layer_mask(zref)
    cp = np.full_like(zref, surf["OH"])                            # OH- in each pocket (comb walls)
    x = None
    if duty:
        dt_max = min(dt_max, duty[1] / 10)                         # resolve the on/off switching
    while t < t_end - 1e-15:
        dt = min(dt, t_end - t)
        on = sound is not None and plug and sound_on(t, duty)
        sv = sound(b, L - b) if on else None
        pd = sv["D"] if on else (pump(b, L - b) if (pump and plug) else None)
        cb = C_BUB / np.sqrt(1 - sv["eps"] ** 2) if (on and rect) else C_BUB
        s = PlugSlit(b, surf, state, dt, plug, pd, dz, cb)
        res = s.solve(guess=(x, surf) if x is not None and len(x) == 3 * s.n else
                      (np.concatenate([s.c_old[k] for k in SPECIES]), surf))
        c = res["c"]
        N_in = res["N"]["H2"][-1] if plug else 0.0                # mol/m2/s into the plug
        er_cells = np.interp(zref, s.zc, res["er"]) * (zref < b)    # dry under the plug (flat walls)
        if recess > 0:
            sealed = plug & (zref >= b)
            c_mid = sealed_pocket(cp, recess, 0.5 * dt)             # rate at the step's midpoint
            r_p = pocket_rate(c_mid) * poly_ref * sealed
            N_in = N_in + (2 * r_p * 2 * dz).sum() / P.W_SLIT        # pocket H2 into the plug, per slit area
            er_cells = er_cells + r_p / P.si_flux(1.0)
            cp = np.where(sealed, sealed_pocket(cp, recess, dt), np.interp(zref, s.zc, c["OH"]))
        growth = N_in / RHO_GAS                                     # m/s, plug length
        er_int += er_cells * dt
        t += dt
        h2max = c["H2"].max()
        hist.append(dict(t=t, b=b, plug=plug, l_b=L - b if plug else 0.0, H2_in=N_in * P.W_SLIT, growth=growth,
                         s_max=h2max / P.H2_SAT, sound=bool(on)))
        # ---- events and the next state
        pz = np.concatenate(([0.0], s.zc, [b]))                    # profile points incl. mouth and bottom
        pc = {k: np.concatenate(([surf[k]], c[k], c[k][-1:])) for k in SPECIES}
        if not plug and h2max > s_nuc * P.H2_SAT:                   # nucleate a plug on the floor
            plug, b = True, L - l0
            events.append(("nucleate", t))
            state, dt, x = {k: (pz, pc[k]) for k in SPECIES}, 1e-6, None
        elif plug:
            shift = growth * dt                                     # > 0: plug top rises, liquid pushed out
            b_new = b - shift
            if b_new <= max(b_vent, sv["xi"] if (on and xi_vent) else 0.0):   # reaches the mouth: vent
                events.append(("vent", t))
                vents.append((t, er_int.copy()))
                plug, b, state, dt, x = False, L, fresh, 1e-6, None
            elif b_new >= L - 1e-12:                                # dissolved completely
                events.append(("dissolve", t))
                plug, b, x = False, L, None
                state = {k: (pz, pc[k]) for k in SPECIES}
            else:                                                   # liquid moves with the plug top
                zs = pz - shift                                     # (out of the mouth if shift > 0,
                keep = zs > 0                                       #  mouth liquid comes in if < 0)
                state = {k: (np.concatenate(([0.0], zs[keep])), np.concatenate(([surf[k]], pc[k][keep])))
                         for k in SPECIES}
                b, x = b_new, None
                cap = max_move * dz / max(abs(growth), 1e-30)
                dt = min(dt * 1.5, dt_max, cap)
        else:
            state = {k: (pz, pc[k]) for k in SPECIES}
            x = np.concatenate([c[k] for k in SPECIES])
            dt = min(dt * 1.5, dt_max)
        if log and len(hist) % 200 == 0:
            log(f"t {t * 1e3:7.2f} ms  plug {plug!s:5}  top {b * 1e6:6.3f} um  growth {growth * 1e6:7.1f} um/s  "
                f"S_max {h2max / P.H2_SAT:6.1f}")
    if len(vents) >= 2:                                             # average over whole cycles
        (t0, e0), (t1, e1) = vents[0], vents[-1]
        er_avg, span = (e1 - e0) / (t1 - t0), (t0, t1)
    else:
        er_avg, span = er_int / t_end, (0.0, t_end)
    zl, erl = layer_rates(zref, er_avg)
    return dict(hist=hist, events=events, z_layer=zl, er_layer=erl, t_end=t_end, avg_span=span)


def summarise(run, t_from=None):
    """Cycle period, mean growth, time-averaged top/bottom etch (top/bottom 5 % of poly layers)."""
    ev = run["events"]
    vents = [t for e, t in ev if e == "vent"]
    nucs = [t for e, t in ev if e == "nucleate"]
    period = float(np.mean(np.diff(vents))) if len(vents) > 1 else float("nan")
    grows = [h["growth"] for h in run["hist"] if h["plug"]]
    er = run["er_layer"]
    n5 = max(1, len(er) // 20)
    top, bot = er[:n5].mean(), er[-n5:].mean()
    plug_frac = sum(1 for h in run["hist"] if h["plug"]) / max(1, len(run["hist"]))
    return dict(n_vent=len(vents), n_nucleate=len(nucs), first_nucleation_ms=nucs[0] * 1e3 if nucs else math.nan,
                period_ms=period * 1e3, growth_median_um_s=float(np.median(grows)) * 1e6 if grows else 0.0,
                growth_max_um_s=float(np.max(grows)) * 1e6 if grows else 0.0,
                s_max=max(h["s_max"] for h in run["hist"]),
                er_top_nm_min=top * 6e10, er_bottom_nm_min=bot * 6e10, uniformity=bot / top if top > 0 else math.nan,
                plug_steps_fraction=plug_frac)
