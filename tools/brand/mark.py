# Mark: a rounded tile holding a medical cross whose right arm becomes a pulse line ending in a tracking dot.
#
# Three readings in one shape: the cross is health, the pulse is the body's own signal, and the dot is the
# reading being recorded. Drawn on a 64-unit grid inside a rounded tile (radius 16).
#
# The cross is a single rounded path — the vertical bar and the left arm only — because the right arm is where
# the pulse takes over. The pulse is a stroked path rather than a filled one so its weight stays even through
# the corners, and it is capped and joined round to match the cross's own rounding.
VIEW_BARE = "0 0 64 64"

CROSS_D = ("M21.5 15a4 4 0 0 1 4-4h3a4 4 0 0 1 4 4v34a4 4 0 0 1-4 4h-3a4 4 0 0 1-4-4V37.5H13"
           "a4 4 0 0 1-4-4v-3a4 4 0 0 1 4-4h8.5z")
PULSE_D = "M32 32h5l3.2-8 4.6 16 3.2-8h0.4"
PULSE_W = 4.6
DOT = (55.2, 32, 3.3)


def glyph(fg, styled=False):
    """The mark's three parts.

    `styled` emits style="fill:…" / style="stroke:…" instead of presentation attributes, for the places that
    colour the mark with a CSS custom property — var() is not valid inside a fill="" attribute."""
    if styled:
        f, s = f'style="fill:{fg}"', f'style="stroke:{fg}"'
    else:
        f, s = f'fill="{fg}"', f'stroke="{fg}"'
    cx, cy, r = DOT
    return (f'<path d="{CROSS_D}" {f}/>'
            f'<path d="{PULSE_D}" fill="none" {s} stroke-width="{PULSE_W}" '
            f'stroke-linecap="round" stroke-linejoin="round"/>'
            f'<circle cx="{cx}" cy="{cy}" r="{r}" {f}/>')


def tile(bg, fg='#fff', size=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}">'
            f'<rect width="64" height="64" rx="16" fill="{bg}"/>{glyph(fg)}</svg>')


def bare(fg, size=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEW_BARE}" width="{size}" height="{size}">'
            f'{glyph(fg)}</svg>')
