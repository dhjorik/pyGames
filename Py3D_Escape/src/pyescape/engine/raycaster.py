"""
The raycasting engine: projects the wall segments of a level into a
first-person view, plus the player, collision resolution, and the minimap.

Rendering uses analytic ray/segment intersection (vectorised with numpy):
for every screen column a ray is tested against all wall segments at once
and the nearest hit becomes a vertical wall slice.
"""

import math

import numpy as np
import pygame

from .constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HALF_HEIGHT, NUM_RAYS, COL_W, FOV,
    WALL_SCALE, CEILING_COLOR, FLOOR_COLOR, PALETTE, COLLISION_RADIUS,
)


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle


# Per-column ray angle offsets and fish-eye correction factors (constant).
_cols = (np.arange(NUM_RAYS) + 0.5) / NUM_RAYS
_camera_x = 2.0 * _cols - 1.0
ANG_OFF = np.arctan(_camera_x * math.tan(FOV / 2))
COS_OFF = np.cos(ANG_OFF)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_world(screen, walls, player):
    """Cast one ray per column and draw the projected wall slices."""
    screen.fill(CEILING_COLOR, (0, 0, SCREEN_WIDTH, HALF_HEIGHT))
    screen.fill(FLOOR_COLOR, (0, HALF_HEIGHT, SCREEN_WIDTH, HALF_HEIGHT))

    Ax, Ay = walls["Ax"], walls["Ay"]
    Ex, Ey = walls["Ex"], walls["Ey"]
    if len(Ax) == 0:
        return

    px, py = player.x, player.y
    ray_ang = player.angle + ANG_OFF
    Dx = np.cos(ray_ang)
    Dy = np.sin(ray_ang)

    # Ray/segment intersection for every (ray, segment) pair:
    #   O + t*D = A + u*E  ->  t = (A-O)xE / DxE ,  u = (A-O)xD / DxE
    denom = np.outer(Dx, Ey) - np.outer(Dy, Ex)
    AOx = Ax - px
    AOy = Ay - py
    nt = AOx * Ey - AOy * Ex
    nu = np.outer(Dy, AOx) - np.outer(Dx, AOy)

    with np.errstate(divide="ignore", invalid="ignore"):
        t = nt[None, :] / denom
        u = nu / denom

    valid = (denom != 0) & (t > 1e-6) & (u >= -1e-9) & (u <= 1 + 1e-9)
    t = np.where(valid, t, np.inf)

    idx = np.argmin(t, axis=1)
    tmin = t[np.arange(NUM_RAYS), idx]
    perp = tmin * COS_OFF                     # fish-eye corrected depth

    finite = np.isfinite(perp)
    safe_perp = np.where(finite, perp, 1e9)

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
            continue                          # ray escaped through the exit
        h = lh_l[i]
        y0 = max(0, int(HALF_HEIGHT - h / 2))
        y1 = min(SCREEN_HEIGHT, int(HALF_HEIGHT + h / 2))
        pygame.draw.rect(screen, rgb_l[i], (i * COL_W, y0, COL_W, y1 - y0))


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------
def resolve_collisions(x, y, segs):
    """Push a point out of any wall segment it is within COLLISION_RADIUS of."""
    r2 = COLLISION_RADIUS * COLLISION_RADIUS
    for _ in range(2):                        # a couple of relaxation passes
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
                    push = COLLISION_RADIUS - d
                    x += dx / d * push
                    y += dy / d * push
                else:
                    x += COLLISION_RADIUS
    return x, y


# ---------------------------------------------------------------------------
# Minimap overlay
# ---------------------------------------------------------------------------
def draw_minimap(screen, walls, player):
    segs = walls["segs"]
    if not segs:
        return
    xs = [s[0] for s in segs] + [s[2] for s in segs]
    ys = [s[1] for s in segs] + [s[3] for s in segs]
    minx, maxx, miny, maxy = min(xs), max(xs), min(ys), max(ys)
    box, pad = 210, 12
    scale = min(box / (maxx - minx + 1e-6), box / (maxy - miny + 1e-6))
    ox = SCREEN_WIDTH - box - pad
    oy = pad

    def to_screen(wx, wy):
        return (ox + (wx - minx) * scale, oy + (wy - miny) * scale)

    overlay = pygame.Surface((box + 2 * pad, box + 2 * pad), pygame.SRCALPHA)
    overlay.fill((0, 0, 0, 120))
    screen.blit(overlay, (ox - pad, oy - pad))
    for (ax, ay, bx, by) in segs:
        pygame.draw.line(screen, (200, 200, 210),
                         to_screen(ax, ay), to_screen(bx, by), 1)
    pxs = to_screen(player.x, player.y)
    pygame.draw.circle(screen, (255, 80, 80), (int(pxs[0]), int(pxs[1])), 4)
    hx = player.x + math.cos(player.angle) * 0.9
    hy = player.y + math.sin(player.angle) * 0.9
    pygame.draw.line(screen, (255, 180, 60), pxs, to_screen(hx, hy), 2)