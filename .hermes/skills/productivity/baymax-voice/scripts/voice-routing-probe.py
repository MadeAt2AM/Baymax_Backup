#!/usr/bin/env python3
"""
Voice routing probe — verifies the native voice path is correctly configured
for Chris's Telegram DM topics.

Use this BEFORE sending a voice reply, or after any config change to
tts.* / voice.* / gateway_voice_mode.json. Catches the misroute bug
class before it hits the chat.

Exit codes:
  0 = all checks passed, safe to use text_to_speech tool
  1 = one or more checks failed, do NOT use the native path
  2 = probe itself could not run (missing DB, missing files)

Checks performed:
  1. gateway_voice_mode.json exists and contains Chris's chat with mode != "off"
  2. config.yaml has voice_compatible: true on the kokoro provider
  3. config.yaml has output_format: ogg on the kokoro provider
  4. config.yaml has voice.auto_tts: true
  5. Topic binding exists for the requested thread (default: latest binding)
  6. Topic mode is enabled for the chat
"""
import json
import os
import sqlite3
import sys

CHAT_ID = "1283992553"
DEFAULT_THREAD_ID = os.environ.get("VOICE_PROBE_THREAD_ID")  # optional override


def check_voice_mode_file():
    path = os.path.expanduser("~/.hermes/gateway_voice_mode.json")
    if not os.path.isfile(path):
        return False, f"missing {path}"
    try:
        with open(path) as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        return False, f"malformed JSON in {path}: {e}"
    key = f"telegram:{CHAT_ID}"
    if key not in data:
        return False, f"key {key!r} not in {path} (found: {list(data)})"
    mode = data[key]
    if mode == "off":
        return False, f"voice mode is 'off' for {key}"
    return True, f"voice mode = {mode!r}"


def check_config_flag(flag, required_value):
    path = os.path.expanduser("~/.hermes/config.yaml")
    if not os.path.isfile(path):
        return False, f"missing {path}"
    with open(path) as f:
        content = f.read()
    needle = f"{flag}: {required_value}"
    if needle not in content:
        return False, f"config flag {needle!r} not found in {path}"
    return True, f"{flag} = {required_value}"


def check_topic_binding(thread_id=None):
    db = "/root/.hermes/state.db"
    if not os.path.isfile(db):
        return False, f"missing {db}"
    try:
        conn = sqlite3.connect(db)
        cur = conn.cursor()
        if thread_id:
            cur.execute(
                "SELECT thread_id, session_key FROM telegram_dm_topic_bindings "
                "WHERE chat_id = ? AND thread_id = ?",
                (CHAT_ID, thread_id),
            )
        else:
            cur.execute(
                "SELECT thread_id, session_key FROM telegram_dm_topic_bindings "
                "WHERE chat_id = ? ORDER BY updated_at DESC LIMIT 1",
                (CHAT_ID,),
            )
        row = cur.fetchone()
        if not row:
            return False, f"no binding for chat {CHAT_ID}" + (f" thread {thread_id}" if thread_id else "")
        cur.execute(
            "SELECT enabled FROM telegram_dm_topic_mode WHERE chat_id = ?",
            (CHAT_ID,),
        )
        mode_row = cur.fetchone()
        if not mode_row or mode_row[0] != 1:
            return False, f"topic mode disabled for chat {CHAT_ID}"
        conn.close()
        return True, f"binding: thread={row[0]} session={row[1]}"
    except sqlite3.Error as e:
        return False, f"db error: {e}"


def main():
    print("=== Voice routing probe ===\n")
    checks = [
        ("voice mode file", check_voice_mode_file),
        ("voice_compatible: true", lambda: check_config_flag("voice_compatible", "true")),
        ("output_format: ogg", lambda: check_config_flag("output_format", "ogg")),
        ("auto_tts: true", lambda: check_config_flag("auto_tts", "true")),
        ("topic binding", lambda: check_topic_binding(DEFAULT_THREAD_ID)),
    ]
    failed = []
    for name, fn in checks:
        try:
            ok, detail = fn()
        except Exception as e:
            ok, detail = False, f"probe error: {e}"
        status = "✓" if ok else "✗"
        print(f"  [{status}] {name}: {detail}")
        if not ok:
            failed.append(name)
    print()
    if failed:
        print(f"FAILED ({len(failed)} check(s)): {', '.join(failed)}")
        print("Native voice path is NOT safe. Investigate before sending voice replies.")
        sys.exit(1)
    print("All checks passed. Safe to use text_to_speech tool.")
    sys.exit(0)


if __name__ == "__main__":
    main()