"""Refresh the homepage Instagram rail from the Instagram Graph API.

Run by .github/workflows/refresh-instagram.yml on a schedule. Reads the
IG_ACCESS_TOKEN environment variable (a long-lived Instagram User access
token for the decodepolitics.us Business/Creator account). If the token is
absent the script exits 0 without touching anything, so the site keeps
serving the last committed feed.

Writes assets/ig/ig.json and downloads post images to assets/ig/post-<id>.jpg.
Stdlib only — no pip installs needed on the runner.

Token note: long-lived tokens expire after ~60 days. Refresh with
  GET https://graph.instagram.com/refresh_access_token?grant_type=ig_refresh_token&access_token=<token>
and update the IG_ACCESS_TOKEN repo secret.
"""
import json
import os
import sys
import urllib.request
import urllib.parse
from pathlib import Path

ROOT = Path(__file__).resolve().parent
IG_DIR = ROOT / "assets" / "ig"
PROFILE = "https://www.instagram.com/decodepolitics.us/"
MAX_POSTS = 10


def main():
    token = os.environ.get("IG_ACCESS_TOKEN", "").strip()
    if not token:
        print("IG_ACCESS_TOKEN not set - leaving committed feed as-is.")
        return 0

    fields = "id,caption,media_type,media_url,thumbnail_url,permalink,timestamp"
    url = "https://graph.instagram.com/me/media?" + urllib.parse.urlencode(
        {"fields": fields, "limit": 25, "access_token": token}
    )
    with urllib.request.urlopen(url, timeout=30) as r:
        media = json.load(r).get("data", [])

    posts = []
    keep_files = set()
    for m in media:
        if len(posts) >= MAX_POSTS:
            break
        src = m.get("thumbnail_url") if m.get("media_type") == "VIDEO" else m.get("media_url")
        if not src:
            continue
        fname = f"post-{m['id']}.jpg"
        dest = IG_DIR / fname
        if not dest.exists():
            urllib.request.urlretrieve(src, dest)
        keep_files.add(fname)
        caption = (m.get("caption") or "").strip().splitlines()[0][:120] if m.get("caption") else "decode(politics): Instagram post"
        posts.append(
            {
                "image": f"/assets/ig/{fname}",
                "alt": caption,
                "href": m.get("permalink", PROFILE),
            }
        )

    if not posts:
        print("API returned no usable posts - leaving committed feed as-is.")
        return 0

    for old in IG_DIR.glob("post-*.jpg"):
        if old.name not in keep_files:
            old.unlink()

    manifest = {
        "updated": media[0].get("timestamp") if media else None,
        "source": "instagram-graph-api",
        "profile": PROFILE,
        "posts": posts,
    }
    (IG_DIR / "ig.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"Wrote {len(posts)} posts to assets/ig/ig.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
