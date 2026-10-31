#!/usr/bin/env python3
"""Contour maps and depth profiles of finished 2D cases (matplotlib only, no Fluent).

    python make_contours.py M0_none                     # results/M0_none/plots/*.png
    python make_contours.py M0_none A_f1_I2_t45 ...     # each case, plus the comparison in results/compare/
    python make_contours.py --all                       # every finished case, plus the comparison

Per case: slit and mouth maps (OH-, silicate, H2/saturation, speed, D_osc) and depth profiles.
Comparison (two or more cases): for each quantity one figure with every case side by side on ONE colour
scale (maps_<quantity>.png), maps of the change from the baseline M0_none (diff_<quantity>.png), and the
depth profiles overlaid (profiles.png).
Maps need field_*.csv (written by dump_field at the end of run_case.py); the profiles need only dump_*.csv.
Every figure says that the megasonic field is an imposed oscillating flow plus modelled mixing, not a full
acoustic-streaming solution.
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
BASELINE = "M0_none"
# view name: x range (nm), y range (um), figure size per panel (in)
VIEWS = {"slit": ((-50, 150), (-P.L_SLIT * 1e6 - 0.2, 0.5), (2.4, 8.5)),
         "mouth": ((-500, 600), (-1.0, 1.0), (3.0, 4.2))}


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


def load_field(out, np):
    """Arrays of the whole-field snapshot, sorted by position so cases on the same mesh line up."""
    rows = []
    for fn in glob.glob(str(out / "field_*.csv")):
        with open(fn, newline="") as f:
            rows += [{k: float(v) for k, v in r.items()} for r in csv.DictReader(f)]
    if not rows:
        return None
    rows.sort(key=lambda r: (round(r["y"], 12), round(r["x"], 12)))
    a = {k: np.array([r[k] for r in rows]) for k in rows[0]}
    a["recess"] = recess_of(out)
    a["osc"] = a["d_osc"].max() > 0
    return a


def quantities(a, np):
    """(key, label, values, log scale?) for one case."""
    q = [("c_oh", "OH$^-$ (mM)", a["c_oh"], False),
         ("c_sil", "silicate (mM)", a["c_sil"], False),
         ("h2", "H$_2$ / saturation (-)", a["c_h2"] / P.H2_SAT, False),
         ("speed", "speed (m/s): phase-A mean if oscillating", a["u_mean"] if a["osc"] else np.hypot(a["u"], a["v"]), True),
         ("dosc", "D$_{osc}$ / D$_{OH}$ (-)", a["d_osc"] / P.D["OH"], True)]
    return q if a["osc"] else q[:4]


def view_tri(a, view, mtri, np):
    (x0, x1), (y0, y1), _ = VIEWS[view]
    xs, ys = a["x"] * 1e9, a["y"] * 1e6                         # nm, um
    sel = (xs > x0 - 50) & (xs < x1 + 50) & (ys > y0 - 0.2) & (ys < y1 + 0.2)
    tri = mtri.Triangulation(xs[sel], ys[sel])
    cx = xs[sel][tri.triangles].mean(axis=1) * 1e-9
    cy = ys[sel][tri.triangles].mean(axis=1) * 1e-6
    tri.set_mask(~fluid(cx, cy, a["recess"], np))
    return tri, sel


def panel(fig, ax, tri, v, label, log, view, np, vmin=None, vmax=None, cmap="viridis"):
    (x0, x1), (y0, y1), _ = VIEWS[view]
    if log:
        v = np.log10(np.maximum(v, 1e-12))
        label = "log$_{10}$ " + label
    if vmin is None:
        vmin, vmax = float(v.min()), float(v.max())
    if vmax <= vmin:
        vmax = vmin + 1e-9 * max(1.0, abs(vmin))
    levels = np.linspace(vmin, vmax, 31)
    cs = ax.tricontourf(tri, np.clip(v, vmin, vmax), levels=levels, cmap=cmap)
    fig.colorbar(cs, ax=ax, shrink=0.8).set_label(label, fontsize=8)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    ax.set_xlabel("x (nm)")


def maps(case, out, plt, mtri, np):
    a = load_field(out, np)
    if a is None:
        print(f"{case}: no field_*.csv (rerun the case with the current run_case.py); maps skipped")
        return
    qs = quantities(a, np)
    for view in VIEWS:
        tri, sel = view_tri(a, view, mtri, np)
        w, h = VIEWS[view][2]
        fig, axes = plt.subplots(1, len(qs), figsize=(w * len(qs), h), constrained_layout=True)
        for ax, (_, label, val, log) in zip(axes, qs):
            panel(fig, ax, tri, val[sel], label, log, view, np)
            ax.set_title(label, fontsize=9)
        axes[0].set_ylabel("y (µm), mouth at 0")
        fig.suptitle(f"{case}: {view} view", fontsize=11)
        fig.text(0.01, 0.002, NOTE, fontsize=7, style="italic")
        fn = out / "plots" / f"{case}_{view}.png"
        fig.savefig(fn, dpi=130)
        plt.close(fig)
        print("wrote", fn)


def compare_maps(cases, outs, plt, mtri, np, dest):
    """Every case side by side per quantity on one colour scale, and the change from the baseline."""
    fields = [(c, load_field(o, np)) for c, o in zip(cases, outs)]
    fields = [(c, a) for c, a in fields if a is not None]
    if len(fields) < 2:
        print("comparison maps need field_*.csv in at least two cases; skipped")
        return
    base = dict(fields).get(BASELINE)
    keys = [q[0] for q in quantities(fields[0][1], np)] + (["dosc"] if any(a["osc"] for _, a in fields) else [])
    keys = list(dict.fromkeys(keys))
    for key in keys:
        vals, label, log = [], None, False
        for c, a in fields:
            q = {k: (lab, v, lg) for k, lab, v, lg in quantities(a, np)}
            if key in q:
                label, v, log = q[key]
            else:                                                  # D_osc of a non-oscillating case is zero
                v = np.zeros_like(a["x"])
            vals.append((c, a, v))
        for view in VIEWS:
            w, h = VIEWS[view][2]
            sels = [(c, a, v) + view_tri(a, view, mtri, np) for c, a, v in vals]
            allv = np.concatenate([np.log10(np.maximum(v[s], 1e-12)) if log else v[s] for _, _, v, _, s in sels])
            vmin, vmax = float(allv.min()), float(allv.max())
            fig, axes = plt.subplots(1, len(sels), figsize=(w * len(sels), h), constrained_layout=True, squeeze=False)
            for ax, (c, a, v, tri, s) in zip(axes[0], sels):
                panel(fig, ax, tri, v[s], label, log, view, np, vmin, vmax)
                ax.set_title(c, fontsize=9)
            axes[0][0].set_ylabel("y (µm), mouth at 0")
            fig.suptitle(f"All cases, {label}, {view} view (one colour scale)", fontsize=11)
            fig.text(0.01, 0.002, NOTE, fontsize=7, style="italic")
            fn = dest / f"maps_{key}_{view}.png"
            fig.savefig(fn, dpi=110)
            plt.close(fig)
            print("wrote", fn)
            # change from the baseline, only for cases on the same mesh (same cell count and positions)
            if base is None or key in ("dosc", "speed"):
                continue
            bq = {k: v for k, _, v, _ in quantities(base, np)}[key]
            diffs = [(c, a, v - bq, tri, s) for c, a, v, tri, s in sels
                     if c != BASELINE and a["x"].shape == base["x"].shape and np.allclose(a["x"], base["x"])
                     and np.allclose(a["y"], base["y"])]
            if not diffs:
                continue
            m = max(float(np.abs(d[s]).max()) for _, _, d, _, s in diffs) or 1e-9
            fig, axes = plt.subplots(1, len(diffs), figsize=(w * len(diffs), h), constrained_layout=True, squeeze=False)
            for ax, (c, a, d, tri, s) in zip(axes[0], diffs):
                panel(fig, ax, tri, d[s], "change from " + BASELINE + ": " + label, False, view, np, -m, m, "RdBu_r")
                ax.set_title(c, fontsize=9)
            axes[0][0].set_ylabel("y (µm), mouth at 0")
            fig.suptitle(f"Change from {BASELINE}, {label}, {view} view", fontsize=11)
            fig.text(0.01, 0.002, NOTE, fontsize=7, style="italic")
            fn = dest / f"diff_{key}_{view}.png"
            fig.savefig(fn, dpi=110)
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
    args = sys.argv[1:] or [BASELINE]
    if args == ["--all"]:
        args = sorted(p.parent.name for p in (HERE / "results").glob("*/summary.json")
                      if not p.parent.name.endswith(("_test", "_discover")))
        args.sort(key=lambda c: c != BASELINE)                    # baseline first
        print("cases:", " ".join(args))
    plt, mtri, np = mpl()
    outs = [HERE / "results" / c for c in args]
    for c, o in zip(args, outs):
        if not o.is_dir():
            raise SystemExit(f"no results/{c}")
        (o / "plots").mkdir(exist_ok=True)
        maps(c, o, plt, mtri, np)
        profiles([c], [o], o / "plots" / f"{c}_profiles.png", plt)
    if len(args) > 1:
        dest = HERE / "results" / "compare"
        dest.mkdir(parents=True, exist_ok=True)
        profiles(args, outs, dest / "profiles.png", plt)
        compare_maps(args, outs, plt, mtri, np, dest)


if __name__ == "__main__":
    main()
