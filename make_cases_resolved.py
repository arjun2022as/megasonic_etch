#!/usr/bin/env python3
"""Generate cases_resolved.csv: case 10, RESOLVED megasonic oscillation (no D_osc closure), bubble-free.

  R0_*    no sound (resolved cell, the baseline)
  R15_*   1 MHz, 2 W/cm2 at 15 deg: tangential slip u_t = 0.311 m/s + wall pressure 0.49 MPa (compression)
  R90_*   1 MHz, 2 W/cm2 at 90 deg (flat MegPie): no slip, wall pressure 0.458 MPa (compression only)
  _flat / _comb   flat walls / poly-Si recessed 300 nm (comb)
  _H5     liquid cell 5 um instead of 10 um (check that the top of the cell does not steer the result)
Columns slip / compress switch the two parts of the sound on (1) or off (0).
"""
import csv
from pathlib import Path

COLS = ["case", "walltime", "f_MHz", "I_W_cm2", "theta_deg", "slip", "compress", "recess_nm", "H_um",
        "settle_cycles", "measure_cycles", "iters", "note"]


def row(case, note, I=0, theta=90, recess=0, H=10, walltime="24:00:00", slip=1, compress=1):
    return dict(case=case, walltime=walltime, f_MHz=1 if I else 0, I_W_cm2=I, theta_deg=theta, slip=slip,
                compress=compress, recess_nm=recess, H_um=H, settle_cycles=300, measure_cycles=200, iters=10,
                note=note)


ROWS = [
    row("R0_flat", "no sound, flat walls, resolved cell"),
    row("R0_comb", "no sound, comb walls (300 nm recess)", recess=300, walltime="36:00:00"),
    row("R15_flat", "15 deg (slip + compression), flat walls", 2, 15, walltime="96:00:00"),
    row("R15_comb", "15 deg (slip + compression), comb walls", 2, 15, recess=300, walltime="168:00:00"),
    row("R90_flat", "90 deg MegPie (compression only), flat walls", 2, 90, walltime="96:00:00"),
    row("R15_flat_H5", "15 deg, flat walls, 5 um liquid cell (top-boundary check)", 2, 15, H=5, walltime="96:00:00"),
]

if __name__ == "__main__":
    with open(Path(__file__).resolve().parent / "cases_resolved.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=COLS, lineterminator="\n")
        w.writeheader()
        w.writerows(ROWS)
    print(f"{len(ROWS)} cases -> cases_resolved.csv")
