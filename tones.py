"""tone(frequency, ms) -> something with .play(), on the board and the desktop.

On the Explorer the minigame shim provides pygame.tone, which drives the
speaker. Under desktop pygame this builds a mixer Sound from a square wave
(close to what the board's speaker makes), or a silent stand-in if there is
no sound device.
"""
import pygame


class Silent:
    def play(self):
        pass

    def stop(self):
        pass


def tone(frequency, ms, volume=0.2):
    if hasattr(pygame, 'tone'):
        return pygame.tone(frequency, ms)
    return _desktop_tone(frequency, ms, volume)


def _desktop_tone(frequency, ms, volume):
    from array import array
    settings = pygame.mixer.get_init()
    if not settings:
        return Silent()
    rate, size, channels = settings
    if abs(size) != 16:
        return Silent()
    level = int(32767 * volume)
    period = rate / frequency
    samples = array('h')
    for i in range(rate * ms // 1000):
        value = level if (i % period) < period / 2 else -level
        for _ in range(channels):
            samples.append(value)
    return pygame.mixer.Sound(buffer=samples.tobytes())
