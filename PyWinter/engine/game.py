"""
Main game engine and event loop.
"""

import sys
import os
import pygame
from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, FPS, TITLE,
    COLOR_BLACK, COLOR_WHITE, PLAYER_START_X, PLAYER_START_Y,
    BACKGROUND_FILL_COLOR
)
from .camera import Camera
from .player import Player
from .platforms import Level
from .background import ParallaxBackground


class Game:
    """Main game engine."""
    
    def __init__(self):
        """Initialize game engine."""
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))

        pygame.display.set_caption(TITLE)
        self.clock = pygame.time.Clock()
        self.running = True
        
        # Game objects
        # self.level = Level(3200, 2400)
        self.level = Level(SCREEN_WIDTH * 50, SCREEN_HEIGHT)

        self.player = Player(PLAYER_START_X, PLAYER_START_Y)
        self.camera = Camera(self.level.level_width, self.level.level_height)
        
        self.buffer = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA, 32)
        
        # Background
        backgrounds_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            'assets', 'backgrounds', 'class002', 'layers'
        )
        self.background = ParallaxBackground(backgrounds_path, 
                                            self.level.level_width, 
                                            self.level.level_height)

        # UI
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 24)
    
    def handle_events(self):
        """Process input events."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
    
    def update(self):
        """Update game logic."""
        # Get input
        keys = pygame.key.get_pressed()
        self.player.handle_input(keys)
        
        # Update physics
        self.player.update(self.level.platforms, self.level.level_width, self.level.level_height)
        self.level.update()
        
        # Update camera
        self.camera.update(self.player)
    
    def draw(self):
        """Render frame."""
        self.buffer.fill(BACKGROUND_FILL_COLOR)
        
        # Draw background layers behind player
        self.background.draw_back(self.buffer, self.camera.x, self.camera.y)
        # self.background.draw_back(self.buffer, 0, 0)
        
        # Draw level
        self.level.draw(self.buffer, self.camera)
        
        # Draw player
        self.player.draw(self.buffer, self.camera)
        
        # Draw background layers in front of player
        # self.background.draw_front(self.buffer, self.camera.x, self.camera.y)
        self.background.draw_front(self.buffer, 0, 0)
        
        # Draw UI
        self._draw_ui(self.buffer)
        
        self.screen.blit(self.buffer, (0, 0))

        pygame.display.flip()
    
    def _draw_ui(self, surface):
        """Draw user interface elements."""
        # Position info
        pos_text = self.small_font.render(
            f"Pos: {int(self.player.x)}, {int(self.player.y)} | Vel: {self.player.vx:.1f}, {self.player.vy:.1f}",
            True, COLOR_WHITE
        )
        surface.blit(pos_text, (10, 10))
        pos_text = self.small_font.render(
            f"Camera: {int(self.camera.x)}, {int(self.camera.y)}",
            True, COLOR_WHITE
        )
        surface.blit(pos_text, (10, 40))
        
        # Controls info
        controls_text = self.small_font.render(
            "A/D or Arrows: Move | W/Space: Jump | ESC: Quit",
            True, COLOR_WHITE
        )
        surface.blit(controls_text, (10, 70))
        
        # FPS
        fps_text = self.small_font.render(
            f"FPS: {int(self.clock.get_fps())}",
            True, COLOR_WHITE
        )
        surface.blit(fps_text, (SCREEN_WIDTH - 150, 10))
    
    def run(self):
        """Main game loop."""
        while self.running:
            self.handle_events()
            self.update()
            self.draw()
            self.clock.tick(FPS)
        
        pygame.quit()
        sys.exit()


def main():
    """Entry point."""
    game = Game()
    game.run()
