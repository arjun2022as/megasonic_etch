#!/usr/bin/env python3
"""Steady-state flux balance of a finished 2D case, from its dump_*.csv (no Fluent needed).

    python check_2d.py M0_none

At quasi-steady state the flux of each species through a slit cross-section at depth z must equal what
the poly-Si below z consumes or releases (Si + 2 OH- -> silicate + 2 H2):
    N_OH = +2 R(z)/W (inward),  N_SIL = -R(z)/W,  N_H2 = -2 R(z)/W,  R(z) = sum of Si flux x face length below z.
The fluxes are rebuilt from the centre-column profile with the same Nernst-Planck formula as the 1D model
(etchsim/slit1d.py): N = -D dc/dz + z D c S/Q. H2 (neutral) checks diffusion + reaction; OH- and silicate
check the electromigration term in etch.c face_source. The net current sum z_i N_i must be ~0.
Bubble cases: only the liquid between the mouth and the top of the H2 plug is checked (the liquid below a
plug is sealed and not quasi-steady), with the pumping dispersion D_pump added to each species.
"""
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_case import read_dumps  # noqa: E402
from etchsim import props as P  # noqa: E402

D = P.D
W = P.W_SLIT


def main():
    case = sys.argv[1] if len(sys.argv) > 1 else "M0_none"
    out = HERE / "results" / case
    poly, centre = read_dumps(out)
    if not centre:
        raise SystemExit(f"no dump_*.csv in {out}")

    rows = {}                                   # centre column: average the two cells either side of x = W/2
    for r in centre:
        if r["y"] < 0:
            rows.setdefault(round(r["y"], 12), []).append(r)
    zs = sorted(-y for y in rows)               # depth below the mouth, increasing
    prof = {}
    for z in zs:
        rr = rows[round(-z, 12)]
        prof[z] = {s: sum(r[k] for r in rr) / len(rr) for s, k in (("OH", "c_oh"), ("SIL", "c_sil"), ("H2", "c_h2"))}

    ys = sorted({round(-r["y"], 12) for r in poly})
    dy = min(b - a for a, b in zip(ys, ys[1:]) if b - a > 1e-12)
    src = [(-r["y"], P.si_flux(r["etch_m_s"]) * dy) for r in poly]   # mol Si / s per m of depth, per cell
    try:
        summ = json.loads((out / "summary.json").read_text())
        b_top = float(summ["mesh"].get("bubble_top", 0.0)) if float(summ["mesh"].get("bubble_len", 0.0)) > 0 else 0.0
        pump = {k: float(v) for k, v in summ.get("pump", {}).get("D", {}).items()}
    except (OSError, KeyError, ValueError):
        b_top, pump = 0.0, {}
    if b_top > 0:
        zs = [z for z in zs if z < b_top]
        src = [(z, s) for z, s in src if z < b_top]
        print(f"H2 plug top at {b_top * 1e6:g} um: checking only the liquid above it; pumping D: "
              + ", ".join(f"{k} {v:.3e}" for k, v in pump.items()))
    r_total = sum(s for _, s in src)
    print(f"case {case}: {len(zs)} centre rows, {len(poly)} poly cells, dy = {dy * 1e9:.2f} nm, "
          f"total Si {r_total:.4e} mol/s/m")
    print(f"{'depth um':>9} | {'N_OH 2D':>10} {'expected':>10} | {'N_SIL 2D':>10} {'expected':>10} | "
          f"{'N_H2 2D':>10} {'expected':>10} | {'current/F':>10} | {'E=S/Q 1/m':>10}")
    worst = {"OH": 0.0, "SIL": 0.0, "H2": 0.0}
    diag = []
    step = max(1, len(zs) // 12)
    for a, b in list(zip(zs, zs[1:]))[::step]:
        zf = 0.5 * (a + b)
        g = {s: (prof[b][s] - prof[a][s]) / (b - a) for s in ("OH", "SIL", "H2")}
        m = {s: 0.5 * (prof[a][s] + prof[b][s]) for s in ("OH", "SIL", "H2")}
        g["TMA"], m["TMA"] = g["OH"] + 2 * g["SIL"], m["OH"] + 2 * m["SIL"]
        S = sum(P.Z[i] * (D[i] + pump.get(i, 0.0)) * g[i] for i in ("OH", "SIL", "TMA"))
        Q = sum(P.Z[i] ** 2 * D[i] * max(m[i], 1e-12) for i in ("OH", "SIL", "TMA"))
        N = {s: -(D[s] + pump.get(s, 0.0)) * g[s] + P.Z[s] * D[s] * m[s] * S / Q for s in ("OH", "SIL", "H2", "TMA")}
        R = sum(s for zz, s in src if zz > zf) / W                    # mol Si / m2 of slit cross-section / s
        exp = {"OH": 2 * R, "SIL": -R, "H2": -2 * R}
        cur = sum(P.Z[s] * N[s] for s in ("OH", "SIL", "TMA"))
        for s in worst:
            if abs(exp[s]) > 1e-3 * 2 * r_total / W:
                worst[s] = max(worst[s], abs(N[s] / exp[s] - 1))
        print(f"{zf * 1e6:9.3f} | {N['OH']:10.3e} {exp['OH']:10.3e} | {N['SIL']:10.3e} {exp['SIL']:10.3e} | "
              f"{N['H2']:10.3e} {exp['H2']:10.3e} | {cur:10.2e} | {S / Q:10.3e}")
        # what would balance each species: (a) the diffusivity Fluent effectively used, with migration as
        # coded; (b) the field each ion effectively felt, with D as intended
        mig = {s: P.Z[s] * D[s] * m[s] * S / Q for s in ("OH", "SIL", "H2")}
        d_eff = {s: (mig[s] - exp[s]) / g[s] if g[s] else float("nan") for s in mig}
        e_eff = {s: (exp[s] + D[s] * g[s]) / (P.Z[s] * D[s] * m[s]) for s in ("OH", "SIL")}
        diag.append((zf, m, d_eff, e_eff, N["TMA"]))
    print("largest relative flux mismatch: " + ", ".join(f"{s} {v * 100:.1f} %" for s, v in worst.items()))
    print("\nIntended D: " + ", ".join(f"{s} {D[s]:.3e}" for s in ("OH", "SIL", "H2", "TMA")) + " m2/s")
    print(f"{'depth um':>9} | {'c_OH':>7} {'c_SIL':>7} {'c_H2':>7} | {'D_eff OH':>9} {'D_eff SIL':>9} {'D_eff H2':>9} | "
          f"{'E_eff OH':>9} {'E_eff SIL':>9} | {'N_TMA':>9}")
    for zf, m, de, ee, nt in diag:
        print(f"{zf * 1e6:9.3f} | {m['OH']:7.1f} {m['SIL']:7.1f} {m['H2']:7.1f} | {de['OH']:9.3e} {de['SIL']:9.3e} "
              f"{de['H2']:9.3e} | {ee['OH']:9.3e} {ee['SIL']:9.3e} | {nt:9.2e}")
    print("D_eff = diffusivity that balances the poly-Si consumption if migration is as coded; E_eff = field"
          " each ion would need if D is as intended. N_TMA must be ~0 at steady state.")
    print("A few % is discretisation; tens of % in OH/SIL but not H2 points at the migration term.")


if __name__ == "__main__":
    main()
