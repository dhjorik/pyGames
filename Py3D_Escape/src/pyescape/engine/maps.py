"""
Map creation: hexagon geometry, maze generation, and wall building.

Besides the solid wall segments, build_walls tags every face with the light
of the room it belongs to (centre position + a palette colour index that
changes room by room). The 'shaded' theme uses that to light each room.
"""

import math
import random
from collections import defaultdict

from .constants import R, HW, LEFT, FRONT_LEFT, FRONT_RIGHT, RIGHT
from .configurations import CONNECTOR_STEPS


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


# ---------------------------------------------------------------------------
# Maze generation -> WORLD_MAP of (color, wall_byte) cells
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


# ---------------------------------------------------------------------------
# Wall-segment construction
#
# Every emitted face is a 7-tuple:
#     (p1, p2, color_idx, shade, light_x, light_y, light_color_idx)
# ---------------------------------------------------------------------------
def _emit_wall(p1, p2, color, shade, light, thickness, out):
    """Emit one edge as a thin segment or a 4-sided slab of given width."""
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
    out.append((c1, c2, color, shade, lx, ly, lc))   # long face (+normal)
    out.append((c3, c4, color, shade, lx, ly, lc))   # long face (-normal)
    out.append((c2, c3, color, cap, lx, ly, lc))     # end cap
    out.append((c4, c1, color, cap, lx, ly, lc))     # end cap


def _emit_connector(vx, vy, d1, d2, radius, color, shade, light, out,
                    steps=CONNECTOR_STEPS):
    """Round the corner where two walls meet at vertex (vx, vy)."""
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
    a1 = math.atan2(n1y, n1x)
    a2 = math.atan2(n2y, n2x)
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
    """Turn a WORLD_MAP into flat arrays of solid wall segments for the engine."""
    import numpy as np

    height = len(world)
    width = len(world[0])

    def in_bounds(r, c):
        return 0 <= r < height and 0 <= c < width

    def bit(r, c, mask):
        return in_bounds(r, c) and (world[r][c][1] & mask)

    shade_of = {
        "left": 1.0, "right": 1.0,
        "front_left": 0.72, "front_right": 0.72,
        "back_left": 0.88, "back_right": 0.88,
    }

    # Unique closed edges, each remembering the light of its owning room.
    seen = {}
    for r in range(height):
        for c in range(width):
            color, byte = world[r][c]
            light = (*hex_center(r, c), 1 + ((r * width + c) % 7))
            open_state = {
                "left":        bool(byte & LEFT),
                "right":       bool(byte & RIGHT),
                "front_left":  bool(byte & FRONT_LEFT),
                "front_right": bool(byte & FRONT_RIGHT),
                "back_left":   bool(bit(*back_left_neighbor(r, c), FRONT_RIGHT)),
                "back_right":  bool(bit(*back_right_neighbor(r, c), FRONT_LEFT)),
            }
            for name, p1, p2 in hex_edges(r, c):
                if open_state[name]:
                    continue
                key = frozenset((
                    (round(p1[0], 3), round(p1[1], 3)),
                    (round(p2[0], 3), round(p2[1], 3)),
                ))
                if key not in seen:
                    seen[key] = (p1, p2, color, shade_of[name], light)

    # Expand edges into faces, recording which walls meet at each vertex.
    faces = []
    incident = defaultdict(list)
    for (p1, p2, color, shade, light) in seen.values():
        _emit_wall(p1, p2, color, shade, light, thickness, faces)
        if thickness > 0.0:
            dx, dy = p2[0] - p1[0], p2[1] - p1[1]
            length = math.hypot(dx, dy) or 1.0
            ux, uy = dx / length, dy / length
            v1 = (round(p1[0], 3), round(p1[1], 3))
            v2 = (round(p2[0], 3), round(p2[1], 3))
            incident[v1].append((ux, uy, color, shade, light))
            incident[v2].append((-ux, -uy, color, shade, light))

    # Curved connector only where exactly two adjacent walls meet.
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