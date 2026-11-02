#!/usr/bin/env python3
"""Growing H2 plug on the floor: nucleate -> grow -> vent -> refill cycle (1D, etchsim/plug.py), no Fluent.

    python run_plug.py              # numpy, scipy, matplotlib; ~15 min on the laptop
    python run_plug.py --quick      # shorter runs (0.1 s), for a first look

Sound conditions (mouth concentrations taken from cases.csv, i.e. the same 1D wafer-level values the 2D
cases use):  none (M0 mouth, no sound), 90 deg (M0 mouth + plug pumping), 60 / 45 / 15 deg (A-case mouth +
plug pumping), all 1 MHz 2 W/cm2.
Nucleation threshold s_nuc (x H2 saturation) is unknown and swept: 13.9 (a plug-sized gas pocket is always
there), 27 (50 nm spherical seed), 70, 100, inf (no bubbles: control).
Writes results_1d/plug_cycle.csv (one row per run) and results_1d/plug_cycle.png.
Imposed oscillating flow and modelled mixing, not a full acoustic-streaming solution.
"""
import csv
import math
import sys
from pathlib import Path

from etchsim import plug as PL

HERE = Path(__file__).resolve().parent
OUT = HERE / "results_1d"
SOUND = {"none": ("M0_none", None), "t90": ("M0_none", 90.0), "t60": ("A_f1_I2_t60", 60.0),
         "t45": ("A_f1_I2_t45", 45.0), "t15": ("A_f1_I2_t15", 15.0)}
S_NUC = (PL.S_PLUG, 27.0, 70.0, 100.0, math.inf)


def mouth(case):
    with open(HERE / "cases.csv", newline="") as f:
        for r in csv.DictReader(f):
            if r["case"] == case:
                return dict(OH=float(r["c_oh_surf"]), SIL=float(r["c_sil_surf"]), H2=float(r["c_h2_surf"]))
    raise SystemExit(f"{case} not in cases.csv")


def main(quick=False):
    t_end = 0.1 if quick else 0.3
    rows, runs = [], {}
    for tag, (case, theta) in SOUND.items():
        surf = mouth(case)
        pump = PL.pump_fn(1e6, 2.0, theta) if theta else None
        for s in S_NUC:
            r = PL.simulate(surf, pump, t_end=t_end, s_nuc=s)
            sm = PL.summarise(r)
            row = dict(sound=tag, s_nuc=s, mouth_h2_x_sat=surf["H2"] / 0.70, **sm)
            rows.append(row)
            runs[(tag, s)] = r
            print(f"{tag:5s} s_nuc {s:5.1f}: vents {sm['n_vent']:2d}  period {sm['period_ms']:6.1f} ms  "
                  f"growth (median) {sm['growth_median_um_s']:6.1f} um/s  plug present {100 * sm['plug_steps_fraction']:5.1f} % "
                  f"of steps  S_max {sm['s_max']:6.1f}  etch top {sm['er_top_nm_min']:6.1f} bottom "
                  f"{sm['er_bottom_nm_min']:6.1f} nm/min  bottom/top {sm['uniformity']:.4f}", flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "plug_cycle.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    plot(runs)


def plot(runs):
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(1, 3, figsize=(16, 4.8))
    for tag in SOUND:                                        # plug top vs time at the lowest threshold
        h = runs[(tag, PL.S_PLUG)]["hist"]
        ax[0].plot([x["t"] * 1e3 for x in h], [(x["b"] if x["plug"] else 10e-6) * 1e6 for x in h], label=tag, lw=1)
    ax[0].invert_yaxis()
    ax[0].set(xlabel="time (ms)", ylabel="plug top depth (um), 10 = no plug",
              title=f"Plug cycle, s_nuc = {PL.S_PLUG:.1f}x sat")
    ax[0].legend(fontsize=8)
    for s in S_NUC:                                          # time-averaged etch profile, no sound
        r = runs[("none", s)]
        ax[1].plot(r["er_layer"] * 6e10, r["z_layer"] * 1e6, label=f"s_nuc {s:g}", lw=1)
    ax[1].invert_yaxis()
    ax[1].set(xlabel="time-averaged etch rate (nm/min)", ylabel="depth (um)", title="No sound: effect of threshold")
    ax[1].legend(fontsize=8)
    for tag in SOUND:                                        # time-averaged etch, lowest threshold, all sound
        r = runs[(tag, PL.S_PLUG)]
        ax[2].plot(r["er_layer"] * 6e10, r["z_layer"] * 1e6, label=tag, lw=1)
    ax[2].invert_yaxis()
    ax[2].set(xlabel="time-averaged etch rate (nm/min)", ylabel="depth (um)",
              title=f"s_nuc = {PL.S_PLUG:.1f}: effect of sound")
    ax[2].legend(fontsize=8)
    fig.suptitle("1D growing H2 plug (fixed mouth values, 5 wt% TMAH 60 C, 1 MHz 2 W/cm2). "
                 "Imposed oscillating flow + modelled mixing, not acoustic streaming", fontsize=9)
    fig.tight_layout()
    fig.savefig(OUT / "plug_cycle.png", dpi=130)


if __name__ == "__main__":
    main("--quick" in sys.argv)
