import importlib
import sys

import minigame as mg
import pong
from fakes import RecordingDisplay, ScriptedButtons, FakeTimer, fake_pygame

# Game logic, using real pygame.Rect


def test_paddle_moves_and_stays_on_screen():
    game = pong.Pong()
    y = game.paddle.y
    game.update(up=True, down=False)
    assert game.paddle.y == y - pong.PADDLE_SPEED
    for _ in range(100):
        game.update(up=True, down=False)
    assert game.paddle.top == 0


def test_ball_bounces_off_top_wall():
    game = pong.Pong()
    game.ball.top = 1
    game.vy = -2
    game.update(False, False)
    assert game.vy > 0


def test_ball_bounces_off_paddle():
    game = pong.Pong()
    game.ball.left = game.paddle.right + 1
    game.ball.centery = game.paddle.centery
    game.vx = -3
    game.update(False, False)
    assert game.vx > 0


def test_missed_ball_is_counted_and_served_again():
    game = pong.Pong()
    game.paddle.top = 0
    game.ball.right = 1
    game.ball.top = 200
    game.vx, game.vy = -3, 0
    game.update(False, False)
    assert game.misses == 1
    assert game.ball.center == game.bounds.center


# Walking skeleton end to end: pong.main() on the minigame shim, with fakes


def test_main_runs_on_the_shim_until_minus_is_pressed(monkeypatch):
    display = RecordingDisplay()
    held_up = [{mg.K_UP}] * 5
    pg = fake_pygame(display=display,
                     buttons=ScriptedButtons(*(held_up + [{mg.K_ESCAPE}])),
                     timer=FakeTimer())
    monkeypatch.setitem(sys.modules, 'pygame', pg)
    monkeypatch.delitem(sys.modules, 'pong')
    shim_pong = importlib.import_module('pong')

    game = shim_pong.main()

    assert display.frames == 6
    assert game.paddle.y == 100 - 5 * shim_pong.PADDLE_SPEED
    assert display.calls[0] == ('fill', (0, 0, 0))
    assert display.calls[1] == ('rect', (255, 255, 255), 8, 96, 6, 40)
