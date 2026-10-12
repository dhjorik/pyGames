"""
The render engine: projects the 3D mesh (floor triangles + wall boxes) into a
first-person view and fills the polygons, in one of three themes.

  flat        : stone floor + palette walls, relief-shaded, depth fog.
  shaded      : every room tinted by its own palette-coloured light.
  tron_theme  : dark fills with glowing neon edges (the triangulated floor
                reads as a Space Paranoids grid).

Pipeline: transform to camera space -> near-plane clip -> perspective project
-> painter's sort (far first) -> fill. Collision and the minimap stay 2D.
"""

import math

import numpy as np
import pygame

from .configurations import SCREEN_WIDTH, SCREEN_HEIGHT, HALF_HEIGHT, FOV, PALETTE
from .constants import COLLISION_RADIUS

HALF_W = SCREEN_WIDTH / 2.0
FOCAL = (SCREEN_WIDTH / 2.0) / math.tan(FOV / 2.0)
NEAR = 0.05
FOG_K = 4.0
FLOOR_BASE = np.array([95.0, 98.0, 112.0])      # flat-theme floor colour
_CLAMP = 100000


# ---------------------------------------------------------------------------
# Player
# ---------------------------------------------------------------------------
class Player:
    def __init__(self, x, y, angle):
        self.x = x
        self.y = y
        self.angle = angle


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------
def _clip_near(F, Rr, U):
    """Clip a camera-space polygon against the plane forward == NEAR."""
    n = len(F)
    of, oR, oU = [], [], []
    for i in range(n):
        j = (i + 1) % n
        fi, fj = F[i], F[j]
        ini, inj = fi >= NEAR, fj >= NEAR
        if ini:
            of.append(fi); oR.append(Rr[i]); oU.append(U[i])
        if ini != inj:
            tt = (NEAR - fi) / (fj - fi)
            of.append(NEAR)
            oR.append(Rr[i] + tt * (Rr[j] - Rr[i]))
            oU.append(U[i] + tt * (U[j] - U[i]))
    return of, oR, oU


def _rgb(a):
    return (int(max(0, min(255, a[0]))),
            int(max(0, min(255, a[1]))),
            int(max(0, min(255, a[2]))))


def _clamp(v, lo, hi):
    return lo if v < lo else (hi if v > hi else v)


# ---------------------------------------------------------------------------
# Rendering
# ---------------------------------------------------------------------------
def render_world(screen, mesh, player, theme="flat",
                 ceiling_color=(38, 38, 54), floor_color=(58, 58, 58),
                 eye_h=0.5):
    screen.fill(ceiling_color, (0, 0, SCREEN_WIDTH, HALF_HEIGHT))
    screen.fill(floor_color, (0, HALF_HEIGHT, SCREEN_WIDTH,
                              SCREEN_HEIGHT - HALF_HEIGHT))

    V = mesh["V"]
    polys = mesh["polys"]
    if len(V) == 0 or not polys:
        return

    px, py = player.x, player.y
    yaw = player.angle
    fx, fy = math.cos(yaw), math.sin(yaw)
    rx, ry = -math.sin(yaw), math.cos(yaw)

    d0 = V[:, 0] - px
    d1 = V[:, 1] - py
    CF = (d0 * fx + d1 * fy).tolist()           # forward (depth)
    CR = (d0 * rx + d1 * ry).tolist()           # right
    CU = (V[:, 2] - eye_h).tolist()             # up

    tron = (theme == "tron_theme")
    shaded = (theme == "shaded")

    draw_list = []
    for poly in polys:
        idx = poly["idx"]
        Fv = [CF[i] for i in idx]
        if max(Fv) <= NEAR:
            continue                            # entirely behind camera
        Rv = [CR[i] for i in idx]
        Uv = [CU[i] for i in idx]
        if min(Fv) < NEAR:
            Fv, Rv, Uv = _clip_near(Fv, Rv, Uv)
            if len(Fv) < 3:
                continue

        pts = []
        depth = 0.0
        minx = miny = 1e18
        maxx = maxy = -1e18
        for F, Rr, U in zip(Fv, Rv, Uv):
            sx = _clamp(HALF_W + FOCAL * Rr / F, -_CLAMP, _CLAMP)
            sy = _clamp(HALF_HEIGHT - FOCAL * U / F, -_CLAMP, _CLAMP)
            pts.append((sx, sy))
            depth += F
            minx = min(minx, sx); maxx = max(maxx, sx)
            miny = min(miny, sy); maxy = max(maxy, sy)
        if maxx < 0 or minx > SCREEN_WIDTH or maxy < 0 or miny > SCREEN_HEIGHT:
            continue                            # off-screen
        draw_list.append((depth / len(Fv), pts, poly))

    draw_list.sort(key=lambda e: e[0], reverse=True)   # far first

    for depth, pts, poly in draw_list:
        fog = _clamp(FOG_K / depth, 0.15, 1.0)
        if tron:
            neon = PALETTE[poly["cidx"]] * _clamp(fog * 1.3, 0.3, 1.0)
            pygame.draw.polygon(screen, _rgb(neon * 0.12), pts)
            pygame.draw.polygon(screen, _rgb(neon), pts, 1)
            continue
        if shaded:
            base = PALETTE[poly["lci"]]
        elif poly["kind"] == 0:
            base = FLOOR_BASE
        else:
            base = PALETTE[poly["cidx"]]
        pygame.draw.polygon(screen, _rgb(base * (poly["shade"] * fog)), pts)


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
# Minimap overlay (2D)
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