"""
Platform and level elements system.
"""

import pygame
from .config import COLOR_BROWN, COLOR_GREEN, COLOR_SKY


class Platform(pygame.sprite.Sprite):
    """Static platform element for the level."""
    
    def __init__(self, x, y, width, height, color=COLOR_BROWN):
        """
        Initialize platform.
        
        Args:
            x: X position
            y: Y position
            width: Platform width
            height: Platform height
            color: RGB color tuple
        """
        super().__init__()
        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.color = color
        
        self.rect = pygame.Rect(x, y, width, height)
        self.image = pygame.Surface((width, height))
        self.image.fill(color)
    
    def draw(self, surface, camera):
        """
        Draw platform on screen.
        
        Args:
            surface: Pygame surface to draw on
            camera: Camera object for coordinate transformation
        """
        if camera.is_visible(self.x, self.y, self.width, self.height):
            screen_x, screen_y = camera.apply(self.x, self.y)
            pygame.draw.rect(surface, self.color, (screen_x, screen_y, self.width, self.height))


class Background(pygame.sprite.Sprite):
    """Parallax scrolling background."""
    
    def __init__(self, level_width, level_height):
        """
        Initialize background.
        
        Args:
            level_width: Level width for tiling
            level_height: Level height
        """
        super().__init__()
        self.level_width = level_width
        self.level_height = level_height
    
    def draw(self, surface, camera):
        """
        Draw parallax background.
        
        Args:
            surface: Pygame surface to draw on
            camera: Camera object for coordinate transformation
        """
        return # Background drawing is handled by ParallaxBackground class
        # Draw sky gradient effect
        for y in range(int(camera.y), int(camera.y + surface.get_height()) + 32, 32):
            color_value = max(0, min(255, 180 - int((y / self.level_height) * 80)))
            pygame.draw.line(
                surface,
                (100, color_value, 200),
                (0, y - int(camera.y)),
                (surface.get_width(), y - int(camera.y)),
                2
            )


class Level:
    """Manages all level platforms and elements."""
    
    def __init__(self, level_width=3200, level_height=2400):
        """
        Initialize level.
        
        Args:
            level_width: Total level width
            level_height: Total level height
        """
        self.level_width = level_width
        self.level_height = level_height
        self.platforms = []
        self.background = Background(level_width, level_height)
        self._create_level()
    
    def _create_level(self):
        """Create the test level layout."""
        # Ground
        # self.platforms.append(Platform(0, 700, 3200, 100, COLOR_GREEN))
        platform_y = self.level_height - 50
        self.platforms.append(Platform(0, platform_y, self.level_width, 40, COLOR_GREEN))
        
        # Platform stairs going right
        for i in range(0, 10):
            x = 300 + i * 150
            y = platform_y - 100 - i * 60
            self.platforms.append(Platform(x, y, 120, 20, COLOR_BROWN))
        
        # Upper platform section
        self.platforms.append(Platform(1800, platform_y - 300 , 300, 20, COLOR_BROWN))
        
        # Jump section
        for i in range(0, 8):
            x = 2200 + i * 100
            y = platform_y - 350 - i * 50
            self.platforms.append(Platform(x, y, 80, 20, COLOR_GREEN))
        
        # Final platform
        self.platforms.append(Platform(2900, platform_y - 200, 200, 20, COLOR_BROWN))
    
    def update(self):
        """Update level logic."""
        pass
    
    def draw(self, surface, camera):
        """
        Draw entire level.
        
        Args:
            surface: Pygame surface to draw on
            camera: Camera object for coordinate transformation
        """
        # Draw background
        self.background.draw(surface, camera)
        
        # Draw all platforms
        for platform in self.platforms:
            platform.draw(surface, camera)
