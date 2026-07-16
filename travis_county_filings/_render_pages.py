"""Render every PDF page to grayscale PNG for vision extraction.

Output: <out_root>/<official>/<report-stem>/p0001.png ...
"""
import fitz, json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
OUT_ROOT = sys.argv[1] if len(sys.argv) > 1 else os.path.join(ROOT, '_pages')
DPI = 200

inv = json.load(open(os.path.join(ROOT, '_inventory.json')))
done_pages = 0
for r in inv:
    stem = r['file'][:-4]
    outdir = os.path.join(OUT_ROOT, r['official'], stem)
    os.makedirs(outdir, exist_ok=True)
    doc = fitz.open(os.path.join(ROOT, r['official'], r['file']))
    for i, page in enumerate(doc):
        dest = os.path.join(outdir, f'p{i+1:04d}.png')
        if os.path.exists(dest):
            continue
        pix = page.get_pixmap(dpi=DPI, colorspace=fitz.csGRAY)
        pix.save(dest)
    done_pages += doc.page_count
    doc.close()
    print(f"{done_pages:5d} pages  {r['official']}/{stem}", flush=True)
print('DONE', done_pages)
