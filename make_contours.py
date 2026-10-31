#!/usr/bin/env python3
"""Contour maps and depth profiles of finished 2D cases (matplotlib only, no Fluent).

    python make_contours.py M0_none                     # results/M0_none/plots/*.png
    python make_contours.py M0_none A_f1_I2_t45 ...     # also results/compare/profiles_<cases>.png

Maps need field_*.csv (written by dump_field at the end of run_case.py); the depth profiles need only
dump_*.csv. Every figure says that the megasonic field is an imposed oscillating flow plus modelled mixing,
not a full acoustic-streaming solution.
"""
import csv
import glob
import json
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from run_case import metrics, read_dumps  # noqa: E402
from etchsim import props as P  # noqa: E402

NOTE = ("Megasonics = imposed oscillating flow + modelled mixing D_osc, not a full acoustic-streaming solution. "
        "x and y scales differ.")


def mpl():
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        import matplotlib.tri as mtri
        import numpy as np
    except ImportError:
        raise SystemExit("matplotlib missing: source ~/venvs/pyfluent241/bin/activate && pip install matplotlib")
    return plt, mtri, np


def read_field(out):
    rows = []
    for fn in glob.glob(str(out / "field_*.csv")):
        with open(fn, newline="") as f:
            rows += [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    return rows


def recess_of(out):
    try:
        return float(json.loads((out / "summary.json").read_text())["mesh"]["recess"])
    except (OSError, KeyError, ValueError):
        return 0.0


def fluid(x, y, recess, np):
    """True where a point lies in liquid: above the wafer, inside the slit, or inside a poly-Si pocket."""
    W, L, lay = P.W_SLIT, P.L_SLIT, P.LAYER
    in_slit = (x >= 0) & (x <= W) & (y >= -L)
    k = np.floor(-y / lay)
    in_pocket = (recess > 0) & (y < 0) & (y >= -L) & (k % 2 == 1) & (x >= -recess) & (x <= W + recess)
    return (y >= 0) | in_slit | in_pocket


def maps(case, out, plt, mtri, np):
    rows = read_field(out)
    if not rows:
        print(f"{case}: no field_*.csv (rerun the case with the current run_case.py); maps skipped")
        return
    a = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    recess = recess_of(out)
    osc = a["d_osc"].max() > 0
    fields = [("c_oh", "OH$^-$ (mM)", a["c_oh"], None),
              ("c_sil", "silicate (mM)", a["c_sil"], None),
              ("h2", "H$_2$ / saturation (-)", a["c_h2"] / P.H2_SAT, None),
              ("speed", "phase-A mean speed (m/s)" if osc else "speed (m/s)",
               a["u_mean"] if osc else np.hypot(a["u"], a["v"]), "log")]
    if osc:
        fields.append(("dosc", "D$_{osc}$ / D$_{OH}$ (-)", a["d_osc"] / P.D["OH"], "log"))
    views = [("slit", (-50, 150), (-P.L_SLIT * 1e6 - 0.2, 0.5), (len(fields) * 2.4, 8.5)),
             ("mouth", (-500, 600), (-1.0, 1.0), (len(fields) * 3.0, 4.2))]
    for vname, (x0, x1), (y0, y1), size in views:
        xs, ys = a["x"] * 1e9, a["y"] * 1e6                     # nm, um
        sel = (xs > x0 - 50) & (xs < x1 + 50) & (ys > y0 - 0.2) & (ys < y1 + 0.2)
        tri = mtri.Triangulation(xs[sel], ys[sel])
        cx = xs[sel][tri.triangles].mean(axis=1) * 1e-9
        cy = ys[sel][tri.triangles].mean(axis=1) * 1e-6
        tri.set_mask(~fluid(cx, cy, recess, np))
        fig, axes = plt.subplots(1, len(fields), figsize=size, constrained_layout=True)
        for ax, (_, label, val, scale) in zip(axes, fields):
            v = val[sel]
            if scale == "log":
                v = np.log10(np.maximum(v, 1e-12))
                label = "log$_{10}$ " + label
            cs = ax.tricontourf(tri, v, levels=30, cmap="viridis")
            fig.colorbar(cs, ax=ax, shrink=0.8).set_label(label, fontsize=8)
            ax.set_xlim(x0, x1)
            ax.set_ylim(y0, y1)
            ax.set_xlabel("x (nm)")
            ax.set_title(label, fontsize=9)
        axes[0].set_ylabel("y (µm), mouth at 0")
        fig.suptitle(f"{case}: {vname} view", fontsize=11)
        fig.text(0.01, 0.002, NOTE, fontsize=7, style="italic")
        fn = out / "plots" / f"{case}_{vname}.png"
        fig.savefig(fn, dpi=130)
        plt.close(fig)
        print("wrote", fn)


def profile_data(out):
    poly, centre = read_dumps(out)
    if not poly:
        return None
    m = metrics(poly, centre)
    cen = sorted((r for r in centre if r["y"] < 0), key=lambda r: -r["y"])
    rows = {}
    for r in cen:                                                # average the two centre columns
        rows.setdefault(round(-r["y"] * 1e6, 6), []).append(r)
    z = sorted(rows)
    col = {k: [sum(r[k] for r in rows[d]) / len(rows[d]) for d in z] for k in ("c_oh", "c_sil", "c_h2")}
    lz = [(k + 0.5) * P.LAYER * 1e6 for k, _ in m["layers"]]
    return dict(m=m, z=z, lz=lz, er=[e for _, e in m["layers"]], **col)


def profiles(cases, outs, fn, plt):
    data = [(c, profile_data(o)) for c, o in zip(cases, outs)]
    data = [(c, d) for c, d in data if d]
    if not data:
        print("no dump_*.csv found; profiles skipped")
        return
    fig, axes = plt.subplots(1, 4, figsize=(14, 6), sharey=True, constrained_layout=True)
    for c, d in data:
        lab = f"{c} (bottom/top {d['m']['uniformity']:.4f})"
        axes[0].plot(d["er"], d["lz"], ".-", ms=3, label=lab)
        axes[1].plot(d["c_oh"], d["z"], label=lab)
        axes[2].plot(d["c_sil"], d["z"], label=lab)
        axes[3].plot([h / P.H2_SAT for h in d["c_h2"]], d["z"], label=lab)
    for ax, t in zip(axes, ("poly-Si etch rate (nm/min)", "OH$^-$, slit centre (mM)", "silicate, slit centre (mM)",
                            "H$_2$ / saturation (-)")):
        ax.set_xlabel(t)
        ax.grid(alpha=0.3)
    axes[0].set_ylabel("depth below the mouth (µm)")
    axes[0].invert_yaxis()
    axes[0].legend(fontsize=7, loc="lower left")
    fig.suptitle("Depth profiles at quasi-steady state", fontsize=11)
    fig.text(0.01, 0.002, NOTE.split(" x and")[0], fontsize=7, style="italic")
    fn.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(fn, dpi=130)
    plt.close(fig)
    print("wrote", fn)


def main():
    cases = sys.argv[1:] or ["M0_none"]
    plt, mtri, np = mpl()
    outs = [HERE / "results" / c for c in cases]
    for c, o in zip(cases, outs):
        if not o.is_dir():
            raise SystemExit(f"no results/{c}")
        (o / "plots").mkdir(exist_ok=True)
        maps(c, o, plt, mtri, np)
        profiles([c], [o], o / "plots" / f"{c}_profiles.png", plt)
    if len(cases) > 1:
        profiles(cases, outs, HERE / "results" / "compare" / f"profiles_{'_'.join(cases)[:120]}.png", plt)


if __name__ == "__main__":
    main()
