"""Small helpers shared by the games. Runs under desktop pygame and the shim."""


def render_fitting(fonts, text, colour, max_width):
    """Render text with the first (largest) font it fits in; the last font if none."""
    for font in fonts:
        surface = font.render(text, False, colour)
        if surface.get_width() <= max_width:
            return surface
    return surface
