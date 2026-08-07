#!/usr/bin/env python3
"""
Daily Email Briefing — pulls the last ~24h of Gmail.

Two output modes:

  --pretty   (default)  Grouped HTML digest sent to Telegram (legacy format).
                         Use for ad-hoc human runs:  python3 email_briefing.py

  --json                 Emit one JSON object per email to stdout. The
                         inbox-triage skill (LLM-driven) consumes this and
                         formats the ACTION / WAIT / ARCHIVE table. This is
                         the canonical interface for the daily-email-briefing
                         cron.

Examples:
  python3 /root/.hermes/scripts/email_briefing.py --pretty
  python3 /root/.hermes/scripts/email_briefing.py --json | jq '.[0].from'
"""

import json
import subprocess
import sys
import os
import re
import argparse
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
    """Legacy 5-flag classifier — only used by --pretty mode.
    The inbox-triage skill does its own ACTION/WAIT/ARCHIVE classification
    over the --json output. Do not unify these two — they have different
    priorities (the old flags are about urgency; the new buckets are about
    decision ownership)."""
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


def fetch_emails() -> list:
    """Pull last ~26h of Gmail. Returns list of dicts as returned by gapi."""
    return run(f'{GAPI} gmail search "newer_than:1d" --max 30')


def parse_emails(raw: list) -> list:
    """Attach the legacy 5-flag classification to each email dict.
    Used by --pretty and exposed in --json so the triage skill can see
    what the legacy classifier thought, without being bound to it."""
    parsed = []
    for e in raw:
        flags = classify_email(
            e.get("subject", ""),
            e.get("snippet", ""),
            e.get("from", ""),
            e.get("labels", [])
        )
        parsed.append({
            "id": e.get("id"),
            "from": format_address(e.get("from", "")),
            "from_raw": e.get("from", ""),
            "subject": e.get("subject") or "(no subject)",
            "date": e.get("date", ""),
            "snippet": e.get("snippet", ""),
            "labels": e.get("labels", []),
            "is_unread": "unread" in [l.lower() for l in e.get("labels", [])],
            "legacy_flags": flags["flags"],
        })
    return parsed


def build_pretty(parsed: list) -> str:
    """Legacy grouped-by-flag HTML digest for Telegram."""
    now_sgd = datetime.now(SGD_TZ)
    date_str = now_sgd.strftime("%d %b %Y, %I:%M %p SGT")

    if not parsed:
        return (
            f"📬 <b>Email Briefing</b>\n"
            f"🗓 {date_str}\n\n"
            f"No emails found in the last 24 hours.\n"
            f"You're all caught up! ✅"
        )

    # Sort: flagged items first, then by recency
    priority_order = ["⚠️ urgent", "📌 needs reply", "💰 financial", "📅 invite/event", "🔒 security"]
    def sort_key(e):
        flag_score = 0
        for i, f in enumerate(priority_order):
            if f in e["legacy_flags"]:
                flag_score = len(priority_order) - i
        return (flag_score, e["date"])
    parsed = sorted(parsed, key=sort_key, reverse=True)

    lines = []
    lines.append(f"📬 <b>Daily Email Briefing</b>")
    lines.append(f"🗓 {date_str}")
    lines.append(f"📧 {len(parsed)} emails in last 24h")
    lines.append("")
    lines.append("─────────────────────")

    urgent = [e for e in parsed if "⚠️ urgent" in e["legacy_flags"]]
    needs_reply = [e for e in parsed if "📌 needs reply" in e["legacy_flags"]]
    financial = [e for e in parsed if "💰 financial" in e["legacy_flags"]]
    events = [e for e in parsed if "📅 invite/event" in e["legacy_flags"]]
    security = [e for e in parsed if "🔒 security" in e["legacy_flags"]]
    other = [e for e in parsed if not e["legacy_flags"]]

    if urgent:
        lines.append("\n🔴 <b>URGENT</b>")
        for e in urgent:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")
            lines.append(f"    {e['snippet'][:120]}...")

    if needs_reply:
        lines.append("\n📌 <b>Needs Your Reply</b>")
        for e in needs_reply:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")
            lines.append(f"    {e['snippet'][:120]}...")

    if financial:
        lines.append("\n💰 <b>Financial</b>")
        for e in financial:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")

    if events:
        lines.append("\n📅 <b>Invites / Events</b>")
        for e in events:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    From: {e['from']} | {e['date']}")

    if security:
        lines.append("\n🔒 <b>Security Alerts</b>")
        for e in security:
            lines.append(f"  • {e['subject']}")
            lines.append(f"    {e['date']}")

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


def main():
    parser = argparse.ArgumentParser(description="Daily email briefing")
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--pretty", action="store_true", help="Grouped HTML digest (default)")
    mode.add_argument("--json", action="store_true", help="Emit structured JSON to stdout for the inbox-triage skill")
    args = parser.parse_args()

    raw = fetch_emails()
    parsed = parse_emails(raw)

    if args.json:
        # Add a couple of pre-computed hints the triage skill can lean on
        # without being bound by them. The skill does its own classification.
        output = {
            "fetched_at": datetime.now(SGD_TZ).isoformat(),
            "count": len(parsed),
            "emails": parsed,
        }
        print(json.dumps(output, ensure_ascii=False, indent=2))
        return 0

    # --pretty (default): send to Telegram, same behaviour as before
    print(f"Fetching emails... found {len(parsed)}", file=sys.stderr)
    brief = build_pretty(parsed)
    print(f"\nBrief compiled ({len(brief)} chars), sending to Telegram...", file=sys.stderr)

    if send_telegram(brief):
        print("✅ Briefing sent to Telegram.", file=sys.stderr)
        return 0
    else:
        print("❌ Failed to send to Telegram. Check bot token.", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())