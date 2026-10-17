# Mark: rounded tile; a medical cross whose right arm becomes a pulse line ending in a tracking dot.
def glyph(fg):
    # cross (vertical bar + left arm) as one rounded path; the right arm becomes a heartbeat that ends in a tracking dot
    cross=('<path d="M21.5 15a4 4 0 0 1 4-4h3a4 4 0 0 1 4 4v34a4 4 0 0 1-4 4h-3a4 4 0 0 1-4-4V37.5H13a4 4 0 0 1-4-4v-3a4 4 0 0 1 4-4h8.5z" fill="%s"/>'%fg)
    pulse='<path d="M32 32h5l3.2-8 4.6 16 3.2-8h0.4" fill="none" stroke="%s" stroke-width="4.6" stroke-linecap="round" stroke-linejoin="round"/>'%fg
    dot='<circle cx="55.2" cy="32" r="3.3" fill="%s"/>'%fg
    return cross+pulse+dot
def tile(bg,fg='#fff',size=64):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}"><rect width="64" height="64" rx="16" fill="{bg}"/>{glyph(fg)}</svg>'
def bare(fg,size=64):
    return f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 64 64" width="{size}" height="{size}">{glyph(fg)}</svg>'
