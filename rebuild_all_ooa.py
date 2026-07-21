"""One-shot: regenerate every existing profile's data JSON (now with the
out_of_austin block) and re-render its HTML from the updated template.
Recipient strings come from each profile's own meta, so no roster is needed."""

import glob
import json
import os

import build_candidate as bc
import generate_profile_data as gpd

ROOT = os.path.dirname(os.path.abspath(__file__))

slugs = sorted(os.path.basename(f)[: -len("_data.json")]
               for f in glob.glob(os.path.join(ROOT, "*_data.json")))
print(f"Rebuilding {len(slugs)} profiles: {', '.join(slugs)}\n", flush=True)

failed = []
for slug in slugs:
    with open(os.path.join(ROOT, f"{slug}_data.json"), encoding="utf-8") as f:
        recipient = json.load(f)["meta"]["candidate_name"]
    print(f"\n{'#' * 70}\n# {slug}  ({recipient})\n{'#' * 70}", flush=True)
    try:
        gpd.generate(recipient, ROOT, slug_override=slug)
        html_path = bc.make_profile_html(slug)
        print(f"HTML: {html_path}", flush=True)
    except Exception as e:
        print(f"FAILED {slug}: {e}", flush=True)
        failed.append(slug)

print(f"\n\nDone. {len(slugs) - len(failed)}/{len(slugs)} rebuilt."
      + (f" FAILED: {failed}" if failed else ""), flush=True)
