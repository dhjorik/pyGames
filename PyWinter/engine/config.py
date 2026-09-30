# Game Configuration

# Display
SCREEN_WIDTH = 1024
SCREEN_HEIGHT = 768
# SCREEN_WIDTH = 400
# SCREEN_HEIGHT = 380
FPS = 60
TITLE = "PyWinter - Platform Game"

# Physics
GRAVITY = 0.6
PLAYER_JUMP_POWER = 15
PLAYER_SPEED = 5
PLAYER_MAX_FALL_SPEED = 20

# Player
PLAYER_WIDTH = 32
PLAYER_HEIGHT = 48
PLAYER_START_X = 100
PLAYER_START_Y = 0

# Camera
CAMERA_FOLLOW_SPEED = 0.2
CAMERA_OFFSET_X = SCREEN_WIDTH // 3  # Keep player 1/3 from left edge

# Colors
COLOR_BLACK = (0, 0, 0)
COLOR_WHITE = (255, 255, 255)
COLOR_BLUE = (100, 150, 255)
COLOR_GREEN = (100, 200, 100)
COLOR_BROWN = (139, 69, 19)

# Background
# COLOR_SKY = (135, 206, 235)
COLOR_SKY = COLOR_BLACK
BACKGROUND_FILL_COLOR = (0, 0, 0, 0)  # Fully transparent background for player/platform level
BACKGROUND_LAYER_ALPHA = {
    'layer01_front': 255,  # Fully opaque
    'layer02_front': 255,
    'layer03_back': 240,   # Slight transparency
    'layer04_back': 230,
    'layer05_back': 220,
    'layer06_back': 210,
    'layer07_fixed': 255,  # Fully opaque
}
# Default alpha if layer not in dict
DEFAULT_LAYER_ALPHA = 240
