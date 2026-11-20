import importlib
import sys

import minigame as mg
import pong
from fakes import RecordingDisplay, ScriptedButtons, FakeTimer, RecordingSpeaker, fake_pygame

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
    assert game.update(False, False, 33) == ['wall']
    assert game.vy > 0


def test_ball_bounces_off_paddle():
    game = pong.Pong()
    game.ball_x = game.paddle.right + 1
    game.ball_y = game.paddle.centery
    assert game.update(False, False, 33) == ['paddle']
    assert game.vx > 0
    assert game.score == 1


def test_nothing_happens_in_open_space():
    assert pong.Pong().update(False, False, 33) == []


def test_status_shows_score_and_misses():
    game = pong.Pong()
    game.score, game.misses = 7, 2
    assert game.status() == 'Score 7   Missed 2'


def test_missed_ball_is_counted_and_served_again():
    game = pong.Pong()
    game.paddle_y = 0
    game.ball_x, game.ball_y = -5, 200
    assert game.update(False, False, 33) == ['miss']
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
    monkeypatch.delitem(sys.modules, 'tones', raising=False)
    shim_pong = importlib.import_module('pong')

    game = shim_pong.main(fps=25)

    assert display.frames == 6
    assert timer.slept == [40] * 5          # no work takes time with fakes
    # frames 1 and 2 have dt 0 (the first tick only starts the clock);
    # frames 3-5 hold UP for 40 ms each at 240 px/s: 3 * 9.6 px
    assert game.paddle.y == int(100 - 3 * 9.6)
    assert display.calls[0] == ('fill', (0, 0, 0))
    assert display.calls[1][:3] == ('text', (255, 255, 255), 'Score 0   Missed 0')


def test_main_plays_sounds_through_the_shim(monkeypatch):
    """Serve the ball low along the bottom, past the paddle: a miss buzzes."""
    speaker = RecordingSpeaker()
    pg = fake_pygame(buttons=ScriptedButtons(*([set()] * 40 + [{mg.K_ESCAPE}])),
                     speaker=speaker)
    monkeypatch.setitem(sys.modules, 'pygame', pg)
    monkeypatch.delitem(sys.modules, 'pong')
    monkeypatch.delitem(sys.modules, 'tones', raising=False)
    shim_pong = importlib.import_module('pong')
    monkeypatch.setattr(shim_pong.Pong, 'serve', _serve_low)

    shim_pong.main()

    assert ('play', 110, None) in speaker.calls
    assert speaker.calls[-1] == ('stop', None)      # quit silences it


def _serve_low(self):
    self.ball = self.bounds.__class__(0, 0, 6, 6)
    self.ball.center = (60, 230)
    self.ball_x, self.ball_y = float(self.ball.x), float(self.ball.y)
    self.vx, self.vy = -180, 0
