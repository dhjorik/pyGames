"""
Read configuration from engine.txt and levels.txt.

engine.txt holds engine-wide parameters. They are read once when this module
is imported and exposed as module attributes (SCREEN_WIDTH, NUM_RAYS, PALETTE,
...) so the rest of the code can import them by name just like plain constants.

levels.txt holds one level per line:

    number  seed  maze_w  maze_h  theme  ceiling(#hex)  floor(#hex)

theme is one of: flat, shaded, tron_theme.
"""

import math
import re

import numpy as np

from .constants import LEVELS_PATH, ENGINE_PATH

# Valid render themes.
THEMES = ("flat", "shaded", "tron_theme")

# ---------------------------------------------------------------------------
# Small parsing helpers
# ---------------------------------------------------------------------------
def _parse_hex(token, fallback=(128, 128, 128)):
    """Parse '#rrggbb' or 'rrggbb' into an (r, g, b) tuple."""
    s = str(token).strip().lstrip("#")
    try:
        return (int(s[0:2], 16), int(s[2:4], 16), int(s[4:6], 16))
    except (ValueError, IndexError):
        return fallback


def _norm_theme(token):
    t = str(token).strip().lower()
    if t in ("tron", "tron_theme", "tron-theme"):
        return "tron_theme"
    if t in THEMES:
        return t
    return "flat"


# ---------------------------------------------------------------------------
# engine.txt
# ---------------------------------------------------------------------------
# Fallback engine settings, used when engine.txt is missing or a key is absent.
DEFAULT_ENGINE = {
    "screen_width": 960,
    "screen_height": 600,
    "num_rays": 320,
    "fov": 66.0,                 # degrees
    "wall_scale": 1.0,
    "wall_thickness": 0.12,
    "connector_steps": 6,
    "palette": [                 # colours for wall indices 1..7
        (0, 200, 0), (45, 95, 240), (220, 45, 45), (230, 220, 45),
        (40, 210, 210), (245, 150, 30), (240, 240, 240),
    ],
}


def load_engine_config(path=ENGINE_PATH):
    """Return a dict of engine settings parsed from engine.txt."""
    cfg = dict(DEFAULT_ENGINE)
    cfg["palette"] = list(DEFAULT_ENGINE["palette"])
    try:
        with open(path, "r") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                sep = "=" if "=" in line else (":" if ":" in line else None)
                if sep is None:
                    continue
                key, val = line.split(sep, 1)
                key = key.strip().lower()
                val = val.strip()
                if key == "palette":
                    cols = [_parse_hex(t) for t in re.split(r"[,\s]+", val) if t]
                    if cols:
                        cfg["palette"] = cols
                else:
                    val = val.split("#", 1)[0].strip()   # drop inline comment
                    try:
                        val = float(val)
                    except ValueError:
                        pass
                    cfg[key] = val
    except FileNotFoundError:
        print("engine.txt not found at %s - using engine defaults." % path)
    return cfg


# Load once at import and expose as module-level values.
_ENGINE = load_engine_config()

SCREEN_WIDTH = int(_ENGINE["screen_width"])
SCREEN_HEIGHT = int(_ENGINE["screen_height"])
HALF_HEIGHT = SCREEN_HEIGHT // 2
NUM_RAYS = max(1, int(_ENGINE["num_rays"]))
FOV = math.radians(float(_ENGINE["fov"]))
WALL_SCALE = float(_ENGINE["wall_scale"])
WALL_THICKNESS = max(0.0, float(_ENGINE["wall_thickness"]))
CONNECTOR_STEPS = max(1, int(_ENGINE["connector_steps"]))

# PALETTE: index 0 is unused (black); indices 1..7 come from engine.txt.
PALETTE = np.array([[0, 0, 0]] + [list(c) for c in _ENGINE["palette"]],
                   dtype=float)


# ---------------------------------------------------------------------------
# levels.txt
# ---------------------------------------------------------------------------
DEFAULT_LEVELS = [
    {"number": 1, "seed": 101, "w": 8, "h": 8,
     "theme": "flat", "ceiling": (38, 38, 54), "floor": (58, 58, 58)},
    {"number": 2, "seed": 202, "w": 10, "h": 10,
     "theme": "shaded", "ceiling": (10, 10, 24), "floor": (18, 18, 22)},
    {"number": 3, "seed": 303, "w": 12, "h": 12,
     "theme": "tron_theme", "ceiling": (0, 0, 0), "floor": (0, 16, 22)},
]


def load_levels(path=LEVELS_PATH):
    """Return a list of level dicts sorted by level number."""
    levels = []
    try:
        with open(path, "r") as fh:
            for raw in fh:
                line = raw.strip()
                if not line or line.startswith("#"):
                    continue
                parts = re.split(r"[,\s]+", line)
                if len(parts) < 4:
                    continue
                try:
                    num, seed, w, h = (int(parts[0]), int(parts[1]),
                                       int(parts[2]), int(parts[3]))
                except ValueError:
                    continue
                theme = _norm_theme(parts[4]) if len(parts) > 4 else "flat"
                ceiling = _parse_hex(parts[5], (38, 38, 54)) if len(parts) > 5 \
                    else (38, 38, 54)
                floor = _parse_hex(parts[6], (58, 58, 58)) if len(parts) > 6 \
                    else (58, 58, 58)
                levels.append({
                    "number": num, "seed": seed, "w": w, "h": h,
                    "theme": theme, "ceiling": ceiling, "floor": floor,
                })
    except FileNotFoundError:
        print("levels.txt not found at %s - using built-in defaults." % path)

    if not levels:
        return [dict(lv) for lv in DEFAULT_LEVELS]
    levels.sort(key=lambda lv: lv["number"])
    return levels