"""Cave: find your way through a maze, seen in first person.

The top half of the screen is a map of what you've seen so far, with the
name and description of where you are. The bottom half is the view ahead.

Touch the bottom half: left third turns left, right third turns right, the
middle steps forward. On the pad (or the desktop's keyboard or mouse):
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
DEPTH = 4                  # how many cells ahead you can see
PASSAGE = 'A dark passage.'
MAZE = 'mine'


# ---- The maze ----

class Maze:
    """A maze, from a spec: the dict that a maze's YAML (or JSON) file holds."""

    def __init__(self, spec):
        lines = spec['map'].rstrip('\n').split('\n')
        self.width = max(len(line) for line in lines)
        self.height = len(lines)
        # str.ljust isn't in MicroPython
        self.rows = [line + ' ' * (self.width - len(line)) for line in lines]
        self.title = spec.get('title', 'A maze')
        self.passage = spec.get('passage', PASSAGE)
        self.rooms = spec.get('rooms') or {}
        for letter in self.rooms:
            self.find(letter)                    # complains if it's not there
        start = spec.get('start') or {}
        at = start.get('at')
        if at is None:
            self.start = self._first_open_cell()
        elif isinstance(at, str):
            self.start = self.find(at)
        else:
            self.start = (at[0], at[1])
        self.start_facing = DIRECTIONS.index(start.get('facing', 'north'))

    def is_wall(self, x, y):
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.rows[y][x] == WALL
        return True

    def room(self, x, y):
        """The room at (x, y) as a dict, or None for plain passage or rock."""
        if self.is_wall(x, y):
            return None
        return self.rooms.get(self.rows[y][x])

    def find(self, letter):
        for y in range(self.height):
            x = self.rows[y].find(letter)
            if x >= 0:
                return (x, y)
        raise ValueError('%r is not on the map' % letter)

    def _first_open_cell(self):
        for y in range(self.height):
            for x in range(self.width):
                if not self.is_wall(x, y):
                    return (x, y)
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
        self.facing = self.maze.start_facing
        self.seen = set()
        self.won = False
        self._look()

    def act(self, action):
        """'left', 'right', 'around' or 'forward'. Returns what happened, for sounds."""
        if self.won:
            self.restart()
            return ['new']
        if action == 'forward':
            x, y = self._ahead(self.position)
            if self.maze.is_wall(x, y):
                return ['bump']
            self.position = (x, y)
            self._look()
            room = self.maze.room(x, y)
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

    def room_name(self):
        room = self.maze.room(*self.position)
        return room.get('name', '') if room else ''

    def description(self):
        room = self.maze.room(*self.position)
        if room and room.get('description'):
            return room['description'].strip()
        return self.maze.passage

    def view(self):
        """What's ahead, nearest first: for each cell up to DEPTH ahead,
        (wall on the left, wall on the right, wall ahead). Stops at a wall."""
        slices = []
        for (x, y) in self._cells_ahead():
            slices.append((self.maze.is_wall(*self._side((x, y), -1)),
                           self.maze.is_wall(*self._side((x, y), 1)),
                           self.maze.is_wall(*self._ahead((x, y)))))
        return slices

    def _cells_ahead(self):
        cells = [self.position]
        while len(cells) < DEPTH and not self.maze.is_wall(*self._ahead(cells[-1])):
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
    """What a touch at pos means: thirds of the view, left to right."""
    x, y = pos
    if y < layout.view_y:
        return None
    third = layout.width // 3
    if x < third:
        return 'left'
    if x >= layout.width - third:
        return 'right'
    return 'forward'


# ---- Drawing ----

SIZE = (240, 240)       # the desktop window: the Presto's shape
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GREY = (150, 150, 150)
ROCK = (150, 150, 180)
FLOOR = (50, 100, 50)
ROOM = (70, 140, 140)
GOAL = (200, 180, 40)
PLAYER = (240, 80, 80)
CEILING = (20, 20, 30)
GROUND = (50, 40, 30)
EDGE = (30, 30, 40)
# Frames for each depth ahead, as fractions of the view's width and height.
FRAMES = (0.5, 0.3, 0.175, 0.1, 0.06)
MAX_CELL = 12
DESCRIPTION_LINES = 3


class Layout:
    """Map and text in the top half, the view ahead in the bottom half."""

    def __init__(self, width, height, line_height):
        self.width, self.height = width, height
        self.line_height = line_height
        self.view_y = height // 2
        self.view_h = height - self.view_y
        self.text_y = self.view_y - (DESCRIPTION_LINES + 1) * line_height - 2
        self.map_y = 2
        self.map_h = self.text_y - self.map_y - 2

    def frame(self, depth):
        """The rectangle where the walls at a depth meet the next: x0, y0, x1, y1."""
        f = FRAMES[depth]
        cx, cy = self.width // 2, self.view_y + self.view_h // 2
        hw, hh = int(f * self.width), int(f * self.view_h)
        return cx - hw, cy - hh, cx + hw, cy + hh


def shade(colour, depth):
    k = 1 - 0.17 * depth
    return (int(colour[0] * k), int(colour[1] * k), int(colour[2] * k))


def face(screen, colour, points):
    pygame.draw.polygon(screen, colour, points)
    for i in range(len(points)):
        pygame.draw.line(screen, EDGE, points[i], points[(i + 1) % len(points)])


def draw_view(screen, game, layout):
    w, top, h = layout.width, layout.view_y, layout.view_h
    pygame.draw.rect(screen, CEILING, (0, top, w, h // 2))
    pygame.draw.rect(screen, GROUND, (0, top + h // 2, w, h - h // 2))
    view = game.view()
    last = len(view) - 1
    if not view[last][2]:                        # no wall in sight: darkness
        x0, y0, x1, y1 = layout.frame(last + 1)
        pygame.draw.rect(screen, BLACK, (x0, y0, x1 - x0, y1 - y0))
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
        room = maze.room(x, y)
        if maze.is_wall(x, y):
            colour = ROCK
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


def draw_text(screen, game, layout, font):
    x, y = 4, layout.text_y
    if game.won:
        name, text = 'You made it!', game.description() + ' Touch to play again.'
    else:
        name, text = game.room_name(), game.description()
    if name:
        screen.blit(font.render(name, False, WHITE), (x, y))
    y += layout.line_height
    for line in wrap(font, text, layout.width - 2 * x)[:DESCRIPTION_LINES]:
        screen.blit(font.render(line, False, GREY), (x, y))
        y += layout.line_height


def draw(screen, game, layout, font):
    screen.fill(BLACK)
    draw_map(screen, game, layout)
    draw_text(screen, game, layout, font)
    draw_view(screen, game, layout)


def main(fps=30, game=None, size=SIZE, maze=MAZE):
    pygame.init()
    screen = pygame.display.set_mode(size, getattr(pygame, 'SCALED', 0))
    font = pygame.font.Font(None, 16)
    layout = Layout(*screen.get_size(), line_height=font.size('Ag')[1])
    clock = pygame.time.Clock()
    sounds = {'step': tone(600, 20), 'turn': tone(900, 10), 'bump': tone(120, 60),
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
