"""The cave game's screen: the drawing adapter.

From the top: a toolbar with the name of where you are, a map of what you've
seen so far, a description, and a strip at the bottom with the adventurer's
stats on the left and the view ahead on the right, marked with faint chevrons
where a tap turns. An open menu covers the map and description.
"""
import pygame

from cave_core import Cave, Kind, STEPS, DOWN, DOOR
from cave_input import Menu
from cave_layout import Layout, DESCRIPTION_LINES

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (150, 150, 150)
TOOLBAR = (30, 40, 70)
PANEL = (20, 25, 45)
CHEVRON = (205, 205, 225)
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
MAX_CELL = 12           # largest map cell, in pixels


def surface_colour(blocked: str | None) -> tuple[int, int, int]:
    """The colour of what blocks the way: rock, or a locked door."""
    return DOOR_COLOUR if blocked == DOOR else ROCK


def shade(colour: tuple[int, int, int], depth: float) -> tuple[int, int, int]:
    """Darker with distance."""
    k = 1 - 0.17 * depth
    return (int(colour[0] * k), int(colour[1] * k), int(colour[2] * k))


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


def chevron_size(layout: Layout) -> int:
    return max(3, (layout.floor_y - layout.view_y) // 6)


def chevron_tips(layout: Layout) -> tuple[tuple[int, int], tuple[int, int], tuple[int, int]]:
    """Where the turn-left, turn-right and turn-round chevrons point."""
    r = chevron_size(layout)
    cy = (layout.view_y + layout.floor_y) // 2
    left = (layout.view_x + r // 2 + 2, cy)
    right = (layout.width - r // 2 - 3, cy)
    floor_h = layout.view_y + layout.view_h - layout.floor_y
    middle = (layout.view_x + layout.view_w // 2, layout.floor_y + (floor_h + r) // 2)
    return left, right, middle


class Screen:
    """Draws the game, and the menu when it's open, onto a surface."""

    def __init__(self, surface: "pygame.Surface", font: "pygame.font.Font",
                 layout: Layout) -> None:
        self.surface = surface
        self.font = font
        self.layout = layout

    def draw(self, game: Cave, menu: Menu) -> None:
        self.surface.fill(BLACK)
        self._toolbar(game)
        self._map(game)
        self._text(game)
        self._stats(game)
        self._view(game)
        self._chevrons()
        if menu.is_open:
            self._menu(menu)

    # ---- The parts of the screen ----

    def _toolbar(self, game: Cave) -> None:
        layout, font = self.layout, self.font
        h = layout.toolbar_h
        pygame.draw.rect(self.surface, TOOLBAR, (0, 0, layout.width, h))
        for i in (1, 2, 3):                        # the menu button
            pygame.draw.rect(self.surface, WHITE, (h // 5, i * h // 4 - 1, h * 3 // 5, 2))
        if game.won:
            title = 'You made it!'
        else:
            title = game.room_name() or game.maze.title
        self.surface.blit(font.render(title, False, WHITE), (h + 2, 2))
        if len(game.maze.levels) > 1:
            label = font.render('L%d' % (game.level + 1), False, GREY)
            self.surface.blit(label, label.get_rect(right=layout.width - 4, top=2))

    def _map(self, game: Cave) -> None:
        layout, screen = self.layout, self.surface
        maze = game.maze
        cell = min(MAX_CELL, layout.width // maze.width, layout.map_h // maze.height)
        cell = max(cell, 4)
        px, py = game.position
        if cell * maze.width <= layout.width and cell * maze.height <= layout.map_h:
            ox = (layout.width - cell * maze.width) // 2
            oy = layout.map_y + (layout.map_h - cell * maze.height) // 2
        else:                                      # too big: keep the player in the middle
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

    def _text(self, game: Cave) -> None:
        """The description, or a message after an action; and what's lying here."""
        layout, font = self.layout, self.font
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
            self.surface.blit(font.render(line, False, colour), (x, y))
            y += layout.line_height
        for line in here_lines:
            self.surface.blit(font.render(line, False, TREASURE_GLINT), (x, y))
            y += layout.line_height

    def _view(self, game: Cave) -> None:
        layout, screen = self.layout, self.surface
        x, w, top, h = layout.view_x, layout.view_w, layout.view_y, layout.view_h
        pygame.draw.rect(screen, CEILING, (x, top, w, h // 2))
        pygame.draw.rect(screen, GROUND, (x, top + h // 2, w, h - h // 2))
        view = game.view()
        last = len(view) - 1
        if not view[last][2]:                      # no wall in sight: darkness
            x0, y0, x1, y1 = layout.frame(last + 1)
            pygame.draw.rect(screen, BLACK, (x0, y0, x1 - x0, y1 - y0))
        for depth, kind in game.steps_in_view():
            self._steps(depth, kind)
        for depth in game.objects_in_view():
            self._glint(depth)
        for depth in range(last, -1, -1):          # far to near
            left, right, ahead = view[depth]
            x0, y0, x1, y1 = layout.frame(depth)
            a0, b0, a1, b1 = layout.frame(depth + 1)
            if ahead:
                self._face(shade(surface_colour(ahead), depth + 1),
                           [(a0, b0), (a1, b0), (a1, b1), (a0, b1)])
                if ahead == DOOR:                  # a keyhole
                    kx, ky = (a0 + a1) // 2, (b0 + b1) // 2
                    r = max(1, (a1 - a0) // 16)
                    pygame.draw.rect(screen, EDGE, (kx - r, ky - r, 2 * r, 3 * r))
            for wall, outer, inner in ((left, x0, a0), (right, x1, a1)):
                if wall:
                    self._face(shade(surface_colour(wall), depth + 0.5),
                               [(outer, y0), (inner, b0), (inner, b1), (outer, y1)])
                else:                              # an opening: the far wall of a side passage
                    self._face(shade(ROCK, depth + 1),
                               [(outer, b0), (inner, b0), (inner, b1), (outer, b1)])

    def _steps(self, depth: int, kind: str) -> None:
        """Steps on the floor of the cell at depth: dark going down, pale going up."""
        x0, y0, x1, y1 = self.layout.frame(depth)
        a0, b0, a1, b1 = self.layout.frame(depth + 1)
        colour = STAIRS_DOWN if kind == DOWN else STAIRS_UP
        pygame.draw.polygon(self.surface, shade(colour, depth),
                            [(x0, y1), (x1, y1), (a1, b1), (a0, b1)])
        for i in (1, 2, 3):
            t = i / 4
            y = y1 + (b1 - y1) * t
            pygame.draw.line(self.surface, EDGE, (x0 + (a0 - x0) * t, y),
                             (x1 + (a1 - x1) * t, y))

    def _glint(self, depth: int) -> None:
        """Something lying on the floor of the cell at depth: a small gold diamond."""
        x0, y0, x1, y1 = self.layout.frame(depth)
        a0, b0, a1, b1 = self.layout.frame(depth + 1)
        cx, cy = (x0 + x1) // 2, (y1 + b1) // 2
        r = max(2, (x1 - x0) // 24)
        pygame.draw.polygon(self.surface, shade(TREASURE_GLINT, depth),
                            [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])

    def _face(self, colour: tuple[int, int, int], points: list[tuple[int, int]]) -> None:
        pygame.draw.polygon(self.surface, colour, points)
        for i in range(len(points)):
            pygame.draw.line(self.surface, EDGE, points[i], points[(i + 1) % len(points)])

    def _stats(self, game: Cave) -> None:
        """How the adventurer is doing: one label and value a line."""
        layout, font = self.layout, self.font
        x, y, w, h = layout.stats_x, layout.stats_y, layout.stats_w, layout.stats_h
        pygame.draw.rect(self.surface, PANEL, (x, y, w, h))
        lines = max(1, h // layout.line_height)
        top = y + (h - min(lines, len(game.stats())) * layout.line_height) // 2
        for label, value in game.stats()[:lines]:
            self.surface.blit(font.render(label, False, GREY), (x + 4, top))
            shown = font.render(value, False, WHITE)
            self.surface.blit(shown, shown.get_rect(right=x + w - 4, top=top))
            top += layout.line_height

    def _chevrons(self) -> None:
        """Faint marks where a tap on the view turns: left, right and round."""
        (lx, ly), (rx, ry), (fx, fy) = chevron_tips(self.layout)
        r = chevron_size(self.layout)
        for dx in (0, 1):                          # two pixels thick
            self._chevron((lx + dx, ly), (r, -r), (r, r))
            self._chevron((rx - dx, ry), (-r, -r), (-r, r))
        for dy in (0, 1):
            self._chevron((fx, fy - dy), (-r, -r), (r, -r))

    def _chevron(self, tip: tuple[int, int], arm1: tuple[int, int],
                 arm2: tuple[int, int]) -> None:
        for ax, ay in (arm1, arm2):
            pygame.draw.line(self.surface, CHEVRON, tip, (tip[0] + ax, tip[1] + ay))

    def _menu(self, menu: Menu) -> None:
        layout, font = self.layout, self.font
        top = layout.menu_y
        bottom = layout.menu_y + len(menu.items) * layout.menu_row_h
        pygame.draw.rect(self.surface, MENU_BG, (0, top, layout.width, bottom - top))
        for i, (label, command) in enumerate(menu.items):
            x, y, w, h = layout.menu_item_rect(i)
            if i == menu.selected:
                pygame.draw.rect(self.surface, MENU_SELECTED, (x, y, w, h))
            self.surface.blit(font.render(label, False, WHITE), (x + 8, y + 3))
            pygame.draw.line(self.surface, EDGE, (x, y + h - 1), (x + w - 1, y + h - 1))
