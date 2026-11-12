"""Build data/xr/<book>.json cross-references from OpenBible.info (CC-BY),
via scrollmapper/bible_databases sources/extras/cross_references.txt.

Usage: python3 tools/build_xrefs.py path/to/cross_references.txt data/xr

Each book file maps "chapter:verse" to a space-separated list of references,
best first (by OpenBible votes). A reference is "book.chapter.verse" or
"book.chapter.verse-endverse". References with zero or negative votes are dropped.
"""
import json, os, sys

CODES = ("Gen Exod Lev Num Deut Josh Judg Ruth 1Sam 2Sam 1Kgs 2Kgs 1Chr 2Chr Ezra Neh Esth Job Ps Prov "
         "Eccl Song Isa Jer Lam Ezek Dan Hos Joel Amos Obad Jonah Mic Nah Hab Zeph Hag Zech Mal Matt Mark Luke "
         "John Acts Rom 1Cor 2Cor Gal Eph Phil Col 1Thess 2Thess 1Tim 2Tim Titus Phlm Heb Jas 1Pet 2Pet 1John "
         "2John 3John Jude Rev").split()
NUM = {c: i + 1 for i, c in enumerate(CODES)}


def parse(ref):
    b, c, v = ref.split('.')
    return NUM[b], int(c), int(v)


def main(src, out):
    books = {}
    with open(src, encoding='utf-8') as f:
        next(f)
        for line in f:
            parts = line.rstrip('\n').split('\t')
            if len(parts) < 3:
                continue
            frm, to, votes = parts[0], parts[1], int(parts[2])
            if votes <= 0:
                continue
            b, c, v = parse(frm)
            start = to.split('-')[0]
            tb, tc, tv = parse(start)
            label = '%d.%d.%d' % (tb, tc, tv)
            if '-' in to:
                eb, ec, ev = parse(to.split('-')[1])
                if (eb, ec) == (tb, tc) and ev > tv:
                    label += '-%d' % ev
            books.setdefault(b, {}).setdefault('%d:%d' % (c, v), []).append((votes, label))
    os.makedirs(out, exist_ok=True)
    total = 0
    for b, verses in books.items():
        data = {k: ' '.join(l for _, l in sorted(refs, key=lambda x: -x[0])) for k, refs in verses.items()}
        total += sum(len(r) for r in verses.values())
        with open(os.path.join(out, '%d.json' % b), 'w', encoding='utf-8') as f:
            json.dump(data, f, separators=(',', ':'))
    print('books', len(books), 'references', total)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
