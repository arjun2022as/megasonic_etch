#!/usr/bin/env python3
"""Case 4, comb walls: growing H2 plug cycle when the poly-Si is recessed into pockets (etchsim/plug.py, recess).

    python run_comb_cycle.py        # numpy, scipy, matplotlib; ~10 min

Pockets beside the plug stay liquid-filled and keep etching on stored etchant (exact sealed-pocket formula);
their H2 feeds the plug. Recess swept 0 (flat, = before), 50, 100, 300, 600 nm; bubbles start at 13.9x (seeds) or
100x; no sound / flat MegPie 90 deg (same mouth). 0.3 s per run.
Writes results_1d/comb_cycle.csv and results_1d/comb_cycle.png.
Imposed oscillating flow + modelled mixing, not acoustic streaming.
"""
import csv

from etchsim import plug as PL
from run_plug import OUT, mouth

RECESS_NM = (0, 50, 100, 300, 600)


def main():
    surf = mouth("M0_none")
    rows, runs = [], {}
    for s_nuc in (PL.S_PLUG, 100.0):
        for R in RECESS_NM:
            run = PL.simulate(surf, t_end=0.3, s_nuc=s_nuc, recess=R * 1e-9)
            sm = PL.summarise(run)
            runs[(s_nuc, R)] = run
            rows.append(dict(start=round(s_nuc, 1), recess_nm=R, **{k: sm[k] for k in (
                "n_vent", "period_ms", "growth_median_um_s", "er_top_nm_min", "er_bottom_nm_min", "uniformity")}))
            r = rows[-1]
            print(f"start {r['start']:5.1f}x  recess {R:3d} nm: cycle {r['period_ms']:6.1f} ms  growth "
                  f"{r['growth_median_um_s']:6.1f} um/s  top {r['er_top_nm_min']:6.1f}  bottom "
                  f"{r['er_bottom_nm_min']:6.1f} nm/min  bottom/top {r['uniformity']:.3f}", flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "comb_cycle.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    plot(runs)


def plot(runs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 2, figsize=(13, 5), sharey=True)
    for a, s_nuc in zip(ax, (PL.S_PLUG, 100.0)):
        for R in RECESS_NM:
            run = runs[(s_nuc, R)]
            a.plot(run["er_layer"] * 6e10, run["z_layer"] * 1e6, label=f"recess {R} nm")
        a.set(xlabel="time-averaged etch rate (nm/min)", title=f"bubbles start at {s_nuc:.1f}x")
        a.legend(fontsize=8)
    ax[0].invert_yaxis()
    ax[0].set_ylabel("depth (um)")
    fig.suptitle("Case 4, comb walls: pockets beside a bubble keep etching on stored etchant (1D growing-plug cycle, "
                 "no sound / 90 deg). Imposed oscillating flow + modelled mixing, not acoustic streaming", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "comb_cycle.png", dpi=130)


if __name__ == "__main__":
    main()
