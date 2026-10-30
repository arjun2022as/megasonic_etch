#!/usr/bin/env python3
"""Generate cases.csv for the 2D Fluent study (edit here, not in the CSV).

All cases: 5 wt% TMAH, 60 C, slit 100 nm x 10 um, SiO2/poly-Si 50/50 nm, MegPie spin tool (300 rpm, 2 mm gap).
  M0   no megasonic (spin shear only); the reference
  A    incidence-angle sweep at 1 MHz, 2 W/cm2: theta = 90 (MegPie, normal), 75, 60, 45, 30, 15 deg from the wafer
  F    frequency: 2 and 3 MHz at 45 deg, 2 W/cm2   (at 90 deg there is no tangential flow at any frequency)
  P    power: 0.5 and 1 W/cm2 at 1 MHz, 45 deg
  R    poly-Si already recessed 300 nm: no megasonic, and 1 MHz 2 W/cm2 45 deg
  V    checks: no electromigration, rate order 1, mesh refined 2x
"""
import csv
from pathlib import Path

COLS = ["case", "walltime", "f_MHz", "I_W_cm2", "theta_deg", "recess_nm", "order", "migration", "er_ref_nm_min",
        "refine", "osc_scale", "iters", "note"]


def row(case, note, f=0, I=0, theta=90, recess=0, order="", migration=1, refine=1, walltime="04:00:00"):
    return dict(case=case, walltime=walltime, f_MHz=f, I_W_cm2=I, theta_deg=theta, recess_nm=recess, order=order,
                migration=migration, er_ref_nm_min="", refine=refine, osc_scale=1, iters=20, note=note)


def rows():
    out = [row("M0_none", "no megasonic: spin shear only")]
    for th in (90, 75, 60, 45, 30, 15):
        out.append(row(f"A_f1_I2_t{th:02d}", f"1 MHz, 2 W/cm2, incidence {th} deg from the wafer", 1, 2, th))
    for f in (2, 3):
        out.append(row(f"F_f{f}_I2_t45", f"{f} MHz, 2 W/cm2, 45 deg", f, 2, 45))
    for I, tag in ((0.5, "05"), (1, "1")):
        out.append(row(f"P_f1_I{tag}_t45", f"1 MHz, {I} W/cm2, 45 deg", 1, I, 45))
    out.append(row("R_none_r300", "poly-Si recessed 300 nm, no megasonic", recess=300, walltime="06:00:00"))
    out.append(row("R_f1_I2_t45_r300", "poly-Si recessed 300 nm, 1 MHz 2 W/cm2 45 deg", 1, 2, 45, recess=300,
                   walltime="06:00:00"))
    out.append(row("V_nomig", "check: electromigration off", migration=0))
    out.append(row("V_order1", "check: first-order rate in OH-", order=1.0))
    out.append(row("V_mesh2", "check: cells refined 2x (no megasonic)", refine=2, walltime="10:00:00"))
    return out


if __name__ == "__main__":
    rs = rows()
    with open(Path(__file__).resolve().parent / "cases.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rs)
    print(f"{len(rs)} cases -> cases.csv")
