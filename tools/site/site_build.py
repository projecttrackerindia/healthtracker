"""Build the landing page: inject the outlined logo and mark, then pre-compress site files."""
import json, brotli, gzip, os
F = json.load(open('/home/claude/work/brand/files.json'))
s = open('/home/claude/work/site_src/index.html', encoding='utf-8').read()
logo = F['user-logo'].replace('<svg ', '<svg role="img" aria-label="TheHealthTracker" ', 1)
s = s.replace('{{LOGO}}', logo).replace('{{MARK}}', F['user-icon'].replace('<svg ', '<svg width="44" height="44" aria-hidden="true" ', 1))
s = s.replace("${'<input inputmode=\"numeric\" maxlength=\"1\" aria-label=\"Digit\">'.repeat(6)}", ''.join(f'<input inputmode="numeric" maxlength="1" aria-label="Digit {i+1}">' for i in range(6)))
s = s.replace('</style>', '@media (prefers-color-scheme:dark){:root:not([data-theme=light]) .logo svg path[transform],:root:not([data-theme=light]) footer svg path[transform]{fill:#E8EDFF}}\n</style>', 1)
assert '{{' not in s and '.repeat(6)' not in s
OUT = '/home/claude/work/dokko/site'
open(f'{OUT}/index.html', 'w', encoding='utf-8').write(s)
for root, _, files in os.walk(OUT):
    for f in files:
        if f.endswith(('.html', '.js', '.css', '.svg', '.json')):
            p = os.path.join(root, f); d = open(p, 'rb').read()
            open(p + '.br', 'wb').write(brotli.compress(d, quality=11)); open(p + '.gz', 'wb').write(gzip.compress(d, 9))
print('site ok', len(s))
