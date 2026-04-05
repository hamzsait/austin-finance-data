"""
Sample-based scoring run to understand score distribution before full pipeline.
Strategy:
  1. Normalize all unique individual donor records
  2. Block by (last_name_normalized, zip5)
  3. Score all pairs within each block
  4. Plot distribution + report tier stats
"""

import sqlite3
import re
import unicodedata
from collections import defaultdict
from rapidfuzz import fuzz
from jellyfish import soundex
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches

DB = "austin_finance.db"

# ── Nickname table ────────────────────────────────────────────────────────────
NICKNAMES = {
    "bill": "william", "billy": "william", "will": "william", "willy": "william",
    "bob": "robert", "rob": "robert", "bobby": "robert",
    "jim": "james", "jimmy": "james", "jamie": "james",
    "tom": "thomas", "tommy": "thomas",
    "mike": "michael", "mick": "michael", "mickey": "michael",
    "dick": "richard", "rick": "richard", "ricky": "richard",
    "dave": "david", "davy": "david",
    "joe": "joseph", "joey": "joseph",
    "sue": "susan", "susie": "susan",
    "liz": "elizabeth", "beth": "elizabeth", "betty": "elizabeth", "lisa": "elizabeth",
    "kate": "katherine", "kathy": "katherine", "katie": "kathryn", "kat": "katherine",
    "jan": "janet", "phil": "philip",
    "chris": "christopher",
    "dan": "daniel", "danny": "daniel",
    "pat": "patricia", "patty": "patricia",
    "sam": "samuel",
    "ed": "edward", "eddie": "edward", "ted": "edward",
    "ben": "benjamin",
    "nick": "nicholas",
    "tony": "anthony",
    "andy": "andrew",
    "alex": "alexander",
    "greg": "gregory",
    "ken": "kenneth",
    "steve": "stephen",
    "matt": "matthew",
    "jeff": "jeffrey",
    "jerry": "gerald", "gerry": "gerald",
    "chuck": "charles", "charlie": "charles",
    "harry": "harold",
    "hank": "henry",
    "jack": "john",
    "peggy": "margaret", "meg": "margaret", "maggie": "margaret",
    "peg": "margaret",
    "cathy": "catherine", "cat": "catherine",
    "barb": "barbara", "babs": "barbara",
    "cindy": "cynthia",
    "donna": "madonna",
    "dot": "dorothy", "dottie": "dorothy",
    "frank": "francis",
    "fred": "frederick",
    "jake": "jacob",
    "jay": "james",
    "lenny": "leonard",
    "lou": "louis",
    "max": "maximilian",
    "nan": "nancy",
    "nat": "nathaniel",
    "ray": "raymond",
    "ron": "ronald", "ronnie": "ronald",
    "russ": "russell",
    "stu": "stuart",
    "sue": "susan", "susie": "susan", "suzy": "susan",
    "tim": "timothy", "timmy": "timothy",
    "vince": "vincent",
    "walt": "walter",
    "wendy": "gwendolyn",
}

NOISE_EMPLOYERS = {
    "city of austin", "retired", "self", "self employed", "self-employed",
    "self-employed", "selfemployed", "not employed", "not-employed",
    "na", "n/a", "none", "unknown", "best efforts", "n a", "homemaker",
    "student", "unemployed", "housewife", "homemaker", "various",
    "austin police department",  # too common to be a signal
}

def to_ascii(s):
    """Best-effort unicode → ASCII transliteration."""
    try:
        return unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    except Exception:
        return s

def normalize_name(raw):
    """Return (last, first) both normalized."""
    s = to_ascii(raw or "").lower().strip()
    s = re.sub(r"[^a-z ,]", "", s)
    if "," in s:
        parts = s.split(",", 1)
        last = parts[0].strip()
        first = parts[1].strip().split()[0] if parts[1].strip() else ""
    else:
        tokens = s.split()
        last = tokens[-1] if tokens else ""
        first = tokens[0] if len(tokens) > 1 else ""
    first = NICKNAMES.get(first, first)
    return last, first

def normalize_zip(city_state_zip):
    """Extract 5-digit zip."""
    m = re.search(r"\b(\d{5})(?:-\d{4})?\b", city_state_zip or "")
    return m.group(1) if m else ""

def normalize_employer(emp):
    s = to_ascii(emp or "").lower().strip()
    s = re.sub(r"\b(inc|llc|corp|co|ltd|pc|lp|pllc|pa)\.?\b", "", s)
    s = re.sub(r"[^a-z0-9 ]", " ", s)
    s = re.sub(r"\s+", " ", s).strip()
    return "" if s in NOISE_EMPLOYERS else s

def normalize_occupation(occ):
    s = to_ascii(occ or "").lower().strip()
    s = re.sub(r"[^a-z ]", " ", s)
    return re.sub(r"\s+", " ", s).strip()

# ── Load unique donor profiles ─────────────────────────────────────────────────
print("Loading donors...")
conn = sqlite3.connect(DB)
cur = conn.cursor()
cur.execute("""
    SELECT donor, city_state_zip, donor_reported_employer, donor_reported_occupation
    FROM campaign_finance
    WHERE donor_type IN ('INDIVIDUAL','Individual') AND donor LIKE '%,%'
    GROUP BY donor, city_state_zip, donor_reported_employer, donor_reported_occupation
""")
rows = cur.fetchall()
conn.close()
print(f"  {len(rows)} unique (donor, zip, employer, occupation) profiles")

# ── Build normalized records ───────────────────────────────────────────────────
records = []
for raw_name, zip_raw, emp_raw, occ_raw in rows:
    last, first = normalize_name(raw_name)
    if not last or not first:
        continue
    zip5 = normalize_zip(zip_raw)
    emp = normalize_employer(emp_raw)
    occ = normalize_occupation(occ_raw)
    # treat employer/occupation as a combined token bag (handles field-swap)
    emp_occ_bag = " ".join(sorted(set((emp + " " + occ).split())))
    records.append({
        "raw": raw_name,
        "last": last,
        "first": first,
        "zip5": zip5,
        "emp_occ": emp_occ_bag,
    })

print(f"  {len(records)} normalized profiles")

# ── Blocking: group by (last_name, zip5) ──────────────────────────────────────
print("Blocking...")
blocks = defaultdict(list)
for i, r in enumerate(records):
    if r["last"] and r["zip5"]:
        key = (r["last"], r["zip5"])
        blocks[key].append(i)

# Only blocks with 2–15 members (ignore giant common-name blocks for the sample)
candidate_blocks = {k: v for k, v in blocks.items() if 2 <= len(v) <= 15}
print(f"  {len(candidate_blocks)} blocks with 2–15 members")
total_pairs = sum(len(v)*(len(v)-1)//2 for v in candidate_blocks.values())
print(f"  {total_pairs:,} candidate pairs to score")

# ── Scoring ────────────────────────────────────────────────────────────────────
def score_pair(a, b):
    # Score first and last independently
    last_score  = fuzz.token_sort_ratio(a["last"],  b["last"])  / 100.0
    first_score = fuzz.token_sort_ratio(a["first"], b["first"]) / 100.0

    # Hard floor: if either name component is too dissimilar, cap at 0.69
    # regardless of zip/employer — prevents household false positives (Ana vs Nancy)
    if last_score < 0.75 or first_score < 0.75:
        return round(min(0.50 * last_score + 0.50 * first_score, 0.69), 4)

    name_score = 0.50 * last_score + 0.50 * first_score

    # ZIP: exact=1.0, one unknown=0.5, mismatch=0.0
    if a["zip5"] and b["zip5"]:
        zip_score = 1.0 if a["zip5"] == b["zip5"] else 0.0
    else:
        zip_score = 0.5

    # Employer+occupation token bag — light weight, used as tiebreaker only
    if a["emp_occ"] and b["emp_occ"]:
        emp_score = fuzz.token_sort_ratio(a["emp_occ"], b["emp_occ"]) / 100.0
    else:
        emp_score = 0.5

    # Weights: Last 30% / First 30% / ZIP 30% / Employer 10%
    return round(0.30 * last_score + 0.30 * first_score + 0.30 * zip_score + 0.10 * emp_score, 4)

print("Scoring pairs...")
scores = []
flagged_examples = []  # store examples in the 0.70–0.84 range

for idx, (key, members) in enumerate(candidate_blocks.items()):
    if idx % 5000 == 0:
        print(f"  block {idx}/{len(candidate_blocks)}  scores so far: {len(scores):,}")
    for i in range(len(members)):
        for j in range(i+1, len(members)):
            a = records[members[i]]
            b = records[members[j]]
            s = score_pair(a, b)
            scores.append(s)
            if 0.70 <= s < 0.85 and len(flagged_examples) < 200:
                flagged_examples.append((s, a["raw"], b["raw"], a["zip5"], a["emp_occ"], b["emp_occ"]))

print(f"\nTotal pairs scored: {len(scores):,}")

# ── Stats ──────────────────────────────────────────────────────────────────────
import statistics

auto_match   = sum(1 for s in scores if s >= 0.85)
review_queue = sum(1 for s in scores if 0.70 <= s < 0.85)
no_match     = sum(1 for s in scores if s < 0.70)
total        = len(scores)

print(f"\n=== SCORE DISTRIBUTION ===")
print(f"  Auto-match  (≥0.85):   {auto_match:>8,}  ({100*auto_match/total:.1f}%)")
print(f"  Review queue(0.70–0.84):{review_queue:>7,}  ({100*review_queue/total:.1f}%)")
print(f"  No match    (<0.70):   {no_match:>8,}  ({100*no_match/total:.1f}%)")
print(f"\n  Mean score:   {statistics.mean(scores):.4f}")
print(f"  Median score: {statistics.median(scores):.4f}")
print(f"  Stdev:        {statistics.stdev(scores):.4f}")

# ── Sample review queue examples ──────────────────────────────────────────────
print(f"\n=== SAMPLE REVIEW QUEUE PAIRS (0.70–0.84) ===")
flagged_examples.sort(key=lambda x: x[0], reverse=True)
for s, a_raw, b_raw, zip5, emp_a, emp_b in flagged_examples[:25]:
    print(f"  [{s:.3f}]  '{a_raw}'  vs  '{b_raw}'")
    print(f"           zip={zip5}  emp_a='{emp_a[:40]}'  emp_b='{emp_b[:40]}'")

# ── Plot ───────────────────────────────────────────────────────────────────────
print("\nGenerating plot...")
fig, axes = plt.subplots(1, 2, figsize=(14, 5))
fig.suptitle("Donor Pair Score Distribution", fontsize=14, fontweight="bold")

# Full histogram
ax1 = axes[0]
bins = [i/100 for i in range(0, 102)]
counts = [0] * (len(bins)-1)
for s in scores:
    idx = min(int(s * 100), 100)
    counts[idx] += 1

colors = []
for b in bins[:-1]:
    if b >= 0.85:
        colors.append("#2ecc71")   # green  = auto-match
    elif b >= 0.70:
        colors.append("#f39c12")   # orange = review
    else:
        colors.append("#bdc3c7")   # grey   = no match

ax1.bar(bins[:-1], counts, width=0.01, color=colors, edgecolor="none", align="edge")
ax1.set_xlabel("Score")
ax1.set_ylabel("Pair Count")
ax1.set_title("All Scores (0.0 – 1.0)")
ax1.axvline(0.70, color="#f39c12", linewidth=1.5, linestyle="--")
ax1.axvline(0.85, color="#2ecc71", linewidth=1.5, linestyle="--")
green_patch  = mpatches.Patch(color="#2ecc71", label=f"Auto-match ≥0.85 ({auto_match:,})")
orange_patch = mpatches.Patch(color="#f39c12", label=f"Review 0.70–0.84 ({review_queue:,})")
grey_patch   = mpatches.Patch(color="#bdc3c7", label=f"No match <0.70 ({no_match:,})")
ax1.legend(handles=[green_patch, orange_patch, grey_patch], fontsize=8)

# Zoomed: 0.60–1.00
ax2 = axes[1]
zoom_scores = [s for s in scores if s >= 0.60]
bins2 = [i/200 for i in range(120, 202)]
counts2 = [0] * (len(bins2)-1)
for s in zoom_scores:
    idx = min(int(s * 200) - 120, len(counts2)-1)
    if idx >= 0:
        counts2[idx] += 1

colors2 = []
for b in bins2[:-1]:
    if b >= 0.85:
        colors2.append("#2ecc71")
    elif b >= 0.70:
        colors2.append("#f39c12")
    else:
        colors2.append("#bdc3c7")

ax2.bar(bins2[:-1], counts2, width=0.005, color=colors2, edgecolor="none", align="edge")
ax2.set_xlabel("Score")
ax2.set_ylabel("Pair Count")
ax2.set_title("Zoomed: Scores 0.60 – 1.00")
ax2.axvline(0.70, color="#f39c12", linewidth=1.5, linestyle="--")
ax2.axvline(0.85, color="#2ecc71", linewidth=1.5, linestyle="--")
ax2.legend(handles=[green_patch, orange_patch, grey_patch], fontsize=8)

plt.tight_layout()
plt.savefig("score_distribution.png", dpi=150)
print("Saved: score_distribution.png")
