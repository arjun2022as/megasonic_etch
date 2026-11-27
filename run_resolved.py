#!/usr/bin/env python3
"""Case 10: RESOLVED megasonic oscillation over the slit (no D_osc closure), bubble-free.

    python run_resolved.py --case R15_flat --procs 4
    python run_resolved.py --case R15_flat --setup-only     # a few steps of each phase -> results/R15_flat_test
    python run_resolved.py --case R15_flat --plan-only      # print the plan (no Fluent)

Cell: one pitch (1 um), periodic left/right, the slit (flat or comb walls) and H of liquid above the wafer.
  top (y = H): velocity inlet u = G H + amp_t u_t sin(w (t - t0)), v = v_top(t); species held at the values of
               the no-sound Levich film at height H (outer film: plain D; the run checks that H2 is uniform along
               the wafer there, which is the condition for sound to have no effect above H).
  sound:       body force RHO u_t w cos(w (t - t0)) (tangential slip) and the compression mass source
               -(w p_wall / c^2) cos(w (t - t0)) (pressure antinode), see fluent2d/udf/resolved_extra.c.
Phases:
  B  no sound: the same quasi-steady TMAH transport as run_case.py (reaction + diffusion + migration, no D_osc).
     Rows of H2 flux are recorded at the end (baseline D_eff, = D_H2 if the solver and the measurement agree).
  S  sound on (sound cases only): 40 steps per acoustic period; SETTLE cycles, then MEASURE cycles sampled
     every 4 steps: cycle-averaged H2 flux and gradient per row -> D_eff(y), plus the closure D_osc for comparison.
Output in results/<case>/: rows_B_*.csv, rows_S_*.csv, mouth log, dump_*.csv, field_*.csv, summary.json.
Post-processing on the laptop: analyze_resolved.py.
"""
import argparse
import csv
import glob
import json
import math
import os
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))
from fluent2d import api, mesh2d  # noqa: E402
from fluent2d.params import GAP, PHASE_B, header  # noqa: E402
from etchsim import acoustics as A  # noqa: E402
from etchsim import props as P  # noqa: E402
from run_case import MAX_EXTRA_BLOCKS, metrics, read_dumps  # noqa: E402

CASES_CSV = HERE / "cases_resolved.csv"
FLUID_ZONES = ("bulk", "slit", "pocket")
STEPS_PER_CYCLE, SAMPLE_EVERY, LOG_EVERY_CYCLES = 40, 4, 50
N_UDM = 19


def load(name, path):
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["case"] == name:
                return r
    raise SystemExit(f"case {name} not in {path}")


def top_values(H):
    """Species at height H in the no-sound Levich film: c(H) = c_b + (c_s - c_b)(1 - k H / D) (near-wall profile is
    linear: the spin flow's convection is negligible below ~10 um, Pe = 0.51 Om^1.5 nu^-0.5 H^3 / D ~ 0.014).
    c_s = mouth (wafer-level) values of the no-sound 1D model (cases.csv, M0_none)."""
    m0 = load("M0_none", HERE / "cases.csv")
    cs = {"OH": float(m0["c_oh_surf"]), "SIL": float(m0["c_sil_surf"]), "H2": float(m0["c_h2_surf"])}
    cb = {"OH": P.C_BULK, "SIL": 0.0, "H2": 0.0}
    om = P.omega_spin()
    out = {}
    for k in ("OH", "SIL", "H2"):
        km = P.levich_km(P.D[k], om)
        out[k] = cb[k] + (cs[k] - cb[k]) * (1 - km * H / P.D[k])
    return out, cs


def plan(row):
    f = float(row["f_MHz"]) * 1e6 or 1e6
    I = float(row["I_W_cm2"])
    theta = float(row["theta_deg"])
    H = float(row["H_um"]) * 1e-6
    recess = float(row["recess_nm"]) * 1e-9
    om = 2 * math.pi * f
    if I > 0:
        wv = A.wall_velocities(I, theta)
        u_t = wv["u_t"] if int(row["slip"]) else 0.0
        p_wall = wv["p_wall"] if int(row["compress"]) else 0.0
    else:
        u_t = p_wall = 0.0
    tops, cs = top_values(H)
    p = dict(case=row["case"], f=f, I=I, theta=theta, omega=om, u_t=u_t, p_wall=p_wall, H=H, recess=recess,
             G=P.omega_spin() * P.R_PROBE / GAP, gap=GAP, c_top=tops, c_mouth_1d=cs, sound=u_t > 0 or p_wall > 0,
             settle_cycles=int(row["settle_cycles"]), measure_cycles=int(row["measure_cycles"]),
             iters=int(row["iters"]), iters_B=20, dt=1 / (STEPS_PER_CYCLE * f),
             delta=A.stokes_delta(f), er_ref=P.ER_REF, order=P.ORDER_OH, migration=1, osc_scale=1.0,
             pump=dict(D={k: 0.0 for k in ("OH", "SIL", "H2", "TMA")}),
             mesh=dict(W=P.W_SLIT, L=P.L_SLIT, layer=P.LAYER, recess=recess, pitch=P.PITCH, H=H, dx=5e-9,
                       dy=10e-9, dy_top=5e-9, ratio=1.1, bubble_top=0.0, bubble_len=0.0))
    return p


def mesh_args(p, out):
    m = p["mesh"]
    return ["--W", str(m["W"]), "--L", str(m["L"]), "--layer", str(m["layer"]), "--recess", str(m["recess"]),
            "--pitch", str(m["pitch"]), "--H", str(m["H"]), "--dx", str(m["dx"]), "--dy", str(m["dy"]),
            "--dy-top", str(m["dy_top"]), "--ratio", str(m["ratio"]), "--periodic-sides", "-o", str(out)]


def header_resolved(p):
    extra = dict(U_T=p["u_t"], P_WALL=p["p_wall"], C_SOUND_L=P.C_SOUND, ROW1_Y=p["mesh"]["dy_top"])
    return header(p) + "".join(f"#define {k} {v:.12g}\n" for k, v in extra.items())


def expressions(p, t0, amp_t, amp_n):
    w = "{:.12g}".format
    u = f"{w(p['G'] * p['H'])} [m/s]"
    if amp_t and p["u_t"] > 0:
        u += f" + {w(p['u_t'])} [m/s] * sin({w(p['omega'])} [s^-1] * (t - {w(t0)} [s]))"
    v = "0 [m/s]"
    if amp_n and p["p_wall"] > 0:
        v = f"-{w(p['v_top_amp'])} [m/s] * cos({w(p['omega'])} [s^-1] * (t - {w(t0)} [s]))"
    return u, v


def collect(out, pattern, new_prefix):
    """rename the per-process files of the last dump (rows_<id>.csv -> rows_B_<id>.csv)"""
    for fn in glob.glob(str(out / pattern)):
        q = Path(fn)
        q.replace(q.with_name(new_prefix + q.name.split("_", 1)[1]))


def mouth_now(out):
    s_row = l_row = s_slit = n_slit = 0.0
    for fn in glob.glob(str(out / "mouth_*.csv")):
        with open(fn, newline="") as f:
            r = next(csv.DictReader(f))
        s_row += float(r["s_row"]); l_row += float(r["l_row"])
        s_slit += float(r["s_slit"]); n_slit += float(r["n_slit"])
    return (s_row / l_row if l_row else float("nan"), s_slit / n_slit if n_slit else float("nan"))


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--case", required=True)
    ap.add_argument("--procs", type=int, default=int(os.environ.get("SLURM_CPUS_PER_TASK", 4)))
    ap.add_argument("--setup-only", action="store_true")
    ap.add_argument("--plan-only", action="store_true")
    ap.add_argument("--force", action="store_true")
    a = ap.parse_args()

    p = plan(load(a.case, CASES_CSV))
    out = (HERE / "results" / f"{a.case}{'_test' if a.setup_only else ''}").resolve()
    msh = out / f"{a.case}.msh"
    if a.plan_only:
        api.log("plan", json.dumps(p, indent=1, default=str))
        return
    if (out / "summary.json").exists() and not (a.force or a.setup_only):
        raise SystemExit(f"{out} already has a finished run; use --force")
    out.mkdir(parents=True, exist_ok=True)
    for old in [*out.glob("dump_*.csv"), *out.glob("field_*.csv"), *out.glob("rows_*.csv"), *out.glob("mouth_*.csv")]:
        old.unlink()
    p["mesh_info"] = mesh2d.main(mesh_args(p, msh))
    # compression: all the liquid in the cell is squeezed, the same volume leaves through the top
    p["v_top_amp"] = (p["omega"] * p["p_wall"] * p["mesh_info"]["liquid_area"]
                      / (P.RHO_L * P.C_SOUND ** 2 * P.PITCH))
    api.log("case", a.case, json.dumps({k: v for k, v in p.items() if k not in ("mesh_info",)}, indent=1, default=str))
    src = (HERE / "fluent2d" / "udf" / "etch.c").read_text()
    inc = '#include "etch_params.h"'
    extra_c = (HERE / "fluent2d" / "udf" / "resolved_extra.c").read_text()
    (out / "etch.c").write_text(src.replace(inc, f"/* ---- inlined parameters ---- */\n{header_resolved(p)}\n")
                                + "\n" + extra_c)

    solver = api.launch(a.procs, out)
    t0_wall = time.time()
    try:
        s = api.settings(solver)
        try:
            api.tui(solver, '/file/start-transcript "transcript.txt"')
        except Exception as e:  # noqa: BLE001
            api.log("transcript not started:", e)
        api.first_ok("read mesh", lambda: s.file.read_mesh(file_name=msh.name),
                     lambda: s.file.read(file_type="mesh", file_name=msh.name))
        api.make_periodic(solver, "left", "right")
        api.first_ok("transient", lambda: api.setv(api.pick(s.setup.general.solver, "time"), "unsteady-2nd-order"))
        api.first_ok("laminar", lambda: api.setv(api.pick(s.setup.models.viscous, "model"), "laminar"))
        fl = s.setup.materials.fluid
        mat = list(fl.get_object_names())[0]
        api.first_ok(f"liquid properties on {mat}",
                     lambda: (api.setv(fl[mat].density.option, "constant"), api.setv(fl[mat].density.value, P.RHO_L),
                              api.setv(fl[mat].viscosity.option, "constant"),
                              api.setv(fl[mat].viscosity.value, P.MU_L)))
        api.user_memory(solver, N_UDM)
        api.compile_load_udf(solver, out)
        api.user_scalars(solver, 3, f"uds_flux::{api.UDF_LIB}")
        api.first_ok("early initialization", lambda: s.solution.initialization.standard_initialize())
        d_base = max(P.D[k] for k in ("OH", "SIL", "H2"))
        api.uds_diffusivity(solver, mat, [P.RHO_L * d_base] * 3)
        zones = [z for z in FLUID_ZONES if z in p["mesh_info"]["cell_zones"]]
        api.cell_sources(solver, zones, {0: f"src_oh::{api.UDF_LIB}", 1: f"src_sil::{api.UDF_LIB}",
                                         2: f"src_h2::{api.UDF_LIB}"})
        api.cell_sources_named(solver, zones, {"mass": f"mass_src::{api.UDF_LIB}",
                                               "x-momentum": f"xmom_src::{api.UDF_LIB}"})
        ne = s.setup.named_expressions
        u0, v0 = expressions(p, 0.0, 0, 0)
        ne["u_top"] = {"definition": u0}
        ne["v_top"] = {"definition": v0}
        api.set_inlet_components(s, "top", "u_top", "v_top")
        phi = [p["c_top"][k] / P.RHO_L for k in ("OH", "SIL", "H2")]
        api.uds_values(solver, "velocity_inlet", "top", phi)
        rd = s.solution.monitor.residual.equations
        for n_ in rd.get_object_names():
            try:
                api.setv(rd[n_].absolute_criteria, 1e-8)
            except Exception:  # noqa: BLE001
                pass
        ini = s.solution.initialization
        api.first_ok("standard initialization", lambda: ini.standard_initialize(), lambda: ini.initialize())
        for i, v in enumerate(phi):
            api.patch_uds(solver, p["mesh_info"]["cell_zones"], i, v)
        api.on_demand(solver, "init_poly_area")
        rc = s.solution.run_calculation.transient_controls

        # ---------------- phase B: no sound, quasi-steady
        hist, t_sim = [], 0.0

        def stages():
            yield from PHASE_B
            for _ in range(0 if a.setup_only else MAX_EXTRA_BLOCKS):
                h0, h1 = hist[-2], hist[-1]
                if (abs(h1["uniformity"] - h0["uniformity"]) < 1e-4
                        and abs(h1["c_oh_bottom"] - h0["c_oh_bottom"]) < 1e-4 * max(abs(h1["c_oh_bottom"]), 1.0)
                        and abs(h1["c_sil_bottom"] - h0["c_sil_bottom"]) < 5e-4 * max(abs(h1["c_sil_bottom"]), 1.0)
                        and abs(h1["c_h2_mouth"] - h0["c_h2_mouth"]) < 1e-4 * max(abs(h1["c_h2_mouth"]), 1.0)):
                    return
                yield 1e-3, 50
            api.log(f"WARNING: not settled after {MAX_EXTRA_BLOCKS} extra 50 ms blocks")

        for dt, n in stages():
            n = 2 if a.setup_only else n
            api.setv(rc.time_step_size, dt)
            api.iterate(solver, n, p["iters_B"])
            t_sim += dt * n
            api.on_demand(solver, "dump")
            api.on_demand(solver, "dump_mouth")
            m = metrics(*read_dumps(out))
            mrow, mslit = mouth_now(out)
            hist.append(dict(t=t_sim, dt=dt, c_h2_mouth=mrow, c_h2_slit_top=mslit,
                             **{k: v for k, v in m.items() if k != "layers"}))
            api.log(f"phase B t = {t_sim:.4g} s: bottom/top {m['uniformity']:.5f}, H2 first row {mrow:.3f} mM "
                    f"({mrow / P.H2_SAT:.2f}x), slit top {mslit:.3f} mM, c_SIL bottom {m['c_sil_bottom']:.1f}")
        # baseline rows (steady): a few samples with the same measurement
        api.on_demand(solver, "start_rows")
        api.setv(rc.time_step_size, 1e-4)
        for _ in range(2 if a.setup_only else 10):
            api.iterate(solver, 1, p["iters_B"])
            t_sim += 1e-4
            api.on_demand(solver, "acc_rows")
        api.on_demand(solver, "dump_rows")
        collect(out, "rows_*.csv", "rows_B_")
        api.on_demand(solver, "dump_field")
        collect(out, "field_*.csv", "field_B_")
        result_B = metrics(*read_dumps(out))
        api.first_ok("write case/data B", lambda: s.file.write(file_type="case-data", file_name=f"{a.case}-B.cas.h5"))

        # ---------------- phase S: sound on, resolved
        mouth_log = []
        if p["sound"]:
            t0 = t_sim            # sound_on stores Fluent's own flow time as t0 for the sources (same value)
            u1, v1 = expressions(p, t0, 1, 1)
            ne["u_top"] = {"definition": u1}
            ne["v_top"] = {"definition": v1}
            api.on_demand(solver, "sound_on")
            api.setv(rc.time_step_size, p["dt"])
            settle = 2 if a.setup_only else p["settle_cycles"]
            done = 0
            while done < settle:
                nc = min(LOG_EVERY_CYCLES, settle - done)
                api.iterate(solver, (1 if a.setup_only else nc * STEPS_PER_CYCLE), p["iters"])
                done += nc
                api.on_demand(solver, "dump_mouth")
                mrow, mslit = mouth_now(out)
                mouth_log.append(dict(cycles=done, c_h2_row1=mrow, c_h2_slit_top=mslit))
                api.log(f"phase S settle: {done} cycles, H2 first row {mrow:.3f} mM ({mrow / P.H2_SAT:.2f}x), "
                        f"slit top {mslit:.3f} mM (instantaneous)")
            api.on_demand(solver, "start_rows")
            n_samples = 4 if a.setup_only else p["measure_cycles"] * STEPS_PER_CYCLE // SAMPLE_EVERY
            for k in range(n_samples):
                api.iterate(solver, SAMPLE_EVERY, p["iters"])
                api.on_demand(solver, "acc_rows")
                if (k + 1) % (LOG_EVERY_CYCLES * STEPS_PER_CYCLE // SAMPLE_EVERY) == 0:
                    api.on_demand(solver, "dump_mouth")
                    mrow, mslit = mouth_now(out)
                    mouth_log.append(dict(cycles=settle + (k + 1) * SAMPLE_EVERY // STEPS_PER_CYCLE,
                                          c_h2_row1=mrow, c_h2_slit_top=mslit))
                    api.log(f"phase S measure: sample {k + 1}/{n_samples}, H2 first row {mrow:.3f} mM")
            api.on_demand(solver, "finish_avg")                        # closure D_osc, for comparison only
            api.on_demand(solver, "dump_rows")
            collect(out, "rows_*.csv", "rows_S_")
            api.on_demand(solver, "dump_field")
            collect(out, "field_*.csv", "field_S_")
            api.on_demand(solver, "sound_off")
            api.first_ok("write case/data S",
                         lambda: s.file.write(file_type="case-data", file_name=f"{a.case}-S.cas.h5"))
        api.on_demand(solver, "report")
        api.on_demand(solver, "dump")
        m = metrics(*read_dumps(out))
        p.update(result_B={k: v for k, v in result_B.items() if k != "layers"},
                 result_end={k: v for k, v in m.items() if k != "layers"}, history_B=hist, mouth_log=mouth_log,
                 setup_only=a.setup_only, wall_s=time.time() - t0_wall)
        (out / "summary.json").write_text(json.dumps(p, indent=1, default=str))
        api.log("done", a.case, f"wall {p['wall_s'] / 3600:.2f} h")
    finally:
        solver.exit()


if __name__ == "__main__":
    main()
