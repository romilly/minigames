"""Cave: find your way through a maze, seen in first person.

From the top: a toolbar with the name of where you are, a map of what you've
seen so far, a description, and a strip at the bottom with the view ahead.

Touch the view to step forward, and the arrows either side of it to turn.
The button at the left of the toolbar opens a menu of what you can do: take
or drop things, or see what you're carrying. Find treasure and escape with it.

On the pad (or the desktop's keyboard or mouse): L and R turn, U steps
forward, D turns round; A opens the menu, U and D choose, A does it and B
closes it. '-' (Esc) quits.
When you reach the goal, any move starts again.

Mazes live in mazes/<name>.yaml (see mazes/mine.yaml); cave_mazes.py loads
them, or the JSON copies deploy.sh puts on the board.

This module is the composition root: it builds the core and its adapters
(cave_mazes, cave_input, cave_layout, cave_screen) and runs the loop.
"""
import pygame
from tones import tone

from cave_core import Cave
from cave_input import Controls, Menu
from cave_layout import Layout
from cave_mazes import maze_files
from cave_screen import Screen

MAZE = 'mine'
SIZE = (240, 240)       # the desktop window: the Presto's shape


def main(maze_name: str = MAZE) -> Cave:
    """Play a maze from mazes/ (or its JSON copy on the board). What run.sh calls."""
    return play(Cave(maze_files().load(maze_name)))


def play(game: Cave, fps: int = 30, size: tuple[int, int] = SIZE) -> Cave:
    """Run the game until Esc (the pad's '-') or the window closes; return it."""
    pygame.init()
    surface = pygame.display.set_mode(size, getattr(pygame, 'SCALED', 0))
    font = pygame.font.Font(None, 24)     # scale 2 on the board, like the scores
    layout = Layout(*surface.get_size(), line_height=font.size('Ag')[1])
    clock = pygame.time.Clock()
    sounds = {'step': tone(600, 20), 'steps': tone(330, 150), 'turn': tone(900, 10),
              'bump': tone(120, 60), 'win': tone(1320, 400), 'new': tone(660, 50),
              'menu': tone(800, 15), 'take': tone(1000, 60), 'drop': tone(500, 60),
              'locked': tone(150, 80), 'unlock': tone(1200, 120)}
    menu = Menu()
    controls = Controls(game, menu, layout)
    screen = Screen(surface, font, layout)
    running, dirty = True, True
    while running:
        happened = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                happened += controls.handle(event)
                dirty = True
        for what in happened:
            sounds[what].play()
        if dirty:
            screen.draw(game, menu)
            dirty = False
        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()
    return game


if __name__ == '__main__':
    main()
