"""Cave: find your way through a maze, seen in first person.

From the top: a toolbar with the name of where you are, a map of what you've
seen so far, a description, and a strip at the bottom with the view ahead.

Touch the view to step forward, and the arrows either side of it to turn.
The button at the left of the toolbar opens a menu of what you can do: take
or drop things, or see what you're carrying. Find treasure and escape with it. On the pad (or the desktop's keyboard or mouse):
L and R turn, U steps forward, D turns round; A opens the menu, U and D
choose, A does it and B closes it. '-' (Esc) quits.
When you reach the goal, any move starts again.

Mazes live in mazes/<name>.yaml (see mazes/mine.yaml); cave_mazes.py loads
them, or the JSON copies deploy.sh puts on the board.
"""
import pygame
from tones import tone

from cave_core import Cave, Kind, STEPS, DOWN, DOOR
from cave_input import Controls, Menu
from cave_layout import Layout, DESCRIPTION_LINES
from cave_mazes import maze_files

MAZE = 'mine'


SIZE = (240, 240)       # the desktop window: the Presto's shape
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (150, 150, 150)
TOOLBAR = (30, 40, 70)
ARROW = (110, 110, 140)
ROCK = (150, 150, 180)
FLOOR = (50, 100, 50)
ROOM = (70, 140, 140)
GOAL = (200, 180, 40)
TREASURE_GLINT = (255, 215, 60)
DOOR_COLOUR = (140, 90, 40)
DOOR_OPEN = (110, 80, 50)
MENU_BG = (20, 25, 45)
MENU_SELECTED = (60, 70, 120)
STAIRS_DOWN = (90, 60, 120)
STAIRS_UP = (170, 140, 200)
PLAYER = (240, 80, 80)
CEILING = (20, 20, 30)
GROUND = (50, 40, 30)
EDGE = (30, 30, 40)
MAP_COLOURS = {Kind.ROCK: ROCK, Kind.PASSAGE: FLOOR, Kind.ROOM: ROOM, Kind.GOAL: GOAL,
               Kind.DOWN: STAIRS_DOWN, Kind.UP: STAIRS_UP,
               Kind.DOOR: DOOR_COLOUR, Kind.OPEN_DOOR: DOOR_OPEN}
MAX_CELL = 12

def surface(blocked: str | None) -> tuple[int, int, int]:
    """The colour of what blocks the way: rock, or a locked door."""
    return DOOR_COLOUR if blocked == DOOR else ROCK


def shade(colour: tuple[int, int, int], depth: float) -> tuple[int, int, int]:
    k = 1 - 0.17 * depth
    return (int(colour[0] * k), int(colour[1] * k), int(colour[2] * k))


def face(screen: "pygame.Surface", colour: tuple[int, int, int], points: list[tuple[int, int]]) -> None:
    pygame.draw.polygon(screen, colour, points)
    for i in range(len(points)):
        pygame.draw.line(screen, EDGE, points[i], points[(i + 1) % len(points)])


def draw_view(screen: "pygame.Surface", game: Cave, layout: Layout) -> None:
    x, w, top, h = layout.view_x, layout.view_w, layout.view_y, layout.view_h
    pygame.draw.rect(screen, CEILING, (x, top, w, h // 2))
    pygame.draw.rect(screen, GROUND, (x, top + h // 2, w, h - h // 2))
    view = game.view()
    last = len(view) - 1
    if not view[last][2]:                        # no wall in sight: darkness
        x0, y0, x1, y1 = layout.frame(last + 1)
        pygame.draw.rect(screen, BLACK, (x0, y0, x1 - x0, y1 - y0))
    for depth, kind in game.steps_in_view():
        draw_steps(screen, layout, depth, kind)
    for depth in game.objects_in_view():
        draw_glint(screen, layout, depth)
    for depth in range(last, -1, -1):            # far to near
        left, right, ahead = view[depth]
        x0, y0, x1, y1 = layout.frame(depth)
        a0, b0, a1, b1 = layout.frame(depth + 1)
        if ahead:
            face(screen, shade(surface(ahead), depth + 1),
                 [(a0, b0), (a1, b0), (a1, b1), (a0, b1)])
            if ahead == DOOR:                    # a keyhole
                kx, ky = (a0 + a1) // 2, (b0 + b1) // 2
                r = max(1, (a1 - a0) // 16)
                pygame.draw.rect(screen, EDGE, (kx - r, ky - r, 2 * r, 3 * r))
        for wall, outer, inner in ((left, x0, a0), (right, x1, a1)):
            if wall:
                face(screen, shade(surface(wall), depth + 0.5),
                     [(outer, y0), (inner, b0), (inner, b1), (outer, y1)])
            else:                                # an opening: the far wall of a side passage
                face(screen, shade(ROCK, depth + 1),
                     [(outer, b0), (inner, b0), (inner, b1), (outer, b1)])


def draw_steps(screen: "pygame.Surface", layout: Layout, depth: int, kind: str) -> None:
    """Steps on the floor of the cell at depth: dark going down, pale going up."""
    x0, y0, x1, y1 = layout.frame(depth)
    a0, b0, a1, b1 = layout.frame(depth + 1)
    colour = STAIRS_DOWN if kind == DOWN else STAIRS_UP
    pygame.draw.polygon(screen, shade(colour, depth), [(x0, y1), (x1, y1), (a1, b1), (a0, b1)])
    for i in (1, 2, 3):
        t = i / 4
        y = y1 + (b1 - y1) * t
        pygame.draw.line(screen, EDGE, (x0 + (a0 - x0) * t, y), (x1 + (a1 - x1) * t, y))


def draw_glint(screen: "pygame.Surface", layout: Layout, depth: int) -> None:
    """Something lying on the floor of the cell at depth: a small gold diamond."""
    x0, y0, x1, y1 = layout.frame(depth)
    a0, b0, a1, b1 = layout.frame(depth + 1)
    cx, cy = (x0 + x1) // 2, (y1 + b1) // 2
    r = max(2, (x1 - x0) // 24)
    pygame.draw.polygon(screen, shade(TREASURE_GLINT, depth),
                        [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])


def draw_map(screen: "pygame.Surface", game: Cave, layout: Layout) -> None:
    maze = game.maze
    cell = min(MAX_CELL, layout.width // maze.width, layout.map_h // maze.height)
    cell = max(cell, 4)
    px, py = game.position
    if cell * maze.width <= layout.width and cell * maze.height <= layout.map_h:
        ox = (layout.width - cell * maze.width) // 2
        oy = layout.map_y + (layout.map_h - cell * maze.height) // 2
    else:                                        # too big: keep the player in the middle
        ox = layout.width // 2 - px * cell - cell // 2
        oy = layout.map_y + layout.map_h // 2 - py * cell - cell // 2
    for (x, y, kind, something_here) in game.map_cells():
        sx, sy = ox + x * cell, oy + y * cell
        if sx < 0 or sy < layout.map_y or sx + cell > layout.width or \
                sy + cell > layout.map_y + layout.map_h:
            continue
        pygame.draw.rect(screen, MAP_COLOURS[kind], (sx, sy, cell - 1, cell - 1))
        if something_here and cell >= 6:
            pygame.draw.rect(screen, TREASURE_GLINT,
                             (sx + cell // 2 - 2, sy + cell // 2 - 2, 3, 3))
    cx, cy = ox + px * cell + cell // 2, oy + py * cell + cell // 2
    dx, dy = STEPS[game.facing]
    r = max(2, cell // 2 - 1)
    pygame.draw.polygon(screen, PLAYER, [
        (cx + dx * r, cy + dy * r),
        (cx - dy * r - dx * r, cy + dx * r - dy * r),
        (cx + dy * r - dx * r, cy - dx * r - dy * r)])


def wrap(font: "pygame.font.Font", text: str, max_width: int) -> list[str]:
    """Split text into lines that fit max_width."""
    lines, line = [], ''
    for word in text.split():
        trial = word if not line else line + ' ' + word
        if font.size(trial)[0] <= max_width or not line:
            line = trial
        else:
            lines.append(line)
            line = word
    if line:
        lines.append(line)
    return lines


def draw_arrows(screen: "pygame.Surface", layout: Layout) -> None:
    """Turn arrows in the spaces either side of the view."""
    side = layout.view_x
    if side < 12:
        return
    cy = layout.view_y + layout.view_h // 2
    r = min(side, layout.view_h) // 4
    for cx, d in ((side // 2, -1), (layout.width - side // 2, 1)):
        pygame.draw.polygon(screen, ARROW, [(cx + d * r, cy), (cx - d * r, cy - r),
                                            (cx - d * r, cy + r)])


def draw_toolbar(screen: "pygame.Surface", game: Cave, layout: Layout, font: "pygame.font.Font") -> None:
    h = layout.toolbar_h
    pygame.draw.rect(screen, TOOLBAR, (0, 0, layout.width, h))
    for i in (1, 2, 3):                        # the menu button
        pygame.draw.rect(screen, WHITE, (h // 5, i * h // 4 - 1, h * 3 // 5, 2))
    if game.won:
        title = 'You made it!'
    else:
        title = game.room_name() or game.maze.title
    screen.blit(font.render(title, False, WHITE), (h + 2, 2))
    if len(game.maze.levels) > 1:
        label = font.render('L%d' % (game.level + 1), False, GREY)
        screen.blit(label, label.get_rect(right=layout.width - 4, top=2))


def draw_text(screen: "pygame.Surface", game: Cave, layout: Layout, font: "pygame.font.Font") -> None:
    """The description, or a message after an action; and what's lying here."""
    x, y, width = 4, layout.text_y, layout.width - 8
    here = game.objects_here()
    here_lines = []
    if here and not game.won:
        here_lines = wrap(font, 'Here: ' + ', '.join(game.name_of(t) for t in here),
                          width)[:1]
    if game.message:
        text, colour = game.message, WHITE
    else:
        text, colour = game.description(), GREY
        if game.won:
            text += ' Touch to play again.'
    for line in wrap(font, text, width)[:DESCRIPTION_LINES - len(here_lines)]:
        screen.blit(font.render(line, False, colour), (x, y))
        y += layout.line_height
    for line in here_lines:
        screen.blit(font.render(line, False, TREASURE_GLINT), (x, y))
        y += layout.line_height


def draw_menu(screen: "pygame.Surface", menu: Menu, layout: Layout, font: "pygame.font.Font") -> None:
    top = layout.menu_y
    bottom = layout.menu_y + len(menu.items) * layout.menu_row_h
    pygame.draw.rect(screen, MENU_BG, (0, top, layout.width, bottom - top))
    for i, (label, command) in enumerate(menu.items):
        x, y, w, h = layout.menu_item_rect(i)
        if i == menu.selected:
            pygame.draw.rect(screen, MENU_SELECTED, (x, y, w, h))
        screen.blit(font.render(label, False, WHITE), (x + 8, y + 3))
        pygame.draw.line(screen, EDGE, (x, y + h - 1), (x + w - 1, y + h - 1))


def draw(screen: "pygame.Surface", game: Cave, layout: Layout, font: "pygame.font.Font", menu: Menu) -> None:
    screen.fill(BLACK)
    draw_toolbar(screen, game, layout, font)
    draw_map(screen, game, layout)
    draw_text(screen, game, layout, font)
    draw_view(screen, game, layout)
    draw_arrows(screen, layout)
    if menu.is_open:
        draw_menu(screen, menu, layout, font)


def main(maze_name: str = MAZE) -> Cave:
    """Play a maze from mazes/ (or its JSON copy on the board). What run.sh calls."""
    return play(Cave(maze_files().load(maze_name)))


def play(game: Cave, fps: int = 30, size: tuple[int, int] = SIZE) -> Cave:
    """Run the game until Esc (the pad's '-') or the window closes; return it."""
    pygame.init()
    screen = pygame.display.set_mode(size, getattr(pygame, 'SCALED', 0))
    font = pygame.font.Font(None, 24)     # scale 2 on the board, like the scores
    layout = Layout(*screen.get_size(), line_height=font.size('Ag')[1])
    clock = pygame.time.Clock()
    sounds = {'step': tone(600, 20), 'steps': tone(330, 150), 'turn': tone(900, 10),
              'bump': tone(120, 60), 'win': tone(1320, 400), 'new': tone(660, 50),
              'menu': tone(800, 15), 'take': tone(1000, 60), 'drop': tone(500, 60),
              'locked': tone(150, 80), 'unlock': tone(1200, 120)}
    menu = Menu()
    controls = Controls(game, menu, layout)
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
            draw(screen, game, layout, font, menu)
            dirty = False
        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()
    return game


if __name__ == '__main__':
    main()
