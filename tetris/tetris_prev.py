"""
Basic Tetris in Python + pygame.

Grid:   12 squares wide  x  40 squares tall
Pieces: 7 standard tetrominoes (each made of 4 squares)

All tunable constants (grid size, colours, FPS, flash timing and the
falling SPEED in lines-per-second) live in "parameters.ini", which is
created automatically on first run and can be edited by hand.

Menu screen:
    Up / Down           : move the selection between buttons
    Space               : click the highlighted button (Start / Exit)

In-game controls:
    Left / Right arrows : move
    Down arrow          : soft drop (faster fall)
    Up arrow / X        : rotate clockwise
    Z                   : rotate counter-clockwise
    Space               : hard drop
    P                   : pause
    R                   : restart (after game over)
    Esc                 : back to menu
"""

import configparser
import math
import os
import random
import sys
import pygame

# ----------------------------------------------------------------------
# Configuration  (loaded from / saved to parameters.ini)
# ----------------------------------------------------------------------
PARAMS_FILE = "parameters.ini"

# Default value for every configurable constant.  On first run these are
# written to parameters.ini; after that the file is the source of truth
# and can be edited by hand.  Missing keys are refilled from here.
DEFAULTS = {
    "grid": {
        "cols": "12",            # grid width in squares
        "rows": "40",            # grid height in squares
        "cell": "20",            # pixel size of one square
        "sidebar": "160",        # width of the info panel (pixels)
    },
    "gameplay": {
        "fps": "60",
        "speed": "2.0",          # SPEED: drop rate in LINES PER SECOND
        "flash_duration": "300",   # completed-line flash time (ms)
        "flash_blink": "100",      # flash on/off interval (ms)
    },
    "colors": {                  # values are "R,G,B" (0-255)
        "black": "0,0,0",
        "grey": "40,40,40",
        "white": "230,230,230",
        "bg": "15,15,20",
    },
}


def save_config(parser, path=PARAMS_FILE):
    """Write every constant back out to the ini file (with a help header)."""
    with open(path, "w") as f:
        f.write("; Tetris parameters - edit these to tune the game.\n")
        f.write("; [gameplay] speed = falling speed in lines per second.\n")
        f.write("; [colors]   values are R,G,B in the range 0-255.\n\n")
        parser.write(f)


def load_config(path=PARAMS_FILE):
    """Load parameters.ini, creating or completing it from DEFAULTS."""
    parser = configparser.ConfigParser()
    parser.read(path)
    changed = not os.path.exists(path)
    for section, options in DEFAULTS.items():
        if not parser.has_section(section):
            parser.add_section(section)
            changed = True
        for key, value in options.items():
            if not parser.has_option(section, key):
                parser.set(section, key, value)
                changed = True
    if changed:                  # persist a complete file
        save_config(parser, path)
    return parser


def _rgb(text):
    return tuple(int(part) for part in text.split(","))


# ----- load configuration and expose the constants as globals ---------
_cfg = load_config()

COLS = _cfg.getint("grid", "cols")            # grid width in squares
ROWS = _cfg.getint("grid", "rows")            # grid height in squares
CELL = _cfg.getint("grid", "cell")            # pixel size of one square
SIDEBAR = _cfg.getint("grid", "sidebar")      # info-panel width in pixels

FPS = _cfg.getint("gameplay", "fps")
SPEED = _cfg.getfloat("gameplay", "speed")    # drop rate in lines per second
FLASH_DURATION = _cfg.getint("gameplay", "flash_duration")
FLASH_BLINK = _cfg.getint("gameplay", "flash_blink")

BLACK = _rgb(_cfg.get("colors", "black"))
GREY = _rgb(_cfg.get("colors", "grey"))
WHITE = _rgb(_cfg.get("colors", "white"))
BG = _rgb(_cfg.get("colors", "bg"))

# derived layout values
PLAY_W = COLS * CELL
PLAY_H = ROWS * CELL
SCREEN_W = PLAY_W + SIDEBAR
SCREEN_H = PLAY_H

# ----------------------------------------------------------------------
# Tetromino definitions
# Each shape is a list of rotation states.
# A rotation state is a list of (x, y) offsets for its 4 squares.
# ----------------------------------------------------------------------
SHAPES = {
    "I": [[(0, 1), (1, 1), (2, 1), (3, 1)],
          [(2, 0), (2, 1), (2, 2), (2, 3)]],
    "O": [[(1, 0), (2, 0), (1, 1), (2, 1)]],
    "T": [[(1, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (2, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (1, 2)],
          [(1, 0), (0, 1), (1, 1), (1, 2)]],
    "S": [[(1, 0), (2, 0), (0, 1), (1, 1)],
          [(1, 0), (1, 1), (2, 1), (2, 2)]],
    "Z": [[(0, 0), (1, 0), (1, 1), (2, 1)],
          [(2, 0), (1, 1), (2, 1), (1, 2)]],
    "J": [[(0, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (2, 0), (1, 1), (1, 2)],
          [(0, 1), (1, 1), (2, 1), (2, 2)],
          [(1, 0), (1, 1), (0, 2), (1, 2)]],
    "L": [[(2, 0), (0, 1), (1, 1), (2, 1)],
          [(1, 0), (1, 1), (1, 2), (2, 2)],
          [(0, 1), (1, 1), (2, 1), (0, 2)],
          [(0, 0), (1, 0), (1, 1), (1, 2)]],
}

COLORS = {
    "I": (0, 200, 220),
    "O": (230, 210, 0),
    "T": (170, 60, 200),
    "S": (0, 200, 90),
    "Z": (220, 50, 60),
    "J": (40, 90, 220),
    "L": (230, 130, 30),
}


class Piece:
    """A falling tetromino with a position and a rotation index."""

    def __init__(self, kind):
        self.kind = kind
        self.rotation = 0
        # spawn near the top centre
        self.x = COLS // 2 - 2
        self.y = 0

    def cells(self, rotation=None, x=None, y=None):
        """Absolute (col, row) coordinates of the 4 squares."""
        rot = self.rotation if rotation is None else rotation
        px = self.x if x is None else x
        py = self.y if y is None else y
        states = SHAPES[self.kind]
        state = states[rot % len(states)]
        return [(px + ox, py + oy) for ox, oy in state]


# ----------------------------------------------------------------------
# Game logic
# ----------------------------------------------------------------------
class Tetris:
    def __init__(self):
        self.reset()

    def reset(self):
        # grid[row][col] -> None (empty) or an (r, g, b) colour
        self.grid = [[None] * COLS for _ in range(ROWS)]
        self.bag = []
        self.current = self.new_piece()
        self.next_piece = self.new_piece()
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.paused = False
        # line-clear flash animation
        self.clearing_rows = []    # rows currently flashing before removal
        self.clear_timer = 0       # elapsed flash time in ms
        # fall timing: derived from SPEED (lines per second)
        self.fall_delay = self.fall_delay_for_level()
        self.fall_timer = 0

    def fall_delay_for_level(self):
        """Milliseconds between automatic drops.

        SPEED is the base drop rate in lines per second; each level makes
        the piece fall 15% faster, down to a floor of 40 ms per line.
        """
        lines_per_sec = SPEED * (1.0 + 0.15 * (self.level - 1))
        return max(40.0, 1000.0 / lines_per_sec)

    def new_piece(self):
        """7-bag randomizer: each shape appears once per bag."""
        if not self.bag:
            self.bag = list(SHAPES.keys())
            random.shuffle(self.bag)
        return Piece(self.bag.pop())

    def valid(self, piece, rotation=None, x=None, y=None):
        for cx, cy in piece.cells(rotation, x, y):
            if cx < 0 or cx >= COLS or cy >= ROWS:
                return False
            if cy >= 0 and self.grid[cy][cx] is not None:
                return False
        return True

    def lock_piece(self):
        color = COLORS[self.current.kind]
        for cx, cy in self.current.cells():
            if cy >= 0:
                self.grid[cy][cx] = color
        # find completed rows
        full = [r for r in range(ROWS)
                if all(self.grid[r][c] is not None for c in range(COLS))]
        if full:
            # start the flash; removal happens once it finishes
            self.clearing_rows = full
            self.clear_timer = 0
        else:
            self.spawn_next()

    def spawn_next(self):
        self.current = self.next_piece
        self.next_piece = self.new_piece()
        # if the freshly spawned piece already collides -> game over
        if not self.valid(self.current):
            self.game_over = True

    def finish_clear(self):
        """Remove the flashed rows, update score, and spawn the next piece."""
        cleared = len(self.clearing_rows)
        rows_to_remove = set(self.clearing_rows)
        remaining = [row for i, row in enumerate(self.grid)
                     if i not in rows_to_remove]
        for _ in range(cleared):
            remaining.insert(0, [None] * COLS)
        self.grid = remaining
        # classic scoring
        self.score += (0, 100, 300, 500, 800)[cleared] * self.level
        self.lines += cleared
        self.level = 1 + self.lines // 10
        self.fall_delay = self.fall_delay_for_level()
        self.clearing_rows = []
        self.clear_timer = 0
        self.spawn_next()

    # --- player actions -------------------------------------------------
    def move(self, dx):
        if self.valid(self.current, x=self.current.x + dx):
            self.current.x += dx

    def soft_drop(self):
        if self.valid(self.current, y=self.current.y + 1):
            self.current.y += 1
            self.score += 1
            return True
        self.lock_piece()
        return False

    def hard_drop(self):
        dropped = 0
        while self.valid(self.current, y=self.current.y + 1):
            self.current.y += 1
            dropped += 1
        self.score += dropped * 2
        self.lock_piece()

    def rotate(self, direction):
        new_rot = self.current.rotation + direction
        # simple wall-kick: try in place, then nudged left/right
        for kick in (0, -1, 1, -2, 2):
            if self.valid(self.current, rotation=new_rot,
                          x=self.current.x + kick):
                self.current.rotation = new_rot
                self.current.x += kick
                return

    def step(self, dt):
        if self.paused or self.game_over:
            return
        # while completed lines are flashing, hold everything else
        if self.clearing_rows:
            self.clear_timer += dt
            if self.clear_timer >= FLASH_DURATION:
                self.finish_clear()
            return
        self.fall_timer += dt
        if self.fall_timer >= self.fall_delay:
            self.fall_timer = 0
            self.soft_drop()


# ----------------------------------------------------------------------
# Rendering
# ----------------------------------------------------------------------
def draw_cell(surface, col, row, color):
    rect = pygame.Rect(col * CELL, row * CELL, CELL, CELL)
    pygame.draw.rect(surface, color, rect)
    pygame.draw.rect(surface, BG, rect, 1)


def draw(surface, game, font, big_font):
    surface.fill(BG)

    # playfield background + faint grid
    pygame.draw.rect(surface, BLACK, (0, 0, PLAY_W, PLAY_H))
    for c in range(COLS + 1):
        pygame.draw.line(surface, GREY, (c * CELL, 0), (c * CELL, PLAY_H))
    for r in range(ROWS + 1):
        pygame.draw.line(surface, GREY, (0, r * CELL), (PLAY_W, r * CELL))

    # settled blocks
    flash_on = False
    if game.clearing_rows:
        # blink between the block colour and bright white
        flash_on = (game.clear_timer // FLASH_BLINK) % 2 == 0
    for r in range(ROWS):
        row_flashing = r in game.clearing_rows
        for c in range(COLS):
            if game.grid[r][c]:
                if row_flashing and flash_on:
                    draw_cell(surface, c, r, WHITE)
                else:
                    draw_cell(surface, c, r, game.grid[r][c])

    # ghost + current piece (hidden while lines are flashing / on game over)
    if not game.game_over and not game.clearing_rows:
        ghost_y = game.current.y
        while game.valid(game.current, y=ghost_y + 1):
            ghost_y += 1
        ghost_color = tuple(v // 3 for v in COLORS[game.current.kind])
        for cx, cy in game.current.cells(y=ghost_y):
            if cy >= 0:
                draw_cell(surface, cx, cy, ghost_color)

        # falling piece
        for cx, cy in game.current.cells():
            if cy >= 0:
                draw_cell(surface, cx, cy, COLORS[game.current.kind])

    # ---- sidebar -------------------------------------------------------
    x0 = PLAY_W + 15

    def text(label, y, f=font, color=WHITE):
        surface.blit(f.render(label, True, color), (x0, y))

    text("TETRIS", 20, big_font)
    text(f"Score: {game.score}", 70)
    text(f"Lines: {game.lines}", 95)
    text(f"Level: {game.level}", 120)

    text("Next:", 160)
    # preview of the next piece
    for ox, oy in SHAPES[game.next_piece.kind][0]:
        rect = pygame.Rect(x0 + ox * CELL, 185 + oy * CELL, CELL, CELL)
        pygame.draw.rect(surface, COLORS[game.next_piece.kind], rect)
        pygame.draw.rect(surface, BG, rect, 1)

    controls = [
        "Controls:",
        "< >  move",
        "Down soft drop",
        "Up/X rotate",
        "Z    rotate ccw",
        "Space hard drop",
        "P    pause",
        "Esc  quit",
    ]
    for i, line in enumerate(controls):
        text(line, 300 + i * 22, font, WHITE if i else (150, 150, 150))

    # overlays
    if game.paused:
        text("PAUSED", PLAY_H // 2, big_font, (255, 220, 0))
    if game.game_over:
        surface.blit(big_font.render("GAME OVER", True, (255, 80, 80)),
                     (x0, PLAY_H // 2 - 30))
        text("Press R to restart", PLAY_H // 2 + 5)


# ----------------------------------------------------------------------
# Menu screen
# ----------------------------------------------------------------------
MENU_ITEMS = ["Start", "Exit"]


def _new_floater(grid_cols, grid_rows, spread):
    """A single drifting tetromino for the menu backdrop.

    spread=True places it somewhere on-screen (used for the initial fill);
    spread=False starts it just above the top edge (used when respawning).
    """
    kind = random.choice(list(SHAPES.keys()))
    base_x = random.uniform(0, grid_cols - 4)
    y = random.uniform(0, grid_rows * 0.6) if spread else random.uniform(-6, -3)
    return {
        "kind": kind,
        "color": COLORS[kind],
        "base_x": base_x,          # centre of the horizontal sway (cells)
        "x": base_x,               # current x (cells, fractional)
        "y": y,                    # current y (cells, fractional)
        "vy": random.uniform(0.35, 0.8),        # fall speed (cells / second)
        "amp": random.uniform(0.3, 0.9),        # sway amplitude (cells)
        "sway_speed": random.uniform(0.4, 1.3), # sway rate
        "phase": random.uniform(0, math.tau),   # sway offset
    }


def build_menu_decor():
    """Build the 'arcade cabinet' backdrop: a static pile of stacked blocks
    along the bottom plus a set of drifting tetrominoes that gently fall."""
    grid_cols = SCREEN_W // CELL
    grid_rows = SCREEN_H // CELL
    palette = list(COLORS.values())

    # uneven static pile along the bottom, like a game in progress
    pile = []
    height = grid_rows // 4
    for c in range(grid_cols):
        height = max(2, min(grid_rows // 2, height + random.randint(-2, 2)))
        for r in range(grid_rows - height, grid_rows):
            if random.random() < 0.88:          # leave occasional gaps
                pile.append((c, r, random.choice(palette)))

    floaters = [_new_floater(grid_cols, grid_rows, spread=True)
                for _ in range(7)]

    return {"pile": pile, "floaters": floaters,
            "cols": grid_cols, "rows": grid_rows}


def update_menu_decor(decor, dt):
    """Advance the drifting tetrominoes; respawn them at the top once they
    fall off the bottom."""
    secs = dt / 1000.0
    for f in decor["floaters"]:
        f["y"] += f["vy"] * secs
        f["phase"] += f["sway_speed"] * secs
        f["x"] = f["base_x"] + f["amp"] * math.sin(f["phase"])
        if f["y"] > decor["rows"] + 1:
            f.update(_new_floater(decor["cols"], decor["rows"], spread=False))


def draw_menu(surface, selected, title_font, font, decor):
    surface.fill(BLACK)

    # static pile at the bottom
    for c, r, color in decor["pile"]:
        draw_cell(surface, c, r, color)

    # drifting tetrominoes (fractional pixel positions for smooth motion)
    for f in decor["floaters"]:
        for ox, oy in SHAPES[f["kind"]][0]:
            px = int((f["x"] + ox) * CELL)
            py = int((f["y"] + oy) * CELL)
            rect = pygame.Rect(px, py, CELL, CELL)
            pygame.draw.rect(surface, f["color"], rect)
            pygame.draw.rect(surface, BG, rect, 1)

    # darken the whole screen so the menu text reads clearly
    veil = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
    veil.fill((0, 0, 0, 120))
    surface.blit(veil, (0, 0))

    title_y = SCREEN_H // 4
    start_y = SCREEN_H // 2
    btn_w, btn_h = 200, 50
    gap = 20
    hint_y = start_y + len(MENU_ITEMS) * (btn_h + gap) + 20

    # translucent panel behind the title + buttons
    panel = pygame.Rect(0, 0, 280, hint_y - title_y + 70)
    panel.centerx = SCREEN_W // 2
    panel.y = title_y - 35
    panel_surf = pygame.Surface(panel.size, pygame.SRCALPHA)
    panel_surf.fill((12, 12, 22, 220))
    surface.blit(panel_surf, panel.topleft)
    pygame.draw.rect(surface, (90, 90, 130), panel, 2, border_radius=12)

    # colourful "TETRIS" logo, one tetromino colour per letter
    letters = "TETRIS"
    letter_colors = [COLORS["I"], COLORS["O"], COLORS["T"],
                     COLORS["S"], COLORS["Z"], COLORS["L"]]
    glyphs = [title_font.render(ch, True, letter_colors[i])
              for i, ch in enumerate(letters)]
    total_w = sum(g.get_width() for g in glyphs)
    x = SCREEN_W // 2 - total_w // 2
    for g in glyphs:
        surface.blit(g, (x, title_y))
        x += g.get_width()

    # buttons
    for i, label in enumerate(MENU_ITEMS):
        rect = pygame.Rect(0, 0, btn_w, btn_h)
        rect.centerx = SCREEN_W // 2
        rect.y = start_y + i * (btn_h + gap)

        is_sel = (i == selected)
        fill = (60, 120, 220) if is_sel else (45, 45, 55)
        border = WHITE if is_sel else (90, 90, 100)
        pygame.draw.rect(surface, fill, rect, border_radius=8)
        pygame.draw.rect(surface, border, rect, 3, border_radius=8)

        txt = font.render(label, True, WHITE)
        surface.blit(txt, (rect.centerx - txt.get_width() // 2,
                           rect.centery - txt.get_height() // 2))

    hint = font.render("Up/Down to select, Space to click", True, (150, 150, 160))
    surface.blit(hint, (SCREEN_W // 2 - hint.get_width() // 2, hint_y))


# ----------------------------------------------------------------------
# Main loop
# ----------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    pygame.display.set_caption("Tetris")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)
    big_font = pygame.font.SysFont("consolas", 28, bold=True)
    menu_font = pygame.font.SysFont("consolas", 56, bold=True)

    game = Tetris()
    state = "menu"          # "menu" or "playing"
    selected = 0            # highlighted menu button
    menu_decor = build_menu_decor()   # static cabinet backdrop

    while True:
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()

            if event.type != pygame.KEYDOWN:
                continue

            # -------------------- MENU --------------------
            if state == "menu":
                if event.key == pygame.K_ESCAPE:
                    pygame.quit()
                    sys.exit()
                elif event.key == pygame.K_UP:
                    selected = (selected - 1) % len(MENU_ITEMS)
                elif event.key == pygame.K_DOWN:
                    selected = (selected + 1) % len(MENU_ITEMS)
                elif event.key == pygame.K_SPACE:
                    if MENU_ITEMS[selected] == "Start":
                        game.reset()
                        # let holding keys repeat only during play
                        pygame.key.set_repeat(160, 60)
                        state = "playing"
                    else:  # Exit
                        pygame.quit()
                        sys.exit()
                continue

            # -------------------- PLAYING --------------------
            if event.key == pygame.K_ESCAPE:
                # return to the menu
                pygame.key.set_repeat(0)
                state = "menu"
                continue

            if game.game_over:
                if event.key == pygame.K_r:
                    game.reset()
                continue

            if event.key == pygame.K_p:
                game.paused = not game.paused
            if game.paused:
                continue

            # ignore piece input while completed lines are flashing
            if game.clearing_rows:
                continue

            if event.key == pygame.K_LEFT:
                game.move(-1)
            elif event.key == pygame.K_RIGHT:
                game.move(1)
            elif event.key == pygame.K_DOWN:
                game.soft_drop()
            elif event.key in (pygame.K_UP, pygame.K_x):
                game.rotate(1)
            elif event.key == pygame.K_z:
                game.rotate(-1)
            elif event.key == pygame.K_SPACE:
                game.hard_drop()

        # -------------------- render --------------------
        if state == "menu":
            update_menu_decor(menu_decor, dt)
            draw_menu(screen, selected, menu_font, font, menu_decor)
        else:
            game.step(dt)
            draw(screen, game, font, big_font)

        pygame.display.flip()


if __name__ == "__main__":
    main()