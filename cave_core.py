"""The cave game's core: the maze and the state of play.

No pygame and no files here: the drawing, the controls and maze loading
are adapters around this (see cave.py).
"""

NORTH, EAST, SOUTH, WEST = 0, 1, 2, 3
DIRECTIONS = ('north', 'east', 'south', 'west')
STEPS = ((0, -1), (1, 0), (0, 1), (-1, 0))
WALL = '#'
DOWN, UP = '>', '<'        # steps to the level below, and above
DEPTH = 4                  # how many cells ahead you can see
MAX_HEALTH = 10
CARRIED = 'carried'        # where an object you're carrying is
DOOR = 'door'              # what a locked door looks like in view()
PASSAGE = 'A dark passage.'
STEPS_DOWN = 'Steps lead down into the dark.'
STEPS_UP = 'Steps lead up.'


class Kind:
    """What a cell is, for the map."""
    ROCK = 'rock'
    PASSAGE = 'passage'
    ROOM = 'room'
    GOAL = 'goal'
    DOWN = 'steps down'
    UP = 'steps up'
    DOOR = 'door'               # locked
    OPEN_DOOR = 'open door'


# ---- The maze ----

class Maze:
    """A maze, from a spec: the dict that a maze's YAML (or JSON) file holds.

    A spec has one `map`, or `levels`: a list of {map: ...}, top first. Levels
    are numbered from 0 here, and from 1 in specs and messages. Steps down (>)
    on one level need steps up (<) at the same place on the level below."""

    def __init__(self, spec: dict) -> None:
        grids = [level['map'].rstrip('\n').split('\n')
                 for level in (spec.get('levels') or [spec])]
        self.width = max(len(line) for grid in grids for line in grid)
        self.height = max(len(grid) for grid in grids)
        # Pad every level to the same size (str.ljust isn't in MicroPython)
        self.levels: list[list[str]] = [[line + ' ' * (self.width - len(line)) for line in grid] +
                       [WALL * self.width] * (self.height - len(grid))
                       for grid in grids]
        self.title: str = spec.get('title', 'A maze')
        self.passage: str = spec.get('passage', PASSAGE)
        self.rooms: dict[str, dict] = spec.get('rooms') or {}
        for letter in self.rooms:
            self.find(letter)                    # complains if it's not there
        self._check_steps()
        self.objects: dict[str, dict] = spec.get('objects') or {}
        self.object_starts: dict[str, tuple[int, int, int]] = {}
        for name in self.objects:
            at = self.objects[name].get('at')
            if at is None:
                raise ValueError("object %r needs an 'at' to say where it lies" % name)
            self.object_starts[name] = self.place(at)
        for letter in self.rooms:
            needs = self.rooms[letter].get('needs')
            if needs is not None and needs not in self.objects:
                raise ValueError('room %r needs %r, which is not one of the objects'
                                 % (letter, needs))
        start = spec.get('start') or {}
        if start.get('at') is None:
            x, y, self.start_level = self._first_open_cell()
        else:
            x, y, self.start_level = self.place(start['at'])
        self.start: tuple[int, int] = (x, y)
        self.start_facing = DIRECTIONS.index(start.get('facing', 'north'))

    def cell(self, x: int, y: int, level: int = 0) -> str:
        if 0 <= x < self.width and 0 <= y < self.height:
            return self.levels[level][y][x]
        return WALL

    def is_wall(self, x: int, y: int, level: int = 0) -> bool:
        return self.cell(x, y, level) == WALL

    def room(self, x: int, y: int, level: int = 0) -> dict | None:
        """The room at (x, y) as a dict, or None for plain passage or rock."""
        return self.rooms.get(self.cell(x, y, level))

    def place(self, at: str | list[int]) -> tuple[int, int, int]:
        """(x, y, level) from a spec's `at`: a letter, [x, y] or [x, y, level from 1]."""
        if isinstance(at, str):
            return self.find(at)
        return (at[0], at[1], at[2] - 1 if len(at) > 2 else 0)

    def find(self, letter: str) -> tuple[int, int, int]:
        """Where a letter is: (x, y, level)."""
        for level in range(len(self.levels)):
            for y in range(self.height):
                x = self.levels[level][y].find(letter)
                if x >= 0:
                    return (x, y, level)
        raise ValueError('%r is not on the map' % letter)

    def _check_steps(self) -> None:
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

    def _first_open_cell(self) -> tuple[int, int, int]:
        for y in range(self.height):
            for x in range(self.width):
                if not self.is_wall(x, y):
                    return (x, y, 0)
        raise ValueError('the map has no open cells')


# ---- The game ----

class Cave:
    def __init__(self, maze: Maze) -> None:
        self.maze = maze
        self.restart()

    def restart(self) -> None:
        self.position = self.maze.start
        self.level = self.maze.start_level
        self.facing = self.maze.start_facing
        self._seen: list[set[tuple[int, int]]] = [set() for _ in self.maze.levels]
        self._where: dict[str, tuple[int, int, int] | str] = dict(self.maze.object_starts)   # name -> (x, y, level) or CARRIED
        self.unlocked: set[str] = set()                          # letters of doors you've opened
        self.won = False
        self.message: str | None = None                            # shown instead of the description
        self.max_health = MAX_HEALTH
        self.health = MAX_HEALTH
        self.moves = 0                                             # every act(), as in Colossal Cave
        self._look()

    @property
    def seen(self) -> set[tuple[int, int]]:
        """The cells you've seen on this level."""
        return self._seen[self.level]

    def _blocked(self, cell: tuple[int, int]) -> str | None:
        """What stops you going into cell: WALL, DOOR (locked) or None."""
        here = self.maze.cell(cell[0], cell[1], self.level)
        if here == WALL:
            return WALL
        if self._needs(here) and here not in self.unlocked:
            return DOOR
        return None

    def _needs(self, letter: str) -> str | None:
        room = self.maze.rooms.get(letter)
        return room.get('needs') if room else None

    def _door_name(self, letter: str) -> str:
        return self.maze.rooms[letter].get('name', 'door').lower()

    def act(self, action: str) -> list[str]:
        """'left', 'right', 'around' or 'forward'. Returns what happened, for sounds."""
        if self.won:
            self.restart()
            return ['new']
        self.message = None
        self.moves += 1
        if action == 'forward':
            x, y = self._ahead(self.position)
            blocked = self._blocked((x, y))
            happened = ['step']
            if blocked == WALL:
                return ['bump']
            if blocked == DOOR:
                letter = self.maze.cell(x, y, self.level)
                key = self._needs(letter)
                if key not in self.carried():
                    self.message = 'The %s is locked.' % self._door_name(letter)
                    return ['locked']
                self.unlocked.add(letter)
                self.message = 'You unlock the %s with the %s.' % (
                    self._door_name(letter), self.name_of(key))
                happened = ['unlock']
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
            return happened
        turns = {'left': 3, 'right': 1, 'around': 2}
        if action not in turns:
            return []
        self.facing = (self.facing + turns[action]) % 4
        self._look()
        return ['turn']

    def stats(self) -> list[tuple[str, str]]:
        """How the adventurer is doing, as (label, value) pairs for the screen."""
        return [('Health', '%d/%d' % (self.health, self.max_health)),
                ('Moves', str(self.moves))]

    # ---- Objects ----

    def objects_here(self) -> list[str]:
        return self.objects_at(self.position)

    def carried(self) -> list[str]:
        return sorted(name for name in self._where if self._where[name] == CARRIED)

    def objects_at(self, cell: tuple[int, int]) -> list[str]:
        at = (cell[0], cell[1], self.level)
        return sorted(name for name in self._where if self._where[name] == at)

    def name_of(self, thing: str) -> str:
        return self.maze.objects[thing].get('name', thing)

    def menu_items(self) -> list[tuple[str, tuple]]:
        """What you can do here, as (label, command) pairs for do()."""
        items: list[tuple[str, tuple]] = [
            ('Take ' + self.name_of(t), ('take', t)) for t in self.objects_here()]
        items += [('Drop ' + self.name_of(t), ('drop', t)) for t in self.carried()]
        return items + [('Inventory', ('inventory',))]

    def do(self, command: tuple) -> list[str]:
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

    def treasure(self) -> int:
        return sum(self.maze.objects[t].get('value', 0) for t in self.carried())

    def total_treasure(self) -> int:
        return sum(o.get('value', 0) for o in self.maze.objects.values())

    def map_cells(self) -> list[tuple[int, int, str, bool]]:
        """The cells you've seen on this level, as (x, y, Kind, anything lying there)."""
        return [(x, y, self._kind_of((x, y)), bool(self.objects_at((x, y))))
                for (x, y) in sorted(self.seen)]

    def _kind_of(self, cell: tuple[int, int]) -> str:
        here = self.maze.cell(cell[0], cell[1], self.level)
        if here == WALL:
            return Kind.ROCK
        if here == DOWN:
            return Kind.DOWN
        if here == UP:
            return Kind.UP
        room = self.maze.rooms.get(here)
        if not room:
            return Kind.PASSAGE
        if room.get('needs'):
            return Kind.OPEN_DOOR if here in self.unlocked else Kind.DOOR
        if room.get('goal'):
            return Kind.GOAL
        return Kind.ROOM

    def objects_in_view(self) -> list[int]:
        """Depths ahead (0 is underfoot) where something is lying."""
        return [depth for depth, cell in enumerate(self._cells_ahead())
                if self.objects_at(cell)]

    # ---- Where you are ----

    def here(self) -> str:
        return self.maze.cell(self.position[0], self.position[1], self.level)

    def room_name(self) -> str:
        room = self.maze.rooms.get(self.here())
        return room.get('name', '') if room else ''

    def description(self) -> str:
        text = self._place_description()
        if self.won and self.total_treasure():
            text += ' You escaped with %d of %d points of treasure.' % (
                self.treasure(), self.total_treasure())
        return text

    def _place_description(self) -> str:
        here = self.here()
        room = self.maze.rooms.get(here)
        if room and room.get('description'):
            return room['description'].strip()
        if here == DOWN:
            return STEPS_DOWN
        if here == UP:
            return STEPS_UP
        return self.maze.passage

    def steps_in_view(self) -> list[tuple[int, str]]:
        """Steps you can see, as (depth, DOWN or UP); depth 0 is underfoot."""
        found = []
        for depth, (x, y) in enumerate(self._cells_ahead()):
            here = self.maze.cell(x, y, self.level)
            if here in (DOWN, UP):
                found.append((depth, here))
        return found

    def view(self) -> list[tuple[str | None, str | None, str | None]]:
        """What's ahead, nearest first: for each cell up to DEPTH ahead, what's
        on the left, on the right and ahead: WALL, DOOR or None (open).
        Stops at a wall or a locked door."""
        slices = []
        for cell in self._cells_ahead():
            slices.append((self._blocked(self._side(cell, -1)),
                           self._blocked(self._side(cell, 1)),
                           self._blocked(self._ahead(cell))))
        return slices

    def _cells_ahead(self) -> list[tuple[int, int]]:
        cells = [self.position]
        while len(cells) < DEPTH and not self._blocked(self._ahead(cells[-1])):
            cells.append(self._ahead(cells[-1]))
        return cells

    def _ahead(self, cell: tuple[int, int]) -> tuple[int, int]:
        dx, dy = STEPS[self.facing]
        return (cell[0] + dx, cell[1] + dy)

    def _side(self, cell: tuple[int, int], turn: int) -> tuple[int, int]:
        dx, dy = STEPS[(self.facing + turn) % 4]
        return (cell[0] + dx, cell[1] + dy)

    def _look(self) -> None:
        for cell in self._cells_ahead():
            self.seen.add(cell)
            self.seen.add(self._side(cell, -1))
            self.seen.add(self._side(cell, 1))
            self.seen.add(self._ahead(cell))
