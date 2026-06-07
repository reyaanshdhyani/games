#!/usr/bin/env python3
"""
Build the arcade menu (index.html) from the game HTML files in this folder.

What it does, every time it runs:
  1. Finds every *.html game in this folder (ignores index.html itself).
  2. Makes sure each game has the "keyboard input fix" so arrow/space keys
     control the game instead of scrolling the page (skips files listed in
     games.json -> "noShim").
  3. Regenerates index.html as a category-first menu:
       - the home screen shows one tile per category
       - clicking a category shows the games inside it (with a Back button)
       - clicking a game opens it to play

Game metadata (name, emoji, controls, category, order) lives in games.json.
Any game whose category is missing/unknown falls into the "More Games" bucket.

You normally never run this by hand — the GitHub Action runs it automatically
on every push. But you can run it locally too:  python3 build_index.py
"""

import json
import os
import re
import html

HERE = os.path.dirname(os.path.abspath(__file__))

# Files that are not games and must never appear on the menu.
SKIP = {"index.html"}

SHIM = """<script>
/* --- Cowork input fix (auto-added) -------------------------------------
   Keeps keyboard focus on the game and stops arrow/space keys from
   scrolling the page or triggering browser shortcuts. The game's own
   key handlers still run (propagation is not stopped). */
(function(){
  function focusGame(){ try{ window.focus(); if(document.body){document.body.tabIndex=-1; document.body.focus();} }catch(e){} }
  window.addEventListener('load', focusGame);
  document.addEventListener('mousedown', focusGame);
  document.addEventListener('touchstart', focusGame, {passive:true});
  window.addEventListener('keydown', function(e){
    var t=e.target;
    if(t && (t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable)) return;
    var k=e.key;
    if(k==='ArrowUp'||k==='ArrowDown'||k==='ArrowLeft'||k==='ArrowRight'||k===' '||k==='Spacebar'){
      e.preventDefault();
    }
  }, true);
})();
</script>"""

SHIM_MARK = "Cowork input fix"

# Fallback bucket for games whose category is missing or unknown.
FALLBACK_CAT = {"id": "more", "name": "More Games", "emoji": "🎮", "order": 999,
                "blurb": "A few more games to try."}


def load_config():
    path = os.path.join(HERE, "games.json")
    cfg = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    cfg.setdefault("siteTitle", "🎮 Game Arcade")
    cfg.setdefault("tagline", "Pick a category, then choose a game to play.")
    cfg.setdefault("defaultEmoji", "🎮")
    cfg.setdefault("defaultControls", "Click to play")
    cfg.setdefault("defaultCategory", "more")
    cfg.setdefault("noShim", [])
    cfg.setdefault("overrides", {})
    cfg.setdefault("categories", [])
    return cfg


def title_of(path, fallback):
    try:
        with open(path, encoding="utf-8") as f:
            head = f.read(4000)
        m = re.search(r"<title>(.*?)</title>", head, re.I | re.S)
        if m:
            t = re.sub(r"\s+", " ", m.group(1)).strip()
            # Trim trailing junk after an em dash / pipe (e.g. "Road Warrior — Top-Down").
            t = re.split(r"\s+[—\-|·]\s+", t)[0].strip()
            if t:
                return t
    except Exception:
        pass
    return fallback


def ensure_shim(path, filename, no_shim):
    if filename in no_shim:
        return
    with open(path, encoding="utf-8") as f:
        s = f.read()
    if SHIM_MARK in s:
        return
    low = s.lower()
    i = low.rfind("</body>")
    if i == -1:
        i = low.rfind("</html>")
    s = (s + "\n" + SHIM) if i == -1 else s[:i] + SHIM + "\n" + s[i:]
    with open(path, "w", encoding="utf-8") as f:
        f.write(s)
    print(f"  + added keyboard fix to {filename}")


def main():
    cfg = load_config()
    overrides = cfg["overrides"]
    default_cat = cfg["defaultCategory"]

    # Index the configured categories by id.
    categories = {c["id"]: dict(c) for c in cfg["categories"]}

    games = []
    for fn in sorted(os.listdir(HERE)):
        if not fn.lower().endswith(".html"):
            continue
        if fn in SKIP:
            continue
        path = os.path.join(HERE, fn)
        ensure_shim(path, fn, cfg["noShim"])
        ov = overrides.get(fn, {})
        nice = fn.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        cat = ov.get("category") or default_cat
        if cat not in categories:
            # Unknown category -> use the fallback bucket.
            categories.setdefault(FALLBACK_CAT["id"], dict(FALLBACK_CAT))
            cat = FALLBACK_CAT["id"]
        games.append({
            "file": fn,
            "name": ov.get("name") or title_of(path, nice),
            "emoji": ov.get("emoji", cfg["defaultEmoji"]),
            "controls": ov.get("controls", cfg["defaultControls"]),
            "category": cat,
            "order": ov.get("order", 999),
        })

    # Keep only categories that actually have games, then sort.
    used = {g["category"] for g in games}
    cat_list = [categories[cid] for cid in categories if cid in used]
    cat_list.sort(key=lambda c: (c.get("order", 999), c["name"].lower()))

    # Attach the sorted games for each category and a count.
    for c in cat_list:
        c_games = [g for g in games if g["category"] == c["id"]]
        c_games.sort(key=lambda g: (g.get("order", 999), g["name"].lower()))
        c["games"] = c_games
        c["count"] = len(c_games)

    data = {"categories": cat_list}

    page = TEMPLATE.format(
        title=html.escape(cfg["siteTitle"]),
        tagline=html.escape(cfg["tagline"]),
        count=len(games),
        cat_count=len(cat_list),
        data_json=json.dumps(data, ensure_ascii=False),
    )
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Built index.html with {len(games)} game(s) in {len(cat_list)} categor(ies).")


TEMPLATE = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  :root{{ --bg:#0f1226; --card:#1b1f3a; --card2:#242a52; --accent:#7c5cff; --text:#eef1ff; --muted:#a7adcf; }}
  *{{ box-sizing:border-box; }}
  body{{ margin:0; font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;
        background:radial-gradient(1200px 700px at 50% -10%,#23285a 0%,var(--bg) 60%); color:var(--text); min-height:100vh; }}
  header{{ text-align:center; padding:46px 20px 6px; }}
  header h1{{ margin:0; font-size:40px; letter-spacing:.5px; }}
  header p{{ color:var(--muted); margin:10px 0 0; font-size:15px; }}
  .wrap{{ max-width:1040px; margin:0 auto; padding:0 20px; }}
  .bar{{ max-width:1040px; margin:22px auto 0; padding:0 20px; min-height:34px; }}
  .back{{ display:none; align-items:center; gap:8px; cursor:pointer; background:var(--card2); color:var(--text);
         border:1px solid #2f3666; border-radius:10px; padding:8px 14px; font-size:14px; font-weight:600; }}
  .back:hover{{ border-color:var(--accent); }}
  .section-title{{ text-align:center; margin:18px 0 0; font-size:24px; font-weight:800; }}
  .section-title .em{{ margin-right:8px; }}
  .grid{{ margin:24px auto 60px; display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:18px; }}
  .tile, a.card{{ text-decoration:none; color:inherit; background:linear-gradient(160deg,var(--card2),var(--card));
          border:1px solid #2f3666; border-radius:16px; padding:22px; display:flex; flex-direction:column; gap:8px;
          cursor:pointer; transition:transform .12s ease, box-shadow .12s ease, border-color .12s ease; }}
  .tile:hover, a.card:hover{{ transform:translateY(-4px); box-shadow:0 12px 30px rgba(0,0,0,.45); border-color:var(--accent); }}
  .emoji{{ font-size:36px; }}
  .name{{ font-size:18px; font-weight:700; }}
  .blurb, .controls{{ font-size:12.5px; color:var(--muted); line-height:1.5; }}
  .count{{ font-size:12.5px; color:var(--accent); font-weight:700; margin-top:2px; }}
  footer{{ text-align:center; color:var(--muted); font-size:12.5px; padding:0 20px 40px; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>{tagline}</p>
</header>

<div class="bar"><button class="back" id="backBtn">← All categories</button></div>
<h2 class="section-title" id="sectionTitle"></h2>
<div class="wrap"><div class="grid" id="grid"></div></div>

<footer>{count} games · {cat_count} categories · this menu builds itself when a new game is added 🎮</footer>

<noscript>
  <div class="wrap" style="padding-bottom:40px">
    <p style="color:#a7adcf">JavaScript is off, so here are all the games as direct links:</p>
  </div>
</noscript>

<script>
  var DATA = {data_json};

  var grid = document.getElementById('grid');
  var backBtn = document.getElementById('backBtn');
  var sectionTitle = document.getElementById('sectionTitle');

  function esc(s){{
    return String(s).replace(/[&<>"']/g, function(c){{
      return {{'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}}[c];
    }});
  }}

  function findCat(id){{
    for (var i=0;i<DATA.categories.length;i++) if (DATA.categories[i].id===id) return DATA.categories[i];
    return null;
  }}

  function showHome(){{
    backBtn.style.display = 'none';
    sectionTitle.textContent = '';
    var html = '';
    DATA.categories.forEach(function(c){{
      var n = c.count + (c.count===1 ? ' game' : ' games');
      html += '<div class="tile" role="button" tabindex="0" data-cat="'+esc(c.id)+'">'
            + '<span class="emoji">'+esc(c.emoji||'🎮')+'</span>'
            + '<span class="name">'+esc(c.name)+'</span>'
            + (c.blurb ? '<span class="blurb">'+esc(c.blurb)+'</span>' : '')
            + '<span class="count">'+n+'</span></div>';
    }});
    grid.innerHTML = html;
  }}

  function showCategory(id){{
    var c = findCat(id);
    if (!c){{ showHome(); return; }}
    backBtn.style.display = 'inline-flex';
    sectionTitle.innerHTML = '<span class="em">'+esc(c.emoji||'🎮')+'</span>'+esc(c.name);
    var html = '';
    c.games.forEach(function(g){{
      html += '<a class="card" href="./'+esc(g.file)+'">'
            + '<span class="emoji">'+esc(g.emoji||'🎮')+'</span>'
            + '<span class="name">'+esc(g.name)+'</span>'
            + '<span class="controls">'+esc(g.controls||'')+'</span></a>';
    }});
    grid.innerHTML = html;
  }}

  function route(){{
    var m = (location.hash||'').match(/cat=([^&]+)/);
    if (m) showCategory(decodeURIComponent(m[1]));
    else showHome();
  }}

  grid.addEventListener('click', function(e){{
    var t = e.target.closest('.tile');
    if (t) location.hash = 'cat=' + encodeURIComponent(t.getAttribute('data-cat'));
  }});
  grid.addEventListener('keydown', function(e){{
    if (e.key!=='Enter' && e.key!==' ') return;
    var t = e.target.closest('.tile');
    if (t){{ e.preventDefault(); location.hash = 'cat=' + encodeURIComponent(t.getAttribute('data-cat')); }}
  }});
  backBtn.addEventListener('click', function(){{ location.hash = ''; }});
  window.addEventListener('hashchange', route);
  route();
</script>
</body>
</html>
"""


if __name__ == "__main__":
    main()
