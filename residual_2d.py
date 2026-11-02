#!/usr/bin/env python3
"""Cell-by-cell balance of a finished 2D case from its field_*.csv (no Fluent): which term does not close?

    python3 residual_2d.py A_f1_I2_t45
    python3 residual_2d.py M0_none A_f1_I2_t45 B_f1_I2_floor      # several cases, same table

For every slit cell (away from the mouth, floor and any H2 plug) and every species, the steady equations the
model is meant to solve are rebuilt from the saved cell values, term by term:
  molecular diffusion  sum_f D_i (c_n - c) L_f / d_f          (D_i = intended value)
  D_osc mixing         sum_f 0.5 (Dosc_c + Dosc_n) (c_n - c) L_f / d_f
  pumping              sum_f D_pump,i (c_n - c) L_f / d_f      (axial faces above a plug)
  electromigration     -sum_f z_i D_i c_f (S.n L/d)_f / Q_f     (ions; same face formula as etch.c)
  convection           -sum_f (u.n)_f c_f L_f                   (central, face velocity = mean of the two cells)
  reaction             nu_i r L_wall                            (poly-Si wall cells)
in mol/s per metre of slit length. At steady state they add up to ~0 in every cell. The table gives, per
species and depth band, each term summed over the band and the left-over (residual), all divided by the
band's reaction. A term that should be zero but is not, or a residual of several %, shows the faulty piece.
"""
import csv
import glob
import json
import math
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from etchsim import props as P  # noqa: E402

W, L, LAYER = P.W_SLIT, P.L_SLIT, P.LAYER
SP = ("OH", "SIL", "H2")
COL = {"OH": "c_oh", "SIL": "c_sil", "H2": "c_h2"}
NU = {"OH": -2.0, "SIL": 1.0, "H2": 2.0}
Z = {"OH": -1, "SIL": -2, "H2": 0, "TMA": 1}
D = P.D


def load(case):
    out = HERE / "results" / case
    rows = []
    for fn in glob.glob(str(out / "field_*.csv")):
        with open(fn, newline="") as f:
            rows += [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    if not rows:
        raise SystemExit(f"{case}: no field_*.csv")
    try:
        s = json.loads((out / "summary.json").read_text())
        m = s["mesh"]
        b_top = float(m.get("bubble_top", 0.0)) if float(m.get("bubble_len", 0.0)) > 0 else 0.0
        pump = {k: float(v) for k, v in s.get("pump", {}).get("D", {}).items()}
        mig = bool(int(s.get("migration", 1)))
        hx, hy = float(m["dx"]), float(m["dy"])
    except (OSError, KeyError, ValueError):
        b_top, pump, mig, hx, hy = 0.0, {}, True, 5e-9, 10e-9
    return rows, b_top, pump, mig, hx, hy


def key(x, y):
    return (round(x * 1e11), round(y * 1e11))


def analyse(case):
    rows, b_top, pump, mig, hx, hy = load(case)        # hx, hy: slit cell width and height
    cells = {key(r["x"], r["y"]): r for r in rows}
    xs = sorted({r["x"] for r in rows})
    ys = sorted({r["y"] for r in rows})
    xi = {round(x * 1e11): i for i, x in enumerate(xs)}
    yi = {round(y * 1e11): j for j, y in enumerate(ys)}
    deep = (b_top if b_top > 0 else L)
    bands = [(0.3e-6, deep / 3), (deep / 3, 2 * deep / 3), (2 * deep / 3, deep - 0.1e-6)]
    tot = {b: {s: dict(diff=0.0, dosc=0.0, pump=0.0, mig=0.0, conv=0.0, rxn=0.0) for s in SP} for b in range(3)}
    n_cells = [0, 0, 0]

    def in_pump(r):
        return b_top > 0 and 0 < r["x"] < W and -b_top < r["y"] < 0

    for r in rows:
        x, y = r["x"], r["y"]
        if not (0 < x < W and y < 0):
            continue
        depth = -y
        band = next((b for b, (a, z) in enumerate(bands) if a <= depth < z), None)
        if band is None:
            continue
        n_cells[band] += 1
        i, j = xi[round(x * 1e11)], yi[round(y * 1e11)]
        nbrs = []
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            ii, jj = i + di, j + dj
            if 0 <= ii < len(xs) and 0 <= jj < len(ys):
                n = cells.get(key(xs[ii], ys[jj]))
                if n is not None:
                    nbrs.append((n, di, dj))
        wall_faces = 4 - len(nbrs)
        for n, di, dj in nbrs:
            dx, dy = abs(n["x"] - x), abs(n["y"] - y)
            Lf, d = (hy, dx) if di else (hx, dy)    # vertical face: length hy; horizontal face: length hx
            g = Lf / d
            axial = dj != 0
            pf = axial and in_pump(r) and in_pump(n)
            dosc = 0.5 * (r["d_osc"] + n["d_osc"])
            un = (0.5 * (r["u"] + n["u"])) * di + (0.5 * (r["v"] + n["v"])) * dj     # outward normal velocity
            dc = {s: n[COL[s]] - r[COL[s]] for s in SP}
            cf = {s: 0.5 * (n[COL[s]] + r[COL[s]]) for s in SP}
            if mig:
                d_oh, d_si = dc["OH"] * g, dc["SIL"] * g
                p = {k: (pump.get(k, 0.0) if pf else 0.0) for k in ("OH", "SIL", "TMA")}
                s_a = (-(D["OH"] + p["OH"]) * d_oh - 2 * (D["SIL"] + p["SIL"]) * d_si
                       + (D["TMA"] + p["TMA"]) * (d_oh + 2 * d_si))
                q = D["OH"] * cf["OH"] + 4 * D["SIL"] * cf["SIL"] + D["TMA"] * (cf["OH"] + 2 * cf["SIL"])
            for s in SP:
                t = tot[band][s]
                t["diff"] += D[s] * dc[s] * g
                t["dosc"] += dosc * dc[s] * g
                t["pump"] += (pump.get(s, 0.0) if pf else 0.0) * dc[s] * g
                t["conv"] -= un * cf[s] * Lf
                if mig and Z[s]:
                    t["mig"] -= Z[s] * D[s] * s_a / q * cf[s]
        if r["etch_m_s"] > 0 and wall_faces:
            rate = P.si_flux(r["etch_m_s"]) * wall_faces * hy
            for s in SP:
                tot[band][s]["rxn"] += NU[s] * rate
    print(f"\n== {case}: plug top {b_top * 1e6:g} um, pumping {pump or 'none'}, cells per band {n_cells}")
    print(f"{'band (um)':>13} {'sp':>4} | {'diffusion':>9} {'D_osc':>8} {'pump':>8} {'migr.':>8} {'convect.':>8} "
          f"{'reaction':>9} | {'RESIDUAL':>9}   (all / |reaction|, %)")
    for b, (a, z) in enumerate(bands):
        for s in SP:
            t = tot[b][s]
            ref = abs(t["rxn"]) or 1e-30
            res = sum(t.values())
            print(f"{a * 1e6:5.2f}-{z * 1e6:5.2f} {s:>4} | " + " ".join(
                f"{100 * t[k] / ref:9.2f}" if k in ("diff", "rxn") else f"{100 * t[k] / ref:8.2f}"
                for k in ("diff", "dosc", "pump", "mig", "conv", "rxn")) + f" | {100 * res / ref:9.2f}")


if __name__ == "__main__":
    for c in sys.argv[1:] or ["M0_none"]:
        analyse(c)
