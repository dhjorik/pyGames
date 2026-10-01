"""
All tunable constants and shared parameters for PyEscape.

This module holds only values (no logic), so every other module can import
from it freely without creating import cycles.
"""

import math
import os

import numpy as np

# --- Display ---------------------------------------------------------------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 600
HALF_HEIGHT = SCREEN_HEIGHT // 2
FPS = 60

# --- Raycasting ------------------------------------------------------------
NUM_RAYS = 320                       # vertical columns cast per frame
COL_W = SCREEN_WIDTH // NUM_RAYS     # px width of each column (must divide)
FOV = math.radians(66)              # field of view
WALL_SCALE = 1.0                     # projected wall height factor

# Default wall thickness in map units (R = 1.0). Overridden by engine.txt.
# 0.0 => infinitely thin walls (the old behaviour).
WALL_THICKNESS = 0.12

# --- Colors ----------------------------------------------------------------
CEILING_COLOR = (38, 38, 54)
FLOOR_COLOR = (58, 58, 58)

# Wall palette indexed by the map's color value (index 0 unused).
PALETTE = np.array([
    [0,   0,   0],      # 0 unused
    [0,   200, 0],      # 1 green
    [45,  95,  240],    # 2 blue
    [220, 45,  45],     # 3 red
    [230, 220, 45],     # 4 yellow
    [40,  210, 210],    # 5 cyan
    [245, 150, 30],     # 6 orange
    [240, 240, 240],    # 7 white
], dtype=float)

# --- Movement / physics ----------------------------------------------------
MOVE_SPEED = 2.4                     # units / second
ROT_SPEED = 2.3                      # radians / second
COLLISION_RADIUS = 0.22

# --- Hexagon geometry ------------------------------------------------------
R = 1.0                              # hexagon circumradius (map units)
HW = R * math.sqrt(3.0) / 2.0        # half of a hexagon's flat-to-flat width

# --- Wall bit masks (stored walls) -----------------------------------------
LEFT, FRONT_LEFT, FRONT_RIGHT, RIGHT = 1, 2, 4, 8

# --- Paths -----------------------------------------------------------------
# This file lives in pyescape/engine/, so levels.txt is one directory up.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
LEVELS_PATH = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "levels.txt"))
ENGINE_PATH = os.path.abspath(os.path.join(BASE_DIR, os.pardir, "engine.txt"))