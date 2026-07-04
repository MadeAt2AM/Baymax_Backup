#!/usr/bin/env python3
"""
Kokoro TTS Generator — Hermes Command Provider
Run: python3 kokoro_tts.py --input /tmp/text.txt --output /tmp/audio.ogg

Outputs .ogg (Opus) for Telegram native voice bubbles.
"""
import os, sys, argparse, subprocess, re

os.environ['PHONEMIZER_ESPEAK_LIBRARY'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/libespeak-ng.so'
os.environ['PHONEMIZER_ESPEAK_DATA'] = '/opt/kokoro-venv/lib/python3.11/site-packages/espeakng_loader/espeak-ng-data'

from kokoro_onnx import Kokoro
import scipy.io.wavfile as wavfile
import numpy as np

MODEL = '/root/.kokoro/models/thewh1teagle/kokoro-v1.0.fp16.onnx'
VOICES = '/root/.kokoro/voices/thewh1teagle/voices-v1.0.bin'
_kokoro = None

# Kokoro can choke on text that produces > ~510 phonemes.
# ~200 chars is a safe per-chunk ceiling; we also split on natural
# sentence boundaries so the audio has natural pauses.
MAX_CHARS_PER_CHUNK = 250


def get():
    global _kokoro
    if _kokoro is None:
        _kokoro = Kokoro(MODEL, VOICES)
    return _kokoro


def split_into_chunks(text):
    """Split text into chunks ≤ MAX_CHARS_PER_CHUNK, preferring sentence
    boundaries. Falls back to character splits if no sentence break exists
    within the window."""
    text = text.strip()
    if len(text) <= MAX_CHARS_PER_CHUNK:
        return [text]

    # Prefer splitting on sentence endings: . ! ? followed by whitespace + capital
    sentence_pattern = re.compile(r'(?<=[.!?])\s+(?=[A-Z"\'])')
    sentences = sentence_pattern.split(text)

    chunks = []
    current = ''
    for s in sentences:
        # If adding this sentence keeps us under cap, append.
        if len(current) + len(s) + 1 <= MAX_CHARS_PER_CHUNK:
            current = (current + ' ' + s).strip()
        else:
            # Flush current
            if current:
                chunks.append(current)
            # If the sentence itself is too long, hard-split it on commas/clauses
            if len(s) > MAX_CHARS_PER_CHUNK:
                # Split on commas, then hard char split as last resort
                pieces = re.split(r'(?<=,)\s+', s)
                sub = ''
                for p in pieces:
                    if len(sub) + len(p) + 1 <= MAX_CHARS_PER_CHUNK:
                        sub = (sub + ' ' + p).strip()
                    else:
                        if sub:
                            chunks.append(sub)
                        # Hard char split for very long clauses
                        while len(p) > MAX_CHARS_PER_CHUNK:
                            chunks.append(p[:MAX_CHARS_PER_CHUNK])
                            p = p[MAX_CHARS_PER_CHUNK:]
                        sub = p
                if sub:
                    chunks.append(sub)
                current = ''
            else:
                current = s
    if current:
        chunks.append(current)
    return chunks


def generate(text, out_path, voice='bm_fable', speed=0.95):
    kokoro = get()
    chunks = split_into_chunks(text)

    # Generate each chunk as float audio at 24kHz, then concat.
    sample_rate = None
    audio_parts = []
    for i, chunk in enumerate(chunks):
        if not chunk.strip():
            continue
        try:
            audio, sr = kokoro.create(chunk, voice=voice, speed=speed)
            if sample_rate is None:
                sample_rate = sr
            # kokoro returns float32 in [-1, 1]; convert to int16
            audio_int16 = np.clip(audio, -1.0, 1.0)
            audio_int16 = (audio_int16 * 32767).astype(np.int16)
            # Insert a short silence between chunks for natural pacing
            if audio_parts:
                silence = np.zeros(int(sr * 0.15), dtype=np.int16)
                audio_parts.append(silence)
            audio_parts.append(audio_int16)
        except Exception as e:
            # Skip chunk but keep going — partial is better than nothing
            sys.stderr.write(f"[kokoro_tts] chunk {i} failed ({len(chunk)} chars): {e}\n")
            continue

    if not audio_parts:
        raise RuntimeError("Kokoro failed to produce any audio chunks")

    full_audio = np.concatenate(audio_parts)
    wav_path = out_path.replace('.ogg', '_temp.wav')
    wavfile.write(wav_path, sample_rate, full_audio)

    # Convert to OGG Opus for Telegram voice bubbles
    subprocess.run([
        'ffmpeg', '-y', '-i', wav_path,
        '-codec:a', 'libopus', '-b:a', '128k',
        '-ar', '48000',
        out_path
    ], capture_output=True)

    try:
        os.remove(wav_path)
    except OSError:
        pass
    return out_path


if __name__ == '__main__':
    a = argparse.ArgumentParser(description='Kokoro TTS Generator')
    a.add_argument('--input', help='Text input file')
    a.add_argument('--output', required=True)
    a.add_argument('--voice', default='bm_fable')
    a.add_argument('--speed', type=float, default=0.95)
    a.add_argument('--format', default='ogg')
    args = a.parse_args()

    if args.input:
        with open(args.input, 'r', encoding='utf-8') as f:
            text = f.read().strip()
    else:
        text = sys.stdin.read().strip()

    if not text:
        print("Error: No text provided", file=sys.stderr)
        sys.exit(1)

    try:
        generate(text, args.output, voice=args.voice, speed=args.speed)
    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)