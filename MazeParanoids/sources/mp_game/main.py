import pygame
import sys

from mp_game.engine.constants import *

from mp_game.engine.raycasting import (
    generate_maze, build_walls,
    hex_center, resolve_collisions, 
    render_world, draw_minimap,
    Player
)
# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Hexagonal raycaster")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("consolas", 18)

    maze_h, maze_w = 12, 12
    world, start = generate_maze(maze_h, maze_w, seed=None)
    walls = build_walls(world)

    sx, sy = hex_center(*start)
    player = Player(sx, sy, math.pi / 2)             # face down, into the maze
    exit_y = hex_center(maze_h - 1, 0)[1] + R        # y just past the last row
    escaped = False
    show_map = True

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key == pygame.K_TAB:
                    show_map = not show_map

        keys = pygame.key.get_pressed()
        if keys[pygame.K_LEFT]:
            player.angle -= ROT_SPEED * dt
        if keys[pygame.K_RIGHT]:
            player.angle += ROT_SPEED * dt

        step = MOVE_SPEED * dt
        dir_x, dir_y = math.cos(player.angle), math.sin(player.angle)
        nx, ny = player.x, player.y
        if keys[pygame.K_UP]:
            nx += dir_x * step
            ny += dir_y * step
        if keys[pygame.K_DOWN]:
            nx -= dir_x * step
            ny -= dir_y * step

        if not escaped:
            nx, ny = resolve_collisions(nx, ny, walls["segs"])
        player.x, player.y = nx, ny

        if not escaped and player.y > exit_y + 0.15:
            escaped = True                           # walked out through the exit

        render_world(screen, walls, player)
        if show_map:
            draw_minimap(screen, walls, player)

        hud = font.render(
            "arrows: move/turn   TAB: map   ESC: quit", True, (230, 230, 230))
        screen.blit(hud, (10, SCREEN_HEIGHT - 26))
        if escaped:
            msg = font.render("You escaped the labyrinth!", True, (120, 255, 120))
            screen.blit(msg, (SCREEN_WIDTH // 2 - msg.get_width() // 2, 16))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()