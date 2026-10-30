#!/usr/bin/env python3
"""1D reference study: TMAH etching of poly-Si layers along a 100 nm x 10 um slit, with and without megasonics.

    python run_1d.py            # numpy, scipy, matplotlib; ~1 min; writes results_1d/
Megasonic effects included (upper bounds, see etchsim/acoustics.py): oscillatory mixing D_osc(z) inside the
slit, decaying from the mouth, and faster wafer-level mass transfer outside. Not included: cavitation,
bubble microstreaming, H2 bubble nucleation (reported as dissolved-H2 supersaturation instead).
"""
import csv
import json
import math
from pathlib import Path

import numpy as np

from etchsim import acoustics as A
from etchsim import props as P
from etchsim.slit1d import Slit, thiele

OUT = Path(__file__).resolve().parent / "results_1d"
FREQS = (1e6, 2e6, 3e6)
POWERS = (0.5, 1.0, 2.0)
ANGLES = (90.0, 60.0, 45.0, 30.0)        # incidence from the wafer surface; 90 = MegPie (normal)


def km_spin(extra_mixing=0.0):
    """Wafer-level mass-transfer coefficients: Levich (spinning wafer), D -> D + extra (oscillatory mixing)."""
    om = P.omega_spin()
    return {s: P.levich_km(P.D[s] + extra_mixing, om) for s in ("OH", "SIL", "H2")}


def case(label, osc=None, **kw):
    d_osc = (lambda z: A.d_osc(z, osc, P.W_SLIT)) if osc else None
    extra = osc["u_t"] ** 2 / (2 * 2 * math.pi * osc["f"]) if osc else 0.0
    s = Slit(d_osc=d_osc, km=km_spin(extra), **kw)
    r = s.solve()
    r["label"] = label
    return r


def summary_row(r, **extra):
    return dict(label=r["label"], er_top_nm_min=r["er_top"] * 6e10, er_bottom_nm_min=r["er_bottom"] * 6e10,
                er_mean_nm_min=r["er_mean"] * 6e10, uniformity_bottom_over_top=r["uniformity"],
                oh_min_frac=r["oh_min"] / P.C_BULK, oh_mouth_frac=r["surf"]["OH"] / P.C_BULK,
                silicate_max_mM=r["sil_max"], h2_supersaturation=r["h2_supersat"], **extra)


def main():
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    OUT.mkdir(exist_ok=True)

    scales = dict(c_bulk_mol_m3=P.C_BULK, D_60C=P.D, thiele_squared=thiele(),
                  thiele_squared_order1=thiele(order=1.0), spin_film=P.spin_film(P.DISPENSE_LPM / 6e4,
                                                                                  P.omega_spin(), P.R_PROBE),
                  levich_km_OH=P.levich_km(P.D["OH"], P.omega_spin()))
    osc_table = []
    for f in FREQS:
        for I in POWERS:
            for th in ANGLES:
                o = A.slit_oscillation(I, th, f, P.W_SLIT)
                osc_table.append(dict(f_MHz=f / 1e6, I_W_cm2=I, theta_deg=th, U0=o["U0"], R_abs=abs(o["R"]),
                                      u_t=o["u_t"], delta_um=o["delta"] * 1e6, womersley=o["womersley"],
                                      u_mouth=o["u_mouth"], D_osc_mouth=o["d_osc_mouth"],
                                      D_osc_over_D_OH=o["d_osc_mouth"] / P.D["OH"],
                                      depth_where_Dosc_1pct_nm=max(0.0, P.W_SLIT / (2 * A.K_SLOT) *
                                                                    math.log(max(o["d_osc_mouth"] / (0.01 * P.D["OH"]), 1)) * 1e9),
                                      compression_disp_nm=A.compression_pumping(I, th, P.L_SLIT) * 1e9))
    save_csv("acoustics_table.csv", osc_table)

    # ---- runs
    base = case("no megasonic (spin only)")
    runs, rows = [base], [summary_row(base, f_MHz=0, I_W_cm2=0, theta_deg="")]
    for f in FREQS:
        for I in POWERS:
            for th in ANGLES:
                o = A.slit_oscillation(I, th, f, P.W_SLIT)
                r = case(f"{f / 1e6:g} MHz, {I:g} W/cm2, {th:g} deg", o)
                rows.append(summary_row(r, f_MHz=f / 1e6, I_W_cm2=I, theta_deg=th))
                if (I, th) in ((2.0, 30.0), (1.0, 90.0)):
                    runs.append(r)
    sens = []
    for lab, kw in (("rate order n = 1", dict(order=1.0)), ("ER_ref 100 nm/min", dict(er_ref=100e-9 / 60)),
                    ("ER_ref 600 nm/min", dict(er_ref=600e-9 / 60)), ("no electromigration", dict(migration=False))):
        r = case(lab, **kw)
        sens.append(summary_row(r))
        runs.append(r)
    save_csv("summary.csv", rows + sens)
    (OUT / "scales.json").write_text(json.dumps(scales, indent=1, default=str))

    # ---- figures
    fig, axes = plt.subplots(1, 3, figsize=(15, 5))
    for r in runs:
        z_um = r["z"] * 1e6
        axes[0].plot(r["c"]["OH"] / P.C_BULK, z_um, label=r["label"])
        axes[1].plot(r["er_poly"] * 6e10, r["z_poly"] * 1e6, ".", ms=2, label=r["label"])
        axes[2].plot(r["c"]["H2"] / P.H2_SAT, z_um, label=r["label"])
    axes[0].set(xlabel="OH- / bulk", ylabel="depth below mouth (um)")
    axes[1].set(xlabel="poly-Si lateral etch rate (nm/min)")
    axes[2].set(xlabel="dissolved H2 / saturation (>1: bubbles can form)", xscale="log")
    for ax in axes:
        ax.invert_yaxis()
    axes[0].legend(fontsize=7)
    fig.suptitle("5 wt% TMAH, 60 C, 100 nm x 10 um slit, 50/50 nm SiO2/poly-Si (quasi-steady, 1D)")
    fig.tight_layout()
    fig.savefig(OUT / "profiles.png", dpi=150)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.5))
    for f in FREQS:
        for th in ANGLES:
            sel = [x for x in rows if x["f_MHz"] == f / 1e6 and x["theta_deg"] == th]
            axes[0].plot([x["I_W_cm2"] for x in sel], [x["uniformity_bottom_over_top"] for x in sel], "o-",
                         label=f"{f / 1e6:g} MHz, {th:g} deg")
            axes[1].plot([x["I_W_cm2"] for x in sel], [x["er_mean_nm_min"] for x in sel], "o-")
    for ax, b in zip(axes, (rows[0]["uniformity_bottom_over_top"], rows[0]["er_mean_nm_min"])):
        ax.axhline(b, color="k", ls=":", label="no megasonic")
        ax.set_xlabel("megasonic intensity (W/cm2)")
    axes[0].set_ylabel("etch rate bottom / top")
    axes[1].set_ylabel("mean poly-Si etch rate (nm/min)")
    axes[0].legend(fontsize=6, ncol=2)
    fig.tight_layout()
    fig.savefig(OUT / "megasonic_effect.png", dpi=150)

    print(json.dumps({k: (v if not isinstance(v, dict) else {a: f"{b:.3g}" for a, b in v.items()})
                      for k, v in scales.items()}, indent=1, default=str))
    for x in [rows[0]] + rows[1:] [::12] + sens:
        print(f"{x['label']:32s} top {x['er_top_nm_min']:7.1f}  bottom {x['er_bottom_nm_min']:7.2f} nm/min  "
              f"bottom/top {x['uniformity_bottom_over_top']:.3f}  OH min {x['oh_min_frac']:.3f}  "
              f"H2 x{x['h2_supersaturation']:.0f}")


def save_csv(name, rows):
    with open(OUT / name, "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(rows[0]))
        w.writeheader()
        w.writerows(rows)


if __name__ == "__main__":
    np.seterr(all="ignore")
    main()
