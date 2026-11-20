import pygame as real_pygame
import pytest

import minigame as mg
from fakes import (RecordingDisplay, ScriptedButtons, FakeTimer, FakeGraphics,
                   FakePad, fake_pygame)

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
