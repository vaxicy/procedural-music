#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Render a procedural music track from a style preset.

Examples
--------
  python scripts/render_track.py --list
  python scripts/render_track.py --preset y2k-digital --out ./out --loop --clean
  python scripts/render_track.py --preset lofi-minimal --out ./out --bars 32 --seed 7
  python scripts/render_track.py --preset y2k-dreamy --out ./out --full --qa
"""
from __future__ import annotations

import argparse
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import presets as P
import synth_engine as E


def main():
    ap = argparse.ArgumentParser(description='Render a procedural music track.')
    ap.add_argument('--preset', '-p', help='preset key (see --list)')
    ap.add_argument('--out', '-o', default='./out', help='output directory')
    ap.add_argument('--list', action='store_true', help='list presets and exit')
    mode = ap.add_mutually_exclusive_group()
    mode.add_argument('--loop', action='store_true',
                      help='seamless loop render (default)')
    mode.add_argument('--full', action='store_true',
                      help='render the full-length arrangement instead of a loop')
    ap.add_argument('--bars', type=int, default=24,
                    help='loop length in bars (default 24, rounded up to whole chord cycles)')
    ap.add_argument('--seed', type=int, default=None, help='RNG seed for reproducibility')
    ap.add_argument('--clean', action='store_true',
                    help='drop all noise beds and loop fades (pure/seamless deliverable)')
    ap.add_argument('--name', default=None, help='output file stem (default: preset + duration)')
    ap.add_argument('--seed-demo', dest='seed_demo', type=int, default=None,
                    help=argparse.SUPPRESS)
    ap.add_argument('--no-wav', action='store_true', help='write only the mp3')
    ap.add_argument('--no-mp3', action='store_true', help='write only the wav')
    ap.add_argument('--artist', default='', help='ID3 artist')
    ap.add_argument('--album', default='', help='ID3 album')
    ap.add_argument('--qa', action='store_true', help='run qa_music.py on the result')
    ap.add_argument('--quiet', action='store_true', help='suppress the auto-balance log')
    a = ap.parse_args()

    if a.list or not a.preset:
        print('presets:')
        for k, label, blurb in P.list_presets():
            print('  %-18s %-18s %s' % (k, label, blurb))
        return 0

    if a.preset not in P.PRESETS:
        print('unknown preset %r. use --list.' % a.preset, file=sys.stderr)
        return 2

    if a.seed is not None:
        E.set_seed(a.seed)

    loop = not a.full
    v = P.build(a.preset, bars=a.bars, loop=loop, clean=a.clean)

    st, n = E.render(v, verbose=not a.quiet)

    bars_n = len(v['arr'])
    dur = n / E.SR
    stem = a.name or '%s_%s_%ds' % (a.preset, 'loop' if loop else 'full', round(dur))

    outdir = os.path.abspath(a.out)
    os.makedirs(outdir, exist_ok=True)
    wav_path = os.path.join(outdir, stem + '.wav')
    E.write_wav(wav_path, st)

    print('')
    print('preset   : %s (%s)' % (P.PRESETS[a.preset]['label'], a.preset))
    print('mode     : %s' % ('LOOP (seamless)' if loop else 'FULL (fade-out)'))
    print('bars     : %d   bpm %s   key %s   chord_bars %s'
          % (bars_n, v['bpm'], v.get('key_name'), v.get('chord_bars', 2)))
    print('duration : %d:%02d  (%.2f s)' % (int(dur) // 60, int(dur) % 60, dur))
    print('seed     : %s' % (a.seed if a.seed is not None else 'random'))
    print('wav      : %s  (%.1f MB)' % (wav_path, os.path.getsize(wav_path) / 1048576))

    mp3_path = None
    if not a.no_mp3:
        mp3_path = os.path.join(outdir, stem + '.mp3')
        E.encode_mp3(wav_path, mp3_path, title=stem, artist=a.artist, album=a.album)
        print('mp3      : %s  (%.2f MB)' % (mp3_path, os.path.getsize(mp3_path) / 1048576))
        if a.no_wav:
            os.remove(wav_path)

    rc = 0
    if a.qa:
        import qa_music
        # QA every artifact we actually ship. The MP3 must be checked too: it is
        # a lossy transform, so the decoded waveform can overshoot the WAV peak
        # by ~0.6 dB. Validating only the WAV hides a real headroom problem.
        targets = [p for p in (mp3_path, wav_path) if p and os.path.exists(p)]
        print('')
        rc = qa_music.run(targets, loop=loop)
    return rc


if __name__ == '__main__':
    sys.exit(main())
