"""A small subset of the pygame API, for MicroPython on the Pimoroni Explorer.

Ports (Display, Buttons, Timer) are plain base classes because MicroPython
has no abc module. Adapters for PicoGraphics and the Qw/ST Pad take the
hardware objects as arguments, so everything here can be tested on CPython.

Supported: Rect, display.set_mode/flip, Surface.fill/blit, draw.rect/circle/line
(filled shapes only), font.Font(None, size).render (one bitmap font; size sets
the scale), event.get (KEYDOWN/KEYUP), key.get_pressed, time.Clock.tick,
init/quit, and tone(frequency, ms).play(): not pygame, but tones.py gives games
the same call on the desktop. One note at a time; display.flip() ends notes.
"""

import time

# Event types and key constants. The values differ from pygame's;
# game code should only use the names.
QUIT = 256
KEYDOWN = 768
KEYUP = 769

K_UP = 1
K_DOWN = 2
K_LEFT = 3
K_RIGHT = 4
K_a = 5
K_b = 6
K_x = 7
K_y = 8
K_RETURN = 9
K_ESCAPE = 10
K_SPACE = 11

ALL_KEYS = (K_UP, K_DOWN, K_LEFT, K_RIGHT, K_a, K_b, K_x, K_y,
            K_RETURN, K_ESCAPE, K_SPACE)

PAD_KEYS = {'U': K_UP, 'D': K_DOWN, 'L': K_LEFT, 'R': K_RIGHT,
            'A': K_a, 'B': K_b, 'X': K_x, 'Y': K_y,
            '+': K_RETURN, '-': K_ESCAPE}


class Rect:
    def __init__(self, *args):
        if len(args) == 1:
            args = tuple(args[0])
        if len(args) == 2:
            args = tuple(args[0]) + tuple(args[1])
        x, y, w, h = args
        self.x, self.y, self.w, self.h = int(x), int(y), int(w), int(h)

    def __iter__(self):
        return iter((self.x, self.y, self.w, self.h))

    def __len__(self):
        return 4

    def __getitem__(self, i):
        return (self.x, self.y, self.w, self.h)[i]

    def __eq__(self, other):
        return tuple(self) == tuple(other)

    def __repr__(self):
        return 'Rect(%d, %d, %d, %d)' % tuple(self)

    def copy(self):
        return Rect(self.x, self.y, self.w, self.h)

    @property
    def width(self):
        return self.w

    @width.setter
    def width(self, value):
        self.w = int(value)

    @property
    def height(self):
        return self.h

    @height.setter
    def height(self, value):
        self.h = int(value)

    @property
    def left(self):
        return self.x

    @left.setter
    def left(self, value):
        self.x = int(value)

    @property
    def top(self):
        return self.y

    @top.setter
    def top(self, value):
        self.y = int(value)

    @property
    def right(self):
        return self.x + self.w

    @right.setter
    def right(self, value):
        self.x = int(value) - self.w

    @property
    def bottom(self):
        return self.y + self.h

    @bottom.setter
    def bottom(self, value):
        self.y = int(value) - self.h

    @property
    def centerx(self):
        return self.x + self.w // 2

    @centerx.setter
    def centerx(self, value):
        self.x = int(value) - self.w // 2

    @property
    def centery(self):
        return self.y + self.h // 2

    @centery.setter
    def centery(self, value):
        self.y = int(value) - self.h // 2

    @property
    def center(self):
        return (self.centerx, self.centery)

    @center.setter
    def center(self, value):
        self.centerx, self.centery = value

    def move(self, dx, dy):
        return Rect(self.x + int(dx), self.y + int(dy), self.w, self.h)

    def move_ip(self, dx, dy):
        self.x += int(dx)
        self.y += int(dy)

    def colliderect(self, other):
        other = Rect(other)
        return (self.x < other.x + other.w and other.x < self.x + self.w and
                self.y < other.y + other.h and other.y < self.y + self.h)

    def collidepoint(self, *point):
        if len(point) == 1:
            point = point[0]
        px, py = point
        return self.x <= px < self.x + self.w and self.y <= py < self.y + self.h

    def clamp_ip(self, other):
        other = Rect(other)
        if self.w >= other.w:
            self.x = other.x + other.w // 2 - self.w // 2
        else:
            self.x = min(max(self.x, other.x), other.x + other.w - self.w)
        if self.h >= other.h:
            self.y = other.y + other.h // 2 - self.h // 2
        else:
            self.y = min(max(self.y, other.y), other.y + other.h - self.h)

    def clamp(self, other):
        r = self.copy()
        r.clamp_ip(other)
        return r


# ---- Ports ----

class Display:
    """Where drawing goes. Colours are (r, g, b) tuples."""

    def size(self):
        raise NotImplementedError

    def fill(self, color):
        raise NotImplementedError

    def rect(self, color, x, y, w, h):
        raise NotImplementedError

    def circle(self, color, x, y, r):
        raise NotImplementedError

    def line(self, color, x1, y1, x2, y2):
        raise NotImplementedError

    def text(self, color, text, x, y, scale):
        raise NotImplementedError

    def text_width(self, text, scale):
        raise NotImplementedError

    def text_height(self, scale):
        raise NotImplementedError

    def update(self):
        raise NotImplementedError


class Buttons:
    """Reports which keys are held down, as a set of K_ constants."""

    def pressed(self):
        raise NotImplementedError


class Speaker:
    """Plays one note at a time."""

    def play(self, frequency):
        raise NotImplementedError

    def stop(self):
        raise NotImplementedError


class SilentSpeaker(Speaker):
    def play(self, frequency):
        pass

    def stop(self):
        pass


class Timer:
    def now_ms(self):
        raise NotImplementedError

    def sleep_ms(self, ms):
        raise NotImplementedError

    def diff_ms(self, later, earlier):
        return later - earlier


# ---- Adapters ----

class PicoGraphicsDisplay(Display):
    FONT = 'bitmap8'
    FONT_HEIGHT = 8

    def __init__(self, graphics, update=None):
        """update: what shows the frame. The Explorer uses graphics.update
        (the default); the Presto uses presto.update."""
        self._g = graphics
        self._update = update or graphics.update
        self._pens = {}
        self._g.set_font(self.FONT)

    def _use(self, color):
        color = tuple(color[:3])
        pen = self._pens.get(color)
        if pen is None:
            pen = self._g.create_pen(*color)
            self._pens[color] = pen
        self._g.set_pen(pen)

    def size(self):
        return tuple(self._g.get_bounds())

    def fill(self, color):
        self._use(color)
        self._g.clear()

    def rect(self, color, x, y, w, h):
        self._use(color)
        self._g.rectangle(x, y, w, h)

    def circle(self, color, x, y, r):
        self._use(color)
        self._g.circle(x, y, r)

    def line(self, color, x1, y1, x2, y2):
        self._use(color)
        self._g.line(x1, y1, x2, y2)

    def text(self, color, text, x, y, scale):
        self._use(color)
        self._g.text(text, x, y, -1, scale)

    def text_width(self, text, scale):
        return self._g.measure_text(text, scale)

    def text_height(self, scale):
        return self.FONT_HEIGHT * scale

    def update(self):
        self._update()


class QwstPadButtons(Buttons):
    """Adapts Pimoroni's QwSTPad (read_buttons() -> {'U': bool, ...})."""

    def __init__(self, pad):
        self._pad = pad

    def pressed(self):
        states = self._pad.read_buttons()
        return set(PAD_KEYS[name] for name in PAD_KEYS if states.get(name))


class ExplorerSpeaker(Speaker):
    """Adapts the explorer module's play_tone and stop_playing functions."""

    def __init__(self, play_tone, stop_playing):
        self._play_tone = play_tone
        self._stop_playing = stop_playing

    def play(self, frequency):
        self._play_tone(int(frequency))

    def stop(self):
        self._stop_playing()


class BuzzerSpeaker(Speaker):
    """Adapts the Presto's Buzzer (set_tone(f); set_tone(-1) is silence)."""

    def __init__(self, buzzer):
        self._buzzer = buzzer

    def play(self, frequency):
        self._buzzer.set_tone(int(frequency))

    def stop(self):
        self._buzzer.set_tone(-1)


# The Explorer's own buttons, for when there's no pad. Left column A, B, C;
# right column X, Y, Z.
EXPLORER_KEYS = {'A': K_UP, 'B': K_a, 'C': K_DOWN,
                 'X': K_LEFT, 'Y': K_RETURN, 'Z': K_RIGHT}


class PinButtons(Buttons):
    """Buttons on GPIO pins that read 0 when pressed, like the Explorer's."""

    def __init__(self, pins, keys=EXPLORER_KEYS):
        self._pins = pins          # {'A': Pin, ...}
        self._keys = keys

    def pressed(self):
        return set(self._keys[name] for name in self._pins
                   if self._pins[name].value() == 0)


class NoButtons(Buttons):
    def pressed(self):
        return set()


def pad_or(make_pad, fallback, say=print):
    """The pad's Buttons if it answers, otherwise the fallback."""
    try:
        return QwstPadButtons(make_pad())
    except OSError:
        say('No Qw/ST Pad found: check the cable. Using the board instead.')
        return fallback


class TicksTimer(Timer):
    """MicroPython's time.ticks_ms, which wraps around."""

    def now_ms(self):
        return time.ticks_ms()

    def sleep_ms(self, ms):
        time.sleep_ms(ms)

    def diff_ms(self, later, earlier):
        return time.ticks_diff(later, earlier)


# ---- The pygame-shaped API ----

class Event:
    def __init__(self, type, key=None):
        self.type = type
        self.key = key

    def __repr__(self):
        return 'Event(%d, %r)' % (self.type, self.key)


class Surface:
    """The screen. Off-screen surfaces are not supported."""

    def __init__(self, display):
        self._display = display

    def get_size(self):
        return self._display.size()

    def get_width(self):
        return self.get_size()[0]

    def get_height(self):
        return self.get_size()[1]

    def get_rect(self):
        w, h = self.get_size()
        return Rect(0, 0, w, h)

    def fill(self, color):
        self._display.fill(color)

    def blit(self, source, dest):
        x, y = dest[0], dest[1]
        source._draw_on(self._display, int(x), int(y))
        return Rect(int(x), int(y), source.get_width(), source.get_height())


class TextSurface:
    """What Font.render returns. It can only be blitted to the screen."""

    def __init__(self, display, text, color, scale):
        self._display = display
        self._text = text
        self._color = color
        self._scale = scale

    def _draw_on(self, display, x, y):
        display.text(self._color, self._text, x, y, self._scale)

    def get_width(self):
        return self._display.text_width(self._text, self._scale)

    def get_height(self):
        return self._display.text_height(self._scale)

    def get_size(self):
        return (self.get_width(), self.get_height())

    def get_rect(self, **kwargs):
        r = Rect(0, 0, self.get_width(), self.get_height())
        for name in kwargs:
            setattr(r, name, kwargs[name])
        return r


class Font:
    """pygame.font.Font(None, size). size 24 (pygame's usual) gives scale 2."""

    def __init__(self, display, name=None, size=24):
        self._display = display
        self.scale = max(1, int(size) // 12)

    def render(self, text, antialias=False, color=(255, 255, 255), background=None):
        return TextSurface(self._display, str(text), color, self.scale)

    def size(self, text):
        return (self._display.text_width(str(text), self.scale),
                self._display.text_height(self.scale))


class KeyState:
    def __init__(self, pressed):
        self._pressed = pressed

    def __getitem__(self, key):
        return key in self._pressed


class Clock:
    def __init__(self, timer):
        self._timer = timer
        self._last = None

    def tick(self, framerate=0):
        now = self._timer.now_ms()
        if self._last is None:
            self._last = now
            return 0
        if framerate:
            wait = 1000 // framerate - self._timer.diff_ms(now, self._last)
            if wait > 0:
                self._timer.sleep_ms(wait)
                now = self._timer.now_ms()
        elapsed = self._timer.diff_ms(now, self._last)
        self._last = now
        return elapsed


class Sounds:
    """Starts notes and ends them when their time is up."""

    def __init__(self, speaker, timer):
        self._speaker = speaker
        self._timer = timer
        self._ends_at = None

    def play(self, frequency, ms):
        self._speaker.play(frequency)
        self._ends_at = self._timer.now_ms() + ms

    def stop(self):
        self._speaker.stop()
        self._ends_at = None

    def update(self):
        if self._ends_at is not None and \
                self._timer.diff_ms(self._timer.now_ms(), self._ends_at) >= 0:
            self.stop()


class Tone:
    def __init__(self, sounds, frequency, ms):
        self._sounds = sounds
        self.frequency = frequency
        self.ms = ms

    def play(self):
        self._sounds.play(self.frequency, self.ms)

    def stop(self):
        self._sounds.stop()


class _MixerModule:
    def __init__(self, sounds):
        self._sounds = sounds

    def init(self, *args, **kwargs):
        pass

    def stop(self):
        self._sounds.stop()


class _DisplayModule:
    def __init__(self, display, sounds):
        self._display = display
        self._sounds = sounds

    def set_mode(self, size=None, flags=0):
        return Surface(self._display)

    def flip(self):
        self._display.update()
        self._sounds.update()

    def update(self, *rects):
        self.flip()

    def set_caption(self, title):
        pass


class _DrawModule:
    def rect(self, surface, color, rect):
        r = Rect(rect)
        surface._display.rect(color, r.x, r.y, r.w, r.h)
        return r

    def circle(self, surface, color, center, radius):
        x, y = center
        surface._display.circle(color, int(x), int(y), int(radius))

    def line(self, surface, color, start, end, width=1):
        surface._display.line(color, int(start[0]), int(start[1]),
                              int(end[0]), int(end[1]))


class _FontModule:
    def __init__(self, display):
        self._display = display

    def init(self):
        pass

    def Font(self, name=None, size=24):
        return Font(self._display, name, size)

    def SysFont(self, name=None, size=24, bold=False, italic=False):
        return Font(self._display, name, size)


class _EventModule:
    def __init__(self, buttons):
        self._buttons = buttons
        self.held = set()

    def get(self):
        now = self._buttons.pressed()
        events = []
        for key in ALL_KEYS:
            if key in now and key not in self.held:
                events.append(Event(KEYDOWN, key))
            elif key in self.held and key not in now:
                events.append(Event(KEYUP, key))
        self.held = now
        return events

    def pump(self):
        self.get()


class _KeyModule:
    def __init__(self, events):
        self._events = events

    def get_pressed(self):
        return KeyState(set(self._events.held))


class _TimeModule:
    def __init__(self, timer):
        self._timer = timer

    def Clock(self):
        return Clock(self._timer)

    def get_ticks(self):
        return self._timer.now_ms()


class Pygame:
    """Everything a game reaches through `pygame.`, wired to three ports."""

    def __init__(self, display, buttons, timer, speaker=None):
        self.Rect = Rect
        self.Surface = Surface
        for name in ('QUIT', 'KEYDOWN', 'KEYUP', 'K_UP', 'K_DOWN', 'K_LEFT',
                     'K_RIGHT', 'K_a', 'K_b', 'K_x', 'K_y', 'K_RETURN',
                     'K_ESCAPE', 'K_SPACE'):
            setattr(self, name, globals()[name])
        self._sounds = Sounds(speaker or SilentSpeaker(), timer)
        self.display = _DisplayModule(display, self._sounds)
        self.mixer = _MixerModule(self._sounds)
        self.draw = _DrawModule()
        self.font = _FontModule(display)
        self.event = _EventModule(buttons)
        self.key = _KeyModule(self.event)
        self.time = _TimeModule(timer)

    def init(self):
        return (0, 0)

    def quit(self):
        self._sounds.stop()

    def tone(self, frequency, ms):
        return Tone(self._sounds, frequency, ms)
