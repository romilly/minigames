"""Where mazes come from: a port, and adapters for YAML and JSON files.

Players write mazes as YAML in mazes/. MicroPython has no YAML parser, so
scripts/deploy.sh copies each one to the top of the board's filesystem as
JSON. maze_files() picks whichever this machine can read.
"""
from cave_core import Maze


class Mazes:
    """The port: gives you a Maze by name."""

    def load(self, name: str) -> Maze:
        raise NotImplementedError


class YamlMazes(Mazes):
    """mazes/<name>.yaml, as players write them. Needs PyYAML (the desktop)."""

    def __init__(self, folder: str = 'mazes') -> None:
        self.folder = folder

    def load(self, name: str) -> Maze:
        import yaml
        with open('%s/%s.yaml' % (self.folder, name)) as f:
            return Maze(yaml.safe_load(f))


class JsonMazes(Mazes):
    """<name>.json, as deploy.sh puts them on the board: at the top, by default."""

    def __init__(self, folder: str = '') -> None:
        self.folder = folder

    def load(self, name: str) -> Maze:
        import json
        path = '%s/%s.json' % (self.folder, name) if self.folder else name + '.json'
        with open(path) as f:
            return Maze(json.load(f))


def maze_files() -> Mazes:
    """YAML where PyYAML is installed (the desktop); otherwise the JSON copies."""
    try:
        import yaml                                    # noqa: F401
    except ImportError:
        return JsonMazes()
    return YamlMazes()
