import pytest

import cave


class SixPixelFont:
    def size(self, text):
        return (6 * len(text), 8)


def test_wrap_breaks_between_words():
    assert cave.wrap(SixPixelFont(), 'one two three four', 60) == ['one two', 'three four']


def test_wrap_keeps_a_word_too_long_for_a_line():
    assert cave.wrap(SixPixelFont(), 'abcdefghijklmnop x', 30) == ['abcdefghijklmnop', 'x']
