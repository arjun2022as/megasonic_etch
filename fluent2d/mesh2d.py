"""2D Fluent ASCII mesh: one slit of the 100:1 structure after dry etch, plus liquid above it.

     y = H  +----------------------------- top (velocity inlet) ---------------------------+
            |                                bulk liquid                                     |
     inlet  |                                                                                | outlet
     y = 0  +---- wafer-top (oxide) ----+  mouth  +---- wafer-top (oxide) -----------------+
                                        | slit    |
                         pocket <-R->   |  W      |   <-R-> pocket     (poly-Si layers, recessed by R)
                                        |         |                    (oxide layers: slit wall)
     y = -L                             +--floor--+
          x = X0                       x=0       x=W                                     x = X1

Layers below y = 0 alternate SiO2 / poly-Si (50 nm each, oxide first). Wall zones:
  poly       poly-Si etch front: slit wall in poly layers (R = 0) or the end of each pocket (R > 0)
  oxide      slit wall in oxide layers, pocket roofs/floors, slit floor
  wafer-top  top surface of the stack either side of the slit
  bubble     optional H2 gas plug filling the slit width from depth bubble_top to bubble_top + bubble_len
             (cells removed; its menisci pass H2 only, see etch.c). Flat walls: the poly-Si beside it is dry.
             Recessed walls (comb): the 50 nm pockets beside the plug stay full of liquid in reality, sealed from
             the mouth. They are LEFT OUT of the mesh: Fluent 24.1 mishandled these closed liquid islands (2026-11-02:
             exact stoichiometry but OH- used 3x-70x slower than their own etch rate), and they are not steady anyway.
             They are handled exactly by etchsim.plug.sealed_pocket (stored-etchant formula) in the 1D cycle model.
Cell zones: bulk (y > 0), slit, pocket. Fluent 2D face convention: c0 on the LEFT of n0 -> n1.
"""
import argparse
import json
import math
import sys

BC = {"interior": 2, "wall": 3, "pressure-outlet": 5, "velocity-inlet": 10}
CELL_ZONES = [(2, "bulk"), (3, "slit"), (4, "pocket")]
FACE_ZONES = [(5, "interior", "interior"), (6, "inlet", "velocity-inlet"), (7, "outlet", "pressure-outlet"),
              (8, "top", "velocity-inlet"), (9, "wafer-top", "wall"), (10, "oxide", "wall"), (11, "poly", "wall"),
              (12, "bubble", "wall"), (13, "bubble-pocket", "wall")]
POLY_ID, OXIDE_ID, BUBBLE_ID, BUBBLE_POCKET_ID = 11, 10, 12, 13   # pocket mouths facing a plug get their own zone:
# Fluent splits a wall zone that borders two cell zones (slit, pocket) and renumbers the second part


def in_bubble(y0, y1, bubble_top, bubble_len, tol=1e-12):
    """True if the band y0..y1 (y < 0 below the mouth) lies inside the gas plug."""
    return bubble_len > 0 and y0 >= -(bubble_top + bubble_len) - tol and y1 <= -bubble_top + tol


def wet_poly_layers(L, layer, bubble_top=0.0, bubble_len=0.0, recess=0.0):
    """Number of poly-Si layers (odd k, k = 0 at the top) in the mesh liquid: not beside the gas plug (the sealed
    pockets beside it are left out of the mesh even with recessed walls; recess kept for the call signature)."""
    return sum(1 for k in range(round(L / layer)) if k % 2 == 1
               and not in_bubble(-(k + 1) * layer, -k * layer, bubble_top, bubble_len))


def sealed_poly_layers(L, layer, bubble_top=0.0, bubble_len=0.0):
    """Layer indices k beside the plug (recessed walls: liquid pockets cut off from the mouth)."""
    return [k for k in range(round(L / layer)) if k % 2 == 1
            and in_bubble(-(k + 1) * layer, -k * layer, bubble_top, bubble_len)]


def graded(L, h0, ratio, hmax):
    sizes, tot = [], 0.0
    while tot < L * (1 - 1e-12):
        s = h0 if not sizes else min(hmax, sizes[-1] * ratio)
        sizes.append(s)
        tot += s
    over = tot - L
    sizes[-1] -= over
    if sizes[-1] < 0.3 * h0 and len(sizes) > 1:          # merge a sliver into its neighbour
        sizes[-2] += sizes.pop()
    return sizes


def segment(a, b, h):
    n = max(1, math.ceil((b - a) / h - 1e-9))
    return [a + (b - a) * i / n for i in range(n)]


def build(W, L, layer, R, pitch, H, dx, dy, dy_top0, ratio, bubble_top=0.0, bubble_len=0.0):
    X0, X1 = -(pitch - W) / 2, W + (pitch - W) / 2
    if R > -X0 - dx:
        raise SystemExit(f"recess {R} does not fit inside half the pitch")
    if bubble_len > 0:
        for v in (bubble_top, bubble_len):
            if abs(v / layer - round(v / layer)) > 1e-6:
                raise SystemExit("bubble top and length must be whole layers (multiples of the layer thickness)")
        if bubble_top < layer or bubble_top + bubble_len > L * (1 + 1e-12):
            raise SystemExit("bubble must lie inside the slit, below the first layer")
    breaks = sorted({X0, -R, 0.0, W, W + R, X1})
    xs = []
    for a, b in zip(breaks, breaks[1:]):
        xs += segment(a, b, dx)
    xs.append(X1)
    n_layers = round(L / layer)
    per = max(1, round(layer / dy))
    ys_slit = [-L + layer * (k // per) + layer * (k % per) / per for k in range(n_layers * per)]
    ys_top = [0.0]
    for s in graded(H, dy_top0, ratio, 20 * dy_top0):
        ys_top.append(ys_top[-1] + s)
    ys_top[-1] = H
    ys = ys_slit + ys_top
    j0 = len(ys_slit)                                       # row index of y = 0

    def poly_layer(yc):                                     # layer k = 0 at the top (oxide)
        return int(math.floor(-yc / layer)) % 2 == 1

    def xi(x):
        return min(range(len(xs)), key=lambda i: abs(xs[i] - x))
    i_r0, i_0, i_w, i_r1 = xi(-R), xi(0.0), xi(W), xi(W + R)
    cells = []
    for j in range(len(ys) - 1):
        yc = 0.5 * (ys[j] + ys[j + 1])
        for i in range(len(xs) - 1):
            if j >= j0:
                cells.append((i, j, 2))
            elif i_0 <= i < i_w:
                if not in_bubble(ys[j], ys[j + 1], bubble_top, bubble_len):
                    cells.append((i, j, 3))
            elif (R > 0 and poly_layer(yc) and (i_r0 <= i < i_0 or i_w <= i < i_r1)
                  and not in_bubble(ys[j], ys[j + 1], bubble_top, bubble_len)):   # sealed pockets left out
                cells.append((i, j, 4))
    cells.sort(key=lambda c: (c[2], c[1], c[0]))            # zone by zone (Fluent needs contiguous ids)

    used = set()
    for i, j, _ in cells:
        used |= {(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)}
    node_id, nodes = {}, []
    for ij in sorted(used, key=lambda t: (t[1], t[0])):
        node_id[ij] = len(nodes) + 1
        nodes.append((xs[ij[0]], ys[ij[1]]))
    faces = {}
    for c, (i, j, _) in enumerate(cells, start=1):
        corners = [(i, j), (i + 1, j), (i + 1, j + 1), (i, j + 1)]
        for k in range(4):
            p, q = node_id[corners[k]], node_id[corners[(k + 1) % 4]]
            key = (min(p, q), max(p, q))
            if key in faces:
                faces[key][3] = c
            else:
                faces[key] = [p, q, c, 0]
    tol = 1e-3 * min(dx, dy)
    zones = {zid: [] for zid, _, _ in FACE_ZONES}
    for f in faces.values():
        p, q, c0, c1 = f
        if c1:
            zones[5].append(f)
            continue
        (xa, ya), (xb, yb) = nodes[p - 1], nodes[q - 1]
        xm, ym = 0.5 * (xa + xb), 0.5 * (ya + yb)
        if abs(xm - X0) < tol and ym > 0:
            zones[6].append(f)
        elif abs(xm - X1) < tol and ym > 0:
            zones[7].append(f)
        elif abs(ym - H) < tol:
            zones[8].append(f)
        elif abs(ym) < tol:
            zones[9].append(f)
        elif bubble_len > 0 and abs(ya - yb) < tol and 0 < xm < W and (abs(ym + bubble_top) < tol
                                                                       or abs(ym + bubble_top + bubble_len) < tol):
            zones[BUBBLE_ID].append(f)
        elif (bubble_len > 0 and R > 0 and abs(xa - xb) < tol and (abs(xm) < tol or abs(xm - W) < tol)
              and -(bubble_top + bubble_len) < ym < -bubble_top):   # pocket mouth facing the plug
            zones[BUBBLE_POCKET_ID].append(f)
        elif abs(xa - xb) < tol and poly_layer(ym):          # vertical wall in a poly-Si layer
            zones[POLY_ID].append(f)
        else:
            zones[OXIDE_ID].append(f)
    return nodes, cells, xs, ys, zones, dict(X0=X0, X1=X1)


def check(nodes, cells, xs, ys, zones, W, L, layer, R, H, X0, X1, bubble_top=0.0, bubble_len=0.0):
    def centroid(c):
        i, j, _ = cells[c - 1]
        return 0.5 * (xs[i] + xs[i + 1]), 0.5 * (ys[j] + ys[j + 1])
    refs = [0] * (len(cells) + 1)
    for fl in zones.values():
        for p, q, c0, c1 in fl:
            (px, py), (qx, qy) = nodes[p - 1], nodes[q - 1]
            for c, sgn in ((c0, 1), (c1, -1)):
                if c:
                    cx, cy = centroid(c)
                    if sgn * ((qx - px) * (cy - py) - (qy - py) * (cx - px)) <= 0:
                        raise RuntimeError(f"bad orientation face {p}-{q} cell {c}")
                    refs[c] += 1
    if any(r != 4 for r in refs[1:]):
        raise RuntimeError("a cell does not have 4 faces")

    def length(zid):
        return sum(math.dist(nodes[p - 1], nodes[q - 1]) for p, q, _, _ in zones[zid])
    n_poly = round(L / layer) // 2
    n_wet = wet_poly_layers(L, layer, bubble_top, bubble_len, R)
    want = {6: H, 7: H, 8: X1 - X0, 9: (X1 - X0) - W, POLY_ID: 2 * n_wet * layer}
    if bubble_len > 0:
        want[BUBBLE_ID] = W * (1 if bubble_top + bubble_len >= L * (1 - 1e-12) else 2)
        if R > 0:                                                    # sealed pockets left out: no pocket mouths
            want[BUBBLE_POCKET_ID] = 0.0
    for zid, v in want.items():
        if abs(length(zid) - v) > 1e-6 * v:
            raise RuntimeError(f"zone {zid} length {length(zid)} != {v}")
    area = sum((xs[i + 1] - xs[i]) * (ys[j + 1] - ys[j]) for i, j, _ in cells)
    n_open = n_poly - (len(sealed_poly_layers(L, layer, bubble_top, bubble_len)) if bubble_len > 0 else 0)
    expect = (X1 - X0) * H + W * (L - bubble_len) + 2 * R * layer * n_open
    if abs(area - expect) > 1e-6 * expect:
        raise RuntimeError(f"area {area} != {expect}")


def write_msh(path, nodes, cells, zones, title):
    nn, nc = len(nodes), len(cells)
    order = [z for z in FACE_ZONES if zones[z[0]]]
    nf = sum(len(zones[z[0]]) for z in order)
    with open(path, "w", newline="\n") as f:
        f.write(f'(0 "{title}")\n(2 2)\n(10 (0 1 {nn:x} 0 2))\n(12 (0 1 {nc:x} 0))\n(13 (0 1 {nf:x} 0))\n')
        f.write(f"(10 (1 1 {nn:x} 1 2)(\n")
        f.writelines(f"{x:.15e} {y:.15e}\n" for x, y in nodes)
        f.write("))\n")
        first, czones = 1, []
        for zid, name in CELL_ZONES:
            n = sum(1 for c in cells if c[2] == zid)
            if n:
                f.write(f"(12 ({zid:x} {first:x} {first + n - 1:x} 1 3))\n")
                czones.append((zid, name))
                first += n
        first = 1
        for zid, name, zt in order:
            fl = zones[zid]
            f.write(f"(13 ({zid:x} {first:x} {first + len(fl) - 1:x} {BC[zt]:x} 2)(\n")
            f.writelines(f"{p:x} {q:x} {c0:x} {c1:x}\n" for p, q, c0, c1 in fl)
            f.write("))\n")
            first += len(fl)
        for zid, name in czones:
            f.write(f"(45 ({zid} fluid {name})())\n")
        for zid, name, zt in order:
            f.write(f"(45 ({zid} {zt} {name})())\n")
    return [n for _, n in czones]


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--W", type=float, default=100e-9)
    ap.add_argument("--L", type=float, default=10e-6)
    ap.add_argument("--layer", type=float, default=50e-9)
    ap.add_argument("--recess", type=float, default=0.0, help="lateral recess of the poly-Si layers [m]")
    ap.add_argument("--pitch", type=float, default=1e-6)
    ap.add_argument("--H", type=float, default=2e-6, help="liquid height above the wafer in the model [m]")
    ap.add_argument("--dx", type=float, default=5e-9)
    ap.add_argument("--dy", type=float, default=10e-9, help="row height in the stack (5 rows per 50 nm layer)")
    ap.add_argument("--dy-top", type=float, default=5e-9, help="first row above the wafer")
    ap.add_argument("--ratio", type=float, default=1.1)
    ap.add_argument("--bubble-top", type=float, default=0.0, help="depth of the top of the H2 plug below the mouth [m]")
    ap.add_argument("--bubble-len", type=float, default=0.0, help="length of the H2 plug along the slit [m], 0 = none")
    ap.add_argument("-o", "--out", required=True)
    a = ap.parse_args(argv)
    nodes, cells, xs, ys, zones, ext = build(a.W, a.L, a.layer, a.recess, a.pitch, a.H, a.dx, a.dy, a.dy_top,
                                             a.ratio, a.bubble_top, a.bubble_len)
    check(nodes, cells, xs, ys, zones, a.W, a.L, a.layer, a.recess, a.H, ext["X0"], ext["X1"], a.bubble_top,
          a.bubble_len)
    czones = write_msh(a.out, nodes, cells, zones, f"slit W={a.W:g} L={a.L:g} recess={a.recess:g} "
                                                   f"bubble={a.bubble_top:g}+{a.bubble_len:g}")
    info = dict(n_cells=len(cells), n_nodes=len(nodes), cell_zones=czones, poly_faces=len(zones[POLY_ID]),
                X0=ext["X0"], X1=ext["X1"], H=a.H, W=a.W, L=a.L, recess=a.recess, dx=a.dx, dy=a.dy,
                bubble_top=a.bubble_top, bubble_len=a.bubble_len, bubble_faces=len(zones[BUBBLE_ID]) + len(zones[BUBBLE_POCKET_ID]))
    print(json.dumps(info))
    return info


if __name__ == "__main__":
    sys.exit(0 if main() else 1)
