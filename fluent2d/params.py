"""Per-case plan for the 2D Fluent model: geometry, megasonic boundary flow, concentrations, time steps,
and the C header (etch_params.h) that the UDF is compiled with. Pure Python (no Fluent).

Megasonic boundary flow (wafer frame, x along the wafer, y up). Outside the slit the wall is flat, so the
oscillating flow is the exact Stokes-layer solution on top of the steady shear of the spinning wafer:
    u(y, t) = G y + AMP u_t [cos(w t) - exp(-y/delta) cos(w t - y/delta)],  v = 0
It is imposed on the inlet (x = X0) and the top (y = H); the slit disturbs it only locally.
  u_t  : tangential megasonic velocity at the wafer (etchsim.acoustics.wall_velocities: plane wave of
         intensity I at incidence theta, reflected by the elastic Si wafer). theta = 90 deg (MegPie,
         transducer parallel to the wafer) gives u_t = 0. The normal component moves wafer and liquid
         together at this scale (wavelength ~1 mm) and is not a relative flow.
  G    : shear of the liquid gap between the spinning wafer and the MegPie face, G = Omega r / gap (Couette).
  AMP  : named expression, 1 during the oscillating phase, 0 afterwards.

H2 bubble cases (bubble_top_um, bubble_len_um > 0): a gas plug cut out of the mesh (mesh2d). With sound
(f, I > 0) it pulsates (stable cavitation, etchsim/cavitation.py) and pumps the liquid between it and the
mouth; the resulting Taylor-type dispersion of each species (D_pump) is added in etch.c to the axial faces
of the slit above the plug. Phase B only: the pumping is folded into D_pump, no oscillating flow is solved.
"""
import csv
import math
from pathlib import Path

from etchsim import acoustics as A
from etchsim import cavitation as CV
from etchsim import props as P

from . import mesh2d

ROOT = Path(__file__).resolve().parents[1]
CASES_CSV = ROOT / "cases.csv"
GAP = 2e-3                 # m, ASSUMED MegPie-to-wafer liquid gap
CYCLES_SETTLE, CYCLES_AVG, STEPS_PER_CYCLE = 8, 10, 40
# (dt, steps): ~0.305 s = 6 silicate diffusion times L^2/D_SIL (51 ms); 1 ms steps reported every 50 ms so
# the last reports show whether the slit is quasi-steady (M0_none at 0.155 s was not checked: 0.940 vs 1D 0.957)
PHASE_B = [(1e-7, 20), (1e-6, 30), (1e-5, 30), (1e-4, 50)] + [(1e-3, 50)] * 6


def load_case(name, path=CASES_CSV):
    with open(path, newline="") as f:
        for r in csv.DictReader(f):
            if r["case"] == name:
                return r
    raise SystemExit(f"case {name} not in {path}")


def _f(r, k, d):
    v = r.get(k)
    return float(v) if v not in (None, "") else d


def surface_concentrations(extra_mixing, er_ref, order, migration):
    """Mouth concentrations from the 1D model (wafer-level boundary layer, same physics)."""
    from etchsim.slit1d import Slit
    om = P.omega_spin()
    km = {s: P.levich_km(P.D[s] + extra_mixing, om) for s in ("OH", "SIL", "H2")}
    s = Slit(n=1000, km=km, er_ref=er_ref, order=order, migration=migration)
    res = s.solve()
    return res["surf"], res


ONE_D_COLS = ("c_oh_surf", "c_sil_surf", "c_h2_surf", "one_d_er_top", "one_d_er_bottom", "one_d_uniformity",
              "one_d_oh_min")


def one_d_reference(row):
    """1D mouth concentrations and reference result for a case (needs scipy: run locally by make_cases.py,
    stored in cases.csv so the cluster does not need scipy)."""
    p = plan(row, need_1d=True)
    return {"c_oh_surf": p["c_surf"]["OH"], "c_sil_surf": p["c_surf"]["SIL"], "c_h2_surf": p["c_surf"]["H2"],
            "one_d_er_top": p["one_d"]["er_top"], "one_d_er_bottom": p["one_d"]["er_bottom"],
            "one_d_uniformity": p["one_d"]["uniformity"], "one_d_oh_min": p["one_d"]["oh_min"]}


def plan(row, need_1d=False):
    f = _f(row, "f_MHz", 0.0) * 1e6
    I = _f(row, "I_W_cm2", 0.0)
    theta = _f(row, "theta_deg", 90.0)
    recess = _f(row, "recess_nm", 0.0) * 1e-9
    refine = _f(row, "refine", 1.0)
    order = _f(row, "order", P.ORDER_OH)
    er_ref = _f(row, "er_ref_nm_min", P.ER_REF * 6e10) / 6e10
    migration = int(_f(row, "migration", 1))
    osc_scale = _f(row, "osc_scale", 1.0)
    b_top, b_len = _f(row, "bubble_top_um", 0.0) * 1e-6, _f(row, "bubble_len_um", 0.0) * 1e-6
    pump = dict(D={k: 0.0 for k in ("OH", "SIL", "H2", "TMA")})
    if b_len > 0 and I > 0 and f > 0:
        pump = CV.pumping(f, I, b_top, b_len, theta=theta)
        pump["D"] = {k: CV.oscillatory_dispersion(pump["U"], f, Dm=P.D[k]) for k in ("OH", "SIL", "H2", "TMA")}
    om_spin = P.omega_spin()
    G = om_spin * P.R_PROBE / GAP
    if I > 0 and f > 0:
        o = A.slit_oscillation(I, theta, f, P.W_SLIT)
        u_t, delta, omega = o["u_t"], o["delta"], 2 * math.pi * f
    else:
        o, u_t, delta, omega = None, 0.0, 1.0, 1.0
    osc = u_t > 1e-9
    extra = u_t ** 2 / (2 * omega) if osc else 0.0
    if not need_1d and all(row.get(k) not in (None, "") for k in ONE_D_COLS):     # precomputed in cases.csv
        surf = {"OH": float(row["c_oh_surf"]), "SIL": float(row["c_sil_surf"]), "H2": float(row["c_h2_surf"])}
        res1d = {"er_top": float(row["one_d_er_top"]), "er_bottom": float(row["one_d_er_bottom"]),
                 "uniformity": float(row["one_d_uniformity"]), "oh_min": float(row["one_d_oh_min"])}
    else:
        surf, res1d = surface_concentrations(extra, er_ref, order, bool(migration))
    p = dict(case=row["case"], f=f, I=I, theta=theta, recess=recess, refine=refine, order=order,
             er_ref=er_ref, migration=migration, osc_scale=osc_scale, G=G, gap=GAP, u_t=u_t, delta=delta,
             omega=omega, oscillating=osc, c_surf=surf, rho=P.RHO_L, mu=P.MU_L,
             mesh=dict(W=P.W_SLIT, L=P.L_SLIT, layer=P.LAYER, recess=recess, pitch=P.PITCH, H=2e-6,
                       dx=5e-9 / refine, dy=10e-9 / refine, dy_top=5e-9 / refine, ratio=1.1,
                       bubble_top=b_top, bubble_len=b_len),
             pump=pump,
             one_d=dict(er_top=res1d["er_top"], er_bottom=res1d["er_bottom"], uniformity=res1d["uniformity"],
                        oh_min=res1d["oh_min"]),
             iters=int(_f(row, "iters", 20)))
    p["dt_A"] = 1 / (STEPS_PER_CYCLE * f) if osc else None
    p["steps_A"] = (CYCLES_SETTLE, CYCLES_AVG) if osc else (0, 0)
    p["phase_B"] = PHASE_B
    p["t_B"] = sum(dt * n for dt, n in PHASE_B)
    w = "{:.10g}".format
    p["u_expr"] = (f"{w(G)} [s^-1] * y + amp * {w(u_t)} [m/s] * (cos({w(omega)} [s^-1] * t) - "
                   f"exp(-y / {w(delta)} [m]) * cos({w(omega)} [s^-1] * t - y / {w(delta)} [m]))")
    return p


def mesh_argv(p, out):
    m = p["mesh"]
    return ["--W", str(m["W"]), "--L", str(m["L"]), "--layer", str(m["layer"]), "--recess", str(m["recess"]),
            "--pitch", str(m["pitch"]), "--H", str(m["H"]), "--dx", str(m["dx"]), "--dy", str(m["dy"]),
            "--dy-top", str(m["dy_top"]), "--ratio", str(m["ratio"]), "--bubble-top", str(m["bubble_top"]),
            "--bubble-len", str(m["bubble_len"]), "-o", str(out)]


def header(p):
    """Constants for udf/etch.c (SI units)."""
    m = p["mesh"]
    n_poly = mesh2d.wet_poly_layers(P.L_SLIT, P.LAYER, m["bubble_top"], m["bubble_len"])
    vals = dict(RHO=P.RHO_L, CB=P.C_BULK, D_OH=P.D["OH"], D_SIL=P.D["SIL"], D_TMA=P.D["TMA"], D_H2=P.D["H2"],
                D_BASE=max(P.D[k] for k in ("OH", "SIL", "H2")),
                K_SI=P.si_flux(p["er_ref"]), ORDER=p["order"], EPS=1e-6, OMEGA=p["omega"],
                OSC_SCALE=p["osc_scale"], M_SI=P.M_SI, RHO_SI=P.RHO_SI,
                POLY_LENGTH=2 * n_poly * P.LAYER, W_SLIT=P.W_SLIT, DX_CELL=p["mesh"]["dx"],
                BUB_TOP=m["bubble_top"] if m["bubble_len"] > 0 else 0.0,
                DPUMP_OH=p["pump"]["D"]["OH"], DPUMP_SIL=p["pump"]["D"]["SIL"], DPUMP_H2=p["pump"]["D"]["H2"],
                DPUMP_TMA=p["pump"]["D"]["TMA"])
    lines = [f"/* generated by fluent2d/params.py for case {p['case']} */"]
    lines += [f"#define {k} {v:.12g}" for k, v in vals.items()]
    lines += [f"#define MIGRATION {int(p['migration'])}", f"#define POLY_ID {mesh2d.POLY_ID}"]
    return "\n".join(lines) + "\n"
