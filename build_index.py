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

# --- The universal "play layer" injected into every game --------------------
# It adds three things to each game, driven by the per-game config in
# games.json -> "play":
#   1. A "How to play" start screen, shown every time the game opens.
#   2. Responsive scaling so the game fits phones, iPads, laptops, big screens.
#   3. Swipe/tap touch controls that fire the exact keys each game already
#      listens for (so the game code itself needs no changes).
PLAYLAYER_START = "<!--PLAYLAYER:START-->"
PLAYLAYER_END = "<!--PLAYLAYER:END-->"

VIEWPORT_META = ('<meta name="viewport" '
                 'content="width=device-width, initial-scale=1.0, '
                 'maximum-scale=1.0, user-scalable=no, viewport-fit=cover">')

PLAY_LAYER_TEMPLATE = PLAYLAYER_START + """
<style id="pl-style">
  html,body{margin:0;}
  canvas{max-width:100vw !important; max-height:100vh !important;}
  #pl-overlay{position:fixed; inset:0; z-index:99999; display:flex; align-items:center; justify-content:center;
    background:rgba(8,10,25,.86); -webkit-backdrop-filter:blur(4px); backdrop-filter:blur(4px); padding:20px;
    font-family:-apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
  #pl-overlay .pl-card{background:linear-gradient(160deg,#242a52,#1b1f3a); color:#eef1ff; border:1px solid #3a4178;
    border-radius:18px; padding:26px 24px; max-width:440px; width:100%; max-height:88vh; overflow:auto; text-align:center;
    box-shadow:0 20px 60px rgba(0,0,0,.55);}
  #pl-overlay .pl-title{font-size:26px; font-weight:800; margin:0 0 4px;}
  #pl-overlay .pl-sub{font-size:12px; letter-spacing:2px; text-transform:uppercase; color:#9aa0d0; margin-bottom:12px;}
  #pl-overlay .pl-how{font-size:16px; line-height:1.55; color:#d7daf5; margin-bottom:22px;}
  #pl-overlay .pl-btn{appearance:none; -webkit-appearance:none; border:0; cursor:pointer; background:#7c5cff; color:#fff;
    font-size:19px; font-weight:800; padding:15px 34px; border-radius:14px; width:100%;
    box-shadow:0 8px 22px rgba(124,92,255,.5);}
  #pl-overlay .pl-btn:active{transform:translateY(1px);}
  .pl-hint{position:fixed; left:50%; bottom:18px; transform:translateX(-50%); z-index:99998;
    background:rgba(20,24,52,.92); color:#eef1ff; padding:10px 16px; border-radius:12px; border:1px solid #3a4178;
    max-width:90vw; text-align:center; pointer-events:none; transition:opacity .4s ease;
    font:600 14px/1.4 -apple-system,BlinkMacSystemFont,"Segoe UI",Roboto,Helvetica,Arial,sans-serif;}
</style>
<script>
/* --- Reyaansh play layer (auto-added) -----------------------------------
   "How to play" screen + responsive scaling + swipe/tap touch controls.
   Per-game config is injected just below (see games.json -> "play"). */
(function(){
  var PLAY = __PL_CONFIG__;
  if(!PLAY) PLAY = {type:"page", how:"Tap Play to start."};
  var doc=document, win=window;
  var isTouch = ('ontouchstart' in win) || (navigator.maxTouchPoints>0);

  function focusGame(){ try{ win.focus(); if(doc.body){doc.body.tabIndex=-1; doc.body.focus();} }catch(e){} }
  win.addEventListener('load', focusGame);
  doc.addEventListener('mousedown', focusGame);
  doc.addEventListener('touchstart', focusGame, {passive:true});

  if(PLAY.type==='game'){
    win.addEventListener('keydown', function(e){
      var t=e.target;
      if(t && (t.tagName==='INPUT'||t.tagName==='TEXTAREA'||t.isContentEditable)) return;
      var k=e.key;
      if(k==='ArrowUp'||k==='ArrowDown'||k==='ArrowLeft'||k==='ArrowRight'||k===' '||k==='Spacebar'){ e.preventDefault(); }
    }, true);
  }

  function esc(s){return String(s==null?'':s).replace(/[&<>"']/g,function(c){return {'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c];});}

  /* synthetic key dispatch -- sends both key and code so every game matches */
  function fire(type, pair){ if(!pair) return; try{ doc.dispatchEvent(new KeyboardEvent(type,{key:pair[0],code:pair[1],bubbles:true,cancelable:true})); }catch(e){} }
  var held=null;
  function press(pair){ if(held){fire('keyup',held);} held=pair; fire('keydown',pair); }
  function release(){ if(held){fire('keyup',held); held=null;} }
  function tapKey(pair){ if(!pair) return; fire('keydown',pair); setTimeout(function(){fire('keyup',pair);},70); }

  /* how-to-play overlay (shown every time the game opens) */
  function buildOverlay(){
    var ov=doc.createElement('div'); ov.id='pl-overlay';
    ov.innerHTML='<div class="pl-card"><div class="pl-title">'+esc(PLAY.title||doc.title||'Ready?')+'</div>'
      +'<div class="pl-sub">How to play</div><div class="pl-how">'+esc(PLAY.how||'Tap Play to begin.')+'</div>'
      +'<button class="pl-btn" id="pl-play">▶ Play</button></div>';
    doc.body.appendChild(ov);
    doc.getElementById('pl-play').addEventListener('click', startPlay);
  }
  function startPlay(){
    var ov=doc.getElementById('pl-overlay'); if(ov && ov.parentNode) ov.parentNode.removeChild(ov);
    focusGame();
    if(PLAY.type==='keyboard'){ var inp=doc.querySelector('input,textarea'); if(inp){ try{inp.focus(); inp.click();}catch(e){} } }
    else if(PLAY.start){ setTimeout(function(){ tapKey(PLAY.start); }, 140); }
    if(PLAY.type==='game' && isTouch) showHint();
  }
  function showHint(){
    var h=doc.createElement('div'); h.className='pl-hint'; h.textContent=PLAY.how||'Swipe to move · Tap to act';
    doc.body.appendChild(h);
    setTimeout(function(){ h.style.opacity='0'; setTimeout(function(){ if(h.parentNode) h.parentNode.removeChild(h); },500); }, 3600);
  }

  /* swipe / tap gestures (game type, touch devices only) */
  function isInteractive(el){ return el && el.closest && el.closest('button,a,input,textarea,select,[role=button],#pl-overlay,.pl-hint'); }
  function aimAt(e){
    var cv=doc.querySelector('canvas'); if(!cv) return;
    var t=(e.changedTouches&&e.changedTouches[0]); if(!t) return;
    try{ cv.dispatchEvent(new MouseEvent('mousemove',{clientX:t.clientX,clientY:t.clientY,bubbles:true,cancelable:true})); }catch(err){}
  }
  function attachGestures(){
    var g=PLAY.g||{}, TH=24, sx=0,sy=0,st=0,dir=null,moved=false,skip=false,lastTap=0;
    doc.addEventListener('touchstart', function(e){
      if(e.touches.length>1){ skip=true; return; }
      if(isInteractive(e.target)){ skip=true; return; }
      skip=false; var t=e.touches[0]; sx=t.clientX; sy=t.clientY; st=Date.now(); dir=null; moved=false;
    }, {passive:false});
    doc.addEventListener('touchmove', function(e){
      if(skip) return; var t=e.touches[0]; var dx=t.clientX-sx, dy=t.clientY-sy;
      if(Math.abs(dx)<TH && Math.abs(dy)<TH) return;
      if(e.cancelable) e.preventDefault();
      var nd = (Math.abs(dx)>Math.abs(dy)) ? (dx<0?'l':'r') : (dy<0?'u':'d');
      moved=true; if(nd!==dir){ dir=nd; if(g[nd]) press(g[nd]); }
    }, {passive:false});
    doc.addEventListener('touchend', function(e){
      if(skip){ skip=false; return; }
      if(dir){ release(); dir=null; return; }
      if(moved) return;
      if(Date.now()-st>=320) return;
      function doTap(ev){ if(PLAY.aim) aimAt(ev); tapKey(g.tap); }
      var now=Date.now();
      if(g.dtap && now-lastTap<300){ lastTap=0; tapKey(g.dtap); return; }
      lastTap=now;
      if(g.dtap){ var snap=now; setTimeout(function(){ if(lastTap===snap){ doTap(e); lastTap=0; } },270); }
      else { doTap(e); }
    }, {passive:false});
  }

  function init(){
    if(PLAY.type==='game'){
      try{ doc.documentElement.style.overflow='hidden'; doc.body.style.overflow='hidden';
           doc.documentElement.style.touchAction='none'; doc.body.style.touchAction='none'; }catch(e){}
      if(isTouch) attachGestures();
    }
    buildOverlay();
  }
  if(doc.readyState==='loading') doc.addEventListener('DOMContentLoaded', init); else init();
})();
</script>
""" + PLAYLAYER_END


def strip_old_layer(s):
    """Remove any previously injected layer so rebuilds stay clean/idempotent."""
    s = re.sub(r"\s*" + re.escape(PLAYLAYER_START) + r".*?" + re.escape(PLAYLAYER_END),
               "", s, flags=re.S)
    # Remove the older "Cowork input fix" shim block, if present.
    s = re.sub(r"\s*<script>\s*/\* --- Cowork input fix.*?</script>",
               "", s, flags=re.S)
    return s


def inject_viewport(s):
    """Add a responsive viewport meta tag if the game is missing one."""
    if 'name="viewport"' in s.lower():
        return s
    m = re.search(r"<meta[^>]*charset[^>]*>", s, re.I)
    if m:
        return s[:m.end()] + "\n" + VIEWPORT_META + s[m.end():]
    m = re.search(r"<head[^>]*>", s, re.I)
    if m:
        return s[:m.end()] + "\n" + VIEWPORT_META + s[m.end():]
    return s


def ensure_play_layer(path, filename, play_cfg):
    """Inject the responsive + how-to-play + touch-controls layer into a game."""
    with open(path, encoding="utf-8") as f:
        s = f.read()
    original = s
    s = strip_old_layer(s)
    s = inject_viewport(s)
    cfg = play_cfg.get(filename) or {"type": "page", "how": "Tap Play to start."}
    block = PLAY_LAYER_TEMPLATE.replace("__PL_CONFIG__",
                                        json.dumps(cfg, ensure_ascii=False))
    low = s.lower()
    i = low.rfind("</body>")
    if i == -1:
        i = low.rfind("</html>")
    if i == -1:
        s = s.rstrip() + "\n" + block + "\n"
    else:
        s = s[:i].rstrip() + "\n" + block + "\n" + s[i:]
    if s != original:
        with open(path, "w", encoding="utf-8") as f:
            f.write(s)
        print(f"  + play layer -> {filename}")


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
    cfg.setdefault("play", {})
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
        ensure_play_layer(path, fn, cfg["play"])
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
