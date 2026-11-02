#!/usr/bin/env python3
"""Side view of the trench (depth x length): finite pancake H2 bubbles instead of sealing plugs (etchsim/sideview.py).

    python run_sideview.py          # numpy, scipy, matplotlib; ~30 min on the laptop

Runs (0.3 s each; mouth values from cases.csv):
  realistic tool (flat MegPie = 90 deg, which for bubbles is the same as no sound), bubbles start at 13.9x
  (seeds present), nucleation sites every 5 / 10 / 20 / 40 um along the trench;
  sensitivity at 20 um spacing: comb wall (300 nm recess), 15 deg tilt (A_f1_I2_t15 mouth), seed-free (100x).
Writes results_1d/sideview.csv and results_1d/sideview.png.
"""
import csv
import math

from etchsim import sideview as SV
from run_plug import OUT, mouth

RUNS = [dict(label=f"90deg, sites {s} um", case="M0_none", spacing=s * 1e-6) for s in (5, 10, 20, 40)] + [
    dict(label="90deg, sites 20 um, comb 300 nm", case="M0_none", spacing=20e-6, recess=300e-9),
    dict(label="15deg tilt, sites 20 um", case="A_f1_I2_t15", spacing=20e-6),
    dict(label="90deg, sites 20 um, start 100x", case="M0_none", spacing=20e-6, s_nuc=100.0),
    dict(label="no bubbles", case="M0_none", spacing=0.4e-6, s_nuc=math.inf)]


def main():
    rows, runs = [], []
    for r in RUNS:
        kw = {k: v for k, v in r.items() if k not in ("label", "case")}
        run = SV.simulate(mouth(r["case"]), **kw)
        sm = SV.summarise(run)
        rows.append(dict(label=r["label"], **sm))
        runs.append((r["label"], run))
        print(f"{r['label']:34s} vents {sm['n_vent']:2d} period {sm['period_ms']:6.1f} ms  floor covered "
              f"{100 * sm['floor_blocked_time_avg']:5.1f} % of the time  S_max {sm['s_max']:6.1f}  etch top "
              f"{sm['er_top_nm_min']:6.1f} bottom {sm['er_bottom_nm_min']:6.1f} nm/min  bottom/top {sm['uniformity']:.3f}",
              flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "sideview.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    plot(runs)


def plot(runs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
    for label, run in runs:
        ax[0].plot(run["er_depth"] * 6e10, run["z"] * 1e6, label=label, lw=1)
        h = run["hist"]
        if "start 100x" not in label and "no bubbles" not in label:
            ax[1].plot([x["t"] * 1e3 for x in h], [x["Rb"] * 1e6 for x in h], label=label, lw=1)
    ax[0].invert_yaxis()
    ax[0].set(xlabel="time-averaged etch rate, mean along the trench (nm/min)", ylabel="depth (um)",
              title="Etch profile with finite bubbles")
    ax[0].legend(fontsize=7)
    ax[1].set(xlabel="time (ms)", ylabel="bubble radius (um)", title="Bubble growth and venting")
    ax[1].legend(fontsize=7)
    label, run = next(x for x in runs if x[0] == "90deg, sites 20 um")
    y, z = run["y"] * 1e6, run["z"] * 1e6
    m = ax[2].pcolormesh(y, z, run["er_map"] * 6e10, shading="auto", cmap="viridis")
    ax[2].invert_yaxis()
    ax[2].set(xlabel="distance along the trench from a bubble site (um)", ylabel="depth (um)",
              title="Time-averaged etch, sites 20 um apart")
    fig.colorbar(m, ax=ax[2], label="nm/min")
    fig.suptitle("Side view of a 100 nm x 10 um trench, 5 wt% TMAH 60 C; bubbles start at 13.9x sat unless noted "
                 "(ASSUMED). Imposed oscillating flow + modelled mixing, not acoustic streaming", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "sideview.png", dpi=130)


if __name__ == "__main__":
    main()
