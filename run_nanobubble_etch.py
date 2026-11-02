#!/usr/bin/env python3
"""Case 5, part 2: how much do small (pinned, sub-plug) H2 bubbles slow the etch and change its uniformity?

    python run_nanobubble_etch.py   # numpy, scipy; ~2 min

Pinned caps of footprint radius L cover a fraction phi of the poly-Si wall wherever they can stay small
(S(z) <= S_max(L), etchsim/nanobubble.py). Under a cap the poly-Si does not etch (ASSUMED: the cap sits still),
so the local etch, the OH- use and the H2 made all drop by (1 - phi). Less H2 lowers S, which lets caps stay
small deeper down: solved self-consistently (fixed point on the covered region).
Where S > S_max(L) the caps cannot stay small: they run away to plugs (case 4); that zone is reported, and there
the wall is left uncovered here (the plug cycle of case 4 then applies).
Etch rates reported are averages over the whole wall (covered spots count as zero).
phi is unknown (surface-nanobubble coverage in the literature ranges from a few % to tens of %): swept 0, 10, 30 %.
Mouth values fixed from cases.csv (ASSUMED: caps on the wafer top not included, conservative).
Writes results_1d/nanobubble_etch.csv. Imposed oscillating flow + modelled mixing, not acoustic streaming.
"""
import csv

import numpy as np

from etchsim import nanobubble as NB
from etchsim import props as P
from etchsim.slit1d import Slit, layer_mask
from run_plug import OUT, mouth

SOUND = {"no sound / 90 deg": "M0_none", "15 deg": "A_f1_I2_t15"}
FOOTPRINTS_NM = (10, 15, 20)
COVERAGE = (0.0, 0.10, 0.30)


def solve(case, L, phi, iters=20):
    base = layer_mask((np.arange(1000) + 0.5) * P.L_SLIT / 1000)
    covered = np.ones(1000, bool)                    # start: caps everywhere
    smax = NB.s_max_pinned(L)
    for _ in range(iters):
        s = Slit(n=1000, km=None, poly=base * (1 - phi * covered))
        s.bulk = mouth(case)
        r = s.solve()
        new = r["S_h2"] <= smax
        if np.array_equal(new, covered):
            break
        covered = new
    er_wall = r["er"] * (1 - phi * covered)          # averaged over the wall incl. covered spots
    poly = base > 0
    er_p = er_wall[poly]
    n5 = max(1, len(er_p) // 20)
    top, bot = er_p[:n5].mean(), er_p[-n5:].mean()
    run = ~covered
    return dict(top=top * 6e10, bottom=bot * 6e10, U=bot / top, S_floor=r["S_h2"].max(), S_max=smax,
                runaway_from_um=float(r["z"][run][0] * 1e6) if run.any() else None,
                runaway_fraction=float(run.mean()))


def main():
    rows = []
    print(f"{'sound':18s} {'L nm':>4} {'cover':>5} | {'top':>6} {'bottom':>6} nm/min {'bottom/top':>10} | "
          f"{'S floor':>7} (limit) | caps run away to plugs")
    for label, case in SOUND.items():
        for L in FOOTPRINTS_NM:
            for phi in COVERAGE:
                r = solve(case, L * 1e-9, phi)
                rows.append(dict(sound=label, footprint_nm=L, coverage=phi, **r))
                if r["runaway_from_um"] is None:
                    print(f"{label:18s} {L:4d} {100 * phi:4.0f}% | {r['top']:6.1f} {r['bottom']:6.1f}        "
                          f"{r['U']:10.4f} | {r['S_floor']:7.1f} ({r['S_max']:5.1f}) | nowhere: all stay small",
                          flush=True)
                else:                                    # bottom and ratio meaningless: plugs form there
                    rows[-1].update(bottom=None, U=None)
                    print(f"{label:18s} {L:4d} {100 * phi:4.0f}% | {r['top']:6.1f}   --   (plugs: case 4)"
                          f" | {r['S_floor']:7.1f} ({r['S_max']:5.1f}) | below {r['runaway_from_um']:.2f} um "
                          f"({100 * r['runaway_fraction']:.0f} % of slit)", flush=True)
    OUT.mkdir(exist_ok=True)
    with open(OUT / "nanobubble_etch.csv", "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]), lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    main()
