#!/usr/bin/env python3
"""Generate cases.csv for the 2D Fluent study (edit here, not in the CSV).

All cases: 5 wt% TMAH, 60 C, slit 100 nm x 10 um, SiO2/poly-Si 50/50 nm, MegPie spin tool (300 rpm, 2 mm gap).
  M0   no megasonic (spin shear only); the reference
  A    incidence-angle sweep at 1 MHz, 2 W/cm2: theta = 90 (MegPie, normal), 75, 60, 45, 30, 15 deg from the wafer
  F    frequency: 2 and 3 MHz at 45 deg, 2 W/cm2   (at 90 deg there is no tangential flow at any frequency)
  P    power: 0.5 and 1 W/cm2 at 1 MHz, 45 deg
  R    poly-Si already recessed 300 nm: no megasonic, and 1 MHz 2 W/cm2 45 deg
  V    checks: no electromigration, rate order 1, mesh refined 2x
  B    H2 gas plug 1 um long in the slit (top at 9 um = on the floor, 5 um = mid-depth, 1 um = near the mouth),
       flat wafer (90 deg): B0_* without sound (blocking only), B_f1_I2_* with 1 MHz, 2 W/cm2 (blocking + stable-
       cavitation pumping, etchsim/cavitation.py)
  BA   1 um floor plug + sound at 60 / 45 / 15 deg
  _l3000, _l6000   grown floor plugs 3 / 6 um long (snapshots for the 1D growing-plug model)
"""
import csv
from pathlib import Path

COLS = ["case", "walltime", "f_MHz", "I_W_cm2", "theta_deg", "recess_nm", "order", "migration", "er_ref_nm_min",
        "refine", "osc_scale", "iters", "bubble_top_um", "bubble_len_um", "note"]


def row(case, note, f=0, I=0, theta=90, recess=0, order="", migration=1, refine=1, walltime="04:00:00",
        bubble=("", "")):
    return dict(case=case, walltime=walltime, f_MHz=f, I_W_cm2=I, theta_deg=theta, recess_nm=recess, order=order,
                migration=migration, er_ref_nm_min="", refine=refine, osc_scale=1, iters=20, bubble_top_um=bubble[0],
                bubble_len_um=bubble[1], note=note)


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
    out += bubble_rows()
    out += angle_bubble_rows()
    out += growth_snapshot_rows()
    return out


def bubble_rows():
    """1 um plugs (B0_floor ...) and 200 nm, nucleus-sized plugs (B0_floor_l200 ...); 'floor' = touching it."""
    out = []
    for length, tag in ((1, ""), (0.2, "_l200")):
        for where, top in (("floor", round(10 - length, 3)), ("mid", 5), ("mouth", 1)):
            out.append(row(f"B0_{where}{tag}", f"H2 plug {length:g} um, top {top:g} um below the mouth, no sound",
                           bubble=(top, length)))
            out.append(row(f"B_f1_I2_{where}{tag}", f"H2 plug {length:g} um, top {top:g} um, 1 MHz 2 W/cm2 at 90 deg "
                           "(stable cavitation)", 1, 2, 90, bubble=(top, length)))
    return out


def angle_bubble_rows():
    """1 um H2 plug on the floor with sound at 60 / 45 / 15 deg (1 MHz, 2 W/cm2): how the oscillating flow at the
    mouth and the plug pulsation change the H2 flow into the plug (its growth rate) vs B0_floor / B_f1_I2_floor."""
    return [row(f"BA_f1_I2_t{th}_floor", f"H2 plug 1 um on the floor, 1 MHz 2 W/cm2 at {th} deg", 1, 2, th, bubble=(9, 1))
            for th in (60, 45, 15)]


def growth_snapshot_rows():
    """Snapshots of a GROWN floor plug (1D growing-plug model, etchsim/plug.py, gives the time course): 3 and
    6 um long (top at 7 / 4 um), no sound, 90 deg and 15 deg. With the 1 um B0/B_f1/BA_t15 floor cases they
    check the 1D intake vs plug size in 2D (fixed plug, no displacement flow)."""
    out = []
    for length in (3, 6):
        top, tag = 10 - length, f"_l{length * 1000}"
        out.append(row(f"B0_floor{tag}", f"H2 plug {length} um on the floor (top {top} um), no sound", bubble=(top, length)))
        out.append(row(f"B_f1_I2_floor{tag}", f"H2 plug {length} um on the floor, 1 MHz 2 W/cm2 at 90 deg", 1, 2, 90,
                       bubble=(top, length)))
        out.append(row(f"BA_f1_I2_t15_floor{tag}", f"H2 plug {length} um on the floor, 1 MHz 2 W/cm2 at 15 deg", 1, 2,
                       15, bubble=(top, length)))
    return out


if __name__ == "__main__":
    from fluent2d.params import ONE_D_COLS, one_d_reference
    COLS += list(ONE_D_COLS)
    rs = rows()
    for r in rs:                     # 1D mouth concentrations + reference, so Puma needs no scipy
        r.update({k: f"{v:.10g}" for k, v in one_d_reference(r).items()})
    with open(Path(__file__).resolve().parent / "cases.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(rs)
    print(f"{len(rs)} cases -> cases.csv")
