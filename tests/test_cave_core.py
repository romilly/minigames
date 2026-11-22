import glob
import importlib
import json
import sys

import pytest
import yaml

import cave_core as core
from cave_core import Maze, Cave, Kind, NORTH, EAST, SOUTH, WEST


def test_the_core_does_not_need_pygame(monkeypatch):
    monkeypatch.setitem(sys.modules, 'pygame', None)     # importing pygame now fails
    monkeypatch.delitem(sys.modules, 'cave_core', raising=False)
    importlib.import_module('cave_core')


SPEC = {
    'title': 'Test maze',
    'start': {'at': 'A', 'facing': 'south'},
    'map': '#####\n'
           '#A  #\n'
           '# # #\n'
           '#  B#\n'
           '#####\n',
    'rooms': {
        'A': {'name': 'Entrance', 'description': 'Daylight behind you.'},
        'B': {'name': 'Exit', 'description': 'Fresh air!', 'goal': True},
    },
}


def test_maze_reads_the_map():
    maze = Maze(SPEC)
    assert (maze.width, maze.height) == (5, 5)
    assert maze.is_wall(0, 0)
    assert not maze.is_wall(1, 1)
    assert not maze.is_wall(2, 1)


def test_outside_the_map_is_wall():
    maze = Maze(SPEC)
    assert maze.is_wall(-1, 2) and maze.is_wall(5, 2) and maze.is_wall(2, 99)


def test_short_map_lines_are_padded_with_open_space():
    maze = Maze({'map': '###\n#\n###'})
    assert maze.width == 3
    assert not maze.is_wall(2, 1)


def test_start_is_a_room_letter_and_a_facing():
    maze = Maze(SPEC)
    assert maze.start == (1, 1)
    assert maze.start_facing == SOUTH


def test_start_can_be_coordinates():
    spec = dict(SPEC, start={'at': [3, 1], 'facing': 'west'})
    maze = Maze(spec)
    assert (maze.start, maze.start_facing) == ((3, 1), WEST)


def test_without_a_start_you_begin_in_the_first_open_cell_facing_north():
    maze = Maze({'map': '###\n# #\n###'})
    assert (maze.start, maze.start_facing) == ((1, 1), NORTH)


def test_a_start_room_missing_from_the_map_is_an_error():
    with pytest.raises(ValueError, match='Z'):
        Maze(dict(SPEC, start={'at': 'Z'}))


def test_a_described_room_missing_from_the_map_is_an_error():
    rooms = dict(SPEC['rooms'], Q={'name': 'Nowhere'})
    with pytest.raises(ValueError, match='Q'):
        Maze(dict(SPEC, rooms=rooms))


def test_moving_forward_and_bumping():
    game = Cave(Maze(SPEC))                 # at A, facing south
    assert game.act('forward') == ['step']
    assert game.position == (1, 2)
    assert game.act('left') == ['turn']     # south, turn left: east
    assert game.facing == EAST
    assert game.act('forward') == ['bump']  # (2, 2) is a wall
    assert game.position == (1, 2)


def test_turning_round():
    game = Cave(Maze(SPEC))
    game.act('around')
    assert game.facing == NORTH
    game.act('right')
    assert game.facing == EAST


def test_reaching_the_goal_wins_and_any_action_then_restarts():
    game = Cave(Maze(SPEC))
    for action in ('forward', 'forward', 'left', 'forward', 'forward'):
        happened = game.act(action)
    assert happened == ['win'] and game.won
    assert game.act('left') == ['new']
    assert not game.won and game.position == (1, 1) and game.facing == SOUTH


def test_text_for_rooms_and_plain_passage():
    game = Cave(Maze(SPEC))
    assert (game.room_name(), game.description()) == ('Entrance', 'Daylight behind you.')
    game.act('forward')
    assert game.room_name() == ''
    assert game.description() == core.PASSAGE


def test_a_maze_can_set_its_own_passage_text():
    game = Cave(Maze(dict(SPEC, passage='Damp rock.')))
    game.act('forward')
    assert game.description() == 'Damp rock.'


def test_view_looks_ahead_until_a_wall():
    # Facing east from A: (2,1) and (3,1) are open, (4,1) is wall.
    game = Cave(Maze(dict(SPEC, start={'at': 'A', 'facing': 'east'})))
    view = game.view()
    # Each slice: what's on the left, on the right and ahead: WALL, DOOR or None
    W = core.WALL
    assert view == [(W, None, None),        # at A: north wall, south (1,2) open
                    (W, W, None),           # (2,1): (2,2) is wall
                    (W, None, W)]           # (3,1): (3,2) open, (4,1) wall


def test_what_you_have_seen_is_remembered():
    game = Cave(Maze(dict(SPEC, start={'at': 'A', 'facing': 'east'})))
    assert {(1, 1), (2, 1), (3, 1), (4, 1), (1, 2), (3, 2), (2, 2)} <= game.seen
    assert (1, 3) not in game.seen
    game.act('right')                         # now facing south
    assert (1, 3) in game.seen


def test_the_sample_mazes_load_from_yaml_and_from_json():
    paths = glob.glob('mazes/*.yaml')
    assert paths
    for path in paths:
        with open(path) as f:
            spec = yaml.safe_load(f)
        a, b = Maze(spec), Maze(json.loads(json.dumps(spec)))
        assert (a.levels, a.start, a.start_level, a.rooms) == (b.levels, b.start, b.start_level, b.rooms)
        assert any(room.get('goal') for room in a.rooms.values()), path


# ---- Steps between levels ----

TWO_LEVELS = {
    'start': {'at': 'A', 'facing': 'east'},
    'levels': [
        {'map': '#####\n'
                '#A >#\n'
                '#####\n'},
        {'map': '#####\n'
                '#B <#\n'
                '#####\n'},
    ],
    'rooms': {'A': {'name': 'Top'}, 'B': {'name': 'Bottom', 'goal': True}},
}


def test_a_maze_can_have_levels():
    maze = Maze(TWO_LEVELS)
    assert len(maze.levels) == 2
    assert maze.is_wall(1, 1, 0) is False and maze.room(1, 1, 1)['name'] == 'Bottom'


def test_rooms_and_the_start_can_be_on_any_level():
    maze = Maze(dict(TWO_LEVELS, start={'at': 'B', 'facing': 'east'}))
    assert (maze.start, maze.start_level) == ((1, 1), 1)
    maze = Maze(dict(TWO_LEVELS, start={'at': [2, 1, 2]}))   # levels count from 1
    assert (maze.start, maze.start_level) == ((2, 1), 1)


def test_stepping_onto_steps_down_takes_you_to_the_level_below():
    game = Cave(Maze(TWO_LEVELS))
    assert game.act('forward') == ['step']
    assert game.act('forward') == ['steps']
    assert (game.level, game.position, game.facing) == (1, (3, 1), EAST)
    assert game.description() == core.STEPS_UP


def test_turning_on_steps_does_not_change_level():
    game = Cave(Maze(TWO_LEVELS))
    game.act('forward'), game.act('forward')
    game.act('around')
    assert game.level == 1


def test_stepping_onto_steps_up_takes_you_back_up():
    game = Cave(Maze(dict(TWO_LEVELS, start={'at': 'B', 'facing': 'east'})))
    game.act('forward')
    assert game.act('forward') == ['steps']
    assert (game.level, game.position) == (0, (3, 1))
    assert game.description() == core.STEPS_DOWN


def test_you_can_win_on_another_level():
    game = Cave(Maze(TWO_LEVELS))
    for action in ('forward', 'forward', 'around', 'forward'):
        game.act(action)
    assert game.act('forward') == ['win']
    game.act('forward')                                  # start again
    assert (game.level, game.position) == (0, (1, 1))


def test_each_level_remembers_what_you_have_seen():
    game = Cave(Maze(TWO_LEVELS))
    game.act('forward'), game.act('forward')             # down the steps
    game.act('around')
    assert (1, 1) in game.seen                           # B, on this level
    game.act('forward'), game.act('around')
    game.act('forward')                                  # back up the steps
    assert game.level == 0
    assert (2, 1) in game.seen and (4, 1) in game.seen   # level 0's, from before


def test_steps_down_need_steps_up_at_the_same_place_below():
    spec = dict(TWO_LEVELS, levels=[TWO_LEVELS['levels'][0],
                                    {'map': '#####\n#B< #\n#####\n'}])
    with pytest.raises(ValueError, match='steps'):
        Maze(spec)


def test_steps_down_on_the_bottom_level_are_an_error():
    with pytest.raises(ValueError, match='steps'):
        Maze({'map': '#####\n#A >#\n#####\n'})


def test_steps_up_on_the_top_level_are_an_error():
    with pytest.raises(ValueError, match='steps'):
        Maze({'map': '#####\n#A <#\n#####\n'})


def test_levels_are_padded_to_the_same_size():
    maze = Maze({'levels': [{'map': '#####\n#A >#\n#####'},
                            {'map': '###\n#  <#\n#   #\n#####'}]})
    assert (maze.width, maze.height) == (5, 4)
    assert maze.is_wall(4, 3, 0)


def test_the_view_shows_steps_ahead_and_underfoot():
    game = Cave(Maze(TWO_LEVELS))
    assert game.steps_in_view() == [(2, '>')]
    game.act('forward'), game.act('forward')
    assert game.steps_in_view() == [(0, '<')]


# ---- Objects and treasure ----

TREASURE = dict(SPEC, objects={
    'nugget': {'name': 'gold nugget', 'description': 'It gleams.', 'at': 'A', 'value': 10},
    'ring': {'name': 'silver ring', 'at': [2, 1], 'value': 5},
    'rope': {'name': 'rope', 'at': 'A'},
})


def test_objects_start_where_the_maze_puts_them():
    game = Cave(Maze(TREASURE))
    assert game.objects_here() == ['nugget', 'rope']        # sorted by id
    game.act('left')                                          # face east
    game.act('forward')
    assert game.objects_here() == ['ring']


def test_an_object_somewhere_not_on_the_map_is_an_error():
    spec = dict(SPEC, objects={'x': {'name': 'x', 'at': 'Q'}})
    with pytest.raises(ValueError, match='Q'):
        Maze(spec)


def test_take_and_drop():
    game = Cave(Maze(TREASURE))
    assert game.do(('take', 'nugget')) == ['take']
    assert game.carried() == ['nugget'] and game.objects_here() == ['rope']
    assert game.message == 'Taken: gold nugget.'
    game.act('forward')
    assert game.message is None                               # moving clears it
    assert game.do(('drop', 'nugget')) == ['drop']
    assert game.carried() == [] and game.objects_here() == ['nugget']


def test_you_cannot_take_what_is_not_here():
    game = Cave(Maze(TREASURE))
    assert game.do(('take', 'ring')) == []
    assert game.carried() == []


def test_the_menu_offers_what_you_can_do_here():
    game = Cave(Maze(TREASURE))
    game.do(('take', 'rope'))
    assert game.menu_items() == [('Take gold nugget', ('take', 'nugget')),
                                 ('Drop rope', ('drop', 'rope')),
                                 ('Inventory', ('inventory',))]


def test_inventory_lists_what_you_carry_and_its_value():
    game = Cave(Maze(TREASURE))
    game.do(('inventory',))
    assert game.message == 'You are carrying nothing.'
    game.do(('take', 'nugget')), game.do(('take', 'rope'))
    game.do(('inventory',))
    assert game.message == 'You are carrying: gold nugget, rope. Treasure: 10.'


def test_escaping_counts_the_treasure_you_carry():
    game = Cave(Maze(TREASURE))
    game.do(('take', 'nugget'))
    for action in ('forward', 'forward', 'left', 'forward', 'forward'):
        game.act(action)
    assert game.won
    assert 'You escaped with 10 of 15 points of treasure.' in game.description()


def test_starting_again_puts_everything_back():
    game = Cave(Maze(TREASURE))
    game.do(('take', 'nugget'))
    game.restart()
    assert game.carried() == [] and game.objects_here() == ['nugget', 'rope']


def test_the_view_shows_objects_ahead():
    game = Cave(Maze(dict(TREASURE, start={'at': 'A', 'facing': 'east'})))
    assert game.objects_in_view() == [0, 1]                   # underfoot and one ahead
    game.do(('take', 'nugget')), game.do(('take', 'rope'))
    assert game.objects_in_view() == [1]


def test_objects_can_be_on_another_level():
    spec = dict(TWO_LEVELS, objects={'gem': {'name': 'gem', 'at': 'B', 'value': 25}})
    assert Cave(Maze(spec)).objects_here() == []
    assert Cave(Maze(dict(spec, start={'at': 'B'}))).objects_here() == ['gem']


def test_actions_do_nothing_once_you_have_won():
    game = Cave(Maze(dict(TREASURE, start={'at': 'B'})))
    game.won = True
    assert game.do(('inventory',)) == []


# ---- Keys and doors ----

DOOR = {
    'start': {'at': 'A', 'facing': 'east'},
    'map': '#######\n'
           '#A F B#\n'
           '#######\n',
    'rooms': {'F': {'name': 'Iron door', 'description': 'A heavy door.', 'needs': 'key'},
              'B': {'name': 'Vault', 'goal': True}},
    'objects': {'key': {'name': 'iron key', 'at': 'A'}},
}


def test_a_door_needs_an_object_the_maze_has():
    rooms = dict(DOOR['rooms'], F={'needs': 'crowbar'})
    with pytest.raises(ValueError, match='crowbar'):
        Maze(dict(DOOR, rooms=rooms))


def test_a_locked_door_bars_the_way():
    game = Cave(Maze(DOOR))
    game.act('forward')
    assert game.act('forward') == ['locked']
    assert game.position == (2, 1)
    assert game.message == 'The iron door is locked.'


def test_the_key_unlocks_the_door_and_it_stays_unlocked():
    game = Cave(Maze(DOOR))
    game.do(('take', 'key'))
    game.act('forward')
    assert game.act('forward') == ['unlock']
    assert game.position == (3, 1)
    assert game.message == 'You unlock the iron door with the iron key.'
    game.do(('drop', 'key'))
    game.act('around'), game.act('forward')
    game.act('around')
    assert game.act('forward') == ['step']               # back through, without the key


def test_a_locked_door_blocks_the_view_and_an_open_one_does_not():
    game = Cave(Maze(DOOR))
    assert game.view() == [(core.WALL, core.WALL, None),
                           (core.WALL, core.WALL, core.DOOR)]
    assert (5, 1) not in game.seen
    game.do(('take', 'key'))
    game.act('forward'), game.act('forward')
    assert (5, 1) in game.seen


def test_starting_again_locks_the_doors():
    game = Cave(Maze(DOOR))
    game.do(('take', 'key'))
    game.act('forward'), game.act('forward')
    game.restart()
    game.act('forward')
    assert game.act('forward') == ['locked']


def test_a_door_can_be_the_goal_side_of_the_maze():
    game = Cave(Maze(DOOR))
    game.do(('take', 'key'))
    assert [game.act('forward') for _ in range(4)] == [['step'], ['unlock'], ['step'], ['win']]


def reachable(maze, start, open_doors):
    """Every (x, y, level) you can walk to, with these door letters open."""
    seen, todo = {start}, [start]
    while todo:
        x, y, level = todo.pop()
        for dx, dy in core.STEPS:
            nx, ny = x + dx, y + dy
            here = maze.cell(nx, ny, level)
            room = maze.rooms.get(here)
            if here == core.WALL or (room and room.get('needs') and here not in open_doors):
                continue
            nlevel = level + (1 if here == core.DOWN else -1 if here == core.UP else 0)
            if (nx, ny, nlevel) not in seen:
                seen.add((nx, ny, nlevel))
                todo.append((nx, ny, nlevel))
    return seen


def test_the_sample_maze_can_be_won_but_only_with_the_key():
    with open('mazes/mine.yaml') as f:
        maze = Maze(yaml.safe_load(f))
    start = maze.start + (maze.start_level,)
    goal = maze.find('E')
    assert goal not in reachable(maze, start, set())
    assert maze.object_starts['key'] in reachable(maze, start, set())
    assert goal in reachable(maze, start, {'F'})
    everything = reachable(maze, start, {'F'})
    assert all(maze.object_starts[t] in everything for t in maze.objects)


# ---- What the map shows ----

def map_of(game):
    return dict(((x, y), (kind, objects)) for x, y, kind, objects in game.map_cells())


def test_the_map_says_what_each_seen_cell_is():
    game = Cave(Maze(dict(SPEC, start={'at': 'A', 'facing': 'east'})))
    cells = map_of(game)
    assert cells[(1, 1)] == (Kind.ROOM, False)
    assert cells[(2, 1)] == (Kind.PASSAGE, False)
    assert cells[(1, 0)] == (Kind.ROCK, False)
    assert (1, 3) not in cells                        # not seen yet


def test_the_map_shows_goals_steps_and_objects():
    game = Cave(Maze(dict(TREASURE, start={'at': 'B', 'facing': 'west'})))
    cells = map_of(game)
    assert cells[(3, 3)] == (Kind.GOAL, False)
    game = Cave(Maze(TWO_LEVELS))
    assert map_of(game)[(3, 1)] == (Kind.DOWN, False)
    game = Cave(Maze(TREASURE))
    assert map_of(game)[(1, 1)] == (Kind.ROOM, True)


def test_the_map_shows_doors_locked_then_open():
    game = Cave(Maze(DOOR))
    assert map_of(game)[(3, 1)] == (Kind.DOOR, False)
    game.do(('take', 'key'))
    game.act('forward'), game.act('forward')
    assert map_of(game)[(3, 1)] == (Kind.OPEN_DOOR, False)


def test_an_object_with_nowhere_to_be_is_an_error():
    spec = dict(SPEC, objects={'lamp': {'name': 'lamp'}})
    with pytest.raises(ValueError, match="lamp.*at"):
        Maze(spec)
