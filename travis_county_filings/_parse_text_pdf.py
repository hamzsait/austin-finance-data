"""Prototype: parse TEC Form C/OH Schedule A1/A2 entries from a text-layer PDF.

Proves the deterministic path for electronically-filed reports (no vision).
Entries are laid out as repeating blocks; we key off the per-entry
'Date / Full name of contributor / Amount' row and read the following lines.
"""
import re, sys, pymupdf

AMT = re.compile(r"^\$?([\d,]+\.\d{2})$")
DATE = re.compile(r"^(\d{2}/\d{2}/\d{4})$")


def lines_of(page):
    """Text lines in reading order, grouped by y."""
    words = page.get_text("words")
    rows = {}
    for w in words:
        rows.setdefault(round(w[1] / 4), []).append(w)
    out = []
    for k in sorted(rows):
        ws = sorted(rows[k], key=lambda w: w[0])
        out.append(" ".join(w[4] for w in ws))
    return out


def parse_page(page, pno):
    txt = page.get_text()
    up = txt.upper()
    if "SCHEDULE" not in up:
        return None, []
    if "MONETARY POLITICAL CONTRIBUTIONS" in up and "NON-MONETARY" not in up:
        sched = "A1"
    elif "NON-MONETARY" in up:
        sched = "A2"
    else:
        return None, []

    ls = lines_of(page)
    entries = []
    for i, ln in enumerate(ls):
        # entry line: "01/15/2026 Albert, David $100.00"
        m = re.match(r"^(\d{2}/\d{2}/\d{4})\s+(.+?)\s+\$([\d,]+\.\d{2})$", ln)
        if not m:
            continue
        date, name, amt = m.group(1), m.group(2).strip(), m.group(3).replace(",", "")
        # address block: lines after, until "Principal occupation"
        addr, occ_emp = [], ""
        for j in range(i + 1, min(i + 9, len(ls))):
            l2 = ls[j]
            if l2.startswith("Contributor address"):
                continue
            if l2.startswith("Principal occupation"):
                if j + 1 < len(ls):
                    occ_emp = ls[j + 1]
                break
            if re.match(r"^\d{2}/\d{2}/\d{4}\s", l2):
                break
            addr.append(l2)
        csz = next((a for a in reversed(addr) if re.search(r",\s*[A-Z]{2}\s+\d{5}", a)), "")
        entries.append({
            "page": pno, "schedule": sched, "date": date, "name": name,
            "amount": float(amt), "city_state_zip": csz,
            "occ_employer_raw": occ_emp,
            "street": " ".join(a for a in addr if a != csz),
        })
    return sched, entries


def main(path):
    doc = pymupdf.open(path)
    all_entries = []
    sched_pages = 0
    for i, page in enumerate(doc, 1):
        s, e = parse_page(page, i)
        if s:
            sched_pages += 1
        all_entries.extend(e)
    total = sum(e["amount"] for e in all_entries)
    print(f"{path}")
    print(f"  pages={doc.page_count} schedule pages={sched_pages}")
    print(f"  entries={len(all_entries)}  sum=${total:,.2f}")
    print(f"  A1={sum(1 for e in all_entries if e['schedule']=='A1')}"
          f"  A2={sum(1 for e in all_entries if e['schedule']=='A2')}")
    print("  sample:")
    for e in all_entries[:5]:
        print("   ", e)
    # cover sheet totals for reconciliation
    for i, page in enumerate(doc, 1):
        t = page.get_text()
        if "TOTAL POLITICAL CONTRIBUTIONS" in t.upper():
            nums = re.findall(r"\$?([\d,]+\.\d{2})", t)
            print(f"  cover page {i} numbers: {nums[:8]}")
            break


if __name__ == "__main__":
    main(sys.argv[1])
