"""
Camera system for scrolling and viewport management.

The camera follows the player and provides smooth scrolling across levels.
"""

from .config import CAMERA_FOLLOW_SPEED, CAMERA_OFFSET_X, SCREEN_WIDTH, SCREEN_HEIGHT


class Camera:
    """Handles viewport scrolling and object positioning relative to camera."""
    
    def __init__(self, level_width, level_height):
        """
        Initialize camera.
        
        Args:
            level_width: Total width of the level
            level_height: Total height of the level
        """
        self.x = 0
        self.y = 0
        self.level_width = level_width
        self.level_height = level_height
        self.target_x = 0
        self.target_y = 0
    
    def update(self, player):
        """
        Update camera position to follow player.
        
        Args:
            player: Player object with x, y attributes
        """
        # Calculate target position - keep player at offset from left
        self.target_x = player.x - CAMERA_OFFSET_X
        self.target_y = player.y - SCREEN_HEIGHT // 3
        
        # Smooth camera movement
        self.x += (self.target_x - self.x) * CAMERA_FOLLOW_SPEED
        self.y += (self.target_y - self.y) * CAMERA_FOLLOW_SPEED
        
        # Clamp camera to level boundaries
        self.x = max(0, min(self.x, self.level_width - SCREEN_WIDTH))
        self.y = max(0, min(self.y, self.level_height - SCREEN_HEIGHT))
    
    def apply(self, x, y):
        """
        Convert world coordinates to screen coordinates.
        
        Args:
            x: World X position
            y: World Y position
            
        Returns:
            Tuple of (screen_x, screen_y)
        """
        screen_x = x - self.x
        screen_y = y - self.y
        return screen_x, screen_y
    
    def is_visible(self, x, y, width, height):
        """
        Check if object is within camera view.
        
        Args:
            x, y: Object world position
            width, height: Object dimensions
            
        Returns:
            True if object should be rendered
        """
        return (x + width > self.x and 
                x < self.x + SCREEN_WIDTH and
                y + height > self.y and
                y < self.y + SCREEN_HEIGHT)
