"""Shankha Amrit site builder: pulls the YouTube feed, keeps videos.json,
writes one SEO page per story, the sitemap, and pre-renders the home grid."""
import difflib, html, json, re, sys, time, unicodedata, urllib.parse, urllib.request, xml.etree.ElementTree as ET
from datetime import date, datetime
from pathlib import Path

CHANNEL = "UCpgKc7L2O35Zuy6jS-gI9CA"
FEED = f"https://www.youtube.com/feeds/videos.xml?channel_id={CHANNEL}"
SITE = "https://shankhaamrit.com"
ROOT = Path(__file__).resolve().parent
NS = {"a": "http://www.w3.org/2005/Atom", "yt": "http://www.youtube.com/xml/schemas/2015",
      "m": "http://search.yahoo.com/mrss/"}
LANG = {"hi": "हिंदी", "ml": "മലയാളം", "en": "English"}
SUB = "https://www.youtube.com/@ShankhaAmrit?sub_confirmation=1"


def lang(t):
    if re.search(r"[ഀ-ൿ]", t): return "ml"
    if re.search(r"[ऀ-ॿ]", t): return "hi"
    return "en"


def clean(t):
    t = re.sub(r"#\S+", "", t)
    t = re.sub(r"\s*\|\s*$", "", t.strip())
    return re.sub(r"\s{2,}", " ", t).strip()


def words(t):
    out = []
    for tok in re.split(r"\s+", clean(t)):
        w = "".join(c for c in tok if unicodedata.category(c)[0] in "LMN")
        if w: out.append(w.lower())
    return out


def slug(v):
    ws = [w for w in words(v["title"]) if w not in {"shorts", "short"}]
    ascii_ws = [w for w in ws if w.isascii() and not w.isdigit()]
    pick = ascii_ws if len(ascii_ws) >= 2 else [w for w in ws if not w.isascii()][:5]
    s = "-".join(pick)[:70].strip("-")
    tag = "malayalam" if v["lang"] == "ml" else "hindi" if v["lang"] == "hi" else ""
    if tag and tag not in s: s = f"{s}-{tag}" if s else tag
    return f"{s}-{v['id']}" if s else v["id"]


def page_url(v):
    return f"{SITE}/story/{urllib.parse.quote(v['path'])}.html"


def yt(v):
    return f"https://www.youtube.com/{'shorts/' if v['short'] else 'watch?v='}{v['id']}"


def thumb(v):
    return f"https://i.ytimg.com/vi/{v['id']}/hqdefault.jpg"


def fetch(src=None):
    data = open(src, "rb").read() if src else urllib.request.urlopen(FEED, timeout=30).read()
    out = []
    for e in ET.fromstring(data).findall("a:entry", NS):
        g = e.find("m:group", NS)
        title = e.find("a:title", NS).text or ""
        st = g.find("m:community/m:statistics", NS) if g is not None else None
        out.append({
            "id": e.find("yt:videoId", NS).text,
            "title": title,
            "date": e.find("a:published", NS).text[:10],
            "short": "/shorts/" in e.find("a:link", NS).get("href"),
            "lang": lang(title),
            "desc": (g.find("m:description", NS).text or "") if g is not None else "",
            "views": int(st.get("views", 0)) if st is not None else 0,
        })
    return out


UA = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36",
      "Accept-Language": "en-US,en;q=0.9"}


def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "ignore")


def initial_data(page):
    m = re.search(r"var ytInitialData = (\{.*?\});</script>", page, re.S)
    return json.loads(m.group(1)) if m else {}


def walk(o, key):
    if isinstance(o, dict):
        if key in o: yield o[key]
        for x in o.values(): yield from walk(x, key)
    elif isinstance(o, list):
        for x in o: yield from walk(x, key)


def scrape_shorts():
    """Newest-first (id, title) list from the channel's Shorts tab."""
    out, seen = [], set()
    for v in walk(initial_data(get("https://www.youtube.com/@ShankhaAmrit/shorts")), "shortsLockupViewModel"):
        m = re.search(r'"videoId": "([\w-]{11})"', json.dumps(v))
        title = v.get("overlayMetadata", {}).get("primaryText", {}).get("content")
        if m and title and m.group(1) not in seen:
            seen.add(m.group(1)); out.append((m.group(1), title))
    return out


def watch_info(vid):
    page = get(f"https://www.youtube.com/watch?v={vid}")
    m = re.search(r'"publishDate":\{"simpleText":"([^"]+)"', page)
    d = datetime.strptime(m.group(1), "%b %d, %Y").date().isoformat() if m else date.today().isoformat()
    desc = next(iter(walk(initial_data(page), "attributedDescription")), {}).get("content", "")
    return {"date": d, "desc": desc}


def skel(t):
    """Consonant skeleton; Malayalam letters are mapped onto their Devanagari twins so
    the Hindi and Malayalam titles of one story look alike."""
    out = []
    for c in re.sub(r"#\S+", "", t):
        o = ord(c)
        if 0x0D00 <= o <= 0x0D7F: o -= 0x400
        if 0x0915 <= o <= 0x0939: out.append(chr(o))
    return "".join(out)


def group_stories(items):
    """Shorts come as Malayalam/Hindi pairs of one story; give each pair one story number."""
    n, S = len(items), [skel(x["title"]) for x in items]
    cand = []
    for i in range(n):
        for j in range(i + 1, min(n, i + 5)):
            if items[i]["lang"] != items[j]["lang"]:
                cand.append((difflib.SequenceMatcher(None, S[i], S[j]).ratio(), i - j, i, j))
    cand.sort(reverse=True)
    mate = {}
    for r, _, i, j in cand:
        if r < 0.4: break
        if i not in mate and j not in mate: mate[i] = j; mate[j] = i
    free = [i for i in range(n) if i not in mate]
    for a, b in zip(free, free[1:]):
        if a not in mate and b not in mate and b == a + 1 and items[a]["lang"] != items[b]["lang"]:
            mate[a] = b; mate[b] = a
    sid = 0
    for i in range(n):
        if "story" in items[i]: continue
        items[i]["story"] = sid
        if i in mate: items[mate[i]]["story"] = sid
        sid += 1


STOPW = {"katha", "story", "malayalam", "hindi", "shorts", "short", "devotional", "kerala", "temple", "temples", "guruvayur", "the", "and"}


def words_en(t):
    return [w.lower() for w in re.findall(r"[A-Za-z]{4,}", re.sub(r"#\S+", "", t)) if w.lower() not in STOPW]


def para(text):
    text = re.sub(r"(?m)^\s*(#\S+\s*)+$", "", text)
    out = []
    for p in re.split(r"\n\s*\n", text.strip()):
        p = html.escape(p.strip())
        if not p: continue
        p = re.sub(r"(https?://[^\s<]+)", r'<a href="\1" rel="noopener">\1</a>', p)
        out.append("<p>" + p.replace("\n", "<br>") + "</p>")
    return "\n".join(out)


def card(v):
    return (f'<a class="card" href="/story/{v["path"]}.html">'
            f'<div class="thumb" style="background-image:url({thumb(v)})">'
            f'<span class="badge">{LANG.get(v["lang"], "")}{" · Short" if v["short"] else ""}</span></div>'
            f'<div class="t">{html.escape(clean(v["title"]))}</div><div class="d">{v["date"]}</div></a>')


PAGE = """<!doctype html>
<html lang="{lang}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title} | Shankha Amrit शंखामृत</title>
<meta name="description" content="{meta}">
<link rel="canonical" href="{url}">
<meta property="og:type" content="video.other">
<meta property="og:title" content="{title}">
<meta property="og:description" content="{meta}">
<meta property="og:image" content="{thumb}">
<meta property="og:url" content="{url}">
<meta property="og:site_name" content="Shankha Amrit">
<meta name="twitter:card" content="summary_large_image">
<meta name="theme-color" content="#7a1f12">
<link rel="icon" href="/favicon.svg" type="image/svg+xml">
<link rel="preconnect" href="https://fonts.googleapis.com"><link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@600;700&family=Noto+Sans:wght@400;500;600&family=Noto+Sans+Devanagari:wght@400;500;600&family=Noto+Sans+Malayalam:wght@400;500;600&display=swap" rel="stylesheet">
<script type="application/ld+json">{ld}</script>
<style>
:root{{--red:#7a1f12;--red-deep:#4e130b;--gold:#e8b54a;--gold-soft:#f3d58c;--paper:#fbf6ec;--ink:#2a1a12;--muted:#6e5a4c;--line:#e6d8c0;--card:#fffdf8}}
*{{box-sizing:border-box;margin:0;padding:0}}
body{{font-family:"Noto Sans","Noto Sans Devanagari","Noto Sans Malayalam",system-ui,sans-serif;background:var(--paper);color:var(--ink);line-height:1.7}}
a{{color:var(--red)}}
.wrap{{max-width:980px;margin:0 auto;padding:0 20px}}
header{{background:var(--red-deep);border-bottom:1px solid rgba(232,181,74,.35)}}
.bar{{display:flex;align-items:center;justify-content:space-between;height:60px}}
.brand{{color:var(--gold-soft);text-decoration:none;font-family:"Cormorant Garamond",serif;font-size:1.4rem;font-weight:700}}
.btn{{display:inline-block;background:var(--gold);color:var(--red-deep);font-weight:600;text-decoration:none;padding:9px 18px;border-radius:999px}}
main{{padding:32px 0 56px}}
.crumb{{font-size:.85rem;color:var(--muted);margin-bottom:12px}}
h1{{font-size:clamp(1.4rem,3.4vw,2rem);line-height:1.35;color:var(--red-deep);margin-bottom:6px}}
.meta{{color:var(--muted);font-size:.9rem;margin-bottom:22px}}
.layout{{display:grid;grid-template-columns:{cols};gap:32px;align-items:start}}
.player{{aspect-ratio:{ratio};border-radius:16px;overflow:hidden;background:#2a0b06;border:2px solid rgba(232,181,74,.55)}}
.player iframe{{width:100%;height:100%;border:0;display:block}}
.desc p{{margin-bottom:14px}}
.cta{{margin:22px 0;display:flex;gap:10px;flex-wrap:wrap}}
.btn.alt{{background:var(--red);color:#fbeed2}}
.btn.wa{{background:#1f9d55;color:#fff}}
h2{{font-family:"Cormorant Garamond",serif;font-size:1.7rem;color:var(--red);margin:46px 0 18px}}
.grid{{display:grid;grid-template-columns:repeat(auto-fill,minmax(210px,1fr));gap:18px}}
.card{{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;text-decoration:none;color:var(--ink);display:flex;flex-direction:column}}
.thumb{{position:relative;aspect-ratio:16/9;background:#e9dcc6 center/cover no-repeat}}
.badge{{position:absolute;left:8px;top:8px;background:rgba(78,19,11,.88);color:var(--gold-soft);font-size:.7rem;font-weight:600;padding:2px 8px;border-radius:999px}}
.card .t{{padding:10px 12px 2px;font-size:.9rem;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.card .d{{padding:0 12px 12px;font-size:.78rem;color:var(--muted)}}
footer{{background:#2a0b06;color:#cdb898;font-size:.88rem;padding:24px 0}}
footer a{{color:var(--gold-soft)}}
@media(max-width:760px){{.layout{{grid-template-columns:1fr}}.player{{max-width:{pmax};margin:0 auto;width:100%}}}}
</style>
</head>
<body>
<header><div class="wrap bar"><a class="brand" href="/">Shankha Amrit · शंखामृत</a><a class="btn" href="{sub}" target="_blank" rel="noopener">Subscribe</a></div></header>
<main><div class="wrap">
<div class="crumb"><a href="/">शंखामृत</a> › <a href="/#stories">कथाएँ · Stories</a></div>
<h1>{title}</h1>
<div class="meta">{langname}{kind} · {date}</div>
<div class="layout">
<div class="player"><iframe src="https://www.youtube-nocookie.com/embed/{id}?rel=0" title="{title}" allow="accelerometer; encrypted-media; gyroscope; picture-in-picture; web-share" allowfullscreen loading="lazy"></iframe></div>
<div>
<div class="desc">{desc}</div>
<div class="cta"><a class="btn alt" href="{yt}" target="_blank" rel="noopener">▶ YouTube पर देखें · Watch on YouTube</a><a class="btn" href="{sub}" target="_blank" rel="noopener">Subscribe</a><a class="btn wa" href="{wa}" target="_blank" rel="noopener">{walabel}</a></div>
</div>
</div>
{other}
<h2>और कथाएँ · More stories</h2>
<div class="grid">{related}</div>
</div></main>
<footer><div class="wrap">© Shankha Amrit · Made by Santosh Roy · <a href="/">shankhaamrit.com</a></div></footer>
</body>
</html>
"""


def story_page(v, videos):
    title = html.escape(clean(v["title"]))
    plain = re.sub(r"\s+", " ", re.sub(r"#\S+|https?://\S+", "", v.get("desc", ""))).strip()
    meta = html.escape((plain[:155].rsplit(" ", 1)[0] + "…") if len(plain) > 160 else plain or clean(v["title"]))
    url = page_url(v)
    ld = {"@context": "https://schema.org", "@type": "VideoObject", "name": clean(v["title"]),
          "description": plain[:500] or clean(v["title"]), "thumbnailUrl": [thumb(v)],
          "uploadDate": v["date"], "embedUrl": f"https://www.youtube.com/embed/{v['id']}",
          "contentUrl": yt(v), "inLanguage": v["lang"],
          "publisher": {"@type": "Organization", "name": "Shankha Amrit", "url": SITE}}
    if v.get("views"):
        ld["interactionStatistic"] = {"@type": "InteractionCounter",
                                      "interactionType": {"@type": "WatchAction"},
                                      "userInteractionCount": v["views"]}
    same = [x for x in videos if x["id"] != v["id"] and x["lang"] == v["lang"]]
    rest = [x for x in videos if x["id"] != v["id"] and x["lang"] != v["lang"]]
    related = "".join(card(x) for x in (same + rest)[:8])
    # pair: same story in the other language (same date, other lang, same format)
    other = ""
    twin = next((x for x in videos if x["date"] == v["date"] and x["lang"] != v["lang"]
                 and x["short"] == v["short"] and x["lang"] in ("hi", "ml")), None)
    if twin:
        other = (f'<p style="margin-top:26px">{"यह कथा मलयालम में भी" if twin["lang"] == "ml" else "ഈ കഥ ഹിന്ദിയിലും"}: '
                 f'<a href="/story/{twin["path"]}.html">{html.escape(clean(twin["title"]))}</a></p>')
    return PAGE.format(lang=v["lang"], title=title, meta=meta, url=url, thumb=thumb(v),
                       ld=json.dumps(ld, ensure_ascii=False).replace("</", "<\\/"),
                       cols="minmax(0,340px) 1fr" if v["short"] else "1fr",
                       ratio="9/16" if v["short"] else "16/9", pmax="340px" if v["short"] else "100%",
                       sub=SUB, langname=LANG.get(v["lang"], ""), kind=" · Short" if v["short"] else "",
                       date=v["date"], id=v["id"], desc=para(v.get("desc", "")), yt=yt(v),
                       other=other, related=related,
                       wa="https://wa.me/?text=" + urllib.parse.quote(clean(v["title"]) + "\n" + url, safe=""),
                       walabel={"hi": "WhatsApp पर भेजें", "ml": "WhatsApp-ൽ പങ്കിടൂ"}.get(v["lang"], "Share on WhatsApp"))


def between(text, tag, inner):
    a, b = f"<!--{tag}:START-->", f"<!--{tag}:END-->"
    i, j = text.index(a) + len(a), text.index(b)
    return text[:i] + inner + text[j:]


def main(src=None):
    out = ROOT / "videos.json"
    old = json.loads(out.read_text("utf-8")) if out.exists() else []
    fresh = fetch(src)
    by = {v["id"]: v for v in old}
    for v in fresh:
        by[v["id"]] = {**by.get(v["id"], {}), **v}
    try:
        shorts = scrape_shorts()
    except Exception as e:
        print("Shorts tab not read:", e); shorts = []
    if shorts:
        fetched = 0
        for rank, (vid, title) in enumerate(shorts):
            if vid not in by:
                if fetched >= 40: continue
                try:
                    time.sleep(2.5); info = watch_info(vid); fetched += 1
                except Exception as e:
                    print("skip", vid, e); continue
                by[vid] = {"id": vid, "title": title, "date": info["date"], "short": True,
                           "lang": lang(title), "desc": info["desc"], "views": 0}
        ids = [s[0] for s in shorts]
        for v in by.values():
            v.pop("rank", None); v.pop("story", None)
        light = [{"id": vid, "title": title, "lang": lang(title)} for vid, title in shorts]
        group_stories(light)
        for rank, s in enumerate(light):
            if s["id"] in by: by[s["id"]].update(rank=rank, story=s["story"])
    videos = sorted(by.values(), key=lambda v: (v["date"], -v.get("rank", 9999)), reverse=True)
    for v in videos:
        v.setdefault("desc", ""); v.setdefault("views", 0)
        v["path"] = slug(v)
    out.write_text(json.dumps(videos, ensure_ascii=False, indent=1) + "\n", "utf-8")

    sd = ROOT / "story"; sd.mkdir(exist_ok=True)
    for v in videos:
        (sd / f"{v['path']}.html").write_text(story_page(v, videos), "utf-8")

    today = date.today().isoformat()
    urls = [f"<url><loc>{SITE}/</loc><lastmod>{today}</lastmod><changefreq>daily</changefreq><priority>1.0</priority></url>"]
    urls += [f"<url><loc>{page_url(v)}</loc><lastmod>{v['date']}</lastmod></url>" for v in videos]
    (ROOT / "sitemap.xml").write_text('<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
                                      + "\n".join(urls) + "\n</urlset>\n", "utf-8")
    (ROOT / "robots.txt").write_text(f"User-agent: *\nAllow: /\n\nSitemap: {SITE}/sitemap.xml\n", "utf-8")

    idx = ROOT / "index.html"
    t = idx.read_text("utf-8")
    t = between(t, "CARDS", "".join(card(v) for v in videos[:24]))
    site_ld = [{"@context": "https://schema.org", "@type": "WebSite", "name": "Shankha Amrit",
                "alternateName": ["शंखामृत", "ശംഖാമൃതം", "ShankhaAmrit"], "url": SITE + "/",
                "inLanguage": ["hi", "ml"]},
               {"@context": "https://schema.org", "@type": "Organization", "name": "Shankha Amrit",
                "url": SITE + "/", "logo": SITE + "/favicon.svg",
                "sameAs": ["https://www.youtube.com/@ShankhaAmrit"]},
               {"@context": "https://schema.org", "@type": "ItemList", "itemListElement": [
                   {"@type": "ListItem", "position": i + 1, "url": page_url(v),
                    "name": clean(v["title"])} for i, v in enumerate(videos[:24])]}]
    t = between(t, "LD", '<script type="application/ld+json">'
                + json.dumps(site_ld, ensure_ascii=False).replace("</", "<\\/") + "</script>")
    idx.write_text(t, "utf-8")
    print(f"{len(videos)} videos, {len(videos)} story pages")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else None)
