#!/usr/bin/env python3
"""Generate cases_resolved.csv: case 10, RESOLVED megasonic oscillation (no D_osc closure), bubble-free.

  R0_*    no sound (resolved cell, the baseline)
  R15_*   1 MHz, 2 W/cm2 at 15 deg: tangential slip u_t = 0.311 m/s + wall pressure 0.49 MPa (compression)
  R90_*   1 MHz, 2 W/cm2 at 90 deg (flat MegPie): no slip, wall pressure 0.458 MPa (compression only)
  _flat / _comb   flat walls / poly-Si recessed 300 nm (comb)
  _fine   cells 2x finer (2.5 nm) and 80 steps per period: numerical check (independent review B2)
  _H5, _H20   liquid cell 5 / 20 um instead of 10 um: if the results do not change with the cell height, the
              top boundary is not steering them (the sheared layer and the mixing are decided by the flow itself)
Columns slip / compress switch the two parts of the sound on (1) or off (0).
"""
import csv
from pathlib import Path

COLS = ["case", "walltime", "f_MHz", "I_W_cm2", "theta_deg", "slip", "compress", "recess_nm", "H_um",
        "settle_cycles", "measure_cycles", "iters", "refine", "steps_per_cycle", "note"]


def row(case, note, I=0, theta=90, recess=0, H=10, walltime="24:00:00", slip=1, compress=1, settle=300, measure=200,
        refine=1, spc=40):
    return dict(case=case, walltime=walltime, f_MHz=1 if I else 0, I_W_cm2=I, theta_deg=theta, slip=slip,
                compress=compress, recess_nm=recess, H_um=H, settle_cycles=settle, measure_cycles=measure, iters=10,
                refine=refine, steps_per_cycle=spc, note=note)


ROWS = [   # walltimes from the 2026-11-26 smoke test (~1 s per 25 ns step on 4 cores, 44 k cells)
    row("R0_flat", "no sound, flat walls, resolved cell", walltime="12:00:00"),
    row("R0_comb", "no sound, comb walls (300 nm recess)", recess=300, walltime="24:00:00"),
    row("R15_flat", "15 deg (slip + compression), flat walls - WHAT-IF (flat MegPie cannot tilt)", 2, 15),
    row("R15_comb", "15 deg (slip + compression), comb walls - WHAT-IF", 2, 15, recess=300, walltime="48:00:00"),
    row("R90_flat", "90 deg flat MegPie = REAL TOOL (compression only), flat walls", 2, 90, settle=50, measure=50,
        walltime="12:00:00"),
    row("R15_flat_H5", "15 deg, flat walls, 5 um liquid cell (top-boundary check)", 2, 15, H=5),
    row("R15_flat_H20", "15 deg, flat walls, 20 um liquid cell (top-boundary check)", 2, 15, H=20, walltime="36:00:00"),
    row("R15_flat_fine", "15 deg, flat walls, cells 2x finer and 80 steps per cycle (numerical check)", 2, 15,
        settle=100, measure=50, refine=2, spc=80, walltime="72:00:00"),
]

if __name__ == "__main__":
    with open(Path(__file__).resolve().parent / "cases_resolved.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(ROWS)
    print(f"{len(ROWS)} cases -> cases_resolved.csv")
