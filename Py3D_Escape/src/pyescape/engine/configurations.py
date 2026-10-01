"""
Read level definitions from the levels.txt configuration file.

Each non-comment line holds four integers (comma or whitespace separated):

    level_number   seed   maze_w(hex per row)   maze_h(rows)

The seed makes each level fully reproducible.
"""

import re

from .constants import LEVELS_PATH, ENGINE_PATH, WALL_THICKNESS

# Fallback used when levels.txt is missing or empty, so the game still runs.
DEFAULT_LEVELS = [
    {"number": 1, "seed": 101, "w": 8, "h": 8},
    {"number": 2, "seed": 202, "w": 10, "h": 10},
    {"number": 3, "seed": 303, "w": 12, "h": 12},
]

# Fallback engine settings, used when engine.txt is missing.
DEFAULT_ENGINE = {
    "wall_thickness": WALL_THICKNESS,
}


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
                levels.append({"number": num, "seed": seed, "w": w, "h": h})
    except FileNotFoundError:
        print("levels.txt not found at %s - using built-in defaults." % path)

    if not levels:
        return list(DEFAULT_LEVELS)
    levels.sort(key=lambda lv: lv["number"])
    return levels


def load_engine_config(path=ENGINE_PATH):
    """Read engine settings (currently wall_thickness) from engine.txt.

    Lines are ``key = value`` (``:`` also accepted). Unknown keys are kept as
    strings; numeric values are converted to float. Missing keys fall back to
    DEFAULT_ENGINE.
    """
    cfg = dict(DEFAULT_ENGINE)
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
                try:
                    val = float(val)
                except ValueError:
                    pass
                cfg[key] = val
    except FileNotFoundError:
        print("engine.txt not found at %s - using engine defaults." % path)

    # Validate wall_thickness (non-negative float).
    try:
        cfg["wall_thickness"] = max(0.0, float(cfg.get("wall_thickness")))
    except (TypeError, ValueError):
        cfg["wall_thickness"] = DEFAULT_ENGINE["wall_thickness"]
    return cfg