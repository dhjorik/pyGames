"""
Map creation: hexagon geometry, maze generation, per-hexagon floor heights,
2D wall segments (for collision / minimap) and a 3D mesh (for rendering).

Floor mesh: each hexagon is split into six triangles (center + the two
endpoints of each edge). The center vertex is at the hexagon's height; each
edge's two vertices sit at the interpolated height of the two hexagons that
share the edge (so the floor connects continuously across edges). Walls rise
from that interpolated edge height up by a wall height.
"""

import math
import random
from collections import defaultdict

import numpy as np

from .constants import R, HW, LEFT, FRONT_LEFT, FRONT_RIGHT, RIGHT
from .configurations import CONNECTOR_STEPS, HEIGHT_RANGE


# ---------------------------------------------------------------------------
# Hexagon geometry ("odd rows shifted right" layout)
# ---------------------------------------------------------------------------
def hex_center(r, c):
    cx = HW + 2.0 * HW * c + (HW if (r % 2) else 0.0)
    cy = R + 1.5 * R * r
    return cx, cy


def hex_edges(r, c):
    """Return the 6 edges of a hexagon as (name, (x1, y1), (x2, y2))."""
    cx, cy = hex_center(r, c)
    T  = (cx,      cy - R)
    UR = (cx + HW, cy - R / 2)
    LR = (cx + HW, cy + R / 2)
    B  = (cx,      cy + R)
    LL = (cx - HW, cy + R / 2)
    UL = (cx - HW, cy - R / 2)
    return [
        ("left",        UL, LL),
        ("right",       UR, LR),
        ("front_left",  LL, B),
        ("front_right", B,  LR),
        ("back_left",   UL, T),
        ("back_right",  T,  UR),
    ]


def front_left_neighbor(r, c):
    return (r + 1, c - 1) if r % 2 == 0 else (r + 1, c)


def front_right_neighbor(r, c):
    return (r + 1, c) if r % 2 == 0 else (r + 1, c + 1)


def back_left_neighbor(r, c):
    return (r - 1, c - 1) if r % 2 == 0 else (r - 1, c)


def back_right_neighbor(r, c):
    return (r - 1, c) if r % 2 == 0 else (r - 1, c + 1)


def edge_neighbor(r, c, name):
    """The hexagon across a given named edge."""
    return {
        "left": (r, c - 1), "right": (r, c + 1),
        "front_left": front_left_neighbor(r, c),
        "front_right": front_right_neighbor(r, c),
        "back_left": back_left_neighbor(r, c),
        "back_right": back_right_neighbor(r, c),
    }[name]


# ---------------------------------------------------------------------------
# Maze + heights (both seeded)
# ---------------------------------------------------------------------------
def generate_maze(height, width, seed=None):
    """Build a perfect (fully connected) hex maze with a single exit."""
    rng = random.Random(seed)
    walls = [[0] * width for _ in range(height)]
    color = [[1 + int(6 * r / max(1, height - 1)) for _ in range(width)]
             for r in range(height)]
    visited = [[False] * width for _ in range(height)]

    def in_bounds(r, c):
        return 0 <= r < height and 0 <= c < width

    def neighbors(r, c):
        cand = [
            ("L", r, c - 1), ("R", r, c + 1),
            ("FL", *front_left_neighbor(r, c)),
            ("FR", *front_right_neighbor(r, c)),
            ("BL", *back_left_neighbor(r, c)),
            ("BR", *back_right_neighbor(r, c)),
        ]
        return [(t, rr, cc) for (t, rr, cc) in cand if in_bounds(rr, cc)]

    def carve(r, c, tag, rr, cc):
        if tag == "L":
            walls[r][c] |= LEFT;  walls[rr][cc] |= RIGHT
        elif tag == "R":
            walls[r][c] |= RIGHT; walls[rr][cc] |= LEFT
        elif tag == "FL":
            walls[r][c] |= FRONT_LEFT
        elif tag == "FR":
            walls[r][c] |= FRONT_RIGHT
        elif tag == "BL":
            walls[rr][cc] |= FRONT_RIGHT
        elif tag == "BR":
            walls[rr][cc] |= FRONT_LEFT

    start = (0, width // 2)
    visited[start[0]][start[1]] = True
    stack = [start]
    while stack:
        r, c = stack[-1]
        unvisited = [(t, rr, cc) for (t, rr, cc) in neighbors(r, c)
                     if not visited[rr][cc]]
        if not unvisited:
            stack.pop()
            continue
        tag, rr, cc = rng.choice(unvisited)
        carve(r, c, tag, rr, cc)
        visited[rr][cc] = True
        stack.append((rr, cc))

    er = height - 1
    ec = rng.randrange(width)
    walls[er][ec] |= (FRONT_LEFT if rng.random() < 0.5 else FRONT_RIGHT)

    world = [[(color[r][c], walls[r][c]) for c in range(width)]
             for r in range(height)]
    return world, start


def generate_heights(height, width, seed=None):
    """A per-hexagon floor elevation, reproducible from the level seed."""
    rng = random.Random((seed or 0) + 7919)
    return [[rng.uniform(0.0, HEIGHT_RANGE) for _ in range(width)]
            for _ in range(height)]


# ---------------------------------------------------------------------------
# Shared helper: open/closed state of a cell's six walls
# ---------------------------------------------------------------------------
def _bit(world, H, W, r, c, mask):
    return (0 <= r < H and 0 <= c < W) and (world[r][c][1] & mask)


def _open_state(world, H, W, r, c):
    byte = world[r][c][1]
    return {
        "left":        bool(byte & LEFT),
        "right":       bool(byte & RIGHT),
        "front_left":  bool(byte & FRONT_LEFT),
        "front_right": bool(byte & FRONT_RIGHT),
        "back_left":   bool(_bit(world, H, W, *back_left_neighbor(r, c), FRONT_RIGHT)),
        "back_right":  bool(_bit(world, H, W, *back_right_neighbor(r, c), FRONT_LEFT)),
    }


# ---------------------------------------------------------------------------
# 2D wall segments (collision + minimap). Faces carry their room light.
# ---------------------------------------------------------------------------
def _emit_wall(p1, p2, color, shade, light, thickness, out):
    lx, ly, lc = light
    if thickness <= 0.0:
        out.append((p1, p2, color, shade, lx, ly, lc))
        return
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0.0:
        out.append((p1, p2, color, shade, lx, ly, lc))
        return
    nx, ny = -dy / length, dx / length
    h = thickness / 2.0
    c1 = (x1 + nx * h, y1 + ny * h)
    c2 = (x2 + nx * h, y2 + ny * h)
    c3 = (x2 - nx * h, y2 - ny * h)
    c4 = (x1 - nx * h, y1 - ny * h)
    cap = shade * 0.75
    out.append((c1, c2, color, shade, lx, ly, lc))
    out.append((c3, c4, color, shade, lx, ly, lc))
    out.append((c2, c3, color, cap, lx, ly, lc))
    out.append((c4, c1, color, cap, lx, ly, lc))


def _emit_connector(vx, vy, d1, d2, radius, color, shade, light, out,
                    steps=CONNECTOR_STEPS):
    lx, ly, lc = light
    ox, oy = -(d1[0] + d2[0]), -(d1[1] + d2[1])
    ol = math.hypot(ox, oy)
    if ol < 1e-9:
        return
    ox, oy = ox / ol, oy / ol
    n1x, n1y = -d1[1], d1[0]
    if n1x * ox + n1y * oy < 0:
        n1x, n1y = -n1x, -n1y
    n2x, n2y = -d2[1], d2[0]
    if n2x * ox + n2y * oy < 0:
        n2x, n2y = -n2x, -n2y
    a1, a2 = math.atan2(n1y, n1x), math.atan2(n2y, n2x)
    da = a2 - a1
    while da <= -math.pi:
        da += 2 * math.pi
    while da > math.pi:
        da -= 2 * math.pi
    prev = None
    for i in range(steps + 1):
        a = a1 + da * (i / steps)
        pt = (vx + radius * math.cos(a), vy + radius * math.sin(a))
        if prev is not None:
            out.append((prev, pt, color, shade, lx, ly, lc))
        prev = pt


def build_walls(world, thickness=0.0):
    """Flat arrays of 2D wall segments used for collision and the minimap."""
    H = len(world)
    W = len(world[0])
    shade_of = {
        "left": 1.0, "right": 1.0,
        "front_left": 0.72, "front_right": 0.72,
        "back_left": 0.88, "back_right": 0.88,
    }

    seen = {}
    for r in range(H):
        for c in range(W):
            color = world[r][c][0]
            light = (*hex_center(r, c), 1 + ((r * W + c) % 7))
            op = _open_state(world, H, W, r, c)
            for name, p1, p2 in hex_edges(r, c):
                if op[name]:
                    continue
                key = frozenset(((round(p1[0], 3), round(p1[1], 3)),
                                 (round(p2[0], 3), round(p2[1], 3))))
                if key not in seen:
                    seen[key] = (p1, p2, color, shade_of[name], light)

    faces = []
    incident = defaultdict(list)
    for (p1, p2, color, shade, light) in seen.values():
        _emit_wall(p1, p2, color, shade, light, thickness, faces)
        if thickness > 0.0:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            length = math.hypot(dx, dy) or 1.0
            ux, uy = dx / length, dy / length
            incident[(round(p1[0], 3), round(p1[1], 3))].append(
                (ux, uy, color, shade, light))
            incident[(round(p2[0], 3), round(p2[1], 3))].append(
                (-ux, -uy, color, shade, light))

    if thickness > 0.0:
        h = thickness / 2.0
        for (vx, vy), items in incident.items():
            if len(items) != 2:
                continue
            (d1x, d1y, color, shade, light), (d2x, d2y, _, _, _) = items
            _emit_connector(vx, vy, (d1x, d1y), (d2x, d2y),
                            h, color, shade, light, faces)

    ax, ay, ex, ey, cidx, shd = [], [], [], [], [], []
    lcx, lcy, lci, segs = [], [], [], []
    for (p1, p2, color, shade, lx, ly, lc) in faces:
        ax.append(p1[0]); ay.append(p1[1])
        ex.append(p2[0] - p1[0]); ey.append(p2[1] - p1[1])
        cidx.append(color); shd.append(shade)
        lcx.append(lx); lcy.append(ly); lci.append(lc)
        segs.append((p1[0], p1[1], p2[0], p2[1]))

    return {
        "Ax": np.array(ax), "Ay": np.array(ay),
        "Ex": np.array(ex), "Ey": np.array(ey),
        "cidx": np.array(cidx, dtype=int), "shade": np.array(shd),
        "lcx": np.array(lcx), "lcy": np.array(lcy),
        "lci": np.array(lci, dtype=int),
        "segs": segs,
    }


# ---------------------------------------------------------------------------
# 3D mesh (floor triangles + wall boxes) for rendering
# ---------------------------------------------------------------------------
_LIGHT_DIR = (0.35, 0.25, 1.0)
_LN = math.sqrt(sum(k * k for k in _LIGHT_DIR))
_LIGHT = tuple(k / _LN for k in _LIGHT_DIR)


def build_mesh(world, heights, thickness, wall_height):
    """Return a 3D mesh: shared vertex array V plus a list of polygon dicts."""
    H = len(world)
    W = len(world[0])
    V = []
    polys = []

    def addv(x, y, z):
        V.append((x, y, z))
        return len(V) - 1

    def hget(r, c):
        return heights[r][c] if (0 <= r < H and 0 <= c < W) else None

    def shade(ia, ib, ic):
        ax, ay, az = V[ia]; bx, by, bz = V[ib]; cx, cy, cz = V[ic]
        ux, uy, uz = bx - ax, by - ay, bz - az
        vx, vy, vz = cx - ax, cy - ay, cz - az
        nx, ny, nz = uy * vz - uz * vy, uz * vx - ux * vz, ux * vy - uy * vx
        nn = math.sqrt(nx * nx + ny * ny + nz * nz) or 1.0
        d = abs((nx * _LIGHT[0] + ny * _LIGHT[1] + nz * _LIGHT[2]) / nn)
        return 0.35 + 0.65 * d

    centers, center_h = [], []

    # Floor triangles.
    for r in range(H):
        for c in range(W):
            hc = heights[r][c]
            cx, cy = hex_center(r, c)
            centers.append((cx, cy)); center_h.append(hc)
            color = world[r][c][0]
            lci = 1 + ((r * W + c) % 7)
            ci = addv(cx, cy, hc)
            for name, p1, p2 in hex_edges(r, c):
                hn = hget(*edge_neighbor(r, c, name))
                he = hc if hn is None else 0.5 * (hc + hn)
                i1 = addv(p1[0], p1[1], he)
                i2 = addv(p2[0], p2[1], he)
                polys.append({"idx": (ci, i1, i2), "kind": 0, "cidx": color,
                              "lci": lci, "cx": cx, "cy": cy,
                              "shade": shade(ci, i1, i2)})

    # Wall boxes (unique closed edges).
    seen = set()
    for r in range(H):
        for c in range(W):
            hc = heights[r][c]
            cx, cy = hex_center(r, c)
            color = world[r][c][0]
            lci = 1 + ((r * W + c) % 7)
            op = _open_state(world, H, W, r, c)
            for name, p1, p2 in hex_edges(r, c):
                if op[name]:
                    continue
                key = frozenset(((round(p1[0], 3), round(p1[1], 3)),
                                 (round(p2[0], 3), round(p2[1], 3))))
                if key in seen:
                    continue
                seen.add(key)
                hn = hget(*edge_neighbor(r, c, name))
                he = hc if hn is None else 0.5 * (hc + hn)
                _emit_box(addv, polys, shade, p1, p2, thickness,
                          he, he + wall_height, color, lci, cx, cy)

    return {
        "V": np.array(V, dtype=float) if V else np.zeros((0, 3)),
        "polys": polys,
        "centers": np.array(centers, dtype=float),
        "center_h": np.array(center_h, dtype=float),
    }


def _emit_box(addv, polys, shade, p1, p2, thickness, base, top, color, lci,
              cx, cy):
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy) or 1.0

    if thickness <= 0.0:
        a0 = addv(x1, y1, base); b0 = addv(x2, y2, base)
        b1 = addv(x2, y2, top);  a1 = addv(x1, y1, top)
        polys.append({"idx": (a0, b0, b1, a1), "kind": 1, "cidx": color,
                      "lci": lci, "cx": cx, "cy": cy, "shade": shade(a0, b0, b1)})
        return

    nx, ny = -dy / length, dx / length
    h = thickness / 2.0
    corners = [(x1 + nx * h, y1 + ny * h), (x2 + nx * h, y2 + ny * h),
               (x2 - nx * h, y2 - ny * h), (x1 - nx * h, y1 - ny * h)]
    lo = [addv(x, y, base) for (x, y) in corners]
    hi = [addv(x, y, top) for (x, y) in corners]
    for k in range(4):
        j = (k + 1) % 4
        q = (lo[k], lo[j], hi[j], hi[k])        # side face
        polys.append({"idx": q, "kind": 1, "cidx": color, "lci": lci,
                      "cx": cx, "cy": cy, "shade": shade(q[0], q[1], q[2])})
    top_q = (hi[0], hi[1], hi[2], hi[3])        # top cap
    polys.append({"idx": top_q, "kind": 2, "cidx": color, "lci": lci,
                  "cx": cx, "cy": cy, "shade": shade(hi[0], hi[1], hi[2])})


def floor_height_at(px, py, mesh):
    """Floor elevation of the hexagon nearest to (px, py)."""
    C = mesh["centers"]
    if len(C) == 0:
        return 0.0
    dx = C[:, 0] - px
    dy = C[:, 1] - py
    i = int(np.argmin(dx * dx + dy * dy))
    return float(mesh["center_h"][i])