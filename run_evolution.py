#!/usr/bin/env python3
"""Etch evolution (lateral recess growth) and H2 bubble scenarios for the 100 nm x 10 um slit.

    python run_evolution.py        # numpy, scipy, matplotlib; a few minutes; writes results_1d/evolution_*

1. Recess growth: quasi-steady transport at each time, recess of each poly-Si cell advanced by its front
   etch velocity (explicit, dt = 5 s) for 2 minutes.
2. Bubbles: where dissolved H2 exceeds S_crit (a bubble filling the slit width can grow), bubbles take a
   fraction alpha of the slit cross-section. alpha is unknown (no bubble dynamics are solved), so it is swept:
   alpha = 0 is a bubble-free slit; megasonic bubble removal would move a process toward lower alpha.
   The bubble region is found self-consistently (fixed point on the region).
3. Indicator for megasonic action on confined bubbles: acoustic pressure amplitude at the wafer vs the
   Laplace pressure 2 gamma / W that holds a bubble in the slit.
"""
import csv
import math
from pathlib import Path

import numpy as np

from etchsim import acoustics as A
from etchsim import props as P
from etchsim.pocket import GAMMA_60C, s_crit
from run_1d import km_spin

OUT = Path(__file__).resolve().parent / "results_1d"


def slit(**kw):
    from etchsim.slit1d import Slit
    return Slit(km=km_spin(), **kw)


def layer_means(z, v, poly):
    """Average a per-cell quantity over each poly-Si layer -> (layer centre depth, value)."""
    k = np.floor(z / P.LAYER).astype(int)
    out = []
    for kk in np.unique(k[poly > 0]):
        sel = (k == kk) & (poly > 0)
        out.append((z[sel].mean(), v[sel].mean()))
    return np.array(out)


def evolution(t_end=120.0, dt=5.0):
    s = slit()
    hist, guess = [], None
    t = 0.0
    while True:
        r = s.solve(guess=guess)
        guess = (s.x, s.surf)
        lay = layer_means(s.zc, s.recess, s.poly)
        hist.append(dict(t=t, er_top=r["er_top"], er_bottom=r["er_bottom"], uniformity=r["uniformity"],
                         recess_top=lay[:5, 1].mean(), recess_bottom=lay[-5:, 1].mean(),
                         recess_mean=lay[:, 1].mean(), S_max=r["S_h2"].max(),
                         bubble_fraction=float(np.mean(r["S_h2"] > s_crit())), profile=lay))
        if t >= t_end - 1e-9:
            break
        s.recess = s.recess + r["er"] * s.poly * dt
        t += dt
    return hist


def bubble_scenarios(alphas=(0.0, 0.25, 0.5, 0.75, 0.9)):
    sc = s_crit()
    rows, profiles = [], {}
    for a in alphas:
        s = slit()
        region = np.zeros(s.n, bool)
        for _ in range(15):
            liq_c = np.where(region, 1 - a, 1.0)
            s.liquid = np.concatenate(([liq_c[0]], 0.5 * (liq_c[:-1] + liq_c[1:]), [liq_c[-1]]))
            r = s.solve()
            new = r["S_h2"] > sc
            if np.array_equal(new, region):
                break
            region = new
        rows.append(dict(alpha=a, bubble_region_frac=float(region.mean()),
                         bubble_top_um=float(s.zc[region].min() * 1e6) if region.any() else float("nan"),
                         er_top_nm_min=r["er_top"] * 6e10, er_bottom_nm_min=r["er_bottom"] * 6e10,
                         er_mean_nm_min=r["er_mean"] * 6e10, uniformity=r["uniformity"],
                         oh_min_frac=r["oh_min"] / P.C_BULK))
        profiles[a] = (r["z_poly"], r["er_poly"], s.zc, r["S_h2"])
    return rows, profiles


def acoustic_vs_laplace():
    lap = 2 * GAMMA_60C / P.W_SLIT
    out = []
    for f in (1e6, 2e6, 3e6):
        for I in (0.5, 1.0, 2.0):
            for th in (90.0, 45.0):
                w = A.wall_velocities(I, th)
                out.append(dict(f_MHz=f / 1e6, I_W_cm2=I, theta_deg=th, p_wall_kPa=w["p_wall"] / 1e3,
                                laplace_kPa=lap / 1e3, ratio=w["p_wall"] / lap))
    return out


def save_csv(name, rows):
    rows = [{k: v for k, v in r.items() if k != "profile"} for r in rows]
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    OUT.mkdir(exist_ok=True)
    hist = evolution()
    save_csv("evolution.csv", hist)
    rows, profiles = bubble_scenarios()
    save_csv("bubble_scenarios.csv", rows)
    ac = acoustic_vs_laplace()
    save_csv("acoustic_vs_laplace.csv", ac)

    fig, axes = plt.subplots(1, 3, figsize=(16, 5))
    for h in hist[::6]:
        axes[0].plot(h["profile"][:, 1] * 1e9, h["profile"][:, 0] * 1e6, label=f"t = {h['t']:.0f} s")
    axes[0].set(xlabel="lateral recess of each poly-Si layer (nm)", ylabel="depth (um)")
    axes[0].invert_yaxis()
    axes[0].legend(fontsize=8)
    for a, (zp, erp, zc, S) in profiles.items():
        axes[1].plot(erp * 6e10, zp * 1e6, ".", ms=2, label=f"bubbles block {a:.0%} of slit")
        axes[2].plot(S, zc * 1e6, label=f"alpha = {a:.0%}")
    axes[2].axvline(s_crit(), color="k", ls=":", label=f"S_crit = {s_crit():.1f} (bubble can grow)")
    axes[1].set(xlabel="poly-Si etch rate (nm/min)")
    axes[2].set(xlabel="dissolved H2 at the etch front / saturation", xscale="log")
    for ax in axes[1:]:
        ax.invert_yaxis()
    axes[1].legend(fontsize=7, markerscale=4)
    axes[2].legend(fontsize=7)
    fig.suptitle("5 wt% TMAH, 60 C, 100 nm x 10 um slit: recess growth (left) and H2-bubble blocking scenarios")
    fig.tight_layout()
    fig.savefig(OUT / "evolution_bubbles.png", dpi=150)

    h0, h1 = hist[0], hist[-1]
    print(f"recess after {h1['t']:.0f} s: top {h1['recess_top'] * 1e9:.1f} nm, bottom {h1['recess_bottom'] * 1e9:.1f} nm, "
          f"bottom/top {h1['recess_bottom'] / h1['recess_top']:.3f}; etch-rate bottom/top {h0['uniformity']:.4f} -> "
          f"{h1['uniformity']:.4f}")
    print(f"S_crit = {s_crit():.2f}; slit fraction above it: {h0['bubble_fraction']:.2f} (t = 0)")
    for r in rows:
        print(f"alpha {r['alpha']:.2f}: bubble region {r['bubble_region_frac']:.2f} of slit, etch top "
              f"{r['er_top_nm_min']:.0f} bottom {r['er_bottom_nm_min']:.1f} nm/min, bottom/top {r['uniformity']:.3f}")
    for r in ac:
        if r["theta_deg"] == 90.0:
            print(f"{r['f_MHz']:g} MHz {r['I_W_cm2']:g} W/cm2: p_wall {r['p_wall_kPa']:.0f} kPa vs Laplace "
                  f"{r['laplace_kPa']:.0f} kPa (ratio {r['ratio']:.2f})")


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
