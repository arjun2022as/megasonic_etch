#!/usr/bin/env python3
"""Case 4, realistic tool: growing H2 plug cycle under the flat MegPie (90 deg) with intermittent sound,
rectified diffusion and early venting (etchsim/plug.py), against no sound.

    python run_realistic.py         # numpy, scipy; ~15 min

Tool (ASSUMED until ProSys confirms): 300 rpm -> one revolution 0.2 s; MegPie sector 60 deg -> each slit is under
the transducer for 33 ms per revolution; 1 MHz; 1 W/cm2 (mid power) and 2 W/cm2 (top). At 90 deg there is no
sideways flow, so the mouth values are those of no sound (M0_none). Bubbles start at 13.9x (seeds) or 100x.
Writes results_1d/realistic.csv. Imposed oscillating flow + modelled mixing, not acoustic streaming.
"""
import csv

from etchsim import plug as PL
from run_plug import OUT, mouth

T_REV = 60.0 / 300.0                    # s per revolution at 300 rpm (ASSUMED speed)
T_ON = T_REV * 60.0 / 360.0             # under a 60 deg MegPie sector (ASSUMED)
RUNS = [
    ("no sound", {}),
    ("90deg 1 W/cm2 continuous, pumping only", dict(sound=PL.pulsation(1e6, 1.0))),
    ("90deg 1 W/cm2 continuous, + rectified + early vent", dict(sound=PL.pulsation(1e6, 1.0), rect=True, xi_vent=True)),
    ("90deg 1 W/cm2 MegPie (33 of 200 ms), all effects", dict(sound=PL.pulsation(1e6, 1.0), duty=(T_REV, T_ON),
                                                             rect=True, xi_vent=True)),
    ("90deg 2 W/cm2 continuous, all effects", dict(sound=PL.pulsation(1e6, 2.0), rect=True, xi_vent=True)),
]


def main(t_end=0.6):
    surf = mouth("M0_none")
    rows = []
    for s_nuc in (PL.S_PLUG, 100.0):
        for label, kw in RUNS:
            sm = PL.summarise(PL.simulate(surf, t_end=t_end, s_nuc=s_nuc, **kw))
            rows.append(dict(start=round(s_nuc, 1), run=label, **{k: sm[k] for k in (
                "n_vent", "period_ms", "growth_median_um_s", "er_top_nm_min", "er_bottom_nm_min", "uniformity")}))
            r = rows[-1]
            print(f"start {r['start']:5.1f}x  {label:52s} vents {r['n_vent']:2d}  cycle {r['period_ms']:6.2f} ms  "
                  f"growth {r['growth_median_um_s']:6.1f} um/s  bottom {r['er_bottom_nm_min']:6.2f} nm/min  "
                  f"bottom/top {r['uniformity']:.4f}", flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "realistic.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
