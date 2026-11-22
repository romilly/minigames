"""Browser adapters for minigame's ports, for running the games in Pyodide.

Each adapter is given the JavaScript objects it works with (a canvas 2D
context, an AudioContext, a clock function), so it can be tested on the
desktop with stand-ins. browser/pygame.py does the wiring.

Input arrives from the browser as events, between frames; the game polls
once a frame. So a key press or tap that starts and ends between two polls
is remembered until a poll has seen it.
"""
import minigame as mg

TEXT_PX_PER_SCALE = 9          # as the Presto's Roboto (minigame.VectorText)
TEXT_LINE = 1.2
FONT_FAMILY = 'Roboto, sans-serif'
VOLUME = 0.05                  # square waves are loud

KEYS = {
    'ArrowUp': mg.K_UP, 'ArrowDown': mg.K_DOWN,
    'ArrowLeft': mg.K_LEFT, 'ArrowRight': mg.K_RIGHT,
    'a': mg.K_a, 'b': mg.K_b, 'x': mg.K_x, 'y': mg.K_y,
    'Enter': mg.K_RETURN, 'Escape': mg.K_ESCAPE, ' ': mg.K_SPACE,
}


def _rgb(color: tuple[int, int, int]) -> str:
    return 'rgb(%d,%d,%d)' % (color[0], color[1], color[2])


class CanvasDisplay(mg.Display):
    """Draws on an HTML canvas's 2D context. Drawing shows when the page next
    paints, so update() has nothing to do."""

    def __init__(self, ctx, width: int, height: int) -> None:
        self._ctx = ctx
        self._width = width
        self._height = height

    def size(self) -> tuple[int, int]:
        return (self._width, self._height)

    def fill(self, color: tuple[int, int, int]) -> None:
        self._ctx.fillStyle = _rgb(color)
        self._ctx.fillRect(0, 0, self._width, self._height)

    def rect(self, color: tuple[int, int, int], x: int, y: int, w: int, h: int) -> None:
        self._ctx.fillStyle = _rgb(color)
        self._ctx.fillRect(x, y, w, h)

    def circle(self, color: tuple[int, int, int], x: int, y: int, r: int) -> None:
        ctx = self._ctx
        ctx.fillStyle = _rgb(color)
        ctx.beginPath()
        ctx.arc(x, y, r, 0, 6.283185307179586)
        ctx.fill()

    def line(self, color: tuple[int, int, int], x1: int, y1: int, x2: int, y2: int) -> None:
        ctx = self._ctx
        ctx.strokeStyle = _rgb(color)
        ctx.lineWidth = 1
        ctx.beginPath()
        ctx.moveTo(x1 + 0.5, y1 + 0.5)          # pixel centres: crisp 1px lines
        ctx.lineTo(x2 + 0.5, y2 + 0.5)
        ctx.stroke()

    def polygon(self, color: tuple[int, int, int], points: list) -> None:
        ctx = self._ctx
        ctx.fillStyle = _rgb(color)
        ctx.beginPath()
        ctx.moveTo(points[0][0], points[0][1])
        for p in points[1:]:
            ctx.lineTo(p[0], p[1])
        ctx.closePath()
        ctx.fill()

    def _font(self, scale: int) -> None:
        self._ctx.font = '%dpx %s' % (TEXT_PX_PER_SCALE * scale, FONT_FAMILY)

    def text(self, color: tuple[int, int, int], text: str, x: int, y: int, scale: int) -> None:
        self._font(scale)
        self._ctx.fillStyle = _rgb(color)
        self._ctx.textBaseline = 'top'
        self._ctx.fillText(text, x, y)

    def text_width(self, text: str, scale: int) -> int:
        self._font(scale)
        return int(self._ctx.measureText(text).width + 0.5)

    def text_height(self, scale: int) -> int:
        return int(TEXT_LINE * TEXT_PX_PER_SCALE * scale + 0.5)

    def update(self) -> None:
        pass


class KeyboardButtons(mg.Buttons):
    """Keys held down, from the page's keydown and keyup events (by key name).
    Arrows, A B X Y, Enter (+), Esc (-) and Space, as on the pad."""

    def __init__(self) -> None:
        self._held: set[int] = set()
        self._unseen: set[int] = set()      # pressed since the last poll

    @staticmethod
    def _key(name: str) -> int | None:
        return KEYS.get(name.lower() if len(name) == 1 else name)   # Shift, Caps Lock

    @staticmethod
    def handles(name: str) -> bool:
        """Whether the game uses this key, so the page shouldn't (arrows scroll)."""
        return KeyboardButtons._key(name) is not None

    def down(self, name: str) -> None:
        key = self._key(name)
        if key is not None:
            self._held.add(key)
            self._unseen.add(key)

    def up(self, name: str) -> None:
        key = self._key(name)
        if key is not None:
            self._held.discard(key)

    def pressed(self) -> set:
        keys = self._held | self._unseen
        self._unseen = set()
        return keys


class PointerTouch(mg.Touch):
    """The mouse or a finger on the canvas, from pointer events. Positions come
    in the size the canvas is shown at and are scaled to its own pixels."""

    def __init__(self, width: int, height: int) -> None:
        self._width = width
        self._height = height
        self._at: tuple[int, int] | None = None      # while touching
        self._unseen: tuple[int, int] | None = None  # a press no poll has seen

    def _scale(self, x: float, y: float, shown_w: float, shown_h: float) -> tuple[int, int]:
        return (int(x * self._width / shown_w), int(y * self._height / shown_h))

    def down(self, x: float, y: float, shown_w: float, shown_h: float) -> None:
        self._at = self._scale(x, y, shown_w, shown_h)
        self._unseen = self._at

    def move(self, x: float, y: float, shown_w: float, shown_h: float) -> None:
        if self._at is not None:
            self._at = self._scale(x, y, shown_w, shown_h)

    def up(self) -> None:
        self._at = None

    def position(self) -> tuple[int, int] | None:
        at = self._at if self._at is not None else self._unseen
        self._unseen = None
        return at


class WebAudioSpeaker(mg.Speaker):
    """One square-wave note at a time, through a Web Audio AudioContext."""

    def __init__(self, audio) -> None:
        self._audio = audio
        self._oscillator = None

    def play(self, frequency: int) -> None:
        self.stop()
        oscillator = self._audio.createOscillator()
        oscillator.type = 'square'
        oscillator.frequency.value = frequency
        gain = self._audio.createGain()
        gain.gain.value = VOLUME
        oscillator.connect(gain)
        gain.connect(self._audio.destination)
        oscillator.start()
        self._oscillator = oscillator

    def stop(self) -> None:
        if self._oscillator is not None:
            self._oscillator.stop()
            self._oscillator = None


class BrowserTimer(mg.Timer):
    """Milliseconds from the page's clock (performance.now). Never sleeps:
    blocking would freeze the page, so the async loop paces the frames."""

    def __init__(self, now) -> None:
        self._now = now

    def now_ms(self) -> int:
        return int(self._now())

    def sleep_ms(self, ms: int) -> None:
        pass
