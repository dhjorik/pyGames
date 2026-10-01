"""
PyEscape - application entry point.

Wires the engine modules together and runs the menu / gameplay state machine.

Run from this directory:

    python main.py

Requires:  pip install pygame numpy
"""

import math
import sys

import pygame

from pyescape.engine.constants import (
    SCREEN_WIDTH, SCREEN_HEIGHT, HALF_HEIGHT, FPS, MOVE_SPEED, ROT_SPEED, R,
)
from pyescape.engine.configurations import load_levels, load_engine_config
from pyescape.engine.maps import generate_maze, build_walls, hex_center
from pyescape.engine.raycaster import (
    Player, render_world, resolve_collisions, draw_minimap,
)


# ---------------------------------------------------------------------------
# UI button
# ---------------------------------------------------------------------------
class Button:
    def __init__(self, rect, label):
        self.rect = pygame.Rect(rect)
        self.label = label

    def draw(self, screen, font, mouse):
        hover = self.rect.collidepoint(mouse)
        fill = (70, 110, 175) if hover else (48, 74, 122)
        pygame.draw.rect(screen, fill, self.rect, border_radius=10)
        pygame.draw.rect(screen, (200, 210, 235), self.rect, 2, border_radius=10)
        txt = font.render(self.label, True, (240, 240, 248))
        screen.blit(txt, txt.get_rect(center=self.rect.center))


# ---------------------------------------------------------------------------
# Game states
# ---------------------------------------------------------------------------
MENU, PLAYING, COMPLETE, WINNER = "menu", "playing", "complete", "winner"


class Game:
    def __init__(self, screen, levels):
        self.screen = screen
        self.levels = levels
        self.running = True
        self.state = MENU
        self.index = 0
        self.completed_number = 0

        self.walls = None
        self.player = None
        self.exit_y = 0.0
        self.show_map = True

        self.wall_thickness = load_engine_config()["wall_thickness"]

        self.big = pygame.font.SysFont("consolas", 56, bold=True)
        self.mid = pygame.font.SysFont("consolas", 30, bold=True)
        self.font = pygame.font.SysFont("consolas", 22)
        self.small = pygame.font.SysFont("consolas", 18)

        bw, bh = 240, 56
        cx = SCREEN_WIDTH // 2 - bw // 2
        self.start_btn = Button((cx, 300, bw, bh), "START")
        self.exit_btn = Button((cx, 372, bw, bh), "EXIT")

    # -- level lifecycle ----------------------------------------------------
    def load_level(self, index):
        lv = self.levels[index]
        world, start = generate_maze(lv["h"], lv["w"], seed=lv["seed"])
        self.walls = build_walls(world, self.wall_thickness)
        sx, sy = hex_center(*start)
        self.player = Player(sx, sy, math.pi / 2)     # face into the maze
        self.exit_y = hex_center(lv["h"] - 1, 0)[1] + R
        self.index = index
        self.state = PLAYING

    # -- events -------------------------------------------------------------
    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False

            elif self.state == MENU:
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if self.start_btn.rect.collidepoint(event.pos):
                        self.load_level(0)
                    elif self.exit_btn.rect.collidepoint(event.pos):
                        self.running = False
                elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                    self.running = False

            elif self.state == PLAYING:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = MENU                 # abandon level
                    elif event.key == pygame.K_TAB:
                        self.show_map = not self.show_map

            elif self.state == COMPLETE:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = MENU
                    else:
                        self.load_level(self.index + 1)   # next level

            elif self.state == WINNER:
                if event.type == pygame.KEYDOWN:
                    self.state = MENU

    # -- update -------------------------------------------------------------
    def update(self, dt):
        if self.state != PLAYING:
            return
        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            self.player.angle -= ROT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            self.player.angle += ROT_SPEED * dt

        step = MOVE_SPEED * dt
        dx, dy = math.cos(self.player.angle), math.sin(self.player.angle)
        nx, ny = self.player.x, self.player.y
        if keys[pygame.K_UP]:
            nx += dx * step; ny += dy * step
        if keys[pygame.K_DOWN]:
            nx -= dx * step; ny -= dy * step
        nx, ny = resolve_collisions(nx, ny, self.walls["segs"])
        self.player.x, self.player.y = nx, ny

        if self.player.y > self.exit_y + 0.15:            # left via the exit
            self.completed_number = self.levels[self.index]["number"]
            if self.index >= len(self.levels) - 1:
                self.state = WINNER
            else:
                self.state = COMPLETE

    # -- drawing ------------------------------------------------------------
    def draw(self):
        if self.state == MENU:
            self.draw_menu()
            return

        render_world(self.screen, self.walls, self.player)
        if self.show_map:
            draw_minimap(self.screen, self.walls, self.player)

        if self.state == PLAYING:
            hud = self.small.render(
                "arrows: move/turn   TAB: map   ESC: menu", True, (230, 230, 230))
            self.screen.blit(hud, (10, SCREEN_HEIGHT - 26))
        elif self.state == COMPLETE:
            self.draw_center([
                ("Level %d complete!" % self.completed_number,
                 self.mid, (130, 255, 130)),
                ("Press any key to start new level", self.font, (235, 235, 235)),
                ("Esc: return to menu", self.small, (170, 170, 180)),
            ])
        elif self.state == WINNER:
            self.draw_center([
                ("WINNER!", self.big, (255, 215, 70)),
                ("You cleared every level", self.font, (235, 235, 235)),
                ("Press any key to return to the menu",
                 self.small, (170, 170, 180)),
            ])

    def draw_menu(self):
        s = self.screen
        s.fill((22, 24, 34))
        title = self.big.render("PYESCAPE", True, (235, 235, 245))
        s.blit(title, title.get_rect(center=(SCREEN_WIDTH // 2, 150)))
        sub = self.font.render("Escape the hexagonal labyrinth",
                               True, (150, 160, 185))
        s.blit(sub, sub.get_rect(center=(SCREEN_WIDTH // 2, 205)))
        mouse = pygame.mouse.get_pos()
        self.start_btn.draw(s, self.font, mouse)
        self.exit_btn.draw(s, self.font, mouse)
        hint = self.small.render("%d levels loaded" % len(self.levels),
                                 True, (120, 130, 150))
        s.blit(hint, hint.get_rect(center=(SCREEN_WIDTH // 2, SCREEN_HEIGHT - 40)))

    def draw_center(self, lines):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 155))
        self.screen.blit(overlay, (0, 0))
        total = sum(f.get_height() + 12 for _, f, _ in lines)
        y = HALF_HEIGHT - total // 2
        for text, font, color in lines:
            surf = font.render(text, True, color)
            self.screen.blit(surf, surf.get_rect(center=(SCREEN_WIDTH // 2, y)))
            y += font.get_height() + 12


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("PyEscape")
    clock = pygame.time.Clock()

    game = Game(screen, load_levels())

    while game.running:
        dt = clock.tick(FPS) / 1000.0
        game.handle_events()
        game.update(dt)
        game.draw()
        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()