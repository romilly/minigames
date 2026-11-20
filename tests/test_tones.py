import pygame
import pytest

import tones


@pytest.fixture
def mixer(monkeypatch):
    monkeypatch.setenv('SDL_AUDIODRIVER', 'dummy')
    pygame.mixer.init(frequency=22050, size=-16, channels=1)
    yield
    pygame.mixer.quit()


def test_desktop_tone_is_a_sound_of_the_right_length(mixer):
    sound = tones.tone(440, 100)
    assert isinstance(sound, pygame.mixer.Sound)
    assert sound.get_length() == pytest.approx(0.1, abs=0.001)
    sound.play()


def test_desktop_tone_is_silent_without_a_mixer():
    pygame.mixer.quit()
    sound = tones.tone(440, 100)
    assert isinstance(sound, tones.Silent)
    sound.play()
