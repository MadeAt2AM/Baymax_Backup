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
§
Patch-then-test + restart + verify protocol: gateway code = (1) write unit test pinning inline logic via helper methods, (2) run existing tests for touched area, (3) THEN run a LIVE end-to-end round-trip (fire the tool, confirm the user actually received it), (4) only after step 3 succeeds ask Chris to restart / declare closed. Tests/gateway/test_voice_prose_suppression.py = 32 cases pinning prose suppression, voice-tool detection, backstop helper with history_offset scoping — these pin the logic, but the bug was in integration twice on 2026-07-02 (auto-append regex missing valid TTS; backstop over-scoped re-delivering stale files). Unit tests passing ≠ working delivery. Always preserve negative cases (text-only path). Cron/services/configs/scripts: same protocol — devise test, apply patch, run test in one shot, verify live. Stop and ask if test could collide with active resources. Gateway restart needs Chris's go-ahead (live daemon, kills session). Never run `systemctl restart hermes-gateway.service` from inside the gateway session — runtime blocks via `os.environ.get("_HERMES_GATEWAY") == "1"` at tools/terminal_tool.py:2237 (would SIGTERM the gateway and kill the very subprocess running the command). Use systemd from outside.
§
Voice mode rule (2026-07-02 lesson): Chris's chat was left on `"all"` in `~/.hermes/gateway_voice_mode.json` after voice-pipeline debugging, which auto-TTS'd every reply with a voice bubble stitched on top of the text — same bug class as yesterday's voice-after-text. Default for ALL chats is `"off"` — voice is opt-in via the `text_to_speech` tool. `"all"` mode is for explicit debugging only, must be reverted to `"off"` before declaring voice work closed. Part of the verification checklist, not an afterthought.
§
Timezone rule (HARD): operator lives in Singapore. ALL time/date/schedule output in SGT (UTC+8, Asia/Singapore). Convert from source data (UTC/EDT/etc) and show SGT first; include source-native timestamps alongside for reconciliation. Applies to live scores, fixtures, cron runtimes, log timestamps, "yesterday/today/tonight" — anything time-anchored. Persisted in /root/.hermes/SOUL.md "Operator Profile — Singapore (SGT)" section on 2026-07-02.
§
MTU mismatch is the #1 cause of 'works on host, fails in container' for TLS/Postgres/SMTP on Hetzner/Cloud VPS. Host eth0 MTU=1400, Docker default bridge MTU=1500. Fix: custom docker network with driver_opts mtu=1400, explicit networks on ALL services. Discovered 2026-07-05 on Payntra deploy.
§
SMTP: mail.cyberslide.net:587 STARTTLS works. Port 465 SSL failed. Credentials: support@madeat2am.in (user provided, not default Hermes SMTP). Fixed in Payntra deploy 2026-07-05.
§
Deploy flow: push to main → GitHub webhook → VPS port 9000 → project_dev.sh redeploy → Caddy reload → live at payntra.terrybot.top. Webhook: MadeAt2AM/payntra private repo.
§
Project: Payntra at payntra.terrybot.top on VPS 147.79.18.32 (Hetzner Helsinki). Stack: React/Vite/TS/Tailwind + Fastify/Zod/Postgres. Docker network payntra-net MTU 1400. Brand accent: Crimson #D32F2F.
§
Cookie: HTTPOnly, Secure, SameSite=Lax, 30-day TTL, domain=payntra.terrybot.top. JWT in cookie, bcrypt 10 rounds, reset token crypto.randomBytes(32).hex. First-run rollover falls back to expense_templates.