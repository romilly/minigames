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


def test_touches_beside_the_view_turn_and_on_it_step_forward():
    layout = cave.Layout(240, 240, 22)
    y = layout.view_y + 5
    assert cave.touch_action((layout.view_x - 1, y), layout) == 'left'
    assert cave.touch_action((120, y), layout) == 'forward'
    assert cave.touch_action((layout.view_x + layout.view_w, y), layout) == 'right'
    assert cave.touch_action((120, layout.view_y - 1), layout) is None   # above the view


@pytest.mark.parametrize('size', [(240, 240), (320, 240)])
def test_layout_stacks_toolbar_map_text_and_view(size):
    layout = cave.Layout(size[0], size[1], 22)
    assert layout.toolbar_h >= 22
    assert layout.toolbar_h <= layout.map_y
    assert layout.map_y + layout.map_h <= layout.text_y
    assert layout.text_y + cave.DESCRIPTION_LINES * 22 <= layout.view_y
    assert layout.view_y + layout.view_h == size[1]
    assert layout.view_h < size[1] // 3                        # a strip, not half the screen
    assert layout.view_w == 2 * layout.view_h                  # the corridor keeps its shape
    assert layout.view_x * 2 + layout.view_w == size[0]        # centred, room either side
    assert layout.map_h >= 7 * 10                              # mine.yaml at 10px a cell


class SixPixelFont:
    def size(self, text):
        return (6 * len(text), 8)


def test_wrap_breaks_between_words():
    assert cave.wrap(SixPixelFont(), 'one two three four', 60) == ['one two', 'three four']


def test_wrap_keeps_a_word_too_long_for_a_line():
    assert cave.wrap(SixPixelFont(), 'abcdefghijklmnop x', 30) == ['abcdefghijklmnop', 'x']
