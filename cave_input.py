"""The cave game's controls: keys (the pad, or the desktop's keyboard) and
touches (the Presto's screen, or the desktop's mouse), turned into moves and
commands for the core.
"""
import pygame

from cave_core import Cave
from cave_layout import Layout

KEY_ACTIONS = {pygame.K_LEFT: 'left', pygame.K_RIGHT: 'right',
               pygame.K_UP: 'forward', pygame.K_DOWN: 'around'}


def touch_action(pos: tuple[int, int], layout: Layout) -> str | None:
    """What a touch at pos means: left of the view turns left, right of it
    turns right, the view itself steps forward."""
    x, y = pos
    if y < layout.view_y:
        return None
    if x < layout.view_x:
        return 'left'
    if x >= layout.view_x + layout.view_w:
        return 'right'
    return 'forward'


class Menu:
    """The toolbar's menu: a list of (label, command) pairs, one selected."""

    def __init__(self) -> None:
        self.items: list[tuple[str, tuple]] = []      # empty when closed
        self.selected = 0

    @property
    def is_open(self) -> bool:
        return bool(self.items)

    def show(self, items: list[tuple[str, tuple]], rows: int | None = None) -> None:
        """Open with these items; if there are more than rows, keep the last
        (Inventory) and as many of the first as fit."""
        if rows and len(items) > rows:
            items = items[:rows - 1] + items[-1:]
        self.items = items
        self.selected = 0

    def close(self) -> None:
        self.items = []

    def move(self, step: int) -> None:
        self.selected = (self.selected + step) % len(self.items)

    def chosen(self) -> tuple:
        return self.items[self.selected][1]


MENU_KEYS = (pygame.K_a, pygame.K_SPACE, pygame.K_RETURN)


class Controls:
    """Turns key presses and touches into moves and commands for the game.

    Owns the menu's state while it's open; drawing reads it from `menu`."""

    def __init__(self, game: Cave, menu: Menu, layout: Layout) -> None:
        self.game = game
        self.menu = menu
        self.layout = layout

    def handle(self, event: "pygame.event.Event") -> list[str]:
        """One event. Returns what happened, for sounds."""
        if event.type == pygame.KEYDOWN:
            return self._key(event.key)
        if event.type == pygame.MOUSEBUTTONDOWN:
            return self._touch(event.pos)
        return []

    def _key(self, key: int) -> list[str]:
        game, menu = self.game, self.menu
        if game.won:
            return game.act('forward') if key in KEY_ACTIONS or key in MENU_KEYS else []
        if menu.is_open:
            if key in (pygame.K_UP, pygame.K_DOWN):
                menu.move(-1 if key == pygame.K_UP else 1)
                return []
            if key in MENU_KEYS:
                command = menu.chosen()
                menu.close()
                return game.do(command)
            if key == pygame.K_b:
                menu.close()
            return []
        if key in MENU_KEYS:
            return self._open_menu()
        if key in KEY_ACTIONS:
            return game.act(KEY_ACTIONS[key])
        return []

    def _touch(self, pos: tuple[int, int]) -> list[str]:
        game, menu, layout = self.game, self.menu, self.layout
        if game.won:
            return game.act('forward')
        if menu.is_open:
            items = menu.items
            menu.close()
            index = layout.menu_item_at(pos, len(items))
            return [] if index is None else game.do(items[index][1])
        if pos[1] < layout.toolbar_h:
            return self._open_menu()
        action = touch_action(pos, layout)
        return game.act(action) if action else []

    def _open_menu(self) -> list[str]:
        self.menu.show(self.game.menu_items(), self.layout.menu_rows)
        return ['menu']
