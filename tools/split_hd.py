"""Split the HD body into one pack per layer, so the viewer can sharpen just the layer on screen
instead of downloading the whole 35 MB body.

Each pack has the same layout as the body files: a 4-byte JSON length, the JSON header
{"parts":[{k,l,v,i,o,b}, ...]} and the quantised vertices and indices. `k` is the part's index in the
full body (and in names.json), so names and colours stay the same.

    python3 tools/split_hd.py            # writes web/a/hd-l1..5.<hash>.bin and prints the map for body.html
"""
import gzip, hashlib, json, os, struct, glob

A = os.path.join(os.path.dirname(__file__), '..', 'web', 'a')
SRC = sorted(glob.glob(os.path.join(A, 'body-hd.*.bin')))[0]


def main():
    raw = gzip.open(SRC).read()
    jl = struct.unpack('<I', raw[:4])[0]
    meta = json.loads(raw[4:4 + jl])
    base = 4 + jl
    out = {}
    for layer in (1, 2, 3, 4, 5):
        parts, chunks, off = [], [], 0
        for k, p in enumerate(meta['parts']):
            if p.get('l', 1) != layer:
                continue
            n = p['v'] * 6 + p['i'] * 2
            data = raw[base + p['o']: base + p['o'] + n]
            pad = (-len(data)) % 4
            parts.append({'k': k, 'l': layer, 'v': p['v'], 'i': p['i'], 'o': off, 'b': p['b']})
            chunks.append(data + b'\0' * pad)
            off += len(data) + pad
        head = json.dumps({'parts': parts}, separators=(',', ':')).encode()
        head += b' ' * ((-(4 + len(head))) % 4)          # keep the data 4-byte aligned
        blob = struct.pack('<I', len(head)) + head + b''.join(chunks)
        gz = gzip.compress(blob, 9, mtime=0)
        h = hashlib.sha256(gz).hexdigest()[:8]
        for old in glob.glob(os.path.join(A, f'hd-l{layer}.*.bin')):
            os.remove(old)
        name = f'hd-l{layer}.{h}.bin'
        open(os.path.join(A, name), 'wb').write(gz)
        out[layer] = '/a/' + name
        print(name, len(parts), 'parts', round(len(gz) / 1e6, 2), 'MB')
    print('const HDL=' + json.dumps({str(k): v for k, v in out.items()}, separators=(',', ':')) + ';')


if __name__ == '__main__':
    main()
