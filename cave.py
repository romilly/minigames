"""Cave: find your way through a maze, seen in first person.

From the top: a toolbar with the name of where you are, a map of what you've
seen so far, a description, and a strip at the bottom with the view ahead.

Touch the view to step forward, and the arrows either side of it to turn. On the pad (or the desktop's keyboard or mouse):
L and R turn, U steps forward, D turns round. '-' (Esc) quits.
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
        start = spec.get('start') or {}
        at = start.get('at')
        if at is None:
            x, y, self.start_level = self._first_open_cell()
        elif isinstance(at, str):
            x, y, self.start_level = self.find(at)
        else:
            x, y = at[0], at[1]
            self.start_level = at[2] - 1 if len(at) > 2 else 0
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
        self.won = False
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

    def here(self):
        return self.maze.cell(self.position[0], self.position[1], self.level)

    def room_name(self):
        room = self.maze.rooms.get(self.here())
        return room.get('name', '') if room else ''

    def description(self):
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
    pygame.draw.rect(screen, TOOLBAR, (0, 0, layout.width, layout.toolbar_h))
    if game.won:
        title = 'You made it!'
    else:
        title = game.room_name() or game.maze.title
    screen.blit(font.render(title, False, WHITE), (4, 2))
    if len(game.maze.levels) > 1:
        label = font.render('L%d' % (game.level + 1), False, GREY)
        screen.blit(label, label.get_rect(right=layout.width - 4, top=2))


def draw_text(screen, game, layout, font):
    text = game.description()
    if game.won:
        text += ' Touch to play again.'
    x, y = 4, layout.text_y
    for line in wrap(font, text, layout.width - 2 * x)[:DESCRIPTION_LINES]:
        screen.blit(font.render(line, False, GREY), (x, y))
        y += layout.line_height


def draw(screen, game, layout, font):
    screen.fill(BLACK)
    draw_toolbar(screen, game, layout, font)
    draw_map(screen, game, layout)
    draw_text(screen, game, layout, font)
    draw_view(screen, game, layout)
    draw_arrows(screen, layout)


def main(fps=30, game=None, size=SIZE, maze=MAZE):
    pygame.init()
    screen = pygame.display.set_mode(size, getattr(pygame, 'SCALED', 0))
    font = pygame.font.Font(None, 24)     # scale 2 on the board, like the scores
    layout = Layout(*screen.get_size(), line_height=font.size('Ag')[1])
    clock = pygame.time.Clock()
    sounds = {'step': tone(600, 20), 'steps': tone(330, 150), 'turn': tone(900, 10), 'bump': tone(120, 60),
              'win': tone(1320, 400), 'new': tone(660, 50)}
    game = game or Cave(load_maze(maze))
    running, dirty = True, True
    while running:
        happened = []
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                elif event.key in KEY_ACTIONS:
                    happened += game.act(KEY_ACTIONS[event.key])
            elif event.type == pygame.MOUSEBUTTONDOWN:
                action = touch_action(event.pos, layout)
                if action or game.won:
                    happened += game.act(action or 'forward')
        for what in happened:
            sounds[what].play()
        if happened or dirty:
            draw(screen, game, layout, font)
            dirty = False
        pygame.display.flip()
        clock.tick(fps)
    pygame.quit()
    return game


if __name__ == '__main__':
    main()
