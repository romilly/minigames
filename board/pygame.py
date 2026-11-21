# Copy to the board as pygame.py, alongside minigame.py and qwstpad.py.
# Works out whether it's on an Explorer or a Presto, and wires minigame's
# ports to that board's display, speaker and a Qw/ST Pad. With no pad, the
# Explorer's own buttons stand in (the Presto has none to offer).
import os
import minigame as _mg
from qwstpad import QwSTPad, DEFAULT_ADDRESS

# Smooth text with PicoVector, if the font is on the board; otherwise bitmap8.
FONT = '/Roboto-Medium.af'
VECTOR_TEXT = {'explorer': False, 'presto': True}
# The Presto's piezo is quiet; higher notes are louder. 2 = an octave up.
PRESTO_PITCH = 2


def _vector_text(graphics):
    try:
        os.stat(FONT)
        from picovector import PicoVector, ANTIALIAS_FAST
    except (OSError, ImportError):
        return None
    vector = PicoVector(graphics)
    vector.set_antialiasing(ANTIALIAS_FAST)
    vector.set_font(FONT, 18)
    return _mg.VectorText(vector)


try:
    import explorer as _explorer
except ImportError:
    _explorer = None

if _explorer:
    BOARD = 'explorer'
    _text = _vector_text(_explorer.display) if VECTOR_TEXT[BOARD] else None
    _display = _mg.PicoGraphicsDisplay(_explorer.display, vector_text=_text)
    _speaker = _mg.ExplorerSpeaker(_explorer.play_tone, _explorer.stop_playing)
    _i2c = _explorer.i2c
    _fallback = _mg.PinButtons({
        'A': _explorer.button_a, 'B': _explorer.button_b, 'C': _explorer.button_c,
        'X': _explorer.button_x, 'Y': _explorer.button_y, 'Z': _explorer.button_z})
else:
    from machine import I2C
    from presto import Presto, Buzzer
    BOARD = 'presto'
    _presto = Presto()          # 240 x 240, doubled up to fill the screen
    _text = _vector_text(_presto.display) if VECTOR_TEXT[BOARD] else None
    _display = _mg.PicoGraphicsDisplay(_presto.display, update=_presto.update,
                                       vector_text=_text)
    _speaker = _mg.BuzzerSpeaker(Buzzer(43), pitch=PRESTO_PITCH)
    _i2c = I2C(0, sda=40, scl=41)
    _fallback = _mg.NoButtons()

_buttons = _mg.pad_or(lambda: QwSTPad(_i2c, DEFAULT_ADDRESS), _fallback)
_pg = _mg.Pygame(_display, _buttons, _mg.TicksTimer(), _speaker)

Rect = _mg.Rect
Surface = _mg.Surface
QUIT, KEYDOWN, KEYUP = _mg.QUIT, _mg.KEYDOWN, _mg.KEYUP
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
