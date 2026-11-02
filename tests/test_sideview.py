"""Independent checks of etchsim/sideview.py (finite bubbles, side view) and of the comb + plug mesh."""
import sys
from pathlib import Path

import numpy as np
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from etchsim import plug as PL  # noqa: E402
from etchsim import props as P  # noqa: E402
from etchsim import sideview as SV  # noqa: E402
from etchsim.slit1d import Slit  # noqa: E402
from fluent2d import mesh2d  # noqa: E402

SURF = dict(OH=503.0931415, SIL=64.00191517, H2=44.42285922)


def uniform(sv):
    return {s: np.full((sv.nz, sv.ny), SURF[s]) for s in SV.SP}


def test_no_bubble_equals_1d():
    """One column, no gas, steady: same as the 1D slit with smeared walls (f = 1/2) and fixed mouth values."""
    sv = SV.SideView(SURF, spacing=0.4e-6, dz=100e-9, dy=200e-9)
    er, _, smax = sv.outputs(sv.step(uniform(sv), 1e3))
    s1 = Slit(n=100, km=None, poly=np.full(100, 0.5))
    s1.bulk = dict(SURF)
    r1 = s1.solve()
    assert er[-1, 0] / er[0, 0] == pytest.approx(r1["er"][-1] / r1["er"][0], rel=1e-5)
    assert smax == pytest.approx(r1["h2_supersat"], rel=1e-5)


def test_sheet_equals_1d_plug():
    """A bubble wider than the domain is a sheet: H2 intake = 1D plug model with the same top."""
    sv = SV.SideView(SURF, spacing=0.4e-6, dz=100e-9, dy=200e-9)
    sv.set_bubble(1e-6)
    _, h2, _ = sv.outputs(sv.step(uniform(sv), 1e3))
    fresh = {s: (np.array([0.0, P.L_SLIT]), np.array([SURF[s]] * 2)) for s in SV.SP}
    ps = PL.PlugSlit(9e-6, SURF, fresh, 1e3, True, dz=100e-9)
    ps.poly = np.full(ps.n, 0.5)
    assert h2 / sv.ymax == pytest.approx(ps.solve()["N"]["H2"][-1], rel=1e-6)


def test_lateral_symmetry_without_bubble():
    """No gas: nothing varies along the trench."""
    sv = SV.SideView(SURF, spacing=2e-6, dz=200e-9, dy=200e-9)
    c = sv.step(uniform(sv), 1e3)
    assert np.ptp(c["OH"], axis=1).max() < 1e-9 * P.C_BULK


def test_half_disc_area():
    assert SV.half_disc_area(2e-6, 10e-6, 50e-6) == pytest.approx(np.pi * 4e-12 / 4, rel=1e-4)   # quarter disc
    assert SV.half_disc_area(20e-6, 10e-6, 1e-6) == pytest.approx(10e-6 * 1e-6, rel=1e-9)       # capped: full
    assert SV.radius_for_area(SV.half_disc_area(3e-6, 10e-6, 5e-6), 10e-6, 5e-6) == pytest.approx(3e-6, rel=1e-6)


def test_comb_mesh_with_plug():
    """Recessed walls + floor plug: the sealed pockets beside the plug are left out (handled by
    plug.sealed_pocket), built-in checks (orientation, 4 faces per cell, lengths, area) pass."""
    W, L, layer, R = 100e-9, 10e-6, 50e-9, 300e-9
    nodes, cells, xs, ys, zones, ext = mesh2d.build(W, L, layer, R, 1e-6, 2e-6, 5e-9, 10e-9, 5e-9, 1.1, 9e-6, 1e-6)
    mesh2d.check(nodes, cells, xs, ys, zones, W, L, layer, R, 2e-6, ext["X0"], ext["X1"], 9e-6, 1e-6)
    sealed = mesh2d.sealed_poly_layers(L, layer, 9e-6, 1e-6)
    assert len(sealed) == 10
    assert len(zones[mesh2d.POLY_ID]) == 2 * 90 * 5            # 90 open poly layers, 2 sides, 5 rows each
    assert len(zones[mesh2d.BUBBLE_ID]) == 20                   # plug top (20 cells across W)
    assert len(zones[mesh2d.BUBBLE_POCKET_ID]) == 0             # no sealed pockets in the mesh
    assert sum(1 for c in cells if c[2] == 4) == 2 * 90 * 5 * 60   # pocket cells: open layers only, 60 across R
