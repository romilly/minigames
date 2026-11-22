import json
import sys

import pytest

from cave_core import Maze
from cave_mazes import Mazes, YamlMazes, JsonMazes, maze_files

SPEC = {'title': 'Tiny', 'start': {'at': 'A'}, 'map': '###\n#A#\n###'}
YAML = "title: Tiny\nstart: {at: A}\nmap: |\n  ###\n  #A#\n  ###\n"


def test_yaml_mazes_load_from_their_folder(tmp_path):
    (tmp_path / 'tiny.yaml').write_text(YAML)
    maze = YamlMazes(str(tmp_path)).load('tiny')
    assert isinstance(maze, Maze) and maze.title == 'Tiny' and maze.start == (1, 1)


def test_json_mazes_load_from_their_folder(tmp_path):
    (tmp_path / 'tiny.json').write_text(json.dumps(SPEC))
    maze = JsonMazes(str(tmp_path)).load('tiny')
    assert maze.title == 'Tiny' and maze.start == (1, 1)


def test_json_mazes_on_the_board_live_at_the_top(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    (tmp_path / 'tiny.json').write_text(json.dumps(SPEC))
    assert JsonMazes().load('tiny').title == 'Tiny'


def test_both_kinds_are_mazes():
    assert isinstance(YamlMazes(), Mazes) and isinstance(JsonMazes(), Mazes)


def test_the_port_itself_loads_nothing():
    with pytest.raises(NotImplementedError):
        Mazes().load('tiny')


def test_with_pyyaml_we_read_the_yaml_files():
    files = maze_files()
    assert isinstance(files, YamlMazes)
    assert files.load('mine').title == 'The Old Mine'


def test_without_pyyaml_we_read_the_json_copies(monkeypatch):
    monkeypatch.setitem(sys.modules, 'yaml', None)       # as on the board
    assert isinstance(maze_files(), JsonMazes)
