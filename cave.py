"""Cave: find your way through a maze, seen in first person.

From the top: a toolbar with the name of where you are, a map of what you've
seen so far, a description, and a strip at the bottom with the view ahead.

Touch the view to step forward, and the arrows either side of it to turn.
The button at the left of the toolbar opens a menu of what you can do: take
or drop things, or see what you're carrying. Find treasure and escape with it. On the pad (or the desktop's keyboard or mouse):
L and R turn, U steps forward, D turns round; A opens the menu, U and D
choose, A does it and B closes it. '-' (Esc) quits.
When you reach the goal, any move starts again.

Mazes live in mazes/<name>.yaml (see mazes/mine.yaml). MicroPython has no
YAML parser, so scripts/deploy.sh copies them to the board as <name>.json.
"""
import pygame
from tones import tone

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3
DIRECTIONS = ('north', 'east', 'south', 'west')
STEPS = ((0, -1), (1, 0), (0, 1), (-1, 0))
WALL = '#'
DOWN, UP = '>', '<'        # steps to the level below, and above
DEPTH = 4                  # how many cells ahead you can see
CARRIED = 'carried'        # where an object you're carrying is
PASSAGE = 'A dark passage.'
STEPS_DOWN = 'Steps lead down into the dark.'
STEPS_UP = 'Steps lead up.'
MAZE = 'mine'


# ---- The maze ----

class Maze:
    """A maze, from a spec: the dict that a maze's YAML (or JSON) file holds.

    A spec has one `map`, or `levels`: a list of {map: ...}, top first. Levels
    are numbered from 0 here, and from 1 in specs and messages. Steps down (>)
    on one level need steps up (<) at the same place on the level below."""

    def __init__(self, spec):
        grids = [level['map'].rstrip('\n').split('\n')
                 for level in (spec.get('levels') or [spec])]
        self.width = max(len(line) for grid in grids for line in grid)
        self.height = max(len(grid) for grid in grids)
        # Pad every level to the same size (str.ljust isn't in MicroPython)
        self.levels = [[line + ' ' * (self.width - len(line)) for line in grid] +
                       [WALL * self.width] * (self.height - len(grid))
                       for grid in grids]
        self.title = spec.get('title', 'A maze')
        self.passage = spec.get('passage', PASSAGE)
        self.rooms = spec.get('rooms') or {}
        for letter in self.rooms:
            self.find(letter)                    # complains if it's not there
        self._check_steps()
        self.objects = spec.get('objects') or {}
        self.object_starts = dict((name, self.place(self.objects[name].get('at')))
                                  for name in self.objects)
        start = spec.get('start') or {}
        if start.get('at') is None:
            x, y, self.start_level = self._first_open_cell()
        else:
            x, y, self.start_level = self.place(start['at'])
        self.start = (x, y)
        self.start_facing = DIRECTIONS.index(start.get('facing', 'north'))

    def cell(self, x, y, level=0):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.levels[level][y][x]
        return WALL

    def is_wall(self, x, y, level=0):
        return self.cell(x, y, level) == WALL

    def room(self, x, y, level=0):
        """The room at (x, y) as a dict, or None for plain passage or rock."""
        return self.rooms.get(self.cell(x, y, level))

    def place(self, at):
        """(x, y, level) from a spec's `at`: a letter, [x, y] or [x, y, level from 1]."""
        if isinstance(at, str):
            return self.find(at)
        return (at[0], at[1], at[2] - 1 if len(at) > 2 else 0)

    def find(self, letter):
        """Where a letter is: (x, y, level)."""
        for level in range(len(self.levels)):
            for y in range(self.height):
                x = self.levels[level][y].find(letter)
                if x >= 0:
                    return (x, y, level)
        raise ValueError('%r is not on the map' % letter)

    def _check_steps(self):
        last = len(self.levels) - 1
        for level in range(last + 1):
            for y in range(self.height):
                for x in range(self.width):
                    here = self.cell(x, y, level)
                    if here == DOWN and (level == last or self.cell(x, y, level + 1) != UP):
                        raise ValueError(
                            'steps down at (%d, %d) on level %d need steps up (<) at '
                            'the same place on the level below' % (x, y, level + 1))
                    if here == UP and (level == 0 or self.cell(x, y, level - 1) != DOWN):
                        raise ValueError(
                            'steps up at (%d, %d) on level %d need steps down (>) at '
                            'the same place on the level above' % (x, y, level + 1))

    def _first_open_cell(self):
        for y in range(self.height):
            for x in range(self.width):
                if not self.is_wall(x, y):
                    return (x, y, 0)
        raise ValueError('the map has no open cells')


def load_maze(name, folder='mazes'):
    """mazes/<name>.yaml on the desktop; <name>.json on the board."""
    try:
        import yaml
    except ImportError:
        import json
        with open(name + '.json') as f:
            return Maze(json.load(f))
    with open('%s/%s.yaml' % (folder, name)) as f:
        return Maze(yaml.safe_load(f))


# ---- The game ----

class Cave:
    def __init__(self, maze):
        self.maze = maze
        self.restart()

    def restart(self):
        self.position = self.maze.start
        self.level = self.maze.start_level
        self.facing = self.maze.start_facing
        self._seen = [set() for _ in self.maze.levels]
        self._where = dict(self.maze.object_starts)   # name -> (x, y, level) or CARRIED
        self.won = False
        self.message = None                            # shown instead of the description
        self._look()

    @property
    def seen(self):
        """The cells you've seen on this level."""
        return self._seen[self.level]

    def _wall(self, cell):
        return self.maze.is_wall(cell[0], cell[1], self.level)

    def act(self, action):
        """'left', 'right', 'around' or 'forward'. Returns what happened, for sounds."""
        if self.won:
            self.restart()
            return ['new']
        self.message = None
        if action == 'forward':
            x, y = self._ahead(self.position)
            if self._wall((x, y)):
                return ['bump']
            self.position = (x, y)
            here = self.maze.cell(x, y, self.level)
            if here in (DOWN, UP):
                self.level += 1 if here == DOWN else -1
                self._look()
                return ['steps']
            self._look()
            room = self.maze.room(x, y, self.level)
            if room and room.get('goal'):
                self.won = True
                return ['win']
            return ['step']
        turns = {'left': 3, 'right': 1, 'around': 2}
        if action not in turns:
            return []
        self.facing = (self.facing + turns[action]) % 4
        self._look()
        return ['turn']

    # ---- Objects ----

    def objects_here(self):
        return self.objects_at(self.position)

    def carried(self):
        return sorted(name for name in self._where if self._where[name] == CARRIED)

    def objects_at(self, cell):
        at = (cell[0], cell[1], self.level)
        return sorted(name for name in self._where if self._where[name] == at)

    def name_of(self, thing):
        return self.maze.objects[thing].get('name', thing)

    def menu_items(self):
        """What you can do here, as (label, command) pairs for do()."""
        items = [('Take ' + self.name_of(t), ('take', t)) for t in self.objects_here()]
        items += [('Drop ' + self.name_of(t), ('drop', t)) for t in self.carried()]
        return items + [('Inventory', ('inventory',))]

    def do(self, command):
        """Carry out a command from menu_items(). Returns what happened, for sounds."""
        if self.won:
            return []
        kind = command[0]
        if kind == 'take' and command[1] in self.objects_here():
            self._where[command[1]] = CARRIED
            self.message = 'Taken: %s.' % self.name_of(command[1])
            return ['take']
        if kind == 'drop' and command[1] in self.carried():
            self._where[command[1]] = (self.position[0], self.position[1], self.level)
            self.message = 'Dropped: %s.' % self.name_of(command[1])
            return ['drop']
        if kind == 'inventory':
            carried = self.carried()
            if not carried:
                self.message = 'You are carrying nothing.'
            else:
                self.message = 'You are carrying: %s.' % ', '.join(
                    self.name_of(t) for t in carried)
                if self.treasure():
                    self.message += ' Treasure: %d.' % self.treasure()
            return ['menu']
        return []

    def treasure(self):
        return sum(self.maze.objects[t].get('value', 0) for t in self.carried())

    def total_treasure(self):
        return sum(o.get('value', 0) for o in self.maze.objects.values())

    def objects_in_view(self):
        """Depths ahead (0 is underfoot) where something is lying."""
        return [depth for depth, cell in enumerate(self._cells_ahead())
                if self.objects_at(cell)]

    # ---- Where you are ----

    def here(self):
        return self.maze.cell(self.position[0], self.position[1], self.level)

    def room_name(self):
        room = self.maze.rooms.get(self.here())
        return room.get('name', '') if room else ''

    def description(self):
        text = self._place_description()
        if self.won and self.total_treasure():
            text += ' You escaped with %d of %d points of treasure.' % (
                self.treasure(), self.total_treasure())
        return text

    def _place_description(self):
        here = self.here()
        room = self.maze.rooms.get(here)
        if room and room.get('description'):
            return room['description'].strip()
        if here == DOWN:
            return STEPS_DOWN
        if here == UP:
            return STEPS_UP
        return self.maze.passage

    def steps_in_view(self):
        """Steps you can see, as (depth, DOWN or UP); depth 0 is underfoot."""
        found = []
        for depth, (x, y) in enumerate(self._cells_ahead()):
            here = self.maze.cell(x, y, self.level)
            if here in (DOWN, UP):
                found.append((depth, here))
        return found

    def view(self):
        """What's ahead, nearest first: for each cell up to DEPTH ahead,
        (wall on the left, wall on the right, wall ahead). Stops at a wall."""
        slices = []
        for cell in self._cells_ahead():
            slices.append((self._wall(self._side(cell, -1)),
                           self._wall(self._side(cell, 1)),
                           self._wall(self._ahead(cell))))
        return slices

    def _cells_ahead(self):
        cells = [self.position]
        while len(cells) < DEPTH and not self._wall(self._ahead(cells[-1])):
            cells.append(self._ahead(cells[-1]))
        return cells

    def _ahead(self, cell):
        dx, dy = STEPS[self.facing]
        return (cell[0] + dx, cell[1] + dy)

    def _side(self, cell, turn):
        dx, dy = STEPS[(self.facing + turn) % 4]
        return (cell[0] + dx, cell[1] + dy)

    def _look(self):
        for cell in self._cells_ahead():
            self.seen.add(cell)
            self.seen.add(self._side(cell, -1))
            self.seen.add(self._side(cell, 1))
            self.seen.add(self._ahead(cell))


# ---- Controls ----

KEY_ACTIONS = {pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right',
               pygame.K_UP: 'forward', pygame.K_DOWN: 'around'}


def touch_action(pos, layout):
    """What a touch at pos means: left of the view turns left, right of it
    turns right, the view itself steps forward."""
    x, y = pos
    if y < layout.view_y:
        return None
    if x < layout.view_x:
        return 'left'
    if x >= layout.view_x + layout.view_w:
        return 'right'
    return 'forward'


class Menu:
    """The toolbar's menu: a list of (label, command) pairs, one selected."""

    def __init__(self):
        self.items = None
        self.selected = 0

    @property
    def is_open(self):
        return self.items is not None

    def show(self, items, rows=None):
        """Open with these items; if there are more than rows, keep the last
        (Inventory) and as many of the first as fit."""
        if rows and len(items) > rows:
            items = items[:rows - 1] + items[-1:]
        self.items = items
        self.selected = 0

    def close(self):
        self.items = None

    def move(self, step):
        self.selected = (self.selected + step) % len(self.items)

    def chosen(self):
        return self.items[self.selected][1]


MENU_KEYS = (pygame.K_a, pygame.K_SPACE, pygame.K_RETURN)


def handle(event, game, menu, layout):
    """One key press or touch. Returns what happened, for sounds."""
    if event.type == pygame.KEYDOWN:
        key = event.key
        if game.won:
            return game.act('forward') if key in KEY_ACTIONS or key in MENU_KEYS else []
        if menu.is_open:
            if key in (pygame.K_UP, pygame.K_DOWN):
                menu.move(-1 if key == pygame.K_UP else 1)
                return []
            if key in MENU_KEYS:
                command = menu.chosen()
                menu.close()
                return game.do(command)
            if key == pygame.K_b:
                menu.close()
            return []
        if key in MENU_KEYS:
            menu.show(game.menu_items(), layout.menu_rows)
            return ['menu']
        if key in KEY_ACTIONS:
            return game.act(KEY_ACTIONS[key])
        return []
    if event.type == pygame.MOUSEBUTTONDOWN:
        if game.won:
            return game.act('forward')
        if menu.is_open:
            items = menu.items
            menu.close()
            index = layout.menu_item_at(event.pos, len(items))
            return [] if index is None else game.do(items[index][1])
        if event.pos[1] < layout.toolbar_h:
            menu.show(game.menu_items(), layout.menu_rows)
            return ['menu']
        action = touch_action(event.pos, layout)
        return game.act(action) if action else []
    return []


# ---- Drawing ----

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
MENU_BG = (20, 25, 45)
MENU_SELECTED = (60, 70, 120)
STAIRS_DOWN = (90, 60, 120)
STAIRS_UP = (170, 140, 200)
PLAYER = (240, 80, 80)
CEILING = (20, 20, 30)
GROUND = (50, 40, 30)
EDGE = (30, 30, 40)
# Frames for each depth ahead, as fractions of the view's width and height.
FRAMES = (0.5, 0.3, 0.175, 0.1, 0.06)
MAX_CELL = 12
DESCRIPTION_LINES = 3


VIEW_SHARE = 4 / 15     # of the screen's height, for the view ahead


class Layout:
    """From the top: toolbar, map, description, then the view ahead in a
    strip, twice as wide as it is high, with room either side to turn."""

    def __init__(self, width, height, line_height):
        self.width, self.height = width, height
        self.line_height = line_height
        self.toolbar_h = line_height + 4
        self.view_h = int(height * VIEW_SHARE)
        self.view_y = height - self.view_h
        self.view_w = 2 * self.view_h
        self.view_x = (width - self.view_w) // 2
        self.text_y = self.view_y - DESCRIPTION_LINES * line_height - 2
        self.map_y = self.toolbar_h + 2
        self.map_h = self.text_y - self.map_y - 2
        # The menu covers the map and text, one row per item
        self.menu_y = self.toolbar_h + 2
        self.menu_row_h = line_height + 6
        self.menu_rows = (self.view_y - self.menu_y) // self.menu_row_h

    def menu_item_rect(self, index):
        return (0, self.menu_y + index * self.menu_row_h, self.width, self.menu_row_h)

    def menu_item_at(self, pos, count):
        """Which of count menu items pos is on, or None."""
        index = (pos[1] - self.menu_y) // self.menu_row_h
        if pos[1] >= self.menu_y and index < count:
            return index
        return None

    def frame(self, depth):
        """The rectangle where the walls at a depth meet the next: x0, y0, x1, y1."""
        f = FRAMES[depth]
        cx, cy = self.view_x + self.view_w // 2, self.view_y + self.view_h // 2
        hw, hh = int(f * self.view_w), int(f * self.view_h)
        return cx - hw, cy - hh, cx + hw, cy + hh


def shade(colour, depth):
    k = 1 - 0.17 * depth
    return (int(colour[0] * k), int(colour[1] * k), int(colour[2] * k))


def face(screen, colour, points):
    pygame.draw.polygon(screen, colour, points)
    for i in range(len(points)):
        pygame.draw.line(screen, EDGE, points[i], points[(i + 1) % len(points)])


def draw_view(screen, game, layout):
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
            face(screen, shade(ROCK, depth + 1), [(a0, b0), (a1, b0), (a1, b1), (a0, b1)])
        for wall, outer, inner in ((left, x0, a0), (right, x1, a1)):
            if wall:
                face(screen, shade(ROCK, depth + 0.5),
                     [(outer, y0), (inner, b0), (inner, b1), (outer, y1)])
            else:                                # an opening: the far wall of a side passage
                face(screen, shade(ROCK, depth + 1),
                     [(outer, b0), (inner, b0), (inner, b1), (outer, b1)])


def draw_steps(screen, layout, depth, kind):
    """Steps on the floor of the cell at depth: dark going down, pale going up."""
    x0, y0, x1, y1 = layout.frame(depth)
    a0, b0, a1, b1 = layout.frame(depth + 1)
    colour = STAIRS_DOWN if kind == DOWN else STAIRS_UP
    pygame.draw.polygon(screen, shade(colour, depth), [(x0, y1), (x1, y1), (a1, b1), (a0, b1)])
    for i in (1, 2, 3):
        t = i / 4
        y = y1 + (b1 - y1) * t
        pygame.draw.line(screen, EDGE, (x0 + (a0 - x0) * t, y), (x1 + (a1 - x1) * t, y))


def draw_glint(screen, layout, depth):
    """Something lying on the floor of the cell at depth: a small gold diamond."""
    x0, y0, x1, y1 = layout.frame(depth)
    a0, b0, a1, b1 = layout.frame(depth + 1)
    cx, cy = (x0 + x1) // 2, (y1 + b1) // 2
    r = max(2, (x1 - x0) // 24)
    pygame.draw.polygon(screen, shade(TREASURE_GLINT, depth),
                        [(cx, cy - r), (cx + r, cy), (cx, cy + r), (cx - r, cy)])


def draw_map(screen, game, layout):
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
    for (x, y) in game.seen:
        sx, sy = ox + x * cell, oy + y * cell
        if sx < 0 or sy < layout.map_y or sx + cell > layout.width or \
                sy + cell > layout.map_y + layout.map_h:
            continue
        here = maze.cell(x, y, game.level)
        room = maze.rooms.get(here)
        if here == WALL:
            colour = ROCK
        elif here == DOWN:
            colour = STAIRS_DOWN
        elif here == UP:
            colour = STAIRS_UP
        elif room and room.get('goal'):
            colour = GOAL
        elif room:
            colour = ROOM
        else:
            colour = FLOOR
        pygame.draw.rect(screen, colour, (sx, sy, cell - 1, cell - 1))
        if game.objects_at((x, y)) and cell >= 6:
            pygame.draw.rect(screen, TREASURE_GLINT,
                             (sx + cell // 2 - 2, sy + cell // 2 - 2, 3, 3))
    cx, cy = ox + px * cell + cell // 2, oy + py * cell + cell // 2
    dx, dy = STEPS[game.facing]
    r = max(2, cell // 2 - 1)
    pygame.draw.polygon(screen, PLAYER, [
        (cx + dx * r, cy + dy * r),
        (cx - dy * r - dx * r, cy + dx * r - dy * r),
        (cx + dy * r - dx * r, cy - dx * r - dy * r)])


def wrap(font, text, max_width):
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


def draw_arrows(screen, layout):
    """Turn arrows in the spaces either side of the view."""
    side = layout.view_x
    if side < 12:
        return
    cy = layout.view_y + layout.view_h // 2
    r = min(side, layout.view_h) // 4
    for cx, d in ((side // 2, -1), (layout.width - side // 2, 1)):
        pygame.draw.polygon(screen, ARROW, [(cx + d * r, cy), (cx - d * r, cy - r),
                                            (cx - d * r, cy + r)])


def draw_toolbar(screen, game, layout, font):
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


def draw_text(screen, game, layout, font):
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


def draw_menu(screen, menu, layout, font):
    top = layout.menu_y
    bottom = layout.menu_y + len(menu.items) * layout.menu_row_h
    pygame.draw.rect(screen, MENU_BG, (0, top, layout.width, bottom - top))
    for i, (label, command) in enumerate(menu.items):
        x, y, w, h = layout.menu_item_rect(i)
        if i == menu.selected:
            pygame.draw.rect(screen, MENU_SELECTED, (x, y, w, h))
        screen.blit(font.render(label, False, WHITE), (x + 8, y + 3))
        pygame.draw.line(screen, EDGE, (x, y + h - 1), (x + w - 1, y + h - 1))


def draw(screen, game, layout, font, menu=None):
    screen.fill(BLACK)
    draw_toolbar(screen, game, layout, font)
    draw_map(screen, game, layout)
    draw_text(screen, game, layout, font)
    draw_view(screen, game, layout)
    draw_arrows(screen, layout)
    if menu and menu.is_open:
        draw_menu(screen, menu, layout, font)


def main(fps=30, game=None, size=SIZE, maze=MAZE):
    pygame.init()
    screen = pygame.display.set_mode(size, getattr(pygame, 'SCALED', 0))
    font = pygame.font.Font(None, 24)     # scale 2 on the board, like the scores
    layout = Layout(*screen.get_size(), line_height=font.size('Ag')[1])
    clock = pygame.time.Clock()
    sounds = {'step': tone(600, 20), 'steps': tone(330, 150), 'turn': tone(900, 10),
              'bump': tone(120, 60), 'win': tone(1320, 400), 'new': tone(660, 50),
              'menu': tone(800, 15), 'take': tone(1000, 60), 'drop': tone(500, 60)}
    game = game or Cave(load_maze(maze))
    menu = Menu()
    running, dirty = True, True
    while running:
        happened = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE:
                running = False
            elif event.type in (pygame.KEYDOWN, pygame.MOUSEBUTTONDOWN):
                happened += handle(event, game, menu, layout)
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
