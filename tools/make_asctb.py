"""Cells and markers for each organ close-up, from the HuBMAP Human Reference Atlas ASCT+B tables (v2.0 release, CC BY 4.0):
for each anatomical structure, the cell types found there and the genes or proteins that identify them, with the table's
authors, version and DOI so a researcher can cite it.

    python3 tools/make_asctb.py /path/to/asct-b-*.csv     -> web/a/asctb.<h>.json
"""
import csv, glob, hashlib, json, os, re, sys

A = os.path.join(os.path.dirname(__file__), '..', 'web', 'a')
KEY = {'vh-heart': 'heart', 'vh-kidney': 'kidney', 'vh-liver': 'liver', 'vh-lung': 'lung', 'vh-pancreas': 'pancreas', 'vh-skin': 'skinl',
       'allen-brain': 'brain', 'vh-knee': 'knee', 'vh-lymph-node': 'lnode', 'vh-prostate': 'prostate', 'vh-thymus': 'thymus',
       'vh-main-bronchus': 'bronchus', 'vh-palatine-tonsil': 'tonsil'}


def read(path):
    rows = list(csv.reader(open(path, encoding='utf-8', errors='replace')))
    meta, hi = {}, None
    for i, r in enumerate(rows):
        if r and r[0].startswith('AS/1'):
            hi = i; break
        if r and r[0].endswith(':'):
            meta[r[0].rstrip(':')] = r[1].strip()
    head = rows[hi]
    col = {h: j for j, h in enumerate(head)}
    def cols(prefix, suffix):
        return sorted([(int(m.group(1)), j) for h, j in col.items() for m in [re.match(prefix + r'/(\d+)' + suffix + '$', h)] if m])
    as_l, as_i = cols('AS', '/LABEL'), cols('AS', '/ID')
    ct_l, ct_i = cols('CT', '/LABEL'), cols('CT', '/ID')
    bg = [j for h, j in col.items() if re.match(r'BGene/\d+$', h)] + [j for h, j in col.items() if re.match(r'BProtein/\d+$', h)]
    out = {}
    for r in rows[hi + 1:]:
        if not r or not any(r): continue
        g = lambda j: r[j].strip() if j < len(r) else ''
        asl = [(g(j), g(i)) for (_, j), (_, i) in zip(as_l, as_i) if g(j)]
        cts = [(g(j), g(i)) for (_, j), (_, i) in zip(ct_l, ct_i) if g(j)]
        if not asl or not cts: continue
        a, aid = asl[-1]
        c, cid = cts[-1]
        mk = []
        for j in bg:
            v = g(j)
            if v and v not in mk: mk.append(v)
        d = out.setdefault(a, {'id': aid, 'path': [x for x, _ in asl[:-1]][-2:], 'cells': {}})
        e = d['cells'].setdefault(c, {'id': cid, 'mk': []})
        for m in mk:
            if m not in e['mk'] and len(e['mk']) < 5: e['mk'].append(m)
    structs = [{'as': a, 'id': v['id'], 'in': v['path'], 'cells': [{'ct': c, 'id': e['id'], 'mk': e['mk']} for c, e in v['cells'].items()]} for a, v in out.items()]
    return {'title': meta.get('Anatomical Structures, Cell Types and Biomarkers Table for', '') or rows[0][0].strip('"'),
            'authors': meta.get('Author Name(s)', ''), 'doi': meta.get('Data DOI', ''), 'version': meta.get('Version Number', ''), 'date': meta.get('Date', ''),
            'structures': structs}


def main(files):
    res = {}
    for f in files:
        stem = re.sub(r'^asct-b-|\.csv$', '', os.path.basename(f))
        k = KEY.get(stem)
        if not k: continue
        t = read(f); res[k] = t
        print(k, len(t['structures']), 'structures', sum(len(s['cells']) for s in t['structures']), 'cell entries')
    js = json.dumps({'source': 'HuBMAP Human Reference Atlas ASCT+B tables, v2.0 release (CC BY 4.0)', 'organs': res}, separators=(',', ':')).encode()
    h = hashlib.sha256(js).hexdigest()[:8]
    for old in glob.glob(os.path.join(A, 'asctb.*.json')): os.remove(old)
    open(os.path.join(A, f'asctb.{h}.json'), 'wb').write(js)
    print(f'/a/asctb.{h}.json', round(len(js) / 1e3), 'KB')


if __name__ == '__main__':
    main(sys.argv[1:])
