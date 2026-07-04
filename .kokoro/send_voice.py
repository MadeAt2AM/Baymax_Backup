#!/usr/bin/env python3
"""
Kokoro Telegram Voice — Send TTS audio as native Telegram voice message.

Uses the chunked kokoro_tts.py script to handle long text safely.

Usage:
  python3 send_voice.py "text to speak" [voice] [speed] [chat_id] [reply_to] [thread_id]
  python3 send_voice.py --silent "text to speak"   # no stdout output

The script must be called with the correct chat_id, reply_to, and thread_id for the
target topic. It does NOT look up thread context — that information must be passed
in by the caller (e.g. a cron job that knows the topic/thread IDs).
"""
import os, sys, json, subprocess, tempfile, argparse

# Config
BOT_TOKEN = None
DEFAULT_CHAT_ID = "1283992553"  # fallback: Chris Kal DM


def get_token():
    global BOT_TOKEN
    if BOT_TOKEN:
        return BOT_TOKEN
    with open('/root/.hermes/.env') as f:
        for line in f:
            if line.startswith('TELEGRAM_BOT_TOKEN=') and not line.startswith('#'):
                BOT_TOKEN = line.split('=', 1)[1].strip()
                return BOT_TOKEN
    raise ValueError("TELEGRAM_BOT_TOKEN not found in .env")


def generate_audio(text, voice='bm_fable', speed=0.95):
    """Generate OGG audio using the chunked kokoro_tts.py script."""
    fd, txt_path = tempfile.mkstemp(suffix='.txt', dir='/tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as f:
            f.write(text)
        out_path = os.path.join(tempfile.gettempdir(), f"kokoro_{os.getpid()}_{os.urandom(4).hex()}.ogg")

        proc = subprocess.run(
            ['/opt/kokoro-venv/bin/python', '/root/.kokoro/kokoro_tts.py',
             '--input', txt_path, '--output', out_path,
             '--voice', voice, '--speed', str(speed)],
            capture_output=True, text=True, timeout=120,
        )
        if proc.returncode != 0 or not os.path.isfile(out_path):
            raise RuntimeError(
                f"kokoro_tts.py failed (exit={proc.returncode}): "
                f"stdout={proc.stdout[-500:]} stderr={proc.stderr[-500:]}"
            )
        return out_path
    finally:
        try:
            os.remove(txt_path)
        except OSError:
            pass


def send_voice(audio_path, chat_id=None, reply_to=None, thread_id=None):
    """
    Send voice message to Telegram as native voice bubble (no caption).
    """
    import urllib.request

    token = get_token()
    boundary = 'BoundaryKokoroVoice'

    form_fields = {
        'chat_id': str(chat_id if chat_id else DEFAULT_CHAT_ID),
    }
    if reply_to is not None:
        form_fields['reply_to_message_id'] = str(reply_to)
    if thread_id is not None:
        form_fields['message_thread_id'] = str(thread_id)

    with open(audio_path, 'rb') as f:
        voice_data = f.read()

    body_parts = []
    for name, value in form_fields.items():
        body_parts.append(
            f'--{boundary}\r\n'
            f'Content-Disposition: form-data; name="{name}"\r\n\r\n'
            f'{value}\r\n'.encode()
        )

    body_parts.append(
        f'--{boundary}\r\n'
        f'Content-Disposition: form-data; name="voice"; filename="voice.ogg"\r\n'
        f'Content-Type: audio/ogg\r\n\r\n'.encode()
    )
    body_parts.append(voice_data)
    body_parts.append(f'\r\n--{boundary}--\r\n'.encode())

    body = b''.join(body_parts)

    url = f'https://api.telegram.org/bot{token}/sendVoice'
    req = urllib.request.Request(
        url,
        data=body,
        headers={'Content-Type': f'multipart/form-data; boundary={boundary}'},
        method='POST'
    )

    with urllib.request.urlopen(req, timeout=60) as resp:
        result = json.loads(resp.read().decode())
        if result.get('ok'):
            dur = result['result']['voice']['duration']
            return f"sent:{dur}s"
        else:
            raise RuntimeError(f"telegram api error: {result.get('description')}")


if __name__ == '__main__':
    p = argparse.ArgumentParser(description='Send Kokoro TTS voice to Telegram')
    p.add_argument('text', help='Text to speak')
    p.add_argument('voice', nargs='?', default='bm_fable')
    p.add_argument('speed', nargs='?', default=0.95, type=float)
    p.add_argument('chat_id', nargs='?', default=None)
    p.add_argument('reply_to', nargs='?', default=None)
    p.add_argument('thread_id', nargs='?', default=None)
    p.add_argument('--silent', action='store_true',
                   help='Suppress all stdout output (used when called via Hermes terminal)')
    p.add_argument('--keep', action='store_true',
                   help='Keep the audio file after sending')
    args = p.parse_args()

    if args.chat_id:
        try:
            args.chat_id = str(int(args.chat_id))
        except ValueError:
            pass

    try:
        audio = generate_audio(args.text, args.voice, args.speed)
    except Exception as e:
        if not args.silent:
            print(f"tts-fail:{e}", file=sys.stderr)
        sys.exit(1)

    try:
        result = send_voice(audio, chat_id=args.chat_id,
                            reply_to=args.reply_to, thread_id=args.thread_id)
        if not args.silent:
            print(result)
    except Exception as e:
        if not args.silent:
            print(f"send-fail:{e}", file=sys.stderr)
        sys.exit(1)
    finally:
        if not args.keep:
            try:
                os.remove(audio)
            except OSError:
                pass