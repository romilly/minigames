"""The browser's adapters for minigame's ports, tested with stand-ins for the
JavaScript objects they're given (a canvas context, an audio context)."""
import minigame as mg
from browser.minigame_web import (CanvasDisplay, KeyboardButtons, PointerTouch,
                                  WebAudioSpeaker, BrowserTimer)


class FakeContext:
    """Records what's drawn on a canvas 2D context: property sets and calls."""

    def __init__(self):
        object.__setattr__(self, 'log', [])

    def __setattr__(self, name, value):
        self.log.append(('set', name, value))

    def __getattr__(self, name):
        if name == 'measureText':
            return lambda text: type('Metrics', (), {'width': 5.4 * len(text)})()
        return lambda *args: self.log.append((name,) + args)


def drawn(ctx):
    return [entry for entry in ctx.log if entry[0] != 'set']


def test_the_canvas_has_the_size_it_was_given():
    assert CanvasDisplay(FakeContext(), 240, 240).size() == (240, 240)


def test_fill_paints_the_whole_canvas():
    ctx = FakeContext()
    CanvasDisplay(ctx, 240, 200).fill((1, 2, 3))
    assert ('set', 'fillStyle', 'rgb(1,2,3)') in ctx.log
    assert drawn(ctx) == [('fillRect', 0, 0, 240, 200)]


def test_rect_circle_and_polygon_are_filled():
    ctx = FakeContext()
    canvas = CanvasDisplay(ctx, 240, 240)
    canvas.rect((9, 9, 9), 1, 2, 3, 4)
    canvas.circle((9, 9, 9), 10, 20, 5)
    canvas.polygon((9, 9, 9), [(0, 0), (10, 0), (5, 8)])
    names = [entry[0] for entry in drawn(ctx)]
    assert names == ['fillRect', 'beginPath', 'arc', 'fill',
                     'beginPath', 'moveTo', 'lineTo', 'lineTo', 'closePath', 'fill']
    assert ('fillRect', 1, 2, 3, 4) in ctx.log


def test_lines_are_one_pixel_and_sit_on_pixel_centres():
    ctx = FakeContext()
    CanvasDisplay(ctx, 240, 240).line((9, 9, 9), 0, 5, 10, 5)
    assert ('set', 'lineWidth', 1) in ctx.log
    assert ('moveTo', 0.5, 5.5) in ctx.log and ('lineTo', 10.5, 5.5) in ctx.log


def test_text_is_nine_pixels_a_scale_like_the_prestos_roboto():
    ctx = FakeContext()
    canvas = CanvasDisplay(ctx, 240, 240)
    canvas.text((255, 255, 255), 'Hi', 4, 6, 2)
    assert ('set', 'font', '18px Roboto, sans-serif') in ctx.log
    assert ('fillText', 'Hi', 4, 6) in ctx.log
    assert canvas.text_width('Hi', 2) == 11
    assert canvas.text_height(2) == 22


def test_keys_map_to_the_pygame_names():
    keys = KeyboardButtons()
    for name in ('ArrowUp', 'a', 'Escape'):
        keys.down(name)
    assert keys.pressed() == {mg.K_UP, mg.K_a, mg.K_ESCAPE}


def test_other_keys_are_ignored():
    keys = KeyboardButtons()
    keys.down('q')
    assert keys.pressed() == set()


def test_a_key_tapped_between_frames_is_still_seen_once():
    keys = KeyboardButtons()
    keys.down('ArrowLeft')
    keys.up('ArrowLeft')
    assert keys.pressed() == {mg.K_LEFT}
    assert keys.pressed() == set()


def test_a_held_key_stays_pressed_until_released():
    keys = KeyboardButtons()
    keys.down('Enter')
    assert keys.pressed() == {mg.K_RETURN}
    assert keys.pressed() == {mg.K_RETURN}
    keys.up('Enter')
    assert keys.pressed() == set()


def test_touches_are_scaled_from_the_size_the_canvas_is_shown_at():
    touch = PointerTouch(240, 240)
    touch.down(100, 300, 480, 480)          # shown at twice size
    assert touch.position() == (50, 150)
    touch.move(110, 310, 480, 480)
    assert touch.position() == (55, 155)
    touch.up()
    assert touch.position() is None


def test_a_tap_between_frames_is_still_seen_once():
    touch = PointerTouch(240, 240)
    touch.down(20, 40, 240, 240)
    touch.up()
    assert touch.position() == (20, 40)
    assert touch.position() is None


def test_moving_without_touching_is_not_a_touch():
    touch = PointerTouch(240, 240)
    touch.move(20, 40, 240, 240)
    assert touch.position() is None


class FakeAudio:
    def __init__(self):
        self.log = []
        self.destination = 'speakers'
        self.currentTime = 1.0

    def createOscillator(self):
        return FakeNode(self.log, 'oscillator')

    def createGain(self):
        return FakeNode(self.log, 'gain')


class FakeNode:
    def __init__(self, log, kind):
        self.log, self.kind = log, kind
        self.frequency = type('Param', (), {})()
        self.gain = type('Param', (), {})()

    def connect(self, other):
        self.log.append((self.kind, 'connect', getattr(other, 'kind', other)))

    def start(self):
        self.log.append((self.kind, 'start'))

    def stop(self):
        self.log.append((self.kind, 'stop'))


def test_the_speaker_plays_a_quiet_square_wave_and_stops_it():
    audio = FakeAudio()
    speaker = WebAudioSpeaker(audio)
    speaker.play(440)
    assert ('oscillator', 'start') in audio.log
    assert ('gain', 'connect', 'speakers') in audio.log
    speaker.stop()
    assert audio.log[-1] == ('oscillator', 'stop')


def test_a_new_note_stops_the_last():
    audio = FakeAudio()
    speaker = WebAudioSpeaker(audio)
    speaker.play(440)
    speaker.play(880)
    assert [e for e in audio.log if e[1] in ('start', 'stop')] == [
        ('oscillator', 'start'), ('oscillator', 'stop'), ('oscillator', 'start')]


def test_stopping_when_silent_is_fine():
    WebAudioSpeaker(FakeAudio()).stop()


def test_the_timer_reads_the_clock_and_never_blocks():
    now = [1000.4]
    timer = BrowserTimer(lambda: now[0])
    assert timer.now_ms() == 1000
    timer.sleep_ms(500)                     # returns at once
    assert timer.now_ms() == 1000


def test_letter_keys_work_with_shift_or_caps_lock():
    keys = KeyboardButtons()
    keys.down('A')
    assert keys.pressed() == {mg.K_a}
    keys.up('A')
    assert keys.pressed() == set()


def test_the_keys_the_game_uses_are_known_so_the_page_can_claim_them():
    assert KeyboardButtons.handles('ArrowDown') and KeyboardButtons.handles('B')
    assert not KeyboardButtons.handles('F5')
