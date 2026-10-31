"""Refresh videos.json from the Shankha Amrit YouTube feed (keeps older entries)."""
import json, re, sys, urllib.request, xml.etree.ElementTree as ET
from pathlib import Path

CHANNEL = "UCpgKc7L2O35Zuy6jS-gI9CA"
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}"
OUT = Path(__file__).resolve().parent / "videos.json"
KEEP = 90
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015"}

def lang(title):
    if re.search(r"[ഀ-ൿ]", title): return "ml"
    if re.search(r"[ऀ-ॿ]", title): return "hi"
    return "en"

def main(src=None):
    data = open(src, "rb").read() if src else urllib.request.urlopen(FEED, timeout=30).read()
    root = ET.fromstring(data)
    fresh = []
    for e in root.findall("a:entry", NS):
        vid = e.find("yt:videoId", NS).text
        title = e.find("a:title", NS).text or ""
        link = e.find("a:link", NS).get("href")
        fresh.append({
            "id": vid,
            "title": title,
            "date": e.find("a:published", NS).text[:10],
            "short": "/shorts/" in link,
            "lang": lang(title),
        })
    old = json.loads(OUT.read_text("utf-8")) if OUT.exists() else []
    ids = {v["id"] for v in fresh}
    merged = fresh + [v for v in old if v["id"] not in ids]
    merged.sort(key=lambda v: v["date"], reverse=True)
    OUT.write_text(json.dumps(merged[:KEEP], ensure_ascii=False, indent=1) + "\n", "utf-8")
    print(f"{len(merged[:KEEP])} videos")

if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
