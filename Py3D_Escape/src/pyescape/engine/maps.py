"""
Map creation: hexagon geometry, maze generation, and wall building.

A level is a matrix of (color, wall_byte) cells. Walls stored per cell are
left / front-left / front-right / right (bits 0..3); the back walls are
shared with the previous row and derived from that row's front walls.
Layout is "odd rows shifted right".
"""

import math
import random

import numpy as np

from .constants import R, HW, LEFT, FRONT_LEFT, FRONT_RIGHT, RIGHT


# ---------------------------------------------------------------------------
# Hexagon geometry
# ---------------------------------------------------------------------------
def hex_center(r, c):
    cx = HW + 2.0 * HW * c + (HW if (r % 2) else 0.0)
    cy = R + 1.5 * R * r
    return cx, cy


def hex_edges(r, c):
    """Return the 6 edges of a hexagon as (name, (x1, y1), (x2, y2))."""
    cx, cy = hex_center(r, c)
    T  = (cx,      cy - R)        # top point
    UR = (cx + HW, cy - R / 2)    # upper right
    LR = (cx + HW, cy + R / 2)    # lower right
    B  = (cx,      cy + R)        # bottom point
    LL = (cx - HW, cy + R / 2)    # lower left
    UL = (cx - HW, cy - R / 2)    # upper left
    return [
        ("left",        UL, LL),
        ("right",       UR, LR),
        ("front_left",  LL, B),   # front == toward the last row (downward)
        ("front_right", B,  LR),
        ("back_left",   UL, T),   # back  == toward row 0 (upward)
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
    walls = [[0] * width for _ in range(height)]                 # all closed
    color = [[1 + int(6 * r / max(1, height - 1)) for _ in range(width)]
             for r in range(height)]                            # depth gradient
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
        # Open the shared wall by setting the correct *stored* bit(s).
        if tag == "L":
            walls[r][c] |= LEFT;  walls[rr][cc] |= RIGHT
        elif tag == "R":
            walls[r][c] |= RIGHT; walls[rr][cc] |= LEFT
        elif tag == "FL":
            walls[r][c] |= FRONT_LEFT
        elif tag == "FR":
            walls[r][c] |= FRONT_RIGHT
        elif tag == "BL":
            walls[rr][cc] |= FRONT_RIGHT       # our back-left  == nbr front-right
        elif tag == "BR":
            walls[rr][cc] |= FRONT_LEFT        # our back-right == nbr front-left

    # Iterative randomized depth-first search (recursive backtracker).
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

    # Punch exactly one exit on the last row (a front wall with nothing beyond).
    er = height - 1
    ec = rng.randrange(width)
    walls[er][ec] |= (FRONT_LEFT if rng.random() < 0.5 else FRONT_RIGHT)

    world = [[(color[r][c], walls[r][c]) for c in range(width)]
             for r in range(height)]
    return world, start


# ---------------------------------------------------------------------------
# Build solid wall segments from a WORLD_MAP
# ---------------------------------------------------------------------------
def _emit_wall(p1, p2, color, shade, thickness, out):
    """Emit one edge as either a thin segment or a 4-sided slab of given width."""
    if thickness <= 0.0:
        out.append((p1, p2, color, shade))
        return
    x1, y1 = p1
    x2, y2 = p2
    dx, dy = x2 - x1, y2 - y1
    length = math.hypot(dx, dy)
    if length == 0.0:
        out.append((p1, p2, color, shade))
        return
    ux, uy = dx / length, dy / length       # unit vector along the wall
    nx, ny = -uy, ux                         # unit normal
    h = thickness / 2.0
    # Extend each end by h so neighbouring slabs overlap and close the corners.
    ax, ay = x1 - ux * h, y1 - uy * h
    bx, by = x2 + ux * h, y2 + uy * h
    c1 = (ax + nx * h, ay + ny * h)
    c2 = (bx + nx * h, by + ny * h)
    c3 = (bx - nx * h, by - ny * h)
    c4 = (ax - nx * h, ay - ny * h)
    cap = shade * 0.75                       # end caps slightly darker for depth
    out.append((c1, c2, color, shade))       # long face (+normal)
    out.append((c3, c4, color, shade))       # long face (-normal)
    out.append((c2, c3, color, cap))         # end cap
    out.append((c4, c1, color, cap))         # end cap


def build_walls(world, thickness=0.0):
    """Turn a WORLD_MAP into flat arrays of solid wall segments for the engine.

    With ``thickness > 0`` every wall becomes a thin slab (four faces) so the
    walls show real depth at corners and doorways; ``0`` keeps thin walls.
    """
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

    seen = {}   # dedup shared edges by their endpoints
    for r in range(height):
        for c in range(width):
            color, byte = world[r][c]
            open_state = {
                "left":        bool(byte & LEFT),
                "right":       bool(byte & RIGHT),
                "front_left":  bool(byte & FRONT_LEFT),
                "front_right": bool(byte & FRONT_RIGHT),
                # derived back walls (out-of-bounds neighbour => closed)
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
                    seen[key] = (p1, p2, color, shade_of[name])

    # Expand each unique closed edge into faces (thin segment or thick slab).
    faces = []
    for (p1, p2, color, shade) in seen.values():
        _emit_wall(p1, p2, color, shade, thickness, faces)

    ax, ay, ex, ey, cidx, shd, segs = [], [], [], [], [], [], []
    for (p1, p2, color, shade) in faces:
        ax.append(p1[0]); ay.append(p1[1])
        ex.append(p2[0] - p1[0]); ey.append(p2[1] - p1[1])
        cidx.append(color); shd.append(shade)
        segs.append((p1[0], p1[1], p2[0], p2[1]))

    return {
        "Ax": np.array(ax), "Ay": np.array(ay),
        "Ex": np.array(ex), "Ey": np.array(ey),
        "cidx": np.array(cidx, dtype=int), "shade": np.array(shd),
        "segs": segs,
    }