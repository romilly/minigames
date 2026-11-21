"""board/pygame.py, loaded on CPython with fake hardware modules."""
import importlib.util
import os
import sys
import types

import minigame as mg
from fakes import FakeGraphics, FakePad

BOARD_FILE = os.path.join(os.path.dirname(__file__), '..', 'board', 'pygame.py')


class FakePin:
    def __init__(self):
        self.v = 1

    def value(self):
        return self.v


def fake_qwstpad(present=True):
    qwstpad = types.ModuleType('qwstpad')
    qwstpad.DEFAULT_ADDRESS = 0x21
    qwstpad.made = []

    def QwSTPad(i2c, address):
        if not present:
            raise OSError(5)
        qwstpad.made.append((i2c, address))
        return FakePad()

    qwstpad.QwSTPad = QwSTPad
    return qwstpad


def fake_explorer():
    explorer = types.ModuleType('explorer')
    explorer.display = FakeGraphics()
    explorer.i2c = 'explorer-i2c'
    explorer.tones = []
    explorer.play_tone = explorer.tones.append
    explorer.stop_playing = lambda: explorer.tones.append('stop')
    for name in 'abcxyz':
        setattr(explorer, 'button_' + name, FakePin())
    return explorer


def fake_presto_modules():
    presto = types.ModuleType('presto')
    presto.updates = []
    presto.buzzers = []

    class Presto:
        def __init__(self):
            self.display = FakeGraphics()

        def update(self):
            presto.updates.append(True)

    class Buzzer:
        def __init__(self, pin):
            presto.buzzers.append(pin)
            self.tones = []

        def set_tone(self, f):
            self.tones.append(f)

    presto.Presto = Presto
    presto.Buzzer = Buzzer
    machine = types.ModuleType('machine')
    machine.I2C = lambda id, sda, scl: ('I2C', id, sda, scl)
    return presto, machine


def load_board(monkeypatch, **modules):
    monkeypatch.setattr(mg.time, 'ticks_ms', lambda: 0, raising=False)
    monkeypatch.setattr(mg.time, 'ticks_diff', lambda a, b: a - b, raising=False)
    monkeypatch.setattr(mg.time, 'sleep_ms', lambda ms: None, raising=False)
    for name, module in modules.items():
        monkeypatch.setitem(sys.modules, name, module)
    spec = importlib.util.spec_from_file_location('board_pygame', BOARD_FILE)
    board = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(board)
    return board


def test_on_the_explorer(monkeypatch):
    explorer, qwstpad = fake_explorer(), fake_qwstpad()
    board = load_board(monkeypatch, explorer=explorer, qwstpad=qwstpad)
    assert board.BOARD == 'explorer'
    assert qwstpad.made == [('explorer-i2c', 0x21)]
    board.display.flip()
    assert ('update',) in explorer.display.calls
    board.tone(440, 10).play()
    assert explorer.tones == [440]


def test_on_the_explorer_without_a_pad_its_buttons_stand_in(monkeypatch, capsys):
    explorer = fake_explorer()
    board = load_board(monkeypatch, explorer=explorer, qwstpad=fake_qwstpad(present=False))
    explorer.button_b.v = 0
    events = board.event.get()
    assert [(e.type, e.key) for e in events] == [(mg.KEYDOWN, mg.K_a)]
    assert 'No Qw/ST Pad' in capsys.readouterr().out


def test_on_the_presto(monkeypatch):
    presto, machine = fake_presto_modules()
    qwstpad = fake_qwstpad()
    board = load_board(monkeypatch, explorer=None, presto=presto, machine=machine,
                       qwstpad=qwstpad)
    assert board.BOARD == 'presto'
    assert qwstpad.made == [(('I2C', 0, 40, 41), 0x21)]
    assert presto.buzzers == [43]
    board.display.flip()
    assert presto.updates == [True]
    board.tone(440, 10).play()
    board.quit()


def test_on_the_presto_without_a_pad(monkeypatch, capsys):
    presto, machine = fake_presto_modules()
    board = load_board(monkeypatch, explorer=None, presto=presto, machine=machine,
                       qwstpad=fake_qwstpad(present=False))
    assert board.event.get() == []
    assert 'No Qw/ST Pad' in capsys.readouterr().out
