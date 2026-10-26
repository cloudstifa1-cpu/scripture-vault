# Builds Scripture Vault concordance data:
#  data/kjv/{b}.json      KJV text (eBible KJV2006, public domain) - replaces old KJV text
#  data/sn/{b}.json       Strong's tags per verse ("start,end,NUM;...") for KJV
#  data/sd/{G|H}{k}.json  Strong's dictionary chunks (100 numbers each) with every occurrence
#  data/sd/gloss.json     short gloss for every Strong's number (lemma, translit, meaning)
#  data/sd/en.json        English KJV word -> Strong's numbers that it translates
#  data/sd/vc.json        verses per chapter (to turn verse ids back into references)
#  data/{ver}/words.json  word concordance per version: [word, times]
import json, re, os, sys, zipfile, collections, html
import xml.etree.ElementTree as ET
APP = sys.argv[1]; PARSED = sys.argv[2]; GREEK_ZIP = sys.argv[3]; HEB = sys.argv[4]
D = APP + '/data'
p = json.load(open(PARSED))
names = [json.load(open(f'{D}/kjv/{b}.json'))['n'] for b in range(1, 67)]

def b36(n):
    s = '0123456789abcdefghijklmnopqrstuvwxyz'; o = ''
    while True:
        n, r = divmod(n, 36); o = s[r] + o
        if n == 0: return o

# 1-2. KJV text + tags, verse ids, occurrences
os.makedirs(f'{D}/sn', exist_ok=True); os.makedirs(f'{D}/sd', exist_ok=True)
occ = collections.defaultdict(list); vc = []; vid = 0
STOP = set('the a an of to and unto in on for by with from that which is be was were shall will it he she they them his her their its i me my we us our ye you your thou thee thy not as at or but so all this these those there then when what who whom'.split())
en = collections.defaultdict(collections.Counter)
rev = collections.defaultdict(collections.Counter); revf = collections.defaultdict(collections.Counter)
WORD = re.compile(r"[^\W\d_]+(?:['\-][^\W\d_]+)*")
def words_of(t):
    for m in WORD.finditer(t):
        w = m.group(0)
        if w.lower().endswith("'s") and len(w) > 3: w = w[:-2]
        yield w
for b in range(1, 67):
    chs = p[str(b)]; nc = max(int(c) for c in chs)
    text_c, tag_c, vcb = [], [], []
    for c in range(1, nc + 1):
        vs = chs[str(c)]; nv = max(int(v) for v in vs); vcb.append(nv)
        tc, gc = [], []
        for v in range(1, nv + 1):
            t, tags = vs.get(str(v), ['', []])
            t = t.replace('’', "'").replace('‘', "'")
            tc.append(t)
            gc.append(';'.join(f'{s},{e},{n}' for s, e, n in tags))
            for s, e, n in tags:
                for num in n.split():
                    occ[num].append(f'{b36(vid)}.{b36(s)}.{b36(e)}')
                ws = [w for w in words_of(t[s:e])]
                main = [w for w in ws if w.lower() not in STOP] or ws[-1:]
                for w in main:
                    for num in n.split(): en[w.lower()][num] += 1; rev[num][w.lower()] += 1; revf[num][w] += 1
            vid += 1
        text_c.append(tc); tag_c.append(gc)
    json.dump({'n': names[b-1], 'c': text_c}, open(f'{D}/kjv/{b}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    json.dump({'c': tag_c}, open(f'{D}/sn/{b}.json', 'w'), separators=(',', ':'))
    vc.append(vcb)
json.dump(vc, open(f'{D}/sd/vc.json', 'w'), separators=(',', ':'))
print('verses', vid)

# 3. Dictionaries (public-domain Strong's text only)
def clean(s): return re.sub(r'\s+', ' ', s or '').strip()
dic = {}
gx = zipfile.ZipFile(GREEK_ZIP).read('strongsgreek.xml').decode('utf-8')
gx = re.sub(r'<!DOCTYPE.*?\]>', '', gx, flags=re.S)
groot = ET.fromstring(gx)
def gtext(el):
    # flatten an element, turning <greek> into Greek letters and <strongsref> into G123 refs
    out = el.text or ''
    for ch in el:
        if ch.tag == 'greek': out += ch.get('unicode', '')
        elif ch.tag == 'strongsref': out += ('G' if ch.get('language') == 'GREEK' else 'H') + str(int(ch.get('strongs')))
        elif ch.tag == 'pronunciation': out += ch.get('strongs', '')
        else: out += gtext(ch)
        out += ch.tail or ''
    return out
for e in groot.iter('entry'):
    n = 'G' + str(int(e.get('strongs')))
    g = e.find('greek'); pr = e.find('pronunciation')
    dic[n] = {'l': g.get('unicode') if g is not None else '', 'x': g.get('translit') if g is not None else '',
              'p': pr.get('strongs') if pr is not None else '',
              'd': clean(gtext(e.find('strongs_def'))) if e.find('strongs_def') is not None else '',
              'r': clean(gtext(e.find('strongs_derivation'))) if e.find('strongs_derivation') is not None else '',
              'k': re.sub(r'(^|\s|\()X\s', r'\1× ', clean(gtext(e.find('kjv_def'))).lstrip(':- ').strip()) if e.find('kjv_def') is not None else ''}
NS = '{http://www.bibletechnologies.net/2003/OSIS/namespace}'
hroot = ET.parse(HEB).getroot()
def htext(el):
    out = el.text or ''
    for ch in el:
        t = ch.tag.replace(NS, '')
        if t == 'w':
            if ch.get('src'): out += ch.get('src') if ch.get('src')[0] in 'GH' else 'H' + ch.get('src')
            else: out += ch.get('lemma') or (ch.text or '')
            if ch.get('src') and (ch.get('lemma') or ch.text): out += ' (' + (ch.get('lemma') or ch.text) + ')'
        else: out += htext(ch)
        out += ch.tail or ''
    return out
for e in hroot.iter(NS + 'div'):
    if e.get('type') != 'entry': continue
    w = e.find(NS + 'w');
    if w is None or not w.get('ID'): continue
    n = 'H' + str(int(w.get('ID')[1:].rstrip('ab')))
    notes = {x.get('type'): clean(htext(x)) for x in e.findall(NS + 'note')}
    dic[n] = {'l': w.get('lemma', ''), 'x': w.get('xlit', ''), 'p': w.get('POS', ''),
              'd': notes.get('explanation', ''), 'r': notes.get('exegesis', ''), 'k': notes.get('translation', '')}
print('dictionary', sum(1 for k in dic if k[0] == 'G'), 'Greek,', sum(1 for k in dic if k[0] == 'H'), 'Hebrew')

# chunks with occurrences
chunks = collections.defaultdict(dict)
for n, ent in dic.items():
    o = occ.get(n, []); ent = dict(ent); ent['o'] = ','.join(o)
    chunks[n[0] + str(int(n[1:]) // 100)][n[1:]] = ent
missing = [n for n in occ if n not in dic]
print('numbers used in text but missing from dictionary:', len(missing), missing[:10])
for k, v in chunks.items():
    json.dump(v, open(f'{D}/sd/{k}.json', 'w'), ensure_ascii=False, separators=(',', ':'))
def short(s, n=44):
    s = re.sub(r'^\s*(properly|i\.e\.|a primitive root;?)\s*,?\s*', '', s).strip(' ,;:.')
    s = re.split(r'[;:]', s)[0]
    return s if len(s) <= n else s[:n].rsplit(' ', 1)[0] + '…'
def kjv_words(n):
    out = []
    allc = sum(rev[n].values()) or 1
    top = [(w, c) for w, c in rev[n].most_common(8) if w not in STOP or c >= 0.4 * allc] or rev[n].most_common(1)
    for w, c in top[:3]:
        forms = [(f, k) for f, k in revf[n].items() if f.lower() == w]
        lower = sum(k for f, k in forms if f == w)
        best = max(forms, key=lambda x: x[1])[0]
        out.append(w if lower >= 0.3 * c else best)
    return ', '.join(out)
gloss = {n: [e['l'], e['x'], kjv_words(n) or short(e['d'] or e['k'])] for n, e in dic.items()}
json.dump(gloss, open(f'{D}/sd/gloss.json', 'w'), ensure_ascii=False, separators=(',', ':'))
json.dump({w: [[n, c] for n, c in cnt.most_common(8)] for w, cnt in en.items()}, open(f'{D}/sd/en.json', 'w'), separators=(',', ':'))

# 4. Word concordance for every version
for ver in sorted(os.listdir(D)):
    if not os.path.isfile(f'{D}/{ver}/1.json') or ver in ('sn',): continue
    cnt = collections.Counter(); forms = collections.defaultdict(collections.Counter)
    for b in range(1, 67):
        for ch in json.load(open(f'{D}/{ver}/{b}.json'))['c']:
            for t in ch:
                for w in words_of(t.replace('’', "'")):
                    k = w.lower(); cnt[k] += 1; forms[k][w] += 1
    lst = sorted(([forms[k].most_common(1)[0][0], c] for k, c in cnt.items()), key=lambda x: x[0].lower())
    json.dump(lst, open(f'{D}/{ver}/words.json', 'w'), ensure_ascii=False, separators=(',', ':'))
    print(ver, 'words', len(lst))
