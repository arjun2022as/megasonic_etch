"""Thin layer over PyFluent 0.37 / Fluent 2024 R1.

The calls that are proven on Puma (launch, mesh read, transient/laminar, named expressions, velocity-
component inlets, time stepping) come from the sibling projects 3d_nand and 3d_nand_2. The UDF/UDS hookups
could not be checked against 2024 R1 documentation, so each tries several forms, logs what exists when all
fail, and Fluent's own transcript is kept (transcript.txt) for diagnosis. `discover()` prints the relevant
settings trees so the exact paths can be fixed after one short run.
"""
import os
import time

UDF_LIB = "libudf"


def log(*a):
    print(time.strftime("[%H:%M:%S]"), *a, flush=True)


def first_ok(label, *attempts):
    errors = []
    for fn in attempts:
        try:
            out = fn()
            log(f"{label}: ok")
            return out
        except Exception as e:  # noqa: BLE001
            errors.append(f"{type(e).__name__}: {e}")
    raise RuntimeError(f"{label} failed:\n  " + "\n  ".join(errors))


def pick(obj, *names):
    for n in names:
        try:
            return getattr(obj, n)
        except (AttributeError, RuntimeError):
            continue
    raise AttributeError(f"none of {names} under {getattr(obj, 'path', obj)}; "
                         f"available: {getattr(obj, 'child_names', '?')}")


def setv(obj, value):
    obj.set_state(value)
    return obj


def launch(procs, workdir):
    import ansys.fluent.core as pyfluent
    log(f"PyFluent {pyfluent.__version__}, Fluent 2D double precision on {procs} cores")
    for k in [k for k in os.environ if k.startswith("SLURM_")]:     # else PyFluent ssh-spawns
        os.environ.pop(k)
    return pyfluent.launch_fluent(product_version=pyfluent.FluentVersion.v241, dimension=pyfluent.Dimension.TWO,
                                  precision=pyfluent.Precision.DOUBLE, processor_count=procs,
                                  ui_mode=pyfluent.UIMode.NO_GUI_OR_GRAPHICS, cwd=str(workdir), start_timeout=900)


def tui(solver, cmd):
    log("TUI>", cmd)
    fn = getattr(solver, "execute_tui", None)
    if fn is None:
        raise RuntimeError("this PyFluent has no execute_tui")
    out = fn(cmd)
    if out:
        log(str(out)[-2000:])
    return out


def settings(solver):
    return getattr(solver, "settings", solver)


# ---------------------------------------------------------------- discovery
KEYWORDS = ("user_defined", "uds", "scalar", "compiled", "memory", "on_demand", "hook", "source", "diffusiv",
            "udf", "export", "ascii", "patch")


def walk(obj, path, depth, out, max_depth=6, seen=None):
    seen = seen if seen is not None else set()
    if depth > max_depth or id(obj) in seen:
        return
    seen.add(id(obj))
    names = list(getattr(obj, "child_names", []) or [])
    cmds = list(getattr(obj, "command_names", []) or [])
    if any(k in path.lower() for k in KEYWORDS):
        extra = ""
        try:
            av = obj.allowed_values()
            extra = f"  allowed={list(av)[:30]}"
        except Exception:  # noqa: BLE001
            pass
        out.append(f"{path}  children={names[:40]} commands={cmds[:20]}{extra}")
    for n in names:
        try:
            child = getattr(obj, n)
        except Exception:  # noqa: BLE001
            continue
        walk(child, f"{path}.{n}", depth + 1, out, max_depth, seen)
    try:                                     # named-object containers: look inside the first object
        objs = list(obj.get_object_names())
        if objs:
            walk(obj[objs[0]], f"{path}['{objs[0]}']", depth + 1, out, max_depth, seen)
    except Exception:  # noqa: BLE001
        pass


def discover(solver, out_file):
    s = settings(solver)
    lines = []
    for root in ("setup", "solution", "file"):
        try:
            walk(getattr(s, root), root, 0, lines)
        except Exception as e:  # noqa: BLE001
            lines.append(f"{root}: {e}")
    try:
        lines.append("TUI define/user_defined: " + str(dir(solver.tui.define.user_defined)))
    except Exception as e:  # noqa: BLE001
        lines.append(f"tui: {e}")
    with open(out_file, "w") as f:
        f.write("\n".join(lines) + "\n")
    log(f"discovery: {len(lines)} settings paths written to {out_file}")


# ---------------------------------------------------------------- UDF / UDS setup
def compile_load_udf(solver):
    first_ok("compile UDF",
             lambda: tui(solver, f'/define/user-defined/compiled-functions compile "{UDF_LIB}" yes "etch.c" "" ""'),
             lambda: solver.tui.define.user_defined.compiled_functions("compile", UDF_LIB, "yes", "etch.c", "", ""))
    first_ok("load UDF",
             lambda: tui(solver, f'/define/user-defined/compiled-functions load "{UDF_LIB}"'),
             lambda: solver.tui.define.user_defined.compiled_functions("load", UDF_LIB))


def user_memory(solver, n):
    s = settings(solver)
    first_ok(f"{n} user-defined memories",
             lambda: setv(pick(pick(s.setup, "user_defined"), "user_defined_memory", "number_of_memory_locations"), n),
             lambda: tui(solver, f"/define/user-defined/user-defined-memory {n}"))


def user_scalars(solver, n, flux_fn):
    """n UDS solved in all fluid zones, convective flux from the UDF (electromigration), transient term on."""
    s = settings(solver)

    def via_settings():
        ud = pick(s.setup, "user_defined", "models")
        uds = pick(ud, "user_defined_scalars", "uds")
        setv(pick(uds, "number_of_scalars", "n_uds", "number"), n)
        for i in range(n):
            sc = uds.scalars[i] if hasattr(uds, "scalars") else uds[i]
            setv(pick(sc, "flux_function", "flux_func"), flux_fn)
    seq = [str(n)] + [x for _ in range(n) for x in ("all-fluid-zones", f'"{flux_fn}"', "default")]
    first_ok(f"{n} user-defined scalars with flux {flux_fn}",
             via_settings,
             lambda: tui(solver, "/define/user-defined/user-defined-scalars " + " ".join(seq)))


def uds_diffusivity(solver, material, fn, n):
    """2024 R1 (from --discover): uds_diffusivity.option allows only 'defined-per-uds'; each
    uds_diffusivities['uds-i'] then takes its own option + user_defined_function."""
    ud = settings(solver).setup.materials.fluid[material].uds_diffusivity
    setv(ud.option, option(ud.option, "defined-per-uds"))
    per = ud.uds_diffusivities
    log("uds_diffusivities:", list(per.get_object_names()))
    for i in range(n):
        d = per[f"uds-{i}"]
        setv(d.option, option(d.option, "user-defined", "user_defined_function", "udf"))
        setv(d.user_defined_function, fn)
    log(f"UDS diffusivity {fn} on uds-0..{n - 1}: ok")


def source_key(names, i):
    for k in (f"uds-{i}", f"user-scalar-{i}", f"User Scalar {i}", f"uds{i}", f"scalar-{i}"):
        if k in names:
            return k
    hits = [k for k in names if k.endswith(str(i)) and ("uds" in k.lower() or "scalar" in k.lower())]
    if len(hits) == 1:
        return hits[0]
    raise KeyError(f"no source entry for UDS {i}; entries: {names}")


def cell_sources(solver, zones, terms):
    """terms: {uds index: udf name}. 2024 R1: fluid[z].source_terms.sources is the on/off switch and
    source_terms.source_terms[<equation>] is a list of {option, value, ..., udf} (from --discover)."""
    s = settings(solver)
    for z in zones:
        st = s.setup.cell_zone_conditions.fluid[z].source_terms
        setv(st.sources, True)
        tab = st.source_terms
        names = list(tab.get_object_names())
        log(f"cell zone {z} source entries:", names)
        for i, f in terms.items():
            k = source_key(names, i)
            log(f"  {k} before:", tab[k].get_state())
            first_ok(f"source {k} = {f} in {z}",
                     *[lambda k=k, f=f, o=o: setv(tab[k], [{"option": o, "udf": f}])
                       for o in ("udf", "user-defined", "UDF")])


def uds_values(solver, kind, name, values):
    """Specified UDS values (phi = c / rho) on a boundary. 2024 R1 (from --discover): keys 'User Scalar i';
    uds_bc[key] is 'Specified Value' / 'Specified Flux'; uds[key] has option, value, profile_name, udf."""
    u = getattr(settings(solver).setup.boundary_conditions, kind)[name].uds
    for i, v in enumerate(values):
        key = f"User Scalar {i}"
        setv(u.uds_bc[key], option(u.uds_bc[key], "Specified Value"))
        val = u.uds[key]
        try:
            setv(val.option, option(val.option, "value", "constant"))
        except Exception as e:  # noqa: BLE001
            log(f"  {name} {key}: option left as is ({e})")
        setv(val.value, v)
    log(f"UDS values on {name}: ok")


def option_or(obj, *cands):
    try:
        allowed = list(obj.allowed_values())
    except Exception:  # noqa: BLE001
        return cands[0]
    for c in cands:
        if c in allowed:
            return c
    raise ValueError(f"none of {cands} in {allowed}")


def option(obj, *cands):
    allowed = list(obj.allowed_values())
    for c in cands:
        if c in allowed:
            return c
    raise ValueError(f"none of {cands} allowed; allowed: {allowed}")


def set_inlet_components(s, name, u_name, v_name):
    """Velocity components from named expressions (proven on Puma in 3d_nand_2)."""
    vi = s.setup.boundary_conditions.velocity_inlet[name]
    mom = vi.momentum if "momentum" in getattr(vi, "child_names", []) else vi
    meth = pick(mom, "velocity_specification_method", "velocity_spec")
    setv(meth, option(meth, "Components", "components"))
    vc = pick(mom, "velocity_components", "velocity_component", "velocity")

    def by_index(attr=None):
        for i, ex in enumerate((u_name, v_name)):
            setv(getattr(vc[i], attr) if attr else vc[i], ex)
    first_ok(f"{name} components = ({u_name}, {v_name})",
             lambda: setv(vc, [u_name, v_name]), lambda: by_index(), lambda: by_index("value"),
             lambda: setv(vc, {"x": u_name, "y": v_name}))


def iterate(solver, n, iters):
    rc = settings(solver).solution.run_calculation
    first_ok(f"advance {n} steps",
             lambda: rc.dual_time_iterate(time_step_count=n, max_iter_per_step=iters),
             lambda: (setv(rc.transient_controls.time_step_count, n),
                      setv(rc.transient_controls.max_iter_per_time_step, iters), rc.calculate()))


def on_demand(solver, fn):
    first_ok(f"run {fn}",
             lambda: tui(solver, f'/define/user-defined/execute-on-demand "{fn}::{UDF_LIB}"'),
             lambda: solver.tui.define.user_defined.execute_on_demand(f'"{fn}::{UDF_LIB}"'))


def patch_uds(solver, zones, i, value):
    s = settings(solver)
    ini = s.solution.initialization
    first_ok(f"patch uds-{i} = {value:g}",
             *[lambda var=var: ini.patch.calculate_patch(cell_zones=list(zones), variable=var, value=value)
               for var in (f"uds-{i}", f"uds-{i}-scalar", f"user-scalar-{i}", f"scalar-{i}")])
