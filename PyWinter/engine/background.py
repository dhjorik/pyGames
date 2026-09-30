"""
Parallax scrolling background system with layered image support.

Handles loading and rendering background layers from image files with
automatic depth sorting and parallax scrolling based on layer metadata.
"""

import os
import re
import pygame
from .config import (
    SCREEN_WIDTH, SCREEN_HEIGHT, PLAYER_START_X, PLAYER_START_Y,
    BACKGROUND_FILL_COLOR, BACKGROUND_LAYER_ALPHA, DEFAULT_LAYER_ALPHA
)


class BackgroundLayer:
    """Single background layer with parallax scrolling support."""
    
    def __init__(self, image_path, layer_num, layer_type, level_width, level_height, layer_name=None):
        """
        Initialize a background layer.
        
        Args:
            image_path: Path to the layer image file
            layer_num: Layer number (e.g., 1 for layer01)
            layer_type: Type of layer ('fixed', 'back', 'front')
            level_width: Level width for tiling
            level_height: Level height for positioning
            layer_name: Full layer identifier (e.g., 'layer01_front') for alpha lookup
        """
        self.image = pygame.image.load(image_path).convert_alpha()
        self.layer_num = layer_num
        self.layer_type = layer_type
        self.layer_name = layer_name or f"layer{layer_num:02d}_{layer_type}"
        self.level_width = level_width
        self.level_height = level_height
        # No forced alpha: use PNG's own alpha channel
        
        # Calculate parallax speed based on layer type and number
        if layer_type == 'fixed':
            self.speed = 0.0  # No parallax
        else:
            # Back layers scroll slower (smaller numbers are slower)
            # Front layers scroll faster (reverse of back)
            if layer_type in ['back', 'final']:
                # Back layers: layer03 (close to player) scrolls faster than layer06
                # Normalize: layer03=max speed, layer06=slower
                self.speed = 0.3 + (7 - layer_num) * 0.05
            else:  # front
                # Front layers: layer01 (closest to camera) scrolls fastest
                # layer01=max speed, layer02=slower
                self.speed = 0.5 - (layer_num - 1) * 0.1
        
        self.width = self.image.get_width()
        self.height = self.image.get_height()
        self.y = level_height - self.height
    
    def get_depth_key(self):
        """
        Get sort key for depth ordering (bottom to top).
        
        Returns:
            Tuple for sorting (lower = renders first/bottom)
        """
        # Order: fixed (0), back layers (1), front layers (2), final layers (3)
        type_order = {'fixed': 0, 'back': 1, 'front': 2, 'final': 3}
        base_order = type_order[self.layer_type]
        
        # Within same type, sort by layer number
        if self.layer_type == 'fixed':
            return (base_order, 0)  # Fixed layers render in order
        elif self.layer_type == 'back':
            # Back layers: higher layer num = lower (rendered first)
            return (base_order, -self.layer_num)
        elif self.layer_type == 'final':
            # Final layers: higher layer num = lower (rendered first)
            return (base_order, -self.layer_num)
        elif self.layer_type == 'front':
            # Front layers: higher layer num = lower (rendered first)
            return (base_order, -self.layer_num)
    
    def draw(self, surface, camera_x, camera_y):
        """
        Draw the layer with parallax offset (PNG alpha preserved).
        
        Args:
            surface: Pygame surface to draw on
            camera_x: Current camera X position
            camera_y: Current camera Y position
        """
        # Apply parallax: offset is reduced by speed factor
        parallax_offset_x = camera_x * self.speed
        screen_x = -parallax_offset_x
        screen_y = self.y - camera_y
        
        # Handle horizontal tiling
        current_x = screen_x
        while current_x < SCREEN_WIDTH:
            surface.blit(self.image, (int(current_x), int(screen_y)))
            current_x += self.width

class ParallaxBackground:
    """Manages all background layers with parallax scrolling."""
    
    def __init__(self, backgrounds_path, level_width, level_height):
        """
        Initialize parallax background system.
        
        Args:
            backgrounds_path: Path to background layers folder
            level_width: Total level width
            level_height: Total level height
        """
        self.backgrounds_path = backgrounds_path
        self.level_width = level_width
        self.level_height = level_height
        
        self.fixed_layers = []
        self.back_layers = []
        self.front_layers = []
        self.final_layers = []
        
        self._load_layers()
    
    def _load_layers(self):
        """Load and organize all layers from the backgrounds folder."""
        if not os.path.exists(self.backgrounds_path):
            print(f"Warning: Backgrounds path not found: {self.backgrounds_path}")
            return
        
        # Collect all layer images
        layer_dict = {}
        
        for filename in sorted(os.listdir(self.backgrounds_path)):
            if not filename.endswith('.png'):
                continue
            
            # Parse layer metadata from filename
            # Expected format: layer{num}_{type}.png (e.g., layer01_back.png)
            match = re.match(r'layer(\d+)_(fixed|back|front|final)\.png', filename)
            if not match:
                continue
            
            layer_num = int(match.group(1))
            layer_type = match.group(2)
            layer_name = filename.replace('.png', '')  # e.g., 'layer01_back'
            
            image_path = os.path.join(self.backgrounds_path, filename)
            layer = BackgroundLayer(image_path, layer_num, layer_type, 
                                   self.level_width, self.level_height, layer_name)
            
            # Store by type
            if layer_type == 'fixed':
                self.fixed_layers.append(layer)
            # if layer_type == 'back':
            if layer_type == 'back':
                self.back_layers.append(layer)
            if layer_type == 'front':
                self.front_layers.append(layer)
            if layer_type == 'final':
                self.final_layers.append(layer)
        
        # Sort each group by layer number for proper rendering
        self.fixed_layers.sort(key=lambda l: l.layer_num)
        self.back_layers.sort(key=lambda l: l.layer_num, reverse=True)
        self.front_layers.sort(key=lambda l: l.layer_num, reverse=True)
        self.final_layers.sort(key=lambda l: l.layer_num, reverse=True)
        
        print('Fixed:', len(self.fixed_layers), [layer.speed for layer in self.fixed_layers])
        print('Back:', len(self.back_layers), [layer.speed for layer in self.back_layers])
        print('Front:', len(self.front_layers), [layer.speed for layer in self.front_layers])
        print('Final:', len(self.final_layers), [layer.speed for layer in self.final_layers])

    def draw_back(self, surface, camera_x, camera_y):
        """
        Draw background layers behind the player.
        
        Args:
            surface: Pygame surface to draw on
            camera_x: Current camera X position
            camera_y: Current camera Y position
        """
        # Draw fixed layers first (bottom)
        for layer in self.fixed_layers:
            layer.draw(surface, camera_x, camera_y)
        
        # Draw back parallax layers
        # if camera_x > self.final_trigger:  # Only draw back layers if camera has moved
        #     for layer in self.final_layers:
        #         layer.draw(surface, camera_x, camera_y)
        # else:
        #     for layer in self.back_layers:
        #         layer.draw(surface, camera_x, camera_y)
        for layer in self.back_layers:
            layer.draw(surface, camera_x, camera_y)

    def draw_front(self, surface, camera_x, camera_y):
        """
        Draw background layers in front of the player.
        
        Args:
            surface: Pygame surface to draw on
            camera_x: Current camera X position
            camera_y: Current camera Y position
        """
        for layer in self.front_layers:
            layer.draw(surface, camera_x, camera_y)
