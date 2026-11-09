#!/usr/bin/env python3
"""Case 8: with bubbles, no sound vs vertical sound (90 deg, flat MegPie) vs near-horizontal sound (15 deg).

ANSYS part: the existing Fluent fixed-plug runs (flat and comb walls, 1/3/6 um floor plugs) for the three conditions,
side by side on one colour scale -> make_case8.py on Puma (post-processing only, no new Fluent solve).
"Horizontal": the sideways shaking at the wafer, u_t = U0 sin(beta) |1+R|, peaks near 10 deg (0.314 m/s at 2 W/cm2)
and is 0.311 m/s at 15 deg (within 1 %); exactly 0 deg gives 0 (grazing). So 15 deg is the horizontal case.

Laptop part (this script, 1D, no Fluent):
    python run_case8.py --part cycle     # comb walls, bubbles start at 13.9x: bottom etch vs recess, 4 conditions (~25 min)
    python run_case8.py --part plot      # 2-min start-up recess + summary figure with the Fluent numbers (seconds)
Writes results_1d/case8_bottom_vs_recess.csv, case8_startup.csv, case8.png.
ASSUMED: MegPie sector 60 deg (sound 33 of 200 ms), 1 MHz 2 W/cm2, uniform recess, bubbles start at 13.9x.
Imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution.
"""
import argparse
import csv

import numpy as np

from etchsim import plug as PL
from run_plug import OUT, mouth

T_REV = 0.2
T_ON = T_REV / 6
RECESS_NM = (0, 2, 5, 10, 20, 30, 50, 100, 300)
CONDS = [
    ("no sound", "M0_none", {}),
    ("vertical 90 deg, real MegPie (33 of 200 ms)", "M0_none",
     dict(sound=PL.pulsation(1e6, 2.0, 90.0), duty=(T_REV, T_ON), rect=True, xi_vent=True)),
    ("vertical 90 deg, continuous", "M0_none", dict(sound=PL.pulsation(1e6, 2.0, 90.0), rect=True, xi_vent=True)),
    ("horizontal 15 deg, continuous", "A_f1_I2_t15", dict(sound=PL.pulsation(1e6, 2.0, 15.0), rect=True, xi_vent=True)),
]

# 2D Fluent fixed-plug results (STATUS.md 2026-11-01..03; Puma logs "PLUG ... growth"): growth um/s
FLUENT_GROWTH = {
    "flat": {"1 um": (None, 143.0, 115.0), "3 um": (145.0, 146.0, 111.0), "6 um": (175.0, 176.0, 129.0)},
    "comb 300 nm": {"1 um": (147.7, 147.9, 118.3), "3 um": (151.0, 151.3, 115.2), "6 um": (183.4, 184.7, 136.7)},
}
FLUENT_MOUTH_X = (63.5, 63.5, 43.0)          # mouth H2 used as the Fluent boundary value (cases.csv)


def save(name, rows):
    OUT.mkdir(exist_ok=True)
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def read(name):
    with open(OUT / name, newline="") as f:
        return list(csv.DictReader(f))


def part_cycle(t_end=0.2):
    rows = []
    for label, case, kw in CONDS:
        surf = mouth(case)
        for R in RECESS_NM:
            sm = PL.summarise(PL.simulate(surf, t_end=t_end, s_nuc=PL.S_PLUG, recess=R * 1e-9, **kw))
            rows.append(dict(condition=label, recess_nm=R, er_bottom_nm_min=round(sm["er_bottom_nm_min"], 2),
                             er_top_nm_min=round(sm["er_top_nm_min"], 2), period_ms=round(sm["period_ms"], 2)))
            print(rows[-1], flush=True)
            save("case8_bottom_vs_recess.csv", rows)


def grow(r0, t, Rs, ers, dt=0.1):
    R = r0
    for _ in range(int(round(t / dt))):
        R += np.interp(R, Rs, ers) / 60 * dt
    return R


def part_plot():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    tab = read("case8_bottom_vs_recess.csv")
    labels = [c[0] for c in CONDS]
    cols = ("#7f7f7f", "#2a6fb0", "#6baed6", "#e67e22")
    fig, ax = plt.subplots(1, 3, figsize=(19, 5.4))
    # (a) Fluent growth speeds
    x = np.arange(6)
    names = [f"{w}\n{s}" for w in FLUENT_GROWTH for s in FLUENT_GROWTH[w]]
    for k, (lab, col) in enumerate(zip(("no sound", "vertical 90 deg", "horizontal 15 deg"), (cols[0], cols[1], cols[3]))):
        v = [FLUENT_GROWTH[w][s][k] for w in FLUENT_GROWTH for s in FLUENT_GROWTH[w]]
        ax[0].bar(x + (k - 1) * 0.27, [0 if a is None else a for a in v], 0.27, color=col, label=lab)
        for xx, a in zip(x + (k - 1) * 0.27, v):
            ax[0].text(xx, (a or 0) + 2, "n/a" if a is None else f"{a:.0f}", ha="center", fontsize=6.5)
    ax[0].set_xticks(x, names, fontsize=8)
    ax[0].set(ylabel="plug growth speed (um/s)", ylim=(0, 210),
              title="(a) ANSYS Fluent, fixed floor plugs:\nhow fast the plug grows")
    ax[0].legend(fontsize=8, loc="upper left")
    # (b) bottom etch vs recess (1D cycle)
    rows, start = [], []
    for lab, col in zip(labels, cols):
        t = [r for r in tab if r["condition"] == lab]
        if not t:
            continue
        Rs = np.array([float(r["recess_nm"]) for r in t])
        ers = np.array([float(r["er_bottom_nm_min"]) for r in t])
        ax[1].plot(np.maximum(Rs, 0.5), ers, "o-", color=col, label=lab)
        for r0 in (0.0, 5.0):
            out = [round(grow(r0, s, Rs, ers), 1) for s in (15, 30, 60, 90, 120)]
            start.append(dict(condition=lab, start_recess_nm=r0, **{f"bottom_nm_{s}s": v for s, v in
                                                                     zip((15, 30, 60, 90, 120), out)}))
        top = float(np.mean([float(r["er_top_nm_min"]) for r in t]))
        ts = np.arange(0, 121, 5)
        ax[2].plot(ts, [grow(0.0, s, Rs, ers) for s in ts], "-", color=col, label=f"{lab} (top {top * 2:.0f} nm)")
    ax[2].plot(ts, ts / 60 * 281.5, "k:", label="bubble-free bottom (281.5 nm/min)")
    ax[1].set(xscale="log", xlabel="poly-Si recess already there (nm; 0 drawn at 0.5)",
              ylabel="bottom etch with bubbles (nm/min)", title="(b) 1D bubble cycle, comb walls, bubbles start at 13.9x")
    ax[1].legend(fontsize=7)
    ax[2].set(xlabel="etch time (s)", ylabel="bottom recess (nm)", title="(c) Bottom recess from flat walls (start-up)")
    ax[2].legend(fontsize=7)
    fig.suptitle("Case 8: bubbles with no sound, vertical (90 deg) and near-horizontal (15 deg) sound; 1 MHz, 2 W/cm2, "
                 "60 C, 300 rpm. Imposed oscillating flow + modelled mixing, not a full acoustic-streaming solution.",
                 fontsize=10)
    fig.tight_layout()
    fig.savefig(OUT / "case8.png", dpi=140, bbox_inches="tight")
    save("case8_startup.csv", start)
    for r in start:
        print(r)


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--part", choices=("cycle", "plot"), required=True)
    {"cycle": part_cycle, "plot": part_plot}[ap.parse_args().part]()
