Chris (Christus Vincent) — CYBERSLIDE + MadeAt2Am brand. Projects in /root/.hermes/projects/. LLM Wiki: /root/Obsidian-Vaults/Hermes. Catbox: curl -F "reqtype=fileupload" -F "fileToUpload=@file.mp4" https://catbox.moe/user/api.php. Brand: Warm Cream #FDFBF7, Obsidian #111111, Crimson #D32F2F, Yellow #FFC107. Social: IG @made.at.2am, YT @MadeAt2AM, X @MadeAt_2AM, Web madeat2am.in/. Telegram home: -1003825565541. Prefers direct style.
§
GWS: madeat2am.ai@gmail.com. Token: /root/.hermes/google_token.json. Skill: /root/.hermes/skills/productivity/google-workspace/. venv: /root/.hermes/.venv (python3.12).
§
Morning Brief pipeline: Dreaming (6 AM SGT) → Brief (8 AM SGT). Deliver to telegram:-1004490060634. Skills: dreaming-sequence + morning-brief.
§
Dashboard watchdog: cron every 5min, Restart=always on hermes-dashboard.service (fixed --tui flag crash issue).
§
LLM Wiki sync: systemd + cron every 15min. Repo: MadeAt2AM/Obsidian-Vaults.
§
Remotion: /root/claude-code-reel/, Studio http://147.79.18.59:3000. Kill port 3000 before starting. CHROME_BIN=/snap/bin/chromium.
§
Agent Reach: venv ~/.agent-reach-venv/, config ~/.agent-reach/, MCP ~/.mcporter/mcporter.json. xiaohongshu MCP port 18060, Exa via mcporter, Groq key configured. LinkedIn MCP port 3001 (systemd). 14/15 channels live (2026-06-30). Xueqiu skipped.
§
VNC Desktop: https://cyberslide.terrybot.top/ (chris/Cris0037.) — browser-based VNC for cookie extraction (Twitter/Reddit).
§
Voice comms: Chris sends Telegram voice messages to communicate. He WANTS voice replies — native Telegram voice bubbles (OGG/Opus), not MP3 files. Use send_voice.py for direct Telegram delivery: /opt/kokoro-venv/bin/python /root/.kokoro/send_voice.py "text". TTS text must be well-punctuated with commas, periods, exclamation marks — natural prosody and pauses matter. bm_fable voice, speed 0.95.
§
Voice routing: NEVER call /root/.kokoro/send_voice.py directly for Chris's messages — it bypasses the gateway's native voice pipeline and the topic thread, sending to the bot home instead. ALWAYS use the text_to_speech tool (native gateway path), which routes through the platform layer and honors message_thread_id. send_voice.py is fallback-only when the gateway is fully down. Thread ID for current topic: 57217, chat_id: 1283992553.
§
Voice delivery rule (HARD): NEVER call /root/.kokoro/send_voice.py via terminal tool for Chris — bypasses gateway native path, no message_thread_id awareness, sends to bot home instead of topic. ALWAYS use text_to_speech tool which routes through gateway _deliver_media_from_response + [[audio_as_voice]] tag and Telegram adapter with correct thread_id. send_voice.py = fallback ONLY when gateway is fully down. Chris confirmed 2026-07-01: misroute incident in topic 57217, chat_id 1283992553.
§
send_voice.py is NOT a fallback for gateway-down scenarios. Chris: 2026-07-01 — gateway down = Telegram fully offline (no inbound msgs, no session ctx, no thread_id). send_voice.py posts orphan voice bubbles with no conversational continuity. The only real fallback when voice fails is to fix the gateway (systemctl restart hermes-gateway.service) and resume native text_to_speech path. Never claim send_voice.py is a fallback.