#!/usr/bin/env python3
"""
Build the arcade menu (index.html) from the game HTML files in this folder.

What it does, every time it runs:
  1. Finds every *.html game in this folder (ignores index.html itself).
  2. Makes sure each game has the "keyboard input fix" so arrow/space keys
     control the game instead of scrolling the page (skips files listed in
     games.json -> "noShim").
  3. Regenerates index.html with a card for every game.

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


def load_config():
    path = os.path.join(HERE, "games.json")
    cfg = {}
    if os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            cfg = json.load(f)
    cfg.setdefault("siteTitle", "🎮 Game Arcade")
    cfg.setdefault("tagline", "Click a game to play. Tip: click once inside the game window so the keyboard controls respond.")
    cfg.setdefault("defaultEmoji", "🎮")
    cfg.setdefault("defaultControls", "Click to play")
    cfg.setdefault("noShim", [])
    cfg.setdefault("overrides", {})
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

    games = []
    for fn in os.listdir(HERE):
        if not fn.lower().endswith(".html"):
            continue
        if fn in SKIP:
            continue
        path = os.path.join(HERE, fn)
        ensure_shim(path, fn, cfg["noShim"])
        ov = overrides.get(fn, {})
        nice = fn.rsplit(".", 1)[0].replace("_", " ").replace("-", " ").title()
        games.append({
            "file": fn,
            "name": ov.get("name") or title_of(path, nice),
            "emoji": ov.get("emoji", cfg["defaultEmoji"]),
            "controls": ov.get("controls", cfg["defaultControls"]),
            "order": ov.get("order", 999),
        })

    games.sort(key=lambda g: (g["order"], g["name"].lower()))

    cards = []
    for g in games:
        cards.append(
            '  <a class="card" href="./{file}">'
            '<span class="emoji">{emoji}</span>'
            '<span class="name">{name}</span>'
            '<span class="controls">{controls}</span></a>'.format(
                file=html.escape(g["file"], quote=True),
                emoji=html.escape(g["emoji"]),
                name=html.escape(g["name"]),
                controls=html.escape(g["controls"]),
            )
        )

    page = TEMPLATE.format(
        title=html.escape(cfg["siteTitle"]),
        tagline=html.escape(cfg["tagline"]),
        cards="\n".join(cards),
        count=len(games),
    )
    with open(os.path.join(HERE, "index.html"), "w", encoding="utf-8") as f:
        f.write(page)
    print(f"Built index.html with {len(games)} game(s).")


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
  header{{ text-align:center; padding:46px 20px 10px; }}
  header h1{{ margin:0; font-size:40px; letter-spacing:.5px; }}
  header p{{ color:var(--muted); margin:10px 0 0; font-size:15px; }}
  .grid{{ max-width:1040px; margin:30px auto 60px; padding:0 20px;
         display:grid; grid-template-columns:repeat(auto-fill,minmax(220px,1fr)); gap:18px; }}
  a.card{{ text-decoration:none; color:inherit; background:linear-gradient(160deg,var(--card2),var(--card));
          border:1px solid #2f3666; border-radius:16px; padding:20px; display:flex; flex-direction:column; gap:8px;
          transition:transform .12s ease, box-shadow .12s ease, border-color .12s ease; }}
  a.card:hover{{ transform:translateY(-4px); box-shadow:0 12px 30px rgba(0,0,0,.45); border-color:var(--accent); }}
  .emoji{{ font-size:34px; }}
  .name{{ font-size:18px; font-weight:700; }}
  .controls{{ font-size:12.5px; color:var(--muted); line-height:1.5; }}
  footer{{ text-align:center; color:var(--muted); font-size:12.5px; padding:0 20px 40px; }}
</style>
</head>
<body>
<header>
  <h1>{title}</h1>
  <p>{tagline}</p>
</header>

<div class="grid">
{cards}
</div>

<footer>{count} games · this menu builds itself when a new game is added 🎮</footer>
</body>
</html>
"""


if __name__ == "__main__":
    main()
