# 🎮 Reyaansh's Game Arcade

A collection of self-contained HTML games, hosted live on GitHub Pages so anyone
can play them in a browser — just share the link.

**Live site:** https://YOUR_USERNAME.github.io/REPO/

## How it works

Every game is a single `.html` file in this folder. The menu page (`index.html`)
is **generated automatically** by `build_index.py`, which a GitHub Action runs on
every push (see `.github/workflows/deploy.yml`). That same step also auto-adds the
keyboard-input fix to any new game, then deploys everything to GitHub Pages.

So the whole workflow for adding a game is just: **add the file → push**.

## Adding a new game

1. Drop the new `game-name.html` file into this folder.
2. Publish it (either option):
   - Double-click **`publish.command`**, or
   - Run: `git add -A && git commit -m "Add new game" && git push`
3. Wait ~1 minute. The menu updates itself and the game appears live on the site.

### Optional polish

By default a new game shows up using its `<title>` and a generic icon. To give it
a custom name, emoji, and controls hint, add an entry to `games.json`:

```json
"my-game.html": { "name": "My Game", "emoji": "🎯", "controls": "← → move · Space", "order": 15 }
```

- `noShim` in `games.json` lists files that should NOT get the keyboard fix
  (e.g. a static page you want to scroll normally).

## One-time setup

1. Create a new **public** repo on GitHub (empty, no README).
2. From this folder, connect and push:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/REPO.git
   git push -u origin main
   ```
3. On GitHub: **Settings → Pages → Build and deployment → Source: GitHub Actions**.
4. Push once more (or re-run the Action) and your site goes live at the URL above.

## Run the menu builder locally (optional)

```bash
python3 build_index.py
```
