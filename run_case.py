#!/usr/bin/env python3
"""Run one 2D Fluent case: TMAH etching of poly-Si in a 100 nm x 10 um slit under a megasonic field.

    python run_case.py --case M0_none --procs 4
    python run_case.py --case M0_none --discover       # compile the UDF + list Fluent settings (no solve)
    python run_case.py --case M0_none --setup-only     # full setup, a few steps of each phase -> _test
    python run_case.py --case M0_none --plan-only      # print the plan (no Fluent)

Phases:
  A (only with a tangential megasonic flow): oscillating Stokes-layer flow over the slit for 8 cycles to
    settle, then 10 cycles averaged; finish_avg turns the velocity statistics into D_osc.
  B: oscillation off (amp = 0), steady spin shear only; TMAH transport with diffusion + electromigration +
    D_osc and the poly-Si reaction, advanced with growing time steps to the quasi-steady state (~0.15 s).
Output in results/<case>/: dump_*.csv (poly-Si cells and centre column), summary.json, transcript.txt.
"""
import argparse
import csv
import glob
import json
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fluent2d import api, mesh2d  # noqa: E402
from fluent2d.params import header, load_case, mesh_argv, plan  # noqa: E402
from etchsim import props as P  # noqa: E402

FLUID_ZONES = ("bulk", "slit", "pocket")


def read_dumps(out):
    poly, centre = [], []
    for fn in glob.glob(str(out / "dump_*.csv")):
        with open(fn, newline="") as f:
            for r in csv.DictReader(f):
                row = {k: (float(v) if k != "kind" else v) for k, v in r.items()}
                (poly if row["kind"] == "poly" else centre).append(row)
    return poly, centre


def metrics(poly, centre):
    """Per poly-Si layer etch rate (both sides averaged), top/bottom, and the centre-column profile."""
    layers = {}
    for r in poly:
        k = int(-r["y"] // P.LAYER)
        layers.setdefault(k, []).append(r["etch_m_s"])
    ks = sorted(layers)
    er = [sum(layers[k]) / len(layers[k]) for k in ks]
    n5 = max(1, len(er) // 20)
    top, bot = sum(er[:n5]) / n5, sum(er[-n5:]) / n5
    cen = sorted((r for r in centre if r["y"] < 0), key=lambda r: -r["y"])
    return dict(n_poly_layers=len(ks), er_top_nm_min=top * 6e10, er_bottom_nm_min=bot * 6e10,
                uniformity=bot / top if top > 0 else float("nan"),
                er_mean_nm_min=sum(er) / len(er) * 6e10 if er else float("nan"),
                c_oh_bottom=cen[-1]["c_oh"] if cen else float("nan"),
                c_oh_mouth=cen[0]["c_oh"] if cen else float("nan"),
                c_sil_bottom=cen[-1]["c_sil"] if cen else float("nan"),
                c_h2_bottom=cen[-1]["c_h2"] if cen else float("nan"),
                c_oh_min=min((r["c_oh"] for r in poly), default=float("nan")),
                h2_max=max((r["c_h2"] for r in poly), default=float("nan")),
                d_osc_max=max((r["d_osc"] for r in centre), default=0.0),
                layers=[(k, e * 6e10) for k, e in zip(ks, er)])


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", required=True)
    ap.add_argument("--procs", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", 4)))
    ap.add_argument("--discover", action="store_true")
    ap.add_argument("--setup-only", action="store_true")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    p = plan(load_case(a.case))
    api.log("case", a.case, json.dumps({k: v for k, v in p.items() if k != "u_expr"}, indent=1, default=str))
    api.log("u_expr =", p["u_expr"])
    if a.plan_only:
        return
    tag = "_discover" if a.discover else "_test" if a.setup_only else ""
    out = (HERE / "results" / f"{a.case}{tag}").resolve()
    if (out / "summary.json").exists() and not (a.force or tag):
        raise SystemExit(f"{out} already has a finished run; use --force")
    out.mkdir(parents=True, exist_ok=True)
    for old in out.glob("dump_*.csv"):
        old.unlink()
    msh = out / f"{a.case}.msh"
    p["mesh_info"] = mesh2d.main(mesh_argv(p, msh))
    (out / "etch_params.h").write_text(header(p))          # kept for reference only
    src = (HERE / "fluent2d" / "udf" / "etch.c").read_text()
    inc = '#include "etch_params.h"'
    if inc not in src:
        raise SystemExit(f"etch.c has no {inc} line to inline")
    # Fluent copies only listed sources into libudf/src, so the parameters are inlined, not included
    (out / "etch.c").write_text(src.replace(inc, f"/* ---- inlined etch_params.h ---- */\n{header(p)}\n"))

    solver = api.launch(a.procs, out)
    t0 = time.time()
    try:
        s = api.settings(solver)
        try:
            api.tui(solver, '/file/start-transcript "transcript.txt"')
        except Exception as e:  # noqa: BLE001
            api.log("transcript not started:", e)
        api.first_ok("read mesh", lambda: s.file.read_mesh(file_name=msh.name),
                     lambda: s.file.read(file_type="mesh", file_name=msh.name))
        api.first_ok("transient", lambda: api.setv(api.pick(s.setup.general.solver, "time"), "unsteady-2nd-order"))
        api.first_ok("laminar", lambda: api.setv(api.pick(s.setup.models.viscous, "model"), "laminar"))
        fl = s.setup.materials.fluid
        mat = list(fl.get_object_names())[0]
        api.first_ok(f"liquid properties on {mat} (water at 60 C ~ 5 wt% TMAH)",
                     lambda: (api.setv(fl[mat].density.option, "constant"), api.setv(fl[mat].density.value, P.RHO_L),
                              api.setv(fl[mat].viscosity.option, "constant"),
                              api.setv(fl[mat].viscosity.value, P.MU_L)))
        if a.discover:                      # each step separately, so one failure doesn't hide the rest
            for label, fn in (("UDM", lambda: api.user_memory(solver, 9)),
                              ("UDF", lambda: api.compile_load_udf(solver, out)),
                              ("UDS", lambda: api.user_scalars(solver, 3, f"uds_flux::{api.UDF_LIB}"))):
                try:
                    fn()
                except Exception as e:  # noqa: BLE001
                    api.log(f"DISCOVER {label} FAILED:", e)
            api.discover(solver, out / "discover.txt")
            return
        api.user_memory(solver, 9)
        api.compile_load_udf(solver, out)
        api.user_scalars(solver, 3, f"uds_flux::{api.UDF_LIB}")
        # allocate UDM/UDS storage before the UDF hooks are attached (Fluent calls them at once)
        api.first_ok("early initialization", lambda: s.solution.initialization.standard_initialize())
        api.uds_diffusivity(solver, mat, [P.RHO_L * P.D[k] for k in ("OH", "SIL", "H2")])
        # sources everywhere: reaction is zero away from poly-Si, D_osc mixing acts in the bulk too
        zones = [z for z in FLUID_ZONES if z in p["mesh_info"]["cell_zones"]]
        api.cell_sources(solver, zones, {0: f"src_oh::{api.UDF_LIB}", 1: f"src_sil::{api.UDF_LIB}",
                                         2: f"src_h2::{api.UDF_LIB}"})
        ne = s.setup.named_expressions
        ne["amp"] = {"definition": "1" if p["oscillating"] else "0"}
        ne["u_in"] = {"definition": p["u_expr"]}
        ne["v_zero"] = {"definition": "0 [m/s]"}
        for b in ("inlet", "top"):
            api.set_inlet_components(s, b, "u_in", "v_zero")
        phi = [p["c_surf"][k] / P.RHO_L for k in ("OH", "SIL", "H2")]
        for kind, b in (("velocity_inlet", "inlet"), ("velocity_inlet", "top"), ("pressure_outlet", "outlet")):
            api.uds_values(solver, kind, b, phi)
        rd = s.solution.monitor.residual.equations
        for n_ in rd.get_object_names():
            try:
                api.setv(rd[n_].absolute_criteria, 1e-8)
            except Exception:  # noqa: BLE001
                pass

        ini = s.solution.initialization
        api.first_ok("standard initialization", lambda: ini.standard_initialize(), lambda: ini.initialize())
        allz = p["mesh_info"]["cell_zones"]
        for i, v in enumerate(phi):
            api.patch_uds(solver, allz, i, v)
        api.on_demand(solver, "init_poly_area")

        rc = s.solution.run_calculation.transient_controls
        hist = []
        settle, avg = p["steps_A"]
        if p["oscillating"]:
            n_cyc = 40
            api.setv(rc.time_step_size, p["dt_A"])
            api.log(f"phase A: oscillating flow, dt = {p['dt_A']:.3e} s")
            api.iterate(solver, 4 if a.setup_only else settle * n_cyc, p["iters"])
            api.on_demand(solver, "start_avg")
            for _ in range(4 if a.setup_only else avg * n_cyc):
                api.iterate(solver, 1, p["iters"])
                api.on_demand(solver, "accumulate_now")
            api.on_demand(solver, "finish_avg")
        ne["amp"] = {"definition": "0"}
        t_sim = 0.0
        for dt, n in p["phase_B"]:
            n = 2 if a.setup_only else n
            api.setv(rc.time_step_size, dt)
            api.iterate(solver, n, p["iters"])
            t_sim += dt * n
            api.on_demand(solver, "dump")
            m = metrics(*read_dumps(out))
            hist.append(dict(t_B=t_sim, dt=dt, **{k: v for k, v in m.items() if k != "layers"}))
            api.log(f"phase B t = {t_sim:.4g} s: etch top {m['er_top_nm_min']:.2f} bottom {m['er_bottom_nm_min']:.2f} "
                    f"nm/min, bottom/top {m['uniformity']:.4f}, c_OH mouth {m['c_oh_mouth']:.1f} bottom "
                    f"{m['c_oh_bottom']:.1f}, c_SIL bottom {m['c_sil_bottom']:.1f}, c_H2 bottom {m['c_h2_bottom']:.1f}")
        api.on_demand(solver, "report")
        api.on_demand(solver, "dump")
        api.first_ok("write case/data", lambda: s.file.write(file_type="case-data", file_name=f"{a.case}-final.cas.h5"))
        m = metrics(*read_dumps(out))
        conv = abs(hist[-1]["uniformity"] - hist[-2]["uniformity"]) if len(hist) > 1 else float("nan")
        p.update(result=m, history=hist, quasi_steady_change=conv, setup_only=a.setup_only, wall_s=time.time() - t0)
        (out / "summary.json").write_text(json.dumps(p, indent=1, default=str))
        api.log("done:", json.dumps({k: m[k] for k in ("er_top_nm_min", "er_bottom_nm_min", "uniformity")}),
                "| 1D reference:", json.dumps(p["one_d"]))
    finally:
        solver.exit()


if __name__ == "__main__":
    main()
