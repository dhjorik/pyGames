"""
The raycasting engine: casts the scene and draws it in one of three themes.

  flat        : walls coloured by their palette index, shaded by distance.
  shaded      : each room has a coloured point light at its centre (the colour
                changes room by room); walls are tinted and attenuated by it.
  tron_theme  : dark walls with glowing neon edges (Space Paranoids look).

The ray/segment intersection is shared; only colouring and drawing branch.
"""

import math

import numpy as np
import pygame

from .configurations import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HALF_HEIGHT, NUM_RAYS, FOV, WALL_SCALE, PALETTE,
)
from .constants import COLLISION_RADIUS


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle


# Per-column ray offsets, fish-eye factors, and pixel columns (constant).
_cols = (np.arange(NUM_RAYS) + 0.5) / NUM_RAYS
ANG_OFF = np.arctan((2.0 * _cols - 1.0) * math.tan(FOV / 2))
COS_OFF = np.cos(ANG_OFF)

_edges = (np.arange(NUM_RAYS + 1) * SCREEN_WIDTH / NUM_RAYS).astype(int)
COL_X = _edges[:-1].tolist()
COL_WIDTH = np.maximum(1, _edges[1:] - _edges[:-1]).tolist()


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_world(screen, walls, player, theme="flat",
                 ceiling_color=(38, 38, 54), floor_color=(58, 58, 58)):
    screen.fill(ceiling_color, (0, 0, SCREEN_WIDTH, HALF_HEIGHT))
    screen.fill(floor_color, (0, HALF_HEIGHT, SCREEN_WIDTH, HALF_HEIGHT))

    Ax, Ay = walls["Ax"], walls["Ay"]
    Ex, Ey = walls["Ex"], walls["Ey"]
    if len(Ax) == 0:
        return

    px, py = player.x, player.y
    ray_ang = player.angle + ANG_OFF
    Dx = np.cos(ray_ang)
    Dy = np.sin(ray_ang)

    # Nearest wall per column (ray/segment intersection).
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
    perp = tmin * COS_OFF
    finite = np.isfinite(perp)
    safe_perp = np.where(finite, perp, 1e9)
    fog = np.clip(3.0 / safe_perp, 0.20, 1.0)

    line_h = np.zeros(NUM_RAYS)
    line_h[finite] = np.clip(WALL_SCALE * SCREEN_HEIGHT / perp[finite],
                             1, SCREEN_HEIGHT * 3)
    y0 = np.clip(HALF_HEIGHT - line_h / 2, 0, SCREEN_HEIGHT).astype(int)
    y1 = np.clip(HALF_HEIGHT + line_h / 2, 0, SCREEN_HEIGHT).astype(int)

    if theme == "tron_theme":
        _draw_tron(screen, walls, idx, perp, y0, y1, finite, fog)
        return

    if theme == "shaded":
        tsafe = np.where(finite, tmin, 0.0)
        hit_x = px + tsafe * Dx
        hit_y = py + tsafe * Dy
        dd = (hit_x - walls["lcx"][idx]) ** 2 + (hit_y - walls["lcy"][idx]) ** 2
        atten = np.clip(1.7 / (1.0 + dd), 0.15, 1.0)        # room light falloff
        base = PALETTE[walls["lci"][idx]]                   # per-room light hue
        bright = atten * fog * walls["shade"][idx]
    else:  # flat
        base = PALETTE[walls["cidx"][idx]]
        bright = walls["shade"][idx] * fog

    rgb = np.clip(base * bright[:, None], 0, 255)
    _draw_solid(screen, rgb, y0, y1, finite)


def _draw_solid(screen, rgb, y0, y1, finite):
    rl = rgb.astype(int).tolist()
    y0l, y1l, fin = y0.tolist(), y1.tolist(), finite.tolist()
    for i in range(NUM_RAYS):
        if not fin[i]:
            continue
        pygame.draw.rect(screen, rl[i],
                         (COL_X[i], y0l[i], COL_WIDTH[i], y1l[i] - y0l[i]))


def _draw_tron(screen, walls, idx, perp, y0, y1, finite, fog):
    """Dark wall fills with glowing neon edges."""
    neon = np.clip(PALETTE[walls["cidx"][idx]]
                   * np.clip(fog * 1.25, 0.35, 1.0)[:, None], 0, 255)
    dark = np.clip(neon * 0.12, 0, 255)
    neonl, darkl = neon.astype(int).tolist(), dark.astype(int).tolist()
    y0l, y1l = y0.tolist(), y1.tolist()
    fin, perpl, idxl = finite.tolist(), perp.tolist(), idx.tolist()

    # Faint horizon line.
    pygame.draw.rect(screen, (0, 40, 55), (0, HALF_HEIGHT - 1, SCREEN_WIDTH, 2))

    for i in range(NUM_RAYS):
        if not fin[i]:
            continue
        x, w = COL_X[i], COL_WIDTH[i]
        a, b, col = y0l[i], y1l[i], neonl[i]
        pygame.draw.rect(screen, darkl[i], (x, a, w, b - a))     # dark fill
        pygame.draw.rect(screen, col, (x, a, w, 2))             # top edge
        pygame.draw.rect(screen, col, (x, max(a, b - 2), w, 2)) # bottom edge
        # Vertical neon at wall boundaries / depth discontinuities.
        if i > 0 and fin[i - 1] and (idxl[i] != idxl[i - 1]
                                     or abs(perpl[i] - perpl[i - 1]) > 0.3):
            top, bot = min(a, y0l[i - 1]), max(b, y1l[i - 1])
            pygame.draw.rect(screen, col, (x, top, 2, bot - top))
        elif i > 0 and not fin[i - 1]:
            pygame.draw.rect(screen, col, (x, a, 2, b - a))


# ---------------------------------------------------------------------------
# Physics
# ---------------------------------------------------------------------------
def resolve_collisions(x, y, segs):
    """Push a point out of any wall segment it is within COLLISION_RADIUS of."""
    r2 = COLLISION_RADIUS * COLLISION_RADIUS
    for _ in range(2):
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