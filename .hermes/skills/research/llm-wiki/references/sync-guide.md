# Obsidian Sync Guide (No Subscription)

This wiki at `/root/wiki` is designed to sync to Obsidian on your laptop/phone without requiring an Obsidian Sync subscription.

## Recommended: Git Sync (Free)

### Step 1 — Initialize Git Repo (already done on the server)
```bash
cd ~/wiki
git init
git add .
git commit -m "Initial wiki"
```

If repo already exists, skip to step 2.

### Step 2 — Push to GitHub Private Repo
```bash
git remote add origin https://github.com/YOUR_USERNAME/llm-wiki.git
git push -u origin main
```
Use a **private** repo — personal wiki content doesn't need to be public.

### Step 3 — Open as Obsidian Vault on Your Device
1. Install Obsidian on your laptop/phone
2. "Open folder as vault" → point to wherever you cloned the repo
3. Install the **Obsidian Git** community plugin (Settings → Community Plugins → search "Obsidian Git")
4. Configure it: set auto-interval to 5-10 minutes, enable on plugin startup

Now Obsidian on your device auto-pulls every few minutes. The agent writes to `/root/wiki`, you pull on your device. Not real-time, but free and reliable.

## Alternative: iCloud / Google Drive / Dropbox

If you already use one of these for file sync:
```bash
# Create a symlink — example for Google Drive on Linux
ln -s ~/wiki ~/Google\ Drive/My\ Drive/wiki

# Or sync the wiki folder to your cloud folder via rsync (run as a cron job)
0 */6 * * * rsync -av --delete ~/wiki/ /path/to/your/cloud/wiki/
```
Then open the cloud-synced folder as an Obsidian vault directly.

## Important Notes
- The wiki is just a folder of markdown files — no special Obsidian plugin required for the basics
- `[[wikilinks]]` work out of the box (enable in Settings → Editor)
- Install the **Dataview** plugin if you want to query pages by tagsynaml frontmatter
- Set Obsidian's attachment folder to `raw/assets/` so images render correctly
- **No subscription needed** — Obsidian itself is free for personal use, and Git is free
