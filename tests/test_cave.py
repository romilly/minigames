import glob
import json

import pytest
import yaml

import cave
from cave import Maze, Cave, NORTH, EAST, SOUTH, WEST

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
    assert game.description() == cave.PASSAGE


def test_a_maze_can_set_its_own_passage_text():
    game = Cave(Maze(dict(SPEC, passage='Damp rock.')))
    game.act('forward')
    assert game.description() == 'Damp rock.'


def test_view_looks_ahead_until_a_wall():
    # Facing east from A: (2,1) and (3,1) are open, (4,1) is wall.
    game = Cave(Maze(dict(SPEC, start={'at': 'A', 'facing': 'east'})))
    view = game.view()
    # Each slice: (wall on the left, wall on the right, wall ahead)
    assert view == [(True, False, False),   # at A: north wall, south (1,2) open
                    (True, True, False),    # (2,1): (2,2) is wall
                    (True, False, True)]    # (3,1): (3,2) open, (4,1) wall


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
        assert (a.rows, a.start, a.rooms) == (b.rows, b.start, b.rooms)
        assert any(room.get('goal') for room in a.rooms.values()), path


def test_touches_in_the_view_are_left_forward_right_by_thirds():
    layout = cave.Layout(240, 240, 10)
    assert cave.touch_action((10, 200), layout) == 'left'
    assert cave.touch_action((120, 200), layout) == 'forward'
    assert cave.touch_action((230, 200), layout) == 'right'
    assert cave.touch_action((120, 50), layout) is None      # on the map


class SixPixelFont:
    def size(self, text):
        return (6 * len(text), 8)


def test_wrap_breaks_between_words():
    assert cave.wrap(SixPixelFont(), 'one two three four', 60) == ['one two', 'three four']


def test_wrap_keeps_a_word_too_long_for_a_line():
    assert cave.wrap(SixPixelFont(), 'abcdefghijklmnop x', 30) == ['abcdefghijklmnop', 'x']
