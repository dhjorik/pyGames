"""
A Doom-style raycasting engine that renders a HEXAGONAL labyrinth.

--------------------------------------------------------------------------
MAP FORMAT
--------------------------------------------------------------------------
WORLD_MAP is a matrix (list of rows). Each cell is a 2-tuple:

        (color, wall_byte)

  * color     : 1..7  -> wall color (same palette as before)
                    1 green   2 blue   3 red    4 yellow
                    5 cyan    6 orange 7 white
  * wall_byte : the open/closed state of this hexagon's four *stored* walls.
                A bit set to 1 means the wall is OPEN (a passage); 0 means
                the wall is CLOSED (solid, drawn).

                bit 0 (value 1) : left        wall
                bit 1 (value 2) : front-left  wall
                bit 2 (value 4) : front-right wall
                bit 3 (value 8) : right       wall
                bits 4..7       : reserved for future use

The two remaining walls -- back-left and back-right -- are NOT stored.
They are shared with the linked hexagon in the previous row and are
DERIVED from that hexagon's front walls:

    back-left(r, c)  == front-right of its back-left  neighbour in row r-1
    back-right(r, c) == front-left  of its back-right neighbour in row r-1

Row 0 has no previous row, so its back walls are always CLOSED (this forms
the top boundary of the labyrinth). The labyrinth is fully enclosed except
for a single OPEN front wall somewhere on the last row: the exit.

--------------------------------------------------------------------------
CONTROLS
--------------------------------------------------------------------------
    UP    : move forward           DOWN : move backward
    LEFT  : turn left              RIGHT: turn right
    TAB   : toggle minimap         ESC  : quit

"""

import pygame
import numpy as np

import math
import random

from mp_game.engine.constants import *

# ---------------------------------------------------------------------------
# Hexagon coordinate helpers
#
# Layout: "odd rows shifted right".  Even rows sit at x-offset 0, odd rows at
# +HW.  Vertical row spacing is 1.5*R.  A cell (r, c) therefore has:
#   left/right  neighbours in the same row
#   front-left/front-right neighbours in row r+1  (toward the exit)
#   back-left/back-right   neighbours in row r-1  (toward row 0)
# ---------------------------------------------------------------------------
def hex_center(r, c):
    cx = HW + 2.0 * HW * c + (HW if (r % 2) else 0.0)
    cy = R + 1.5 * R * r
    return cx, cy


def hex_edges(r, c):
    """Return the 6 edges of a hexagon as (name, (x1,y1), (x2,y2))."""
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
# Maze generation  -> produces a WORLD_MAP in the (color, wall_byte) format
# ---------------------------------------------------------------------------
def generate_maze(height, width, seed=None):
    """Build a perfect (fully connected) hex maze with a single exit."""
    rng = random.Random(seed)
    walls = [[0] * width for _ in range(height)]                 # all closed
    color = [[1 + int(6 * r / max(1, height - 1)) for _ in range(width)]
             for r in range(height)]                            # rainbow by depth
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
            walls[r][c] |= FRONT_LEFT          # neighbour's back-right derives from this
        elif tag == "FR":
            walls[r][c] |= FRONT_RIGHT         # neighbour's back-left derives from this
        elif tag == "BL":
            walls[rr][cc] |= FRONT_RIGHT       # our back-left  == neighbour's front-right
        elif tag == "BR":
            walls[rr][cc] |= FRONT_LEFT        # our back-right == neighbour's front-left

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

    # Punch exactly one exit on the last row. A last-row front wall has no
    # hexagon beyond it, so opening it leads out of the labyrinth.
    er = height - 1
    ec = rng.randrange(width)
    walls[er][ec] |= (FRONT_LEFT if rng.random() < 0.5 else FRONT_RIGHT)

    world = [[(color[r][c], walls[r][c]) for c in range(width)]
             for r in range(height)]
    return world, start


# ---------------------------------------------------------------------------
# Turn a WORLD_MAP into a flat list of solid wall segments.
# Each closed edge becomes one segment; shared edges are de-duplicated.
# ---------------------------------------------------------------------------
def build_walls(world):
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

    seen = {}   # dedup key -> (segment, color_idx, shade)
    for r in range(height):
        for c in range(width):
            color, byte = world[r][c]
            # Open/closed state of all six walls of this hexagon.
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
                    continue  # passage, no wall
                key = frozenset((
                    (round(p1[0], 3), round(p1[1], 3)),
                    (round(p2[0], 3), round(p2[1], 3)),
                ))
                if key not in seen:
                    seen[key] = (p1, p2, color, shade_of[name])

    ax, ay, ex, ey, cidx, shd = [], [], [], [], [], []
    segs = []
    for (p1, p2, color, shade) in seen.values():
        ax.append(p1[0]); ay.append(p1[1])
        ex.append(p2[0] - p1[0]); ey.append(p2[1] - p1[1])
        cidx.append(color); shd.append(shade)
        segs.append((p1[0], p1[1], p2[0], p2[1]))

    walls = {
        "Ax": np.array(ax), "Ay": np.array(ay),
        "Ex": np.array(ex), "Ey": np.array(ey),
        "cidx": np.array(cidx, dtype=int), "shade": np.array(shd),
        "segs": segs,
    }
    return walls


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle          # +90deg (pi/2) faces the labyrinth (down)


# Precompute per-column ray angle offsets and fish-eye correction factors.
_cols = (np.arange(NUM_RAYS) + 0.5) / NUM_RAYS      # 0..1 across the screen
_camera_x = 2.0 * _cols - 1.0                       # -1..1
ANG_OFF = np.arctan(_camera_x * math.tan(FOV / 2))  # rectilinear projection
COS_OFF = np.cos(ANG_OFF)


def render_world(screen, walls, player):
    """Cast one ray per column and draw the projected wall slices."""
    # Ceiling and floor.
    screen.fill(CEILING_COLOR, (0, 0, SCREEN_WIDTH, HALF_HEIGHT))
    screen.fill(FLOOR_COLOR, (0, HALF_HEIGHT, SCREEN_WIDTH, HALF_HEIGHT))

    Ax, Ay = walls["Ax"], walls["Ay"]
    Ex, Ey = walls["Ex"], walls["Ey"]
    if len(Ax) == 0:
        return

    px, py = player.x, player.y
    ray_ang = player.angle + ANG_OFF                # (R,)
    Dx = np.cos(ray_ang)
    Dy = np.sin(ray_ang)

    # Ray/segment intersection for every (ray, segment) pair.
    #   O + t*D = A + u*E   ->   t = (A-O)xE / DxE ,  u = (A-O)xD / DxE
    denom = np.outer(Dx, Ey) - np.outer(Dy, Ex)     # (R, S)
    AOx = Ax - px
    AOy = Ay - py
    nt = AOx * Ey - AOy * Ex                         # (S,)
    nu = np.outer(Dy, AOx) - np.outer(Dx, AOy)       # (R, S)

    with np.errstate(divide="ignore", invalid="ignore"):
        t = nt[None, :] / denom
        u = nu / denom

    valid = (denom != 0) & (t > 1e-6) & (u >= -1e-9) & (u <= 1 + 1e-9)
    t = np.where(valid, t, np.inf)

    idx = np.argmin(t, axis=1)                       # nearest wall per ray
    tmin = t[np.arange(NUM_RAYS), idx]
    perp = tmin * COS_OFF                            # fish-eye corrected depth

    finite = np.isfinite(perp)
    safe_perp = np.where(finite, perp, 1e9)

    # Colour = palette * edge-shade * distance fog.
    fog = np.clip(3.0 / safe_perp, 0.20, 1.0)
    bright = walls["shade"][idx] * fog
    rgb = np.clip(PALETTE[walls["cidx"][idx]] * bright[:, None], 0, 255)

    line_h = np.zeros(NUM_RAYS)
    line_h[finite] = np.clip(WALL_SCALE * SCREEN_HEIGHT / perp[finite],
                             1, SCREEN_HEIGHT * 3)

    perp_l = perp.tolist()
    lh_l = line_h.tolist()
    rgb_l = rgb.astype(int).tolist()

    for i in range(NUM_RAYS):
        if not math.isfinite(perp_l[i]):
            continue                                 # ray escaped through the exit
        h = lh_l[i]
        y0 = int(HALF_HEIGHT - h / 2)
        y1 = int(HALF_HEIGHT + h / 2)
        y0c = max(0, y0)
        y1c = min(SCREEN_HEIGHT, y1)
        pygame.draw.rect(screen, rgb_l[i], (i * COL_W, y0c, COL_W, y1c - y0c))


# ---------------------------------------------------------------------------
# Collision: push the player out of any wall it is too close to.
# ---------------------------------------------------------------------------
def resolve_collisions(x, y, segs):
    r2 = COLLISION_RADIUS * COLLISION_RADIUS
    for _ in range(2):                               # a couple of relaxation passes
        for (ax, ay, bx, by) in segs:
            ex, ey = bx - ax, by - ay
            L2 = ex * ex + ey * ey
            if L2 == 0.0:
                continue
            tt = ((x - ax) * ex + (y - ay) * ey) / L2
            tt = 0.0 if tt < 0.0 else (1.0 if tt > 1.0 else tt)
            qx, qy = ax + tt * ex, ay + tt * ey
            dx, dy = x - qx, y - qy
            d2 = dx * dx + dy * dy
            if d2 < r2:
                d = math.sqrt(d2)
                if d > 1e-9:
                    push = (COLLISION_RADIUS - d)
                    x += dx / d * push
                    y += dy / d * push
                else:
                    x += COLLISION_RADIUS
    return x, y


# ---------------------------------------------------------------------------
# Minimap (top-down view of the hexagon walls + player)
# ---------------------------------------------------------------------------
def draw_minimap(screen, walls, player):
    segs = walls["segs"]
    if not segs:
        return
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    ys = [s[1] for s in segs] + [s[3] for s in segs]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    box = 230
    pad = 12
    scale = min(box / (maxx - minx + 1e-6), box / (maxy - miny + 1e-6))
    ox = SCREEN_WIDTH - box - pad
    oy = pad

    def to_screen(wx, wy):
        return (ox + (wx - minx) * scale, oy + (wy - miny) * scale)

    overlay = pygame.Surface((box + 2 * pad, box + 2 * pad), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (ox - pad, oy - pad))

    for (ax, ay, bx, by) in segs:
        pygame.draw.line(screen, (200, 200, 210), to_screen(ax, ay),
                         to_screen(bx, by), 1)

    pxs = to_screen(player.x, player.y)
    pygame.draw.circle(screen, (255, 80, 80), (int(pxs[0]), int(pxs[1])), 4)
    hx = player.x + math.cos(player.angle) * 0.9
    hy = player.y + math.sin(player.angle) * 0.9
    pygame.draw.line(screen, (255, 180, 60), pxs, to_screen(hx, hy), 2)
