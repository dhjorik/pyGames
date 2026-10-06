"""
Fixed constants for PyEscape.

Most tunables now live in config files: engine.txt (display, raycasting,
palette, connector steps) is read by configurations.py, and per-level values
(theme, ceiling/floor colors) live in levels.txt. This module keeps only the
values that are intrinsic to the engine and not meant to be edited casually.
"""

import math
import os

# --- Timing / movement -----------------------------------------------------
FPS = 60
MOVE_SPEED = 2.4                     # units / second
ROT_SPEED = 2.3                      # radians / second
COLLISION_RADIUS = 0.22

# --- Hexagon geometry ------------------------------------------------------
R = 1.0                              # hexagon circumradius (map units)
HW = R * math.sqrt(3.0) / 2.0        # half of a hexagon's flat-to-flat width

# --- Wall bit masks (stored walls) -----------------------------------------
LEFT, FRONT_LEFT, FRONT_RIGHT, RIGHT = 1, 2, 4, 8

# --- Paths -----------------------------------------------------------------
# This file lives in pyescape/engine/, so the config files are one dir up.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS_PATH = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "levels.txt"))
ENGINE_PATH = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "engine.txt"))