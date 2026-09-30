import math
import numpy as np

# ---------------------------------------------------------------------------
# Display / engine configuration
# ---------------------------------------------------------------------------
SCREEN_WIDTH = 960
SCREEN_HEIGHT = 600
HALF_HEIGHT = SCREEN_HEIGHT // 2
FPS = 60

NUM_RAYS = 320                       # vertical columns cast per frame
COL_W = SCREEN_WIDTH // NUM_RAYS     # width in px of each column (must divide)
FOV = math.radians(66)
WALL_SCALE = 1.0                     # projected wall height factor

CEILING_COLOR = (38, 38, 54)
FLOOR_COLOR = (58, 58, 58)

# Movement (units per second; delta-time scaled)
MOVE_SPEED = 2.4
ROT_SPEED = 2.3
COLLISION_RADIUS = 0.22

# Hexagon geometry (circumradius R; W is half the flat-to-flat width)
R = 1.0
HW = R * math.sqrt(3.0) / 2.0        # half hexagon width

# Colour palette as float RGB rows, indexed by the map's colour value.
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

# Wall bit masks
LEFT, FRONT_LEFT, FRONT_RIGHT, RIGHT = 1, 2, 4, 8
