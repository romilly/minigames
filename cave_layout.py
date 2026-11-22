"""Where everything goes on the screen, for drawing and for hit-testing touches.

No pygame: just arithmetic on the screen's size and the font's line height.
"""

# Frames for each depth ahead, as fractions of the view's width and height.
FRAMES = (0.5, 0.3, 0.175, 0.1, 0.06)
DESCRIPTION_LINES = 3
VIEW_SHARE = 4 / 15     # of the screen's height, for the view ahead


class Layout:
    """From the top: toolbar, map, description, then the view ahead in a
    strip, twice as wide as it is high, with room either side to turn."""

    def __init__(self, width: int, height: int, line_height: int) -> None:
        self.width, self.height = width, height
        self.line_height = line_height
        self.toolbar_h = line_height + 4
        self.view_h = int(height * VIEW_SHARE)
        self.view_y = height - self.view_h
        self.view_w = 2 * self.view_h
        self.view_x = (width - self.view_w) // 2
        self.text_y = self.view_y - DESCRIPTION_LINES * line_height - 2
        self.map_y = self.toolbar_h + 2
        self.map_h = self.text_y - self.map_y - 2
        # The menu covers the map and text, one row per item
        self.menu_y = self.toolbar_h + 2
        self.menu_row_h = line_height + 6
        self.menu_rows = (self.view_y - self.menu_y) // self.menu_row_h

    def menu_item_rect(self, index: int) -> tuple[int, int, int, int]:
        return (0, self.menu_y + index * self.menu_row_h, self.width, self.menu_row_h)

    def menu_item_at(self, pos: tuple[int, int], count: int) -> int | None:
        """Which of count menu items pos is on, or None."""
        index = (pos[1] - self.menu_y) // self.menu_row_h
        if pos[1] >= self.menu_y and index < count:
            return index
        return None

    def frame(self, depth: int) -> tuple[int, int, int, int]:
        """The rectangle where the walls at a depth meet the next: x0, y0, x1, y1."""
        f = FRAMES[depth]
        cx, cy = self.view_x + self.view_w // 2, self.view_y + self.view_h // 2
        hw, hh = int(f * self.view_w), int(f * self.view_h)
        return cx - hw, cy - hh, cx + hw, cy + hh
