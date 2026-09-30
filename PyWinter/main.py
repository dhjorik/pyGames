"""
PyWinter - 2D Platform Game Engine

A modular platform game engine built with Pygame featuring:
- Player character with physics-based movement
- Scrolling camera following the player
- Layered platforms and level design
- Collision detection and platformer mechanics
"""

import os

import pygame
from engine.game import main

class Resources:
    """Resource manager for game assets."""
    assets_path = os.path.join(os.path.dirname(__file__), 'assets')
    backgrounds = os.path.join(assets_path, 'backgrounds')
    images = os.path.join(assets_path, 'images')
    levels = os.path.join(assets_path, 'levels')
    sounds = os.path.join(assets_path, 'sounds')
    sprites = os.path.join(assets_path, 'sprites')
    
if __name__ == "__main__":
    main()
