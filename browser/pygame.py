# The browser's pygame, for Pyodide: the counterpart of board/pygame.py.
# index.html copies this in as pygame.py, alongside minigame.py and
# minigame_web.py. It wires minigame's ports to the page: a <canvas id="screen">,
# the keyboard, the mouse or a finger on the canvas, and Web Audio.
import js
from pyodide.ffi import create_proxy

import minigame as _mg
import minigame_web as _web

WIDTH, HEIGHT = 240, 240        # the Presto's screen; the page shows it doubled

_canvas = js.document.getElementById('screen')
_canvas.width = WIDTH
_canvas.height = HEIGHT
_display = _web.CanvasDisplay(_canvas.getContext('2d'), WIDTH, HEIGHT)
_buttons = _web.KeyboardButtons()
_touch = _web.PointerTouch(WIDTH, HEIGHT)

# Browsers start audio suspended until the player does something.
_audio = js.AudioContext.new() if hasattr(js, 'AudioContext') else None
_speaker = _web.WebAudioSpeaker(_audio) if _audio else _mg.SilentSpeaker()


def _wake_audio():
    if _audio is not None and _audio.state == 'suspended':
        _audio.resume()


def _key_down(event):
    if _web.KeyboardButtons.handles(event.key):
        event.preventDefault()              # don't scroll the page
        _buttons.down(event.key)
    _wake_audio()


def _key_up(event):
    _buttons.up(event.key)


def _pointer_down(event):
    _canvas.setPointerCapture(event.pointerId)
    _touch.down(event.offsetX, event.offsetY, _canvas.clientWidth, _canvas.clientHeight)
    _wake_audio()


def _pointer_move(event):
    _touch.move(event.offsetX, event.offsetY, _canvas.clientWidth, _canvas.clientHeight)


def _pointer_up(event):
    _touch.up()


# Kept in a list so the proxies live as long as the page.
_listeners = [
    (js.document, 'keydown', _key_down), (js.document, 'keyup', _key_up),
    (_canvas, 'pointerdown', _pointer_down), (_canvas, 'pointermove', _pointer_move),
    (_canvas, 'pointerup', _pointer_up), (_canvas, 'pointercancel', _pointer_up),
]
_proxies = []
for _target, _name, _handler in _listeners:
    _proxy = create_proxy(_handler)
    _proxies.append(_proxy)
    _target.addEventListener(_name, _proxy)

_pg = _mg.Pygame(_display, _buttons, _web.BrowserTimer(js.performance.now), _speaker, _touch)

Rect = _mg.Rect
Surface = _mg.Surface
QUIT, KEYDOWN, KEYUP = _mg.QUIT, _mg.KEYDOWN, _mg.KEYUP
MOUSEBUTTONDOWN, MOUSEBUTTONUP = _mg.MOUSEBUTTONDOWN, _mg.MOUSEBUTTONUP
K_UP, K_DOWN, K_LEFT, K_RIGHT = _mg.K_UP, _mg.K_DOWN, _mg.K_LEFT, _mg.K_RIGHT
K_a, K_b, K_x, K_y = _mg.K_a, _mg.K_b, _mg.K_x, _mg.K_y
K_RETURN, K_ESCAPE, K_SPACE = _mg.K_RETURN, _mg.K_ESCAPE, _mg.K_SPACE

init = _pg.init
quit = _pg.quit
display = _pg.display
draw = _pg.draw
font = _pg.font
mixer = _pg.mixer
tone = _pg.tone
event = _pg.event
key = _pg.key
time = _pg.time
