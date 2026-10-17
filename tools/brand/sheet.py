import json
F=json.load(open('files.json'))
def img(n,h):return f'<div style="height:{h}px">{F[n].replace("<svg ",f"<svg height=\"{h}\" ",1)}</div>'
row=lambda title,sub,col,n: f'''<section><div class="lab"><b style="color:{col}">{title}</b><span>{sub}</span><code>{col}</code></div>
<div class="sw">{img(n+"-logo",52)}</div><div class="sw" style="background:{col}">{img(n+"-logo-white",52)}</div><div class="sw icons">{img(n+"-icon",88)}{img(n+"-icon",44)}{img(n+"-icon",22)}</div></section>'''
h=f'''<html><head><meta charset="utf-8"><style>body{{margin:0;background:#f4f5f8;font:14px Inter,system-ui;color:#1C1E26;padding:40px}}h1{{font-size:30px;letter-spacing:-.03em;margin:0 0 4px}}p{{color:#6b7285;margin:0 0 26px}}
section{{display:grid;grid-template-columns:190px minmax(0,1fr) minmax(0,1fr) 220px;gap:14px;margin-bottom:14px}}.lab{{display:flex;flex-direction:column;justify-content:center;gap:4px}}.lab b{{font-size:18px}}.lab span{{color:#6b7285;font-size:12.5px}}code{{font:600 12px ui-monospace,monospace;color:#6b7285}}
.sw{{border-radius:18px;display:flex;align-items:center;justify-content:center;padding:24px;background:#fff;overflow:hidden}}.icons{{gap:16px}}svg{{display:block;max-width:100%}}
.mono{{display:grid;grid-template-columns:repeat(3,1fr);gap:14px;margin-top:22px}}</style></head><body>
<h1>TheHealthTracker · logo system</h1><p>One mark — a medical cross whose arm becomes a heartbeat ending in a tracking dot — in one colour per audience.</p>
{row("Users","People & families · the app",'#2F5BFF','user')}
{row("Partners","Doctors, hospitals, pharmacies, labs, insurers",'#0B8A7C','partner')}
{row("Admin","Internal console",'#1C1E26','admin')}
<div class="mono"><div class="sw">{img("mono-black-logo",44)}</div><div class="sw" style="background:#111">{img("mono-white-logo",44)}</div><div class="sw">{img("user-logo-stacked",120)}</div></div>
</body></html>'''
open('sheet.html','w').write(h)
