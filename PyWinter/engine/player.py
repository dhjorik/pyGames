"""
Player character with physics, controls, and state management.
"""

import pygame
from .config import (
    PLAYER_WIDTH, PLAYER_HEIGHT, GRAVITY, PLAYER_JUMP_POWER,
    PLAYER_SPEED, PLAYER_MAX_FALL_SPEED, COLOR_BLUE
)


class Player(pygame.sprite.Sprite):
    """Player character with platformer physics."""
    
    def __init__(self, x, y):
        """
        Initialize player.
        
        Args:
            x: Starting X position
            y: Starting Y position
        """
        super().__init__()
        self.x = x
        self.y = y
        self.width = PLAYER_WIDTH
        self.height = PLAYER_HEIGHT
        
        # Velocity
        self.vx = 0
        self.vy = 0
        
        # State
        self.on_ground = False
        self.facing_right = True
        
        # Create rect for collision
        self.rect = pygame.Rect(self.x, self.y, self.width, self.height)
        self.image = pygame.Surface((self.width, self.height))
        self.image.fill(COLOR_BLUE)
    
    def handle_input(self, keys):
        """
        Process keyboard input for movement.
        
        Args:
            keys: pygame.key.get_pressed() result
        """
        self.vx = 0

        mult_x = 1
        mult_y = 1
        if keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]:
            mult_x = 1.5
            mult_y = 1.2

        if keys[pygame.K_a] or keys[pygame.K_LEFT]:
            self.vx = -PLAYER_SPEED * mult_x
            self.facing_right = False
        if keys[pygame.K_d] or keys[pygame.K_RIGHT]:
            self.vx = PLAYER_SPEED * mult_x
            self.facing_right = True
        
        # Jump
        if (keys[pygame.K_w] or keys[pygame.K_UP] or keys[pygame.K_SPACE]) and self.on_ground:
            self.vy = -PLAYER_JUMP_POWER * mult_y
            self.on_ground = False
    
    def update(self, platforms, level_width, level_height):
        """
        Update player physics and collision.
        
        Args:
            platforms: List of platform objects for collision
            level_width: Level width boundary
            level_height: Level height boundary
        """
        # Apply gravity
        self.vy += GRAVITY
        self.vy = min(self.vy, PLAYER_MAX_FALL_SPEED)
        
        # Update position
        self.x += self.vx
        self.y += self.vy
        
        # Boundary checks
        if self.x < 0:
            self.x = 0
        elif self.x + self.width > level_width:
            self.x = level_width - self.width
        
        # Death plane (fall off map)
        if self.y > level_height:
            self.respawn()
        
        # Update rect
        self.rect.x = self.x
        self.rect.y = self.y
        
        # Collision detection
        self.on_ground = False
        for platform in platforms:
            if self.rect.colliderect(platform.rect):
                self._resolve_collision(platform)
    
    def _resolve_collision(self, platform):
        """
        Resolve collision with platform.
        
        Args:
            platform: Platform object
        """
        # Only collide from top (landing on platform)
        if self.vy > 0:  # Falling
            if self.rect.bottom > platform.rect.top:
                self.y = platform.rect.top - self.height
                self.vy = 0
                self.on_ground = True
    
    def respawn(self):
        """Reset player to start position."""
        from .config import PLAYER_START_X, PLAYER_START_Y
        self.x = PLAYER_START_X
        self.y = PLAYER_START_Y
        self.vx = 0
        self.vy = 0
        self.on_ground = False
    
    def draw(self, surface, camera):
        """
        Draw player on screen.
        
        Args:
            surface: Pygame surface to draw on
            camera: Camera object for coordinate transformation
        """
        screen_x, screen_y = camera.apply(self.x, self.y)
        pygame.draw.rect(surface, COLOR_BLUE, (screen_x, screen_y, self.width, self.height))
        
        # Draw eyes for direction
        eye_y = screen_y + 15
        if self.facing_right:
            pygame.draw.circle(surface, (0, 0, 0), (int(screen_x + 22), int(eye_y)), 3)
        else:
            pygame.draw.circle(surface, (0, 0, 0), (int(screen_x + 10), int(eye_y)), 3)
