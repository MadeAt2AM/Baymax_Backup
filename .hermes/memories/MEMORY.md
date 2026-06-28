Chris (Christus Vincent) — CYBERSLIDE + MadeAt2Am. Projects: /root/.hermes/projects/. LLM Wiki: /root/Obsidian-Vaults/Hermes (load llm-wiki-usage). Catbox: curl -F "reqtype=fileupload" -F "fileToUpload=@file.mp4" https://catbox.moe/user/api.php. MadeAt2Am brand: Warm Cream #FDFBF7, Obsidian #111111, Crimson #D32F2F, Yellow #FFC107. Social: IG @made.at.2am, YT @MadeAt2AM, X @MadeAt_2AM, Web madeat2am.in/. Telegram home: -1003825565541.
§
GWS OAuth: madeat2am.ai@gmail.com. Token: /root/.hermes/google_token.json. GWS skill: /root/.hermes/skills/productivity/google-workspace/. venv: /root/.hermes/.venv (python3.12). GAPI: cd /root/.hermes && . .venv/bin/activate && python3 skills/productivity/google-workspace/scripts/google_api.py.
§
Morning Brief: Dreaming (6 AM SGT, job=fab47f7704ba) → Brief (8 AM SGT, job=afb02a1433cf). Deliver local → telegram:-1004490060634. Skills: dreaming-sequence + morning-brief.
§
Dashboard watchdog: cron a0a18fe34a59 every 5min, /root/.hermes/scripts/check-dashboard.sh. Restart=always on hermes-dashboard.service (fixed 2026-06-28 — was Restart=on-failure with --tui flag causing crashes).
§
GitHub: chrisvincodes — PAT ready, needs github-auth skill wired up.
§
Remotion: /root/claude-code-reel/ active project
§
LLM Wiki sync: systemd hermes-wiki-sync (enabled) + cron 59cc5538d6a5 every 15min. Script: /root/.hermes/scripts/wiki-sync.sh. Repo: MadeAt2AM/Obsidian-Vaults.
§
Remotion workspace: /root/.hermes/projects/Remotion_ALL. Always run `npx remotion studio` from this directory. New projects = new composition files (src/ProjectName.tsx) registered in src/Root.tsx. Studio URL: http://localhost:3000. Kill old process on port 3000 before starting.
§
Remotion default workflow: for each new video/project, create a new composition file in src/ (e.g. src/MadeAt2Am_Promo.tsx), register it in src/Root.tsx with a unique id, then preview in Remotion Studio. Never create separate Remotion project folders — all compositions live in /root/.hermes/projects/Remotion_ALL/src/.