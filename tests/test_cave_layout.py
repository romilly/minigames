import importlib
import sys

import pytest

from cave_layout import Layout, DESCRIPTION_LINES


def test_the_layout_does_not_need_pygame(monkeypatch):
    monkeypatch.setitem(sys.modules, 'pygame', None)
    monkeypatch.delitem(sys.modules, 'cave_layout', raising=False)
    importlib.import_module('cave_layout')


@pytest.mark.parametrize('size', [(240, 240), (320, 240)])
def test_layout_stacks_toolbar_map_text_and_view(size):
    layout = Layout(size[0], size[1], 22)
    assert layout.toolbar_h >= 22
    assert layout.toolbar_h <= layout.map_y
    assert layout.map_y + layout.map_h <= layout.text_y
    assert layout.text_y + DESCRIPTION_LINES * 22 <= layout.view_y
    assert layout.view_y + layout.view_h == size[1]
    assert layout.view_h < size[1] // 3                        # a strip, not half the screen
    assert layout.view_w == 2 * layout.view_h                  # the corridor keeps its shape
    assert layout.view_x * 2 + layout.view_w == size[0]        # centred, room either side
    assert layout.map_h >= 7 * 10                              # mine.yaml at 10px a cell


def test_menu_rows_and_hit_testing():
    layout = Layout(240, 240, 22)
    assert 4 <= layout.menu_rows <= 6
    x, y, w, h = layout.menu_item_rect(1)
    assert layout.menu_item_at((x + 5, y + 5), 3) == 1
    assert layout.menu_item_at((x + 5, y + 5), 1) is None      # only one item
    assert layout.menu_item_at((5, 2), 3) is None              # on the toolbar
