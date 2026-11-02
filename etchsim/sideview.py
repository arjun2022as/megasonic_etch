"""Side view of the trench: depth z (0 = mouth .. L = floor) x length y along the trench, averaged over the width W.

Why: the 2D Fluent model is a cross-section, so any bubble there is a gas sheet along the WHOLE trench length
and seals it. A real bubble in a long trench is a finite "pancake" squeezed between the two walls (it fills the
100 nm width, Laplace pressure set by the width, 13.9x saturation at its surface) and liquid reaches the floor
around its sides. This model lets such pancakes grow, vent and re-form, to see how much they really block.

Model (same chemistry as the 1D slit, etchsim/slit1d.py):
  * unknowns c_OH, c_SIL, c_H2 on a (z, y) grid; Nernst-Planck with zero current on every face (z and y).
  * dc/dt = -div N + nu r 2 f_poly / W, implicit Euler; poly-Si smeared: f_poly = 1/2 on every cell (the 50 nm
    layer alternation is below the grid; smearing lowers bottom/top by ~0.003 vs layered walls in 1D).
  * comb wall (recess R > 0): rate and H2 taken at the pocket front (etchsim/pocket.front).
  * mouth (z = 0): fixed concentrations (1D wafer-level values, as in the 2D cases).
  * floor and both ends of the domain: no flux. The domain is half the spacing s between nucleation sites along
    the trench (symmetry), bubble centred at y = 0 on the floor.
  * bubble: half-disc of radius R_b on the floor (in the z-y plane), filling the width. Cells inside are gas
    (no liquid, no etch). Bubble faces: OH-, silicate no flux; H2 held at c* = 13.9 c_sat (Henry, as in Fluent).
    Gas area grows dA/dt = (H2 in, per unit width) / rho_g; isotropic growth (ASSUMED: real bubbles grow
    fastest where the liquid is richest). When R_b exceeds s/2 neighbouring pancakes merge into a sheet.
  * nucleation when max H2 > s_nuc c_sat (one site per spacing s, on the floor, ASSUMED); venting when the
    bubble top is within b_vent of the mouth; the trench refills with mouth liquid (instant, ASSUMED).
  * not included: liquid displaced by the growing bubble (Peclet ~0.15), pumping by the pulsating bubble
    (negligible at the floor), rectified diffusion, meniscus pinning on the comb.
Imposed oscillating flow and modelled mixing (via the mouth values), not a full acoustic-streaming solution.
"""
import math

import numpy as np

from . import props as P
from .plug import C_BUB, RHO_GAS, S_PLUG
from .pocket import front

SP = ("OH", "SIL", "H2")
EPS = 1e-6
OFFS = ((0, 0), (1, 0), (-1, 0), (0, 1), (0, -1))


def rate(c_oh, er_ref=P.ER_REF, order=P.ORDER_OH, cb=P.C_BULK):
    c = np.maximum(c_oh, 0.0)
    return P.si_flux(er_ref) * (c / cb) ** order * c / (c + EPS * cb)


def half_disc_area(R, L, ymax, n=400):
    """Area of {y in [0, ymax], depth from the floor < sqrt(R^2 - y^2)} capped at L (one half of the bubble)."""
    y = (np.arange(n) + 0.5) * min(R, ymax) / n
    return float(np.minimum(np.sqrt(np.maximum(R * R - y * y, 0.0)), L).sum() * min(R, ymax) / n)


def radius_for_area(A, L, ymax):
    lo, hi = 0.0, math.hypot(L, ymax) * 1.0001
    for _ in range(60):
        mid = 0.5 * (lo + hi)
        lo, hi = (mid, hi) if half_disc_area(mid, L, ymax) < A else (lo, mid)
    return 0.5 * (lo + hi)


class SideView:
    def __init__(self, surf, spacing=20e-6, L=P.L_SLIT, dz=100e-9, dy=200e-9, recess=0.0, f_poly=0.5,
                 W=P.W_SLIT, migration=True):
        self.L, self.ymax, self.W, self.f, self.R, self.migration = L, spacing / 2, W, f_poly, recess, migration
        self.nz, self.ny = int(round(L / dz)), max(1, int(round(spacing / 2 / dy)))
        self.dz, self.dy = L / self.nz, spacing / 2 / self.ny
        self.zc = (np.arange(self.nz) + 0.5) * self.dz
        self.yc = (np.arange(self.ny) + 0.5) * self.dy
        self.surf = dict(surf)
        self.D = dict(P.D)
        self.gas = np.zeros((self.nz, self.ny), bool)
        self.n = self.nz * self.ny

    # ---------------------------------------------------------------- geometry
    def set_bubble(self, Rb):
        Z, Y = np.meshgrid(self.L - self.zc, self.yc, indexing="ij")    # height above the floor, y
        self.gas = (Z * Z + Y * Y < Rb * Rb) if Rb > 0 else np.zeros((self.nz, self.ny), bool)

    # ---------------------------------------------------------------- physics
    def wall(self, c):
        if self.R > 0:
            return front(c["OH"], c["SIL"], c["H2"], np.full(c["OH"].shape, self.R), rate)
        return dict(r=rate(c["OH"]), c_h2=c["H2"])

    def _np_flux(self, ca, cb, d):
        """Nernst-Planck fluxes a -> b for every species, arrays of faces; d = centre distance."""
        g = {s: (cb[s] - ca[s]) / d for s in SP}
        m = {s: 0.5 * (ca[s] + cb[s]) for s in SP}
        g["TMA"], m["TMA"] = g["OH"] + 2 * g["SIL"], m["OH"] + 2 * m["SIL"]
        if self.migration:
            S = sum(P.Z[i] * self.D[i] * g[i] for i in ("OH", "SIL", "TMA"))
            Q = sum(P.Z[i] ** 2 * self.D[i] * np.maximum(m[i], 1e-12) for i in ("OH", "SIL", "TMA"))
            ratio = S / Q
        else:
            ratio = 0.0
        return {s: -self.D[s] * g[s] + P.Z[s] * self.D[s] * m[s] * ratio for s in SP}

    def _faces(self, c, axis):
        """Fluxes on interior faces along axis (0: z, 1: y), with gas cells on either side handled."""
        sl_a = (slice(None, -1), slice(None)) if axis == 0 else (slice(None), slice(None, -1))
        sl_b = (slice(1, None), slice(None)) if axis == 0 else (slice(None), slice(1, None))
        d = self.dz if axis == 0 else self.dy
        ca, cb = {s: c[s][sl_a] for s in SP}, {s: c[s][sl_b] for s in SP}
        ga, gb = self.gas[sl_a], self.gas[sl_b]
        N = self._np_flux(ca, cb, d)
        both = ~ga & ~gb
        for s in SP:
            N[s] = np.where(both, N[s], 0.0)
        # liquid a | gas b: H2 into the gas (positive a -> b); gas a | liquid b: negative
        N["H2"] = N["H2"] + np.where(~ga & gb, -self.D["H2"] * (C_BUB - ca["H2"]) / (0.5 * d), 0.0)
        N["H2"] = N["H2"] + np.where(ga & ~gb, -self.D["H2"] * (cb["H2"] - C_BUB) / (0.5 * d), 0.0)
        return N

    def residual(self, x, c_old, dt):
        c = self.unpack(x)
        Nz = self._faces(c, 0)                                         # (nz-1, ny)
        Ny = self._faces(c, 1)                                         # (nz, ny-1)
        top = {s: c[s][0] for s in SP}
        Nm = self._np_flux({s: np.full(self.ny, self.surf[s]) for s in SP}, top, 0.5 * self.dz)   # mouth, into
        for s in SP:
            Nm[s] = np.where(self.gas[0], 0.0, Nm[s])
        w = self.wall(c)
        src = 2 * self.f * w["r"] / self.W
        out = []
        for s in SP:
            div = np.zeros((self.nz, self.ny))
            div[:-1] += Nz[s] / self.dz
            div[1:] -= Nz[s] / self.dz
            div[0] -= Nm[s] / self.dz
            if self.ny > 1:
                div[:, :-1] += Ny[s] / self.dy
                div[:, 1:] -= Ny[s] / self.dy
            res = (c[s] - c_old[s]) / dt + div - P.NU_RXN[s] * src
            out.append(np.where(self.gas, c[s] - c_old[s], res).ravel())
        return np.concatenate(out)

    def unpack(self, x):
        return {s: x[k * self.n:(k + 1) * self.n].reshape(self.nz, self.ny) for k, s in enumerate(SP)}

    def pack(self, c):
        return np.concatenate([c[s].ravel() for s in SP])

    def step(self, c_old, dt, tol=1e-9, max_newton=50):
        from scipy.sparse import csc_matrix
        from scipy.sparse.linalg import spsolve
        nz, ny, n = self.nz, self.ny, self.n
        x = self.pack(c_old)
        xo = {s: c_old[s] for s in SP}
        I, J = np.meshgrid(np.arange(nz), np.arange(ny), indexing="ij")
        colour = ((I + 2 * J) % 5).ravel()                             # 5-point stencils never share a colour
        h = 1e-7 * P.C_BULK
        for _ in range(max_newton):
            F0 = self.residual(x, xo, dt)
            rows, cols, vals = [], [], []
            for sp in range(3):
                for col in range(5):
                    cells = np.nonzero(colour == col)[0]
                    if not len(cells):
                        continue
                    xp = x.copy()
                    xp[sp * n + cells] += h
                    dF = (self.residual(xp, xo, dt) - F0) / h
                    ci, cj = cells // ny, cells % ny
                    for di, dj in OFFS:
                        qi, qj = ci + di, cj + dj
                        ok = (qi >= 0) & (qi < nz) & (qj >= 0) & (qj < ny)
                        q = qi[ok] * ny + qj[ok]
                        for s2 in range(3):
                            rr = s2 * n + q
                            v = dF[rr]
                            nzm = v != 0.0
                            rows.append(rr[nzm])
                            cols.append(sp * n + cells[ok][nzm])
                            vals.append(v[nzm])
            Jm = csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))), shape=(3 * n, 3 * n))
            dx = spsolve(Jm, -F0)
            lam = 1.0
            while lam > 1e-4 and (x[:n] + lam * dx[:n]).min() < -1e-9 * P.C_BULK:
                lam *= 0.5
            x = x + lam * dx
            if np.abs(dx).max() < tol * P.C_BULK:
                break
        else:
            raise RuntimeError("Newton did not converge")
        return self.unpack(x)

    # ---------------------------------------------------------------- outputs
    def outputs(self, c):
        w = self.wall(c)
        er = np.where(self.gas, 0.0, w["r"] / P.si_flux(1.0))          # m/s
        Nz = self._faces(c, 0)
        Ny = self._faces(c, 1)
        ga = self.gas
        h2_in = 0.0                                                     # mol/s per m of width-depth plane / W
        h2_in += (Nz["H2"] * (~ga[:-1] & ga[1:])).sum() * self.dy - (Nz["H2"] * (ga[:-1] & ~ga[1:])).sum() * self.dy
        if self.ny > 1:
            h2_in += (Ny["H2"] * (~ga[:, :-1] & ga[:, 1:])).sum() * self.dz
            h2_in -= (Ny["H2"] * (ga[:, :-1] & ~ga[:, 1:])).sum() * self.dz
        s_max = np.where(self.gas, 0.0, w["c_h2"]).max() / P.H2_SAT
        return er, h2_in, s_max


def simulate(surf, spacing=20e-6, t_end=0.3, s_nuc=S_PLUG, recess=0.0, R0=200e-9, b_vent=200e-9, dz=100e-9,
             dy=200e-9, dt_max=1e-3, log=None):
    """Nucleate -> grow -> vent cycles of pancake bubbles spaced `spacing` along the trench (half domain)."""
    sv = SideView(surf, spacing, dz=dz, dy=dy, recess=recess)
    fresh = {s: np.full((sv.nz, sv.ny), surf[s]) for s in SP}
    c, A, Rb, t, dt = {s: v.copy() for s, v in fresh.items()}, 0.0, 0.0, 0.0, 1e-5
    hist, events, vents = [], [], []
    er_int = np.zeros((sv.nz, sv.ny))
    while t < t_end - 1e-15:
        dt = min(dt, t_end - t)
        sv.set_bubble(Rb)
        c = sv.step(c, dt)
        er, h2_in, s_max = sv.outputs(c)
        er_int += er * dt
        t += dt
        hist.append(dict(t=t, Rb=Rb, h2_in=h2_in, s_max=s_max, blocked_floor=float(sv.gas[-1].mean()),
                         blocked_area=float(sv.gas.mean())))
        if Rb == 0.0 and s_max > s_nuc:                                 # nucleate on the floor at y = 0
            Rb = R0
            A = half_disc_area(Rb, sv.L, sv.ymax)
            events.append(("nucleate", t))
            dt = 1e-5
        elif Rb > 0.0:
            A_new = max(A + h2_in / RHO_GAS * dt, 0.0)                  # area in this half domain
            R_new = radius_for_area(A_new, sv.L, sv.ymax) if A_new > 0 else 0.0
            if R_new >= sv.L - b_vent:                                  # top reaches the mouth: vent, refill
                events.append(("vent", t))
                vents.append((t, er_int.copy()))
                Rb, A, dt = 0.0, 0.0, 1e-5
                c = {s: v.copy() for s, v in fresh.items()}
                continue
            if R_new <= 0.0:
                events.append(("dissolve", t))
            dR = abs(R_new - Rb)
            Rb, A = R_new, A_new
            dt = min(dt * 1.5, dt_max, dt * max(dz, dy) / dR if dR > 0 else dt_max)
        else:
            dt = min(dt * 1.5, dt_max)
        if log and len(hist) % 50 == 0:
            log(f"t {t * 1e3:7.2f} ms  bubble radius {Rb * 1e6:6.2f} um  floor blocked {100 * hist[-1]['blocked_floor']:5.1f} %"
                f"  S_max {s_max:6.1f}")
    if len(vents) >= 2:
        (t0, e0), (t1, e1) = vents[0], vents[-1]
        er_avg, span = (e1 - e0) / (t1 - t0), (t0, t1)
    else:
        er_avg, span = er_int / t_end, (0.0, t_end)
    return dict(sv=sv, hist=hist, events=events, er_map=er_avg, er_depth=er_avg.mean(axis=1), z=sv.zc, y=sv.yc,
                span=span, spacing=spacing)


def summarise(run):
    er = run["er_depth"]
    n5 = max(1, len(er) // 20)
    top, bot = er[:n5].mean(), er[-n5:].mean()
    vents = [t for e, t in run["events"] if e == "vent"]
    h = run["hist"]
    tt = np.array([x["t"] for x in h])
    dts = np.diff(np.concatenate(([0.0], tt)))
    return dict(spacing_um=run["spacing"] * 1e6, n_vent=len(vents),
                period_ms=float(np.mean(np.diff(vents))) * 1e3 if len(vents) > 1 else float("nan"),
                floor_blocked_time_avg=float(sum(x["blocked_floor"] * d for x, d in zip(h, dts)) / tt[-1]),
                s_max=max(x["s_max"] for x in h), er_top_nm_min=top * 6e10, er_bottom_nm_min=bot * 6e10,
                uniformity=bot / top if top > 0 else float("nan"))
