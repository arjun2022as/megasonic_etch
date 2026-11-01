#!/usr/bin/env python3
"""Stable-cavitation (bubble pumping) estimate for the flat wafer (90 deg): pure Python, no Fluent.

    python run_cavitation.py        # writes results_1d/cavitation_table.csv and prints a summary

For an H2 bubble of length l_b with its top z_top below the mouth, at 1/2/3 MHz and 0.5/1/2 W/cm2: acoustic
pressure at the wafer, gas pressure, liquid velocity U and displacement xi of the column above the bubble,
and the Taylor-type dispersion it adds to each species (etchsim/cavitation.py).
"""
import csv
from pathlib import Path

from etchsim import cavitation as CV

OUT = Path(__file__).resolve().parent / "results_1d"
COLS = ["z_top", "l_b", "f", "I", "p_a", "p_gas", "stable", "U", "xi", "dV_over_V", "womersley", "f_res",
        "damping_ratio", "D_disp_OH", "D_disp_over_D_OH", "D_disp_SIL", "D_disp_over_D_SIL", "D_disp_H2",
        "D_disp_over_D_H2"]


def main():
    rows = CV.table()
    OUT.mkdir(exist_ok=True)
    with open(OUT / "cavitation_table.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, extrasaction="ignore", lineterminator="\n")
        w.writeheader()
        w.writerows(rows)
    print(f"{'bubble top/len um':>17} {'f MHz':>5} {'W/cm2':>5} {'p_a kPa':>7} {'U m/s':>7} {'xi nm':>6} "
          f"{'dV/V %':>6} {'D/D OH %':>8} {'D/D SIL %':>9} {'D/D H2 %':>8}")
    for r in rows:
        print(f"{r['z_top'] * 1e6:8.1f}/{r['l_b'] * 1e6:<8.1f} {r['f'] / 1e6:5.0f} {r['I']:5.1f} {r['p_a'] / 1e3:7.0f} "
              f"{r['U']:7.3f} {r['xi'] * 1e9:6.1f} {100 * r['dV_over_V']:6.2f} {100 * r['D_disp_over_D_OH']:8.3f} "
              f"{100 * r['D_disp_over_D_SIL']:9.3f} {100 * r['D_disp_over_D_H2']:8.3f}")
    r0 = rows[0]
    print(f"gas pressure {r0['p_gas'] / 1e6:.2f} MPa; all stable (p_a < p_gas): {all(r['stable'] for r in rows)}; "
          f"damping ratio {min(r['damping_ratio'] for r in rows):.1f}-{max(r['damping_ratio'] for r in rows):.1f} "
          f"(> 1: overdamped, no resonance)")


if __name__ == "__main__":
    main()
