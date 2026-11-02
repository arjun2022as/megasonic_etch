#!/usr/bin/env python3
"""Case 5: where in the slit can H2 bubbles stay smaller than a plug, and what H2 level keeps them all small?

    python run_nanobubble.py        # numpy, scipy, matplotlib; ~1 min

1D slit without plugs (etchsim/slit1d.py), mouth values from cases.csv (no sound = M0_none; tilted sound = the
A cases; flat MegPie at 90 deg gives the same mouth as no sound). At every depth the H2 saturation S(z) is compared
with the limit S_max(L) of pinned surface nanobubbles of footprint radius L (etchsim/nanobubble.py).
Writes results_1d/nanobubble.csv and results_1d/nanobubble.png.
Imposed oscillating flow + modelled mixing (through the mouth values), not acoustic streaming.
"""
import csv

import numpy as np

from etchsim import nanobubble as NB
from etchsim.plug import S_PLUG
from run_plug import OUT, mouth

SOUND = {"no sound / 90 deg": "M0_none", "60 deg": "A_f1_I2_t60", "45 deg": "A_f1_I2_t45", "15 deg": "A_f1_I2_t15"}
FOOTPRINTS_NM = (10, 15, 20, 30, 50)


def profile(case):
    from etchsim.slit1d import Slit
    s = Slit(n=1000, km=None)
    s.bulk = mouth(case)
    r = s.solve()
    return r["z"], r["S_h2"]


def main():
    rows, curves = [], {}
    print("Footprint limits S_max(L): " + ", ".join(f"{L} nm -> {NB.s_max_pinned(L * 1e-9):.1f}x"
                                                    for L in FOOTPRINTS_NM))
    for label, case in SOUND.items():
        z, S = profile(case)
        curves[label] = (z, S)
        for L in FOOTPRINTS_NM:
            smax = NB.s_max_pinned(L * 1e-9)
            over = S > smax
            rows.append(dict(sound=label, footprint_nm=L, S_max=round(smax, 2), S_mouth=round(S[0], 1),
                             S_floor=round(S.max(), 1), runaway_fraction=round(float(over.mean()), 3),
                             runaway_from_depth_um=round(float(z[over][0] * 1e6), 2) if over.any() else None,
                             h2_cut_needed=round(max(0.0, 1 - smax / S.max()), 3)))
        print(f"{label:18s} S mouth {S[0]:5.1f}x floor {S.max():5.1f}x | largest footprint that stays small: "
              f"mouth {NB.footprint_limit(S[0]) * 1e9:4.1f} nm, floor {NB.footprint_limit(S.max()) * 1e9:4.1f} nm")
    print(f"\n{'sound':18s} {'L nm':>5} {'S_max':>6} | {'slit depth where small bubbles run away':>40} | H2 cut needed")
    for r in rows:
        where = (f"{100 * r['runaway_fraction']:5.1f} % (from {r['runaway_from_depth_um']} um)"
                 if r["runaway_fraction"] else "none: all stay small")
        print(f"{r['sound']:18s} {r['footprint_nm']:5d} {r['S_max']:6.1f} | {where:>40} | "
              f"{100 * r['h2_cut_needed']:4.0f} %")
    OUT.mkdir(exist_ok=True)
    with open(OUT / "nanobubble.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    plot(curves)


def plot(curves):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 5))
    for label, (z, S) in curves.items():
        ax[0].plot(S, z * 1e6, label=label)
    for L in FOOTPRINTS_NM:
        smax = NB.s_max_pinned(L * 1e-9)
        ax[0].axvline(smax, ls="--", lw=0.8, color="gray")
        ax[0].text(smax, 9.8, f" {L} nm", rotation=90, va="bottom", fontsize=7, color="gray")
    ax[0].axvline(S_PLUG, ls=":", color="k", lw=0.8)                 # an existing plug keeps growing above this
    ax[0].text(S_PLUG, 9.8, " plug 13.9x", rotation=90, va="bottom", fontsize=7)
    ax[0].invert_yaxis()
    ax[0].set(xlabel="H2 saturation S (x c_sat)", ylabel="depth (um)",
              title="H2 in the slit vs the limit for each footprint (dashed)")
    ax[0].legend(fontsize=8)
    S = np.linspace(10, 140, 300)
    ax[1].plot(S, [NB.footprint_limit(s) * 1e9 for s in S])
    ax[1].axhline(50, ls="--", color="gray", lw=0.8)
    ax[1].text(100, 52, "50 nm = half the slit width", fontsize=8, color="gray")
    ax[1].set(xlabel="H2 saturation S", ylabel="largest footprint radius that stays small (nm)",
              title="Pinned nanobubbles: how big they can be and stay small", ylim=(0, 120))
    fig.suptitle("Case 5: sub-plug H2 bubbles, 100 nm x 10 um slit, 5 wt% TMAH 60 C (gamma, c_sat ASSUMED). "
                 "Imposed oscillating flow + modelled mixing, not acoustic streaming", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "nanobubble.png", dpi=130)


if __name__ == "__main__":
    main()
