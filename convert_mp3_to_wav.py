"""
Convert MP3 files in `assets/sounds` to WAV using ffmpeg.

Usage:
  python convert_mp3_to_wav.py            # convert all .mp3 -> .wav (skip existing)
  python convert_mp3_to_wav.py --force    # overwrite existing .wav files
  python convert_mp3_to_wav.py file.mp3   # convert a specific file

Requirements:
  - `ffmpeg` must be installed and available on PATH.

This script is intentionally simple and prints progress/diagnostics.
"""

import os
import sys
import shutil
import subprocess
import argparse

ROOT = os.path.dirname(__file__)
SOUNDS_DIR = os.path.join(ROOT, 'assets', 'sounds')


def find_ffmpeg():
    exe = shutil.which('ffmpeg') or shutil.which('ffmpeg.exe')
    return exe


def convert_file(ffmpeg, src, dst, force=False):
    if not os.path.exists(src):
        print(f"skip: source not found: {src}")
        return False
    if os.path.exists(dst) and not force:
        print(f"skip: destination exists: {dst}")
        return True
    cmd = [ffmpeg, '-y' if force else '-n', '-i', src, dst]
    print('running:', ' '.join(cmd))
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print('ffmpeg error:', proc.returncode)
        print(proc.stderr)
        return False
    print('converted:', src, '->', dst)
    return True


def convert_all(ffmpeg, force=False, specific=None):
    if not os.path.isdir(SOUNDS_DIR):
        print('sounds directory not found:', SOUNDS_DIR)
        return
    if specific:
        src = os.path.join(SOUNDS_DIR, specific)
        if not src.lower().endswith('.mp3'):
            print('error: specific file must be an .mp3 inside assets/sounds')
            return
        dst = os.path.splitext(src)[0] + '.wav'
        convert_file(ffmpeg, src, dst, force=force)
        return

    files = [f for f in os.listdir(SOUNDS_DIR) if f.lower().endswith('.mp3')]
    if not files:
        print('no mp3 files found in', SOUNDS_DIR)
        return
    for f in files:
        src = os.path.join(SOUNDS_DIR, f)
        dst = os.path.splitext(src)[0] + '.wav'
        convert_file(ffmpeg, src, dst, force=force)


def main():
    parser = argparse.ArgumentParser(description='Convert MP3 -> WAV in assets/sounds')
    parser.add_argument('--force', action='store_true', help='overwrite existing WAVs')
    parser.add_argument('file', nargs='?', help='specific mp3 filename inside assets/sounds')
    args = parser.parse_args()

    ffmpeg = find_ffmpeg()
    if not ffmpeg:
        print('ffmpeg not found on PATH. Please install ffmpeg and ensure it is on your PATH.')
        print('Examples: https://ffmpeg.org/download.html')
        sys.exit(2)

    print('Using ffmpeg:', ffmpeg)
    convert_all(ffmpeg, force=args.force, specific=args.file)


if __name__ == '__main__':
    main()
