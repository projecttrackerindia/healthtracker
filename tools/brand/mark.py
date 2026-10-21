# Mark: a place mark whose counter-form is a medical cross — "health, here".
#
# Urban Health's distinctive claim is not that it is health in a city; it is that it closes the distance
# between a family's home and the city's care — a technician you watch arrive, a queue you join before
# leaving, an SOS that already knows where you are. The map pin carries that, and it is already the most
# used shape in the product. The cross is punched out of the pin rather than set beside it, so the whole
# thing stays one silhouette and survives 16px, which is where marks die.
#
# ONE path, fill-rule evenodd: the cross is a real hole, not a shape filled in the background colour. That
# means the same glyph works on a coloured tile (the hole shows the tile) and bare on any background
# (the hole shows the page) — no second colour to pass around and nothing to get wrong on dark mode.
#
# Geometry on the same 64 grid as before: pin from (32,6), head radius ~20, tapered to a point at y≈55.
# Cross span 23, arm 8.2, optically centred at (32, 25.6) — above the geometric centre, because the point
# below pulls the visual weight down.
PIN = ("M32 6c-11 0-20 8.8-20 19.6 0 10.6 12.9 24.9 17.7 29.9a3.2 3.2 0 0 0 4.6 0"
       "C39.1 50.5 52 36.2 52 25.6 52 14.8 43 6 32 6z")
CROSS = "M27.9 14.1h8.2v7.4h7.4v8.2h-7.4v7.4h-8.2v-7.4h-7.4v-8.2h7.4z"
VIEW_BARE = "10 4 44 54"          # the pin alone, trimmed


def glyph(fg):
    return f'<path fill-rule="evenodd" d="{PIN}{CROSS}" fill="{fg}"/>'


def tile(bg, fg='#fff', size=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}">'
            f'<rect width="64" height="64" rx="16" fill="{bg}"/>{glyph(fg)}</svg>')


def bare(fg, size=64):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEW_BARE}" width="{size}" height="{size}">'
            f'{glyph(fg)}</svg>')
