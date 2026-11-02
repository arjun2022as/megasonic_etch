"""Quasi-steady etchant transport in a deep slit, averaged over its width (1D in depth z).

Valid because the slit is thin: across-width diffusion takes W^2/D ~ 1e-6 s, along the depth L^2/D ~ 0.01 s,
and the etch front moves over minutes, so concentrations are uniform across the width and in steady state
for the current geometry (quasi-steady).

Unknowns c_OH, c_SIL, c_H2 [mol/m3]; TMA+ from electroneutrality: c_TMA = c_OH + 2 c_SIL.
Nernst-Planck flux, z positive into the slit:
    N_i = -(D_i + D_osc(z)) dc_i/dz + z_i D_i c_i (F/RT)(-dphi/dz)
Zero current (no external circuit; the wall reaction consumes 2 OH- and releases one SiO2(OH)2^2-, so it
carries no charge) together with electroneutrality gives the diffusion potential
    -(F/RT) dphi/dz = S / Q,   S = sum_j z_j D_j dc_j/dz,   Q = sum_j z_j^2 D_j c_j   (j over ions)
so the migration velocity of ion i is z_i D_i S / Q. D_osc (megasonic mixing) is mechanical, equal for all
species, and carries no current because sum z_i c_i = 0.
Conservation:  dN_i/dz = nu_i * r(c_OH) * 2 f_poly(z) / W   (both sidewalls; r in mol Si/m2/s).
Boundary conditions: z = 0 (mouth) c_i = c_i,surface; z = L (floor) N_i = 0.
Wafer-level boundary layer: c_i,surface = c_i,bulk + J_i / k_i with J_i = (slit outflow) * W / PITCH ... the
flux out of one slit spread over one pitch of wafer, k_i from the rotating-disk (Levich) correlation.
"""
import numpy as np

from . import props as P

SPECIES = ("OH", "SIL", "H2")
IONS = ("OH", "SIL", "TMA")


def layer_mask(z, layer=P.LAYER, top=P.TOP_LAYER):
    """1 where the sidewall at depth z is poly-Si, 0 where it is SiO2."""
    k = np.floor(z / layer).astype(int)
    first_poly = 1 if top == "SiO2" else 0
    return ((k - first_poly) % 2 == 0).astype(float)


class Slit:
    def __init__(self, n=2000, L=P.L_SLIT, W=P.W_SLIT, D=None, order=P.ORDER_OH, er_ref=P.ER_REF,
                 c_bulk=P.C_BULK, d_osc=None, km=None, pitch=P.PITCH, poly=None, migration=True):
        self.n, self.L, self.W = n, L, W
        self.dz = L / n
        self.zc = (np.arange(n) + 0.5) * self.dz            # cell centres
        self.zf = np.arange(n + 1) * self.dz                 # faces, 0 = mouth
        self.D = dict(D or P.D)
        self.order, self.er_ref, self.cb = order, er_ref, c_bulk
        self.poly = layer_mask(self.zc) if poly is None else np.asarray(poly, float)
        self.dosc_f = np.array([d_osc(z) for z in self.zf]) if d_osc else np.zeros(n + 1)
        self.km = km                                          # {species: k} or None = surface at bulk
        self.pitch, self.migration = pitch, migration
        self.bulk = {"OH": c_bulk, "SIL": 0.0, "H2": 0.0}
        self.recess = np.zeros(n)          # lateral recess depth of the poly-Si at each cell [m]
        self.liquid = np.ones(n + 1)       # liquid fraction of the slit cross-section at each face (bubbles)

    def wall(self, c):
        """Front reaction rate and front concentrations at every cell (pockets of depth self.recess)."""
        from .pocket import front
        if not self.recess.any():
            return dict(r=self.rate(c["OH"]), c_oh=c["OH"], c_sil=c["SIL"], c_h2=c["H2"])
        return front(c["OH"], c["SIL"], c["H2"], self.recess, self.rate)

    # ------------------------------------------------------------ physics
    EPS = 1e-6        # numerical cut-off: below 1e-6 c_bulk the rate goes to zero smoothly (c^n has an
                      # infinite slope at c = 0, which Newton cannot handle); no effect above it

    def rate(self, c_oh):
        """mol Si / m2 / s at each cell (power law in OH-)."""
        c = np.maximum(c_oh, 0.0)
        return P.si_flux(self.er_ref) * (c / self.cb) ** self.order * c / (c + self.EPS * self.cb)

    def fluxes(self, c, surf):
        """Nernst-Planck fluxes at the n+1 faces for state c = {sp: array(n)} and mouth values surf."""
        ext = {s: np.concatenate(([surf[s]], c[s])) for s in SPECIES}       # mouth node + cells
        zpos = np.concatenate(([0.0], self.zc))
        grad, mid = {}, {}
        for s in SPECIES:
            g = np.diff(ext[s]) / np.diff(zpos)                              # faces 0..n-1
            grad[s] = np.concatenate((g, [0.0]))                             # floor: no flux
            mid[s] = np.concatenate((0.5 * (ext[s][:-1] + ext[s][1:]), ext[s][-1:]))   # face values
        grad["TMA"] = grad["OH"] + 2 * grad["SIL"]
        mid["TMA"] = mid["OH"] + 2 * mid["SIL"]
        if self.migration:
            S = sum(P.Z[i] * self.D[i] * grad[i] for i in IONS)
            Q = sum(P.Z[i] ** 2 * self.D[i] * np.maximum(mid[i], 1e-12) for i in IONS)
            ratio = S / Q
        else:
            ratio = np.zeros(self.n + 1)
        N = {}
        for s in SPECIES:
            N[s] = -(self.D[s] + self.dosc_f) * grad[s] + P.Z[s] * self.D[s] * mid[s] * ratio
            N[s] *= self.liquid                  # flux per slit cross-section; bubbles take part of it
            N[s][-1] = 0.0
        return N, ratio

    def surface(self, N):
        """Mouth concentrations from the wafer-level boundary layer."""
        if not self.km:
            return dict(self.bulk)
        out = {}
        for s in SPECIES:
            J = N[s][0] * self.W / self.pitch                # into the slit, per m2 of wafer
            out[s] = self.bulk[s] - J / self.km[s]
        return out

    def residual(self, x, surf):
        c = self._unpack(x)
        N, _ = self.fluxes(c, surf)
        r = self.wall(c)["r"] * 2 * self.poly / self.W
        res = [(np.diff(N[s]) / self.dz) - P.NU_RXN[s] * r for s in SPECIES]
        return np.concatenate(res)

    # ------------------------------------------------------------ solver
    def _unpack(self, x):
        return {s: x[k * self.n:(k + 1) * self.n] for k, s in enumerate(SPECIES)}

    def solve(self, tol=1e-10, max_newton=200, outer=30, guess=None):
        from scipy.sparse import csc_matrix
        from scipy.sparse.linalg import spsolve
        n = self.n
        if guess is not None:                                     # warm start (time stepping)
            x, surf = guess
            x = x.copy()
            surf = dict(surf)
        else:
            x = np.concatenate([np.full(n, self.cb), np.zeros(n), np.zeros(n)])
            surf = dict(self.bulk)
        for _ in range(outer):                                   # outer loop: wafer boundary layer
            for it in range(max_newton):
                F0 = self.residual(x, surf)
                scale = np.abs(F0).max()
                rows, cols, vals = [], [], []
                h = 1e-7 * max(self.cb, 1.0)
                for color in range(9):                           # banded: 3 species x 3-cell stencil
                    sp, off = divmod(color, 3)
                    cells = np.arange(off, n, 3)
                    idx = cells + sp * n
                    xp = x.copy()
                    xp[idx] += h
                    dF = (self.residual(xp, surf) - F0) / h
                    for s2 in range(3):                          # same entries as a cell-by-cell loop
                        for d in (-1, 0, 1):
                            ok = (cells + d >= 0) & (cells + d < n)
                            ii = s2 * n + cells[ok] + d
                            nz = dF[ii] != 0.0
                            rows.append(ii[nz])
                            cols.append(idx[ok][nz])
                            vals.append(dF[ii][nz])
                J = csc_matrix((np.concatenate(vals), (np.concatenate(rows), np.concatenate(cols))),
                               shape=(3 * n, 3 * n))
                dx = spsolve(J, -F0)
                lam = 1.0                                        # damped Newton keeping c_OH >= 0
                while lam > 1e-4:
                    xn = x + lam * dx
                    if xn[:n].min() >= -1e-9 * self.cb and np.abs(self.residual(xn, surf)).max() < scale:
                        break
                    lam *= 0.5
                x = xn
                # converged when the (full) Newton step is negligible; a residual test cannot be used
                # because the diffusion terms D c / dz^2 are ~1e10 and round-off dominates there
                if np.abs(dx).max() < tol * self.cb:
                    break
            else:
                raise RuntimeError("Newton did not converge")
            N, _ = self.fluxes(self._unpack(x), surf)
            new = self.surface(N)
            change = max(abs(new[s] - surf[s]) for s in SPECIES) / self.cb
            surf = new
            if change < 1e-9:
                break
        self.x, self.surf = x, surf
        return self.result()

    # ------------------------------------------------------------ outputs
    def result(self):
        c = self._unpack(self.x)
        N, ratio = self.fluxes(c, self.surf)
        w = self.wall(c)
        er = w["r"] / P.si_flux(1.0)                                      # etch velocity at the front, m/s
        poly = self.poly > 0
        z_poly, er_poly = self.zc[poly], er[poly]
        top = er_poly[: max(1, int(0.05 * len(er_poly)))].mean()        # top 5 % of poly layers
        bot = er_poly[-max(1, int(0.05 * len(er_poly))):].mean()        # bottom 5 %
        consumed = (w["r"] * 2 * self.poly).sum() * self.dz             # mol Si / s per m of slit length
        h2 = np.where(self.poly > 0, w["c_h2"], c["H2"])                  # H2 is highest at the etch front
        return dict(z=self.zc, c=c, N=N, er=er, surf=self.surf, er_top=top, er_bottom=bot,
                    uniformity=bot / top if top > 0 else float("nan"), er_mean=er_poly.mean(),
                    phi_grad_ratio=ratio, si_consumed=consumed, h2_supersat=h2.max() / P.H2_SAT,
                    S_h2=h2 / P.H2_SAT, oh_min=c["OH"].min(), sil_max=c["SIL"].max(),
                    z_poly=z_poly, er_poly=er_poly, front=w)


def thiele(order=P.ORDER_OH, W=P.W_SLIT, L=P.L_SLIT, d=None, poly_fraction=0.5):
    """Order-of-magnitude depletion number: consumption at bulk conditions / diffusive supply.
    phi^2 = (2 OH per Si) r_bulk (2/W) f L^2 / (D c_bulk); phi^2 >> 1 means the bottom starves."""
    d = d or P.D["OH"]
    r = P.si_flux(P.ER_REF)
    return 2 * r * (2 / W) * poly_fraction * L ** 2 / (d * P.C_BULK)


def ambipolar(d_plus, d_minus):
    """Binary 1:1 electrolyte effective diffusivity (classical result, for the migration check)."""
    return 2 * d_plus * d_minus / (d_plus + d_minus)


