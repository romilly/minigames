"""The cave game in a web page: the browser's composition root.

The same core and adapters as on the desktop and the board (cave_core,
cave_mazes, cave_input, cave_screen, cave.Session), on the browser's pygame.
The loop awaits between frames, so the page keeps responding.
"""
import asyncio

import pygame

from cave import MAZE, SIZE, Session
from cave_core import Cave
from cave_mazes import maze_files

FPS = 30


async def run(maze_name: str = MAZE) -> None:
    """Play until the page closes. Esc (the pad's '-') starts again: a page
    has nowhere to quit to."""
    pygame.init()
    surface = pygame.display.set_mode(SIZE)
    font = pygame.font.Font(None, 24)
    while True:
        session = Session(Cave(maze_files().load(maze_name)), surface, font)
        while session.frame():
            await asyncio.sleep(1 / FPS)
