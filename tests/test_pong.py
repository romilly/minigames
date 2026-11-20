import importlib
import sys

import minigame as mg
import pong
from fakes import RecordingDisplay, ScriptedButtons, FakeTimer, fake_pygame

# Game logic, using real pygame.Rect


def test_paddle_moves_at_its_speed_and_stays_on_screen():
    game = pong.Pong()
    y = game.paddle.y
    game.update(up=True, down=False, dt_ms=25)       # 240 px/s for 25 ms = 6 px
    assert game.paddle.y == y - 6
    for _ in range(100):
        game.update(up=True, down=False, dt_ms=33)
    assert game.paddle.top == 0


def test_slow_frames_still_add_up():
    """Ten 4 ms frames move the paddle as far as one 40 ms frame."""
    a, b = pong.Pong(), pong.Pong()
    for _ in range(10):
        a.update(False, True, 4)
    b.update(False, True, 40)
    assert a.paddle.y == b.paddle.y


def test_ball_moves_at_its_speed():
    game = pong.Pong()
    x, y = game.ball.x, game.ball.y
    game.update(False, False, 50)
    assert (game.ball.x, game.ball.y) == (x - 9, y + 6)


def test_a_stall_is_capped():
    game = pong.Pong()
    x = game.ball.x
    game.update(False, False, 1000)
    assert game.ball.x == x - 9                    # as if 50 ms had passed


def test_ball_bounces_off_top_wall():
    game = pong.Pong()
    game.ball_y = 1
    game.vy = -120
    game.update(False, False, 33)
    assert game.vy > 0


def test_ball_bounces_off_paddle():
    game = pong.Pong()
    game.ball_x = game.paddle.right + 1
    game.ball_y = game.paddle.centery
    game.update(False, False, 33)
    assert game.vx > 0


def test_missed_ball_is_counted_and_served_again():
    game = pong.Pong()
    game.paddle_y = 0
    game.ball_x, game.ball_y = -5, 200
    game.update(False, False, 33)
    assert game.misses == 1
    assert game.ball.center == game.bounds.center


# Walking skeleton end to end: pong.main() on the minigame shim, with fakes


def test_main_runs_on_the_shim_until_minus_is_pressed(monkeypatch):
    display = RecordingDisplay()
    held_up = [{mg.K_UP}] * 5
    timer = FakeTimer()
    pg = fake_pygame(display=display,
                     buttons=ScriptedButtons(*(held_up + [{mg.K_ESCAPE}])),
                     timer=timer)
    monkeypatch.setitem(sys.modules, 'pygame', pg)
    monkeypatch.delitem(sys.modules, 'pong')
    shim_pong = importlib.import_module('pong')

    game = shim_pong.main(fps=25)

    assert display.frames == 6
    assert timer.slept == [40] * 5          # no work takes time with fakes
    # frames 1 and 2 have dt 0 (the first tick only starts the clock);
    # frames 3-5 hold UP for 40 ms each at 240 px/s: 3 * 9.6 px
    assert game.paddle.y == int(100 - 3 * 9.6)
    assert display.calls[0] == ('fill', (0, 0, 0))
