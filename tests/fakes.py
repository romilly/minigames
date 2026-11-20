import minigame as mg


class RecordingDisplay(mg.Display):
    def __init__(self, size=(320, 240)):
        self._size = size
        self.calls = []
        self.frames = 0

    def size(self):
        return self._size

    def fill(self, color):
        self.calls.append(('fill', color))

    def rect(self, color, x, y, w, h):
        self.calls.append(('rect', color, x, y, w, h))

    def circle(self, color, x, y, r):
        self.calls.append(('circle', color, x, y, r))

    def line(self, color, x1, y1, x2, y2):
        self.calls.append(('line', color, x1, y1, x2, y2))

    def text(self, color, text, x, y, scale):
        self.calls.append(('text', color, text, x, y, scale))

    def text_width(self, text, scale):
        return len(text) * 6 * scale

    def text_height(self, scale):
        return 8 * scale

    def update(self):
        self.frames += 1


class RecordingSpeaker(mg.Speaker):
    def __init__(self, timer=None):
        self.timer = timer
        self.calls = []

    def _now(self):
        return self.timer.now_ms() if self.timer else None

    def play(self, frequency):
        self.calls.append(('play', frequency, self._now()))

    def stop(self):
        self.calls.append(('stop', self._now()))


class ScriptedButtons(mg.Buttons):
    """Returns each set in turn, then the last one forever."""

    def __init__(self, *frames):
        self._frames = list(frames) or [set()]

    def pressed(self):
        if len(self._frames) > 1:
            return set(self._frames.pop(0))
        return set(self._frames[0])


class FakeTimer(mg.Timer):
    def __init__(self):
        self.t = 0
        self.slept = []

    def now_ms(self):
        return self.t

    def sleep_ms(self, ms):
        self.slept.append(ms)
        self.t += ms


class FakeGraphics:
    """Stands in for PicoGraphics."""

    def __init__(self):
        self.calls = []

    def create_pen(self, r, g, b):
        self.calls.append(('create_pen', r, g, b))
        return (r, g, b)

    def set_pen(self, pen):
        self.calls.append(('set_pen', pen))

    def measure_text(self, text, scale):
        return len(text) * 6 * scale

    def __getattr__(self, name):
        return lambda *args: self.calls.append((name,) + args)


class FakePad:
    """Stands in for qwstpad.QwSTPad: mutates and returns one dict, like the real one."""

    def __init__(self):
        self.states = dict((k, False) for k in 'ABXYUDLR+-')

    def read_buttons(self):
        return self.states


def fake_pygame(buttons=None, display=None, timer=None, speaker=None):
    return mg.Pygame(display or RecordingDisplay(),
                     buttons or ScriptedButtons(),
                     timer or FakeTimer(),
                     speaker)
