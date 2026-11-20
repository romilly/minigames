# Copy to the Explorer as pygame.py, alongside minigame.py and qwstpad.py.
# Wires minigame's ports to the Explorer's display and a Qw/ST Pad.
from explorer import display as _lcd, i2c as _i2c
from qwstpad import QwSTPad, DEFAULT_ADDRESS
import minigame as _mg

_pg = _mg.Pygame(_mg.PicoGraphicsDisplay(_lcd),
                 _mg.QwstPadButtons(QwSTPad(_i2c, DEFAULT_ADDRESS)),
                 _mg.TicksTimer())

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
event = _pg.event
key = _pg.key
time = _pg.time
