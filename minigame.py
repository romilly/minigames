"""A small subset of the pygame API, for MicroPython on the Pimoroni Explorer.

Ports (Display, Buttons, Timer) are plain base classes because MicroPython
has no abc module. Adapters for PicoGraphics and the Qw/ST Pad take the
hardware objects as arguments, so everything here can be tested on CPython.

Supported: Rect, display.set_mode/flip, Surface.fill, draw.rect/circle/line
(filled shapes only), event.get (KEYDOWN/KEYUP), key.get_pressed,
time.Clock.tick, init/quit.
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

    def update(self):
        raise NotImplementedError


class Buttons:
    """Reports which keys are held down, as a set of K_ constants."""

    def pressed(self):
        raise NotImplementedError


class Timer:
    def now_ms(self):
        raise NotImplementedError

    def sleep_ms(self, ms):
        raise NotImplementedError

    def diff_ms(self, later, earlier):
        return later - earlier


# ---- Adapters ----

class PicoGraphicsDisplay(Display):
    def __init__(self, graphics):
        self._g = graphics
        self._pens = {}

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

    def update(self):
        self._g.update()


class QwstPadButtons(Buttons):
    """Adapts Pimoroni's QwSTPad (read_buttons() -> {'U': bool, ...})."""

    def __init__(self, pad):
        self._pad = pad

    def pressed(self):
        states = self._pad.read_buttons()
        return set(PAD_KEYS[name] for name in PAD_KEYS if states.get(name))


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


class _DisplayModule:
    def __init__(self, display):
        self._display = display

    def set_mode(self, size=None, flags=0):
        return Surface(self._display)

    def flip(self):
        self._display.update()

    def update(self, *rects):
        self._display.update()

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

    def __init__(self, display, buttons, timer):
        self.Rect = Rect
        self.Surface = Surface
        for name in ('QUIT', 'KEYDOWN', 'KEYUP', 'K_UP', 'K_DOWN', 'K_LEFT',
                     'K_RIGHT', 'K_a', 'K_b', 'K_x', 'K_y', 'K_RETURN',
                     'K_ESCAPE', 'K_SPACE'):
            setattr(self, name, globals()[name])
        self.display = _DisplayModule(display)
        self.draw = _DrawModule()
        self.event = _EventModule(buttons)
        self.key = _KeyModule(self.event)
        self.time = _TimeModule(timer)

    def init(self):
        return (0, 0)

    def quit(self):
        pass
