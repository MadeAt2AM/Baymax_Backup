#!/usr/bin/env python3
"""
Daily Email Briefing — reads recent Gmail, compiles digest, sends to Telegram.
Run manually: python3 /root/.hermes/scripts/email_briefing.py
"""

import json
import subprocess
import sys
import os
import re
from datetime import datetime, timezone, timedelta
from pathlib import Path

# ── Load .env for Telegram bot token ────────────────────────────────────────
HERMES_ENV = Path("/root/.hermes/.env")
_env_content = HERMES_ENV.read_text()
_tg_match = re.search(r'^TELEGRAM_BOT_TOKEN=(.*)$', _env_content, re.MULTILINE)
TELEGRAM_BOT_TOKEN = _tg_match.group(1).strip() if _tg_match else ""

# ── Config ────────────────────────────────────────────────────────────────────
TELEGRAM_CHAT_ID = "-1003825565541"  # MadeAt2Am home channel
GAPI = "/root/.hermes/.venv/bin/python3 /root/.hermes/skills/productivity/google-workspace/scripts/google_api.py"
SGD_TZ = timezone(timedelta(hours=8))

# ── Helpers ───────────────────────────────────────────────────────────────────
def run(cmd: str) -> list:
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if result.returncode != 0:
        return []
    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return []


def send_telegram(text: str) -> bool:
    url = f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {
        "chat_id": TELEGRAM_CHAT_ID,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }
    import urllib.request
    import urllib.parse
    data = urllib.parse.urlencode(payload).encode()
    req = urllib.request.Request(url, data=data)
    try:
        with urllib.request.urlopen(req, timeout=15):
            pass
        return True
    except Exception as e:
        print(f"Telegram error: {e}", file=sys.stderr)
        return False


def format_address(sender: str) -> str:
    """Strip gmail.com addresses to just the name part for readability."""
    if "<" in sender:
        name = sender.split("<")[0].strip().strip('"')
        addr = sender.split("<")[1].rstrip(">")
        return f"{name} ({addr})" if name else addr
    return sender


def classify_email(subject: str, snippet: str, sender: str, labels: list) -> dict:
    text = f"{subject} {snippet} {sender}".lower()
    label_set = set(l.lower() for l in labels)

    flags = []
    if "inbox" not in label_set and "unread" not in label_set:
        flags.append("archived")
    if any(k in text for k in ["urgent", "asap", "critical", "emergency", "important"]):
        flags.append("⚠️ urgent")
    if any(k in text for k in ["action", "reply", "please respond", "let me know", "your thoughts"]):
        flags.append("📌 needs reply")
    if any(k in text for k in ["invoice", "payment", "receipt", "bill", "due"]):
        flags.append("💰 financial")
    if any(k in text for k in ["meeting", "invite", "calendar", "scheduled"]):
        flags.append("📅 invite/event")
    if any(k in text for k in ["security", "alert", "sign-in", "2-step"]):
        flags.append("🔒 security")

    return {"flags": flags}


def build_brief() -> str:
    now_sgd = datetime.now(SGD_TZ)
    date_str = now_sgd.strftime("%d %b %Y, %I:%M %p SGT")

    # Get last ~26h of emails (newer_than:1d catches most of yesterday SGT-midnight onwards)
    emails = run(f'{GAPI} gmail search "newer_than:1d" --max 30')

    if not emails:
        return (
            f"📬 <b>Email Briefing</b>\n"
            f"🗓 {date_str}\n\n"
            f"No emails found in the last 24 hours.\n"
            f"You're all caught up! ✅"
        )

    # Parse emails into structured list
    parsed = []
    for e in emails:
        flags = classify_email(
            e.get("subject", ""),
            e.get("snippet", ""),
            e.get("from", ""),
            e.get("labels", [])
        )
        parsed.append({
            "id": e.get("id"),
            "from": format_address(e.get("from", "")),
            "subject": e.get("subject") or "(no subject)",
            "date": e.get("date", ""),
            "snippet": e.get("snippet", ""),
            "labels": e.get("labels", []),
            "flags": flags["flags"],
        })

    # Sort: flagged items first, then by recency
    priority_order = ["⚠️ urgent", "📌 needs reply", "💰 financial", "📅 invite/event", "🔒 security"]
    def sort_key(e):
        flag_score = 0
        for i, f in enumerate(priority_order):
            if f in e["flags"]:
                flag_score = len(priority_order) - i
        return (flag_score, e["date"])

    parsed.sort(key=sort_key, reverse=True)

    # Build Telegram message
    lines = []
    lines.append(f"📬 <b>Daily Email Briefing</b>")
    lines.append(f"🗓 {date_str}")
    lines.append(f"📧 {len(emails)} emails in last 24h")
    lines.append("")
    lines.append("─────────────────────")

    # Group by priority
    urgent = [e for e in parsed if "⚠️ urgent" in e["flags"]]
    needs_reply = [e for e in parsed if "📌 needs reply" in e["flags"]]
    financial = [e for e in parsed if "💰 financial" in e["flags"]]
    events = [e for e in parsed if "📅 invite/event" in e["flags"]]
    security = [e for e in parsed if "🔒 security" in e["flags"]]
    other = [e for e in parsed if not e["flags"]]

    # Urgent
    if urgent:
        lines.append("\n🔴 <b>URGENT</b>")
        for e in urgent:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")
            lines.append(f"    {e['snippet'][:120]}...")

    # Needs Reply
    if needs_reply:
        lines.append("\n📌 <b>Needs Your Reply</b>")
        for e in needs_reply:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")
            lines.append(f"    {e['snippet'][:120]}...")

    # Financial
    if financial:
        lines.append("\n💰 <b>Financial</b>")
        for e in financial:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")

    # Events
    if events:
        lines.append("\n📅 <b>Invites / Events</b>")
        for e in events:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")

    # Security
    if security:
        lines.append("\n🔒 <b>Security Alerts</b>")
        for e in security:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    {e['date']}")

    # Other emails (show top 10)
    if other:
        shown = other[:10]
        lines.append(f"\n📗 <b>Other ({len(other)} total, showing {len(shown)})</b>")
        for e in shown:
            preview = e["snippet"][:80] + "..." if len(e["snippet"]) > 80 else e["snippet"]
            lines.append(f"  • {e['subject']} — {e['from']}")
            if preview:
                lines.append(f"    {preview}")

    lines.append("\n─────────────────────")
    lines.append(f"🕐 Compiled at {date_str}")

    return "\n".join(lines)


if __name__ == "__main__":
    print("Fetching emails...")
    brief = build_brief()
    print(f"\nBrief compiled ({len(brief)} chars), sending to Telegram...")

    if send_telegram(brief):
        print("✅ Briefing sent to Telegram.")
    else:
        print("❌ Failed to send to Telegram. Check bot token.")
        sys.exit(1)
