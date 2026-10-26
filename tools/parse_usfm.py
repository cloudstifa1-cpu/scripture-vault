# Parse eBible KJV2006 USFM into plain verse text + Strong's tags (char offsets into the plain text).
import re, os, json, sys
ORDER = "GEN EXO LEV NUM DEU JOS JDG RUT 1SA 2SA 1KI 2KI 1CH 2CH EZR NEH EST JOB PSA PRO ECC SNG ISA JER LAM EZK DAN HOS JOL AMO OBA JON MIC NAM HAB ZEP HAG ZEC MAL MAT MRK LUK JHN ACT ROM 1CO 2CO GAL EPH PHP COL 1TH 2TH 1TI 2TI TIT PHM HEB JAS 1PE 2PE 1JN 2JN 3JN JUD REV".split()
TOK = re.compile(r'\\(\+?[a-z]+[0-9]*)\*?|[^\\]+')
def parse(path):
    src = open(path, encoding='utf-8-sig').read()
    bid = re.search(r'\\id (\w+)', src).group(1)
    # drop footnotes and cross references entirely
    src = re.sub(r'\\f .*?\\f\*', '', src, flags=re.S)
    src = re.sub(r'\\x .*?\\x\*', '', src, flags=re.S)
    chapters = {}
    cur = None  # (c, v)
    c = 0
    buf = {}
    # work line by line on paragraph markers; we only care about \c, \v and inline content
    text_mode = None
    for line in src.split('\n'):
        line = line.rstrip()
        m = re.match(r'\\(\w+)\s?(.*)', line)
        if not m:
            if cur and line.strip(): buf[cur].append(line)
            continue
        tag, rest = m.group(1), m.group(2)
        if tag == 'c':
            c = int(rest.split()[0]); cur = None; continue
        if tag in ('id','h','toc1','toc2','toc3','mt1','mt2','s1','d','tl','ide','rem'):
            if tag in ('d','s1'): cur = None if tag=='d' else cur
            continue
        if tag in ('p','q1','q2','b','m','pi','nb'):
            if not rest: continue
            line = rest; m = re.match(r'\\v (\d+) ?(.*)', line)
            if not m:
                if cur: buf[cur].append(rest)
                continue
            tag, rest = 'v', m.group(1) + ' ' + m.group(2)
        if tag == 'v':
            # a line can hold several verses
            parts = re.split(r'\\v (\d+) ?', '\\v ' + rest)
            for i in range(1, len(parts), 2):
                cur = (c, int(parts[i])); buf.setdefault(cur, []).append(parts[i+1])
            continue
        if cur: buf[cur].append(line)
    out = {}
    for (cc, vv), pieces in buf.items():
        raw = ' '.join(pieces)
        text, tags = '', []
        pos = 0
        # walk tokens
        i = 0
        word_start = None; word_buf = ''
        for mm in re.finditer(r'\\(\+?w)\s(.*?)\|strong="([^"]+)"\\\+?w\*|\\\+?[a-z]+[0-9]*(?:\*|\s)?|([^\\]+)', raw):
            if mm.group(1):
                w = mm.group(2); nums = ' '.join(re.sub(r'^([GH])0*', r'\1', n) for n in mm.group(3).split())
                s = len(text); text += w; tags.append([s, len(text), nums])
            elif mm.group(4) is not None:
                text += mm.group(4)
        # clean: remove pilcrow, collapse spaces (adjust offsets)
        clean, mp = '', []
        prev_space = True
        for ch in text:
            if ch == '¶': mp.append(len(clean)); continue
            if ch.isspace():
                if prev_space: mp.append(len(clean)); continue
                clean += ' '; prev_space = True; mp.append(len(clean) - 1); continue
            mp.append(len(clean)); clean += ch; prev_space = False
        mp.append(len(clean))
        strip_l = len(clean) - len(clean.lstrip())
        final = clean.strip()
        def remap(k): return max(0, min(len(final), mp[k] - strip_l))
        ntags = []
        for s, e, n in tags:
            a, b = remap(s), remap(e)
            seg = final[a:b]
            # trim spaces in tag range
            while a < b and final[a] == ' ': a += 1
            while b > a and final[b-1] == ' ': b -= 1
            if b > a: ntags.append([a, b, n])
        out.setdefault(cc, {})[vv] = (final, ntags)
    return bid, out

if __name__ == '__main__':
    d = sys.argv[1]; res = {}
    for f in sorted(os.listdir(d)):
        if f.endswith('.usfm'):
            bid, data = parse(os.path.join(d, f))
            if bid in ORDER: res[ORDER.index(bid) + 1] = data
    json.dump({str(k): {str(c): {str(v): list(t) for v, t in vs.items()} for c, vs in ch.items()} for k, ch in res.items()},
              open(sys.argv[2], 'w'), ensure_ascii=False)
    print('books', len(res), 'verses', sum(len(vs) for ch in res.values() for vs in ch.values()))
