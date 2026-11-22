import pygame as real_pygame
import pytest

import minigame as mg
from fakes import (RecordingDisplay, ScriptedButtons, FakeTimer, FakeGraphics,
                   FakePad, RecordingSpeaker, ScriptedTouch, fake_pygame)

# ---- Rect: the same tests run against real pygame.Rect, as a contract ----


@pytest.fixture(params=[mg.Rect, real_pygame.Rect], ids=['minigame', 'pygame'])
def Rect(request):
    return request.param


def test_rect_constructors(Rect):
    assert tuple(Rect(1, 2, 3, 4)) == (1, 2, 3, 4)
    assert tuple(Rect((1, 2, 3, 4))) == (1, 2, 3, 4)
    assert tuple(Rect((1, 2), (3, 4))) == (1, 2, 3, 4)
    assert tuple(Rect(1.7, 2.2, 3, 4)) == (1, 2, 3, 4)


def test_rect_edges_and_centre(Rect):
    r = Rect(10, 20, 30, 41)
    assert (r.left, r.top, r.right, r.bottom) == (10, 20, 40, 61)
    assert r.center == (25, 40)
    assert (r.width, r.height) == (30, 41)


def test_rect_setters_move_without_resizing(Rect):
    r = Rect(0, 0, 10, 20)
    r.right = 100
    r.bottom = 50
    assert tuple(r) == (90, 30, 10, 20)
    r.center = (5, 5)
    assert tuple(r) == (0, -5, 10, 20)


def test_rect_move(Rect):
    r = Rect(1, 1, 2, 2)
    assert tuple(r.move(3, 4)) == (4, 5, 2, 2)
    assert tuple(r) == (1, 1, 2, 2)
    r.move_ip(-1, -1)
    assert tuple(r) == (0, 0, 2, 2)


def test_colliderect_edges_touching_do_not_collide(Rect):
    a = Rect(0, 0, 10, 10)
    assert a.colliderect(Rect(5, 5, 10, 10))
    assert not a.colliderect(Rect(10, 0, 5, 5))
    assert not a.colliderect(Rect(0, 10, 5, 5))


def test_rect_indexing(Rect):
    r = Rect(1, 2, 3, 4)
    assert (r[0], r[1], r[2], r[3]) == (1, 2, 3, 4)
    assert len(r) == 4


def test_collidepoint(Rect):
    r = Rect(0, 0, 10, 10)
    assert r.collidepoint(0, 0)
    assert r.collidepoint((9, 9))
    assert not r.collidepoint(10, 5)


def test_clamp_ip(Rect):
    bounds = Rect(0, 0, 100, 50)
    r = Rect(-5, 45, 10, 10)
    r.clamp_ip(bounds)
    assert tuple(r) == (0, 40, 10, 10)
    big = Rect(0, 0, 200, 10)
    big.clamp_ip(bounds)
    assert tuple(big) == (-50, 0, 200, 10)


# ---- Drawing goes to the Display port ----

def test_draw_calls_reach_the_display():
    display = RecordingDisplay()
    pg = fake_pygame(display=display)
    screen = pg.display.set_mode((320, 240))
    screen.fill((0, 0, 0))
    pg.draw.rect(screen, (255, 0, 0), pg.Rect(1, 2, 3, 4))
    pg.draw.rect(screen, (0, 255, 0), (5, 6, 7, 8))
    pg.draw.circle(screen, (0, 0, 255), (10.6, 20), 5)
    pg.draw.line(screen, (9, 9, 9), (0, 0), (3, 4))
    pg.display.flip()
    assert display.calls == [
        ('fill', (0, 0, 0)),
        ('rect', (255, 0, 0), 1, 2, 3, 4),
        ('rect', (0, 255, 0), 5, 6, 7, 8),
        ('circle', (0, 0, 255), 10, 20, 5),
        ('line', (9, 9, 9), 0, 0, 3, 4),
    ]
    assert display.frames == 1
    assert screen.get_rect() == pg.Rect(0, 0, 320, 240)


# ---- Events come from button state changes ----

def test_events_are_edges_of_button_state():
    pg = fake_pygame(buttons=ScriptedButtons(
        set(), {mg.K_UP}, {mg.K_UP, mg.K_a}, {mg.K_a}, set()))
    kinds = []
    for _ in range(5):
        kinds.append([(e.type, e.key) for e in pg.event.get()])
    assert kinds == [
        [],
        [(mg.KEYDOWN, mg.K_UP)],
        [(mg.KEYDOWN, mg.K_a)],
        [(mg.KEYUP, mg.K_UP)],
        [(mg.KEYUP, mg.K_a)],
    ]


def test_get_pressed_reflects_last_event_poll():
    pg = fake_pygame(buttons=ScriptedButtons({mg.K_DOWN}))
    assert not pg.key.get_pressed()[mg.K_DOWN]   # nothing polled yet, as in pygame
    pg.event.get()
    keys = pg.key.get_pressed()
    assert keys[mg.K_DOWN] and not keys[mg.K_UP]


# ---- Clock ----

def test_clock_sleeps_for_the_rest_of_the_frame():
    timer = FakeTimer()
    clock = mg.Clock(timer)
    assert clock.tick(25) == 0        # first tick just starts the clock
    timer.t += 10                     # the frame's work takes 10 ms
    assert clock.tick(25) == 40       # so it sleeps the other 30
    assert timer.slept == [30]


def test_clock_does_not_sleep_when_frame_overruns():
    timer = FakeTimer()
    clock = mg.Clock(timer)
    clock.tick(30)
    timer.t += 50
    assert clock.tick(30) == 50
    assert timer.slept == []


# ---- Adapters ----

def test_picographics_adapter_caches_pens():
    g = FakeGraphics()
    d = mg.PicoGraphicsDisplay(g)
    d.fill((0, 0, 0))
    d.rect((255, 255, 255), 1, 2, 3, 4)
    d.rect((255, 255, 255), 5, 6, 7, 8)
    d.update()
    assert g.calls == [
        ('set_font', 'bitmap8'),
        ('create_pen', 0, 0, 0), ('set_pen', (0, 0, 0)), ('clear',),
        ('create_pen', 255, 255, 255), ('set_pen', (255, 255, 255)),
        ('rectangle', 1, 2, 3, 4),
        ('set_pen', (255, 255, 255)), ('rectangle', 5, 6, 7, 8),
        ('update',),
    ]


def test_qwstpad_adapter_maps_letters_to_keys():
    pad = FakePad()
    buttons = mg.QwstPadButtons(pad)
    pad.states['U'] = pad.states['-'] = True
    first = buttons.pressed()
    pad.states['U'] = False          # the real pad reuses its dict
    assert first == {mg.K_UP, mg.K_ESCAPE}
    assert buttons.pressed() == {mg.K_ESCAPE}


def test_picographics_adapter_text():
    g = FakeGraphics()
    d = mg.PicoGraphicsDisplay(g)
    d.text((255, 255, 255), 'Hi', 10, 20, 2)
    assert g.calls[-1] == ('text', 'Hi', 10, 20, -1, 2)
    assert d.text_width('Hi', 2) == 24
    assert d.text_height(2) == 16


# ---- Fonts ----

def test_rendered_text_is_drawn_where_it_is_blitted():
    display = RecordingDisplay()
    pg = fake_pygame(display=display)
    screen = pg.display.set_mode((320, 240))
    font = pg.font.Font(None, 24)
    text = font.render('Score 3', False, (255, 255, 0))
    where = screen.blit(text, (10, 4))
    assert display.calls == [('text', (255, 255, 0), 'Score 3', 10, 4, 2)]
    assert where == pg.Rect(10, 4, 84, 16)


def test_text_can_be_centred_with_get_rect():
    display = RecordingDisplay()
    pg = fake_pygame(display=display)
    screen = pg.display.set_mode((320, 240))
    text = pg.font.Font(None, 24).render('abcd', False, (1, 1, 1))
    screen.blit(text, text.get_rect(centerx=160, top=4))
    assert display.calls == [('text', (1, 1, 1), 'abcd', 136, 4, 2)]


def test_font_size_sets_the_scale():
    pg = fake_pygame()
    assert [pg.font.Font(None, n).scale for n in (8, 12, 24, 36, 48)] == [1, 1, 2, 3, 4]


# ---- Sound ----

def test_a_tone_plays_until_its_time_is_up_then_flip_stops_it():
    timer = FakeTimer()
    speaker = RecordingSpeaker(timer)
    pg = fake_pygame(timer=timer, speaker=speaker)
    pg.tone(880, 40).play()
    timer.t = 33
    pg.display.flip()
    assert speaker.calls == [('play', 880, 0)]
    timer.t = 40
    pg.display.flip()
    assert speaker.calls == [('play', 880, 0), ('stop', 40)]
    timer.t = 80
    pg.display.flip()
    assert len(speaker.calls) == 2          # stops only once


def test_a_new_tone_cuts_off_the_old_one():
    timer = FakeTimer()
    speaker = RecordingSpeaker(timer)
    pg = fake_pygame(timer=timer, speaker=speaker)
    pg.tone(110, 300).play()
    timer.t = 20
    pg.tone(880, 40).play()
    timer.t = 60
    pg.display.flip()
    assert speaker.calls == [('play', 110, 0), ('play', 880, 20), ('stop', 60)]


def test_quit_and_mixer_stop_silence_the_speaker():
    speaker = RecordingSpeaker()
    pg = fake_pygame(speaker=speaker)
    pg.tone(440, 1000).play()
    pg.mixer.stop()
    pg.tone(440, 1000).play()
    pg.quit()
    assert [c[0] for c in speaker.calls] == ['play', 'stop', 'play', 'stop']


def test_explorer_speaker_adapter():
    calls = []
    speaker = mg.ExplorerSpeaker(lambda f: calls.append(('tone', f)),
                                 lambda: calls.append(('stop',)))
    speaker.play(440.7)
    speaker.stop()
    assert calls == [('tone', 440), ('stop',)]


# ---- Presto and fallback adapters ----

def test_display_can_use_another_update_function():
    g = FakeGraphics()
    shown = []
    d = mg.PicoGraphicsDisplay(g, update=lambda: shown.append(True))
    d.update()
    assert shown == [True]
    assert ('update',) not in g.calls


def test_buzzer_speaker_adapter():
    class Buzzer:
        def __init__(self):
            self.tones = []

        def set_tone(self, f):
            self.tones.append(f)

    buzzer = Buzzer()
    speaker = mg.BuzzerSpeaker(buzzer)
    speaker.play(440.6)
    speaker.stop()
    mg.BuzzerSpeaker(buzzer, pitch=2).play(440)
    assert buzzer.tones == [440, -1, 880]


class FakePin:
    def __init__(self, value=1):
        self._value = value

    def value(self):
        return self._value


def test_pin_buttons_are_active_low():
    pins = {'A': FakePin(0), 'B': FakePin(1), 'C': FakePin(0), 'Y': FakePin(1)}
    assert mg.PinButtons(pins).pressed() == {mg.K_UP, mg.K_DOWN}


def test_pad_or_uses_the_pad_when_it_answers():
    buttons = mg.pad_or(FakePad, mg.NoButtons(), say=None)
    assert isinstance(buttons, mg.QwstPadButtons)


def test_pad_or_falls_back_and_says_so_when_the_pad_is_missing():
    said = []

    def missing_pad():
        raise OSError(5)

    fallback = mg.NoButtons()
    assert mg.pad_or(missing_pad, fallback, said.append) is fallback
    assert 'No Qw/ST Pad' in said[0]


# ---- Vector text ----

class FakeVector:
    """Like PicoVector: text sits on its baseline, so its box starts above y."""

    def __init__(self):
        self.size = None
        self.drawn = []

    def set_font_size(self, size):
        self.size = size

    def measure_text(self, text, x=0, y=0, angle=None):
        # box: 1 px right of x, top at 80% of the size above the baseline
        return (x + 1, y - 0.8 * self.size, len(text) * 0.5 * self.size, self.size)

    def text(self, text, x, y, angle=None):
        self.drawn.append((text, x, y, self.size))


def test_vector_text_puts_the_top_of_the_capitals_where_asked():
    vector = FakeVector()
    d = mg.PicoGraphicsDisplay(FakeGraphics(), vector_text=mg.VectorText(vector))
    d.text((255, 255, 255), 'Hi', 10, 20, 2)
    # size 18: the baseline goes 0.95 * 18 = 17.1 px below the top
    assert vector.drawn == [('Hi', 10, 37, 18)]
    assert d.text_width('Hi', 2) == 18
    assert d.text_height(2) == 22          # 1.2 * 18, room for descenders


def test_vector_text_size_follows_the_scale():
    vector = FakeVector()
    d = mg.PicoGraphicsDisplay(FakeGraphics(), vector_text=mg.VectorText(vector))
    d.text((1, 1, 1), 'X', 0, 0, 6)
    assert vector.drawn[-1][3] == 54


# ---- Polygons ----

def test_draw_polygon_reaches_the_display():
    display = RecordingDisplay()
    pg = fake_pygame(display=display)
    screen = pg.display.set_mode((0, 0))
    pg.draw.polygon(screen, (1, 2, 3), [(0, 0), (10.6, 0), (5, 8)])
    assert display.calls[-1] == ('polygon', (1, 2, 3), [(0, 0), (10, 0), (5, 8)])


def test_picographics_polygon_gets_a_list_of_int_tuples():
    g = FakeGraphics()
    mg.PicoGraphicsDisplay(g).polygon((1, 2, 3), [[0, 0], (10.6, 0), (5, 8)])
    assert g.calls[-1] == ('polygon', [(0, 0), (10, 0), (5, 8)])


# ---- Touch: pygame's mouse events ----

def test_a_touch_is_a_mouse_button_down_then_up():
    touch = ScriptedTouch(None, (10, 20), (11, 21), None)
    pg = fake_pygame(touch=touch)
    frames = []
    for _ in range(4):
        frames.append([(e.type, e.pos) for e in pg.event.get()])
    assert frames == [[], [(mg.MOUSEBUTTONDOWN, (10, 20))], [],
                      [(mg.MOUSEBUTTONUP, (11, 21))]]


def test_mouse_events_carry_button_one():
    pg = fake_pygame(touch=ScriptedTouch((1, 2)))
    event = pg.event.get()[0]
    assert event.button == 1


def test_without_touch_there_are_no_mouse_events():
    assert fake_pygame().event.get() == []


def test_presto_touch_adapter_polls_then_reads():
    class FakePrestoTouch:
        def __init__(self):
            self.polls = 0
            self.state, self.x, self.y = False, 0, 0

        def poll(self):
            self.polls += 1

    raw = FakePrestoTouch()
    touch = mg.PrestoTouch(raw)
    assert touch.position() is None
    raw.state, raw.x, raw.y = True, 30, 40
    assert touch.position() == (30, 40)
    assert raw.polls == 2


def test_pygame_exposes_the_mouse_event_names():
    pg = fake_pygame()
    assert (pg.MOUSEBUTTONDOWN, pg.MOUSEBUTTONUP) == (mg.MOUSEBUTTONDOWN, mg.MOUSEBUTTONUP)
