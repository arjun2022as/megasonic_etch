"""Checks of the 2D Fluent inputs that can run without Fluent."""
import csv
import math
import re
import sys
from pathlib import Path

import numpy as np
import pytest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from etchsim import acoustics as A  # noqa: E402
from etchsim import props as P  # noqa: E402
from fluent2d import mesh2d  # noqa: E402
from fluent2d.params import header, load_case, plan  # noqa: E402

UDF = (ROOT / "fluent2d" / "udf" / "etch.c").read_text()


@pytest.mark.parametrize("recess", [0.0, 300e-9])
def test_mesh_checks(tmp_path, recess):
    info = mesh2d.main(["--recess", str(recess), "-o", str(tmp_path / "m.msh")])   # runs check()
    assert info["poly_faces"] == 2 * 100 * 5                 # 100 poly layers x 2 sides x 5 rows of 10 nm
    assert ("pocket" in info["cell_zones"]) == (recess > 0)
    text = (tmp_path / "m.msh").read_text()
    assert f"(45 ({mesh2d.POLY_ID} wall poly)())" in text


def test_header_defines_every_constant_the_udf_uses():
    p = plan(load_case("M0_none"))
    h = header(p)
    used = {"RHO", "CB", "D_OH", "D_SIL", "D_TMA", "D_H2", "K_SI", "ORDER", "EPS", "OMEGA", "OSC_SCALE", "M_SI",
            "RHO_SI", "POLY_LENGTH", "W_SLIT", "DX_CELL", "MIGRATION", "POLY_ID"}
    for name in used:
        assert re.search(rf"\b{name}\b", UDF), name
        assert f"#define {name} " in h, name


def test_case_table():
    rows = list(csv.DictReader(open(ROOT / "cases.csv")))
    assert len({r["case"] for r in rows}) == len(rows)
    for r in rows:
        assert re.fullmatch(r"\d\d:\d\d:\d\d", r["walltime"])


def test_megasonic_boundary_flow():
    p = plan(load_case("A_f1_I2_t45"))
    o = A.slit_oscillation(2.0, 45.0, 1e6, P.W_SLIT)
    assert p["oscillating"] and p["u_t"] == pytest.approx(o["u_t"])
    expr = re.sub(r"\[[^\]]*\]", "", p["u_expr"])
    for y, t in ((0.0, 3e-7), (0.2e-6, 1.1e-6), (2e-6, 0.4e-6)):
        val = eval(expr, {"__builtins__": {}}, {"y": y, "t": t, "amp": 1.0, "cos": math.cos, "exp": math.exp})
        d, w = p["delta"], p["omega"]
        exact = p["G"] * y + p["u_t"] * (math.cos(w * t) - math.exp(-y / d) * math.cos(w * t - y / d))
        assert val == pytest.approx(exact, rel=1e-9, abs=1e-12)
    assert eval(expr, {"__builtins__": {}}, {"y": 0.0, "t": 0.0, "amp": 1.0, "cos": math.cos, "exp": math.exp}) == 0.0
    q = plan(load_case("A_f1_I2_t90"))
    assert not q["oscillating"]                  # MegPie (normal incidence): no tangential flow


def udf_migration_flux(i, c0, c1, dr):
    """Python transcription of the electromigration part of uds_flux (per unit face area, A = 1 along dr)."""
    zi, Di = {0: (-1.0, P.D["OH"]), 1: (-2.0, P.D["SIL"])}[i]
    geo = 1.0 / dr
    d_oh, d_si = (c1[0] - c0[0]) * geo, (c1[1] - c0[1]) * geo
    s = -P.D["OH"] * d_oh - 2 * P.D["SIL"] * d_si + P.D["TMA"] * (d_oh + 2 * d_si)
    co, cs = 0.5 * (c0[0] + c1[0]), 0.5 * (c0[1] + c1[1])
    q = P.D["OH"] * co + 4 * P.D["SIL"] * cs + P.D["TMA"] * (co + 2 * cs)
    return zi * Di * s / q           # migration velocity; times the upwind c gives the flux


def test_udf_migration_matches_1d_model():
    """The C face formula and slit1d.fluxes must give the same migration velocity for the same two cells."""
    from etchsim.slit1d import Slit
    s = Slit(n=2)
    dz = s.dz
    c = {"OH": np.array([500.0, 480.0]), "SIL": np.array([10.0, 20.0]), "H2": np.zeros(2)}
    surf = {"OH": 510.0, "SIL": 5.0, "H2": 0.0}
    _, ratio = s.fluxes(c, surf)                                  # S/Q at faces 0 (mouth), 1 (between cells)
    for i, key in ((0, "OH"), (1, "SIL")):
        v_udf = udf_migration_flux(i, (500.0, 10.0), (480.0, 20.0), dz)
        v_1d = P.Z[key] * P.D[key] * ratio[1]
        assert v_udf == pytest.approx(v_1d, rel=1e-12)


def test_source_signs():
    m = re.search(r"DEFINE_SOURCE\(src_oh.*?src\(c, t, (-?[\d.]+)", UDF)
    assert float(m.group(1)) == -2.0
    assert "src(c, t, 1.0" in UDF and "src(c, t, 2.0" in UDF
