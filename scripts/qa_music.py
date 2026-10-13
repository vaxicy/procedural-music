#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Self-check for a rendered track.

Band balance uses an averaged Welch PSD — the same measurement the
auto-balancer targets — so the reported numbers are directly comparable to the
`targets` in presets.py.

Loop verdicts are always RELATIVE. "seam jump = 0.00000" on its own means
nothing: a file whose head and tail were both forced to silence also reports
0.00000. Every seam number here is therefore printed next to the distribution of
the same measurement taken everywhere else in the track.

Usage
-----
  python scripts/qa_music.py out/track.wav [more.wav ...]
  python scripts/qa_music.py --loop out/*.wav
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import wave

import numpy as np

SR = 44100
BANDS = [(30, 120), (120, 500), (500, 2000), (2000, 8000), (8000, 17000)]
LABELS = ['sub/bass', 'low-mid', 'mid', 'high', 'air']


def read_audio(path):
    """Return float64 stereo array in [-1, 1]. Uses ffmpeg for non-WAV input."""
    ext = os.path.splitext(path)[1].lower()
    if ext == '.wav':
        with wave.open(path, 'rb') as f:
            ch = f.getnchannels()
            raw = f.readframes(f.getnframes())
        a = np.frombuffer(raw, dtype='<i2').astype(np.float64) / 32768.0
        return a.reshape(-1, ch)
    tmp = tempfile.mkdtemp(prefix='qa_music_')
    wav = os.path.join(tmp, 'decoded.wav')
    r = subprocess.run(['ffmpeg', '-y', '-loglevel', 'error', '-i', path,
                        '-acodec', 'pcm_s16le', wav], capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('ffmpeg decode failed for %s: %s' % (path, r.stderr[:300]))
    return read_audio(wav)


def welch_fracs(x, frame=16384, hop=None):
    hop = hop or frame // 2
    win = np.hanning(frame)
    acc = np.zeros(frame // 2 + 1)
    n = 0
    for i in range(0, len(x) - frame, hop):
        acc += np.abs(np.fft.rfft(x[i:i + frame] * win)) ** 2
        n += 1
    fr = np.fft.rfftfreq(frame, 1 / SR)
    p = np.array([float(acc[(fr >= lo) & (fr < hi)].sum()) for lo, hi in BANDS])
    return p / (p.sum() + 1e-30)


def analyze(path, loop=True):
    a = read_audio(path)
    L, R = a[:, 0], a[:, 1] if a.shape[1] > 1 else a[:, 0]
    mono = 0.5 * (L + R)
    n = len(mono)
    peak = float(max(np.abs(L).max(), np.abs(R).max()))
    rms = float(np.sqrt(np.mean(mono ** 2)))
    clip = int(np.sum((np.abs(L) >= 0.999) | (np.abs(R) >= 0.999)))

    d = {'path': path, 'n': n, 'dur': n / SR, 'peak': peak, 'rms': rms,
         'crest': peak / (rms + 1e-12), 'clip': clip, 'dc': float(mono.mean()),
         'checks': []}

    def check(name, ok, detail):
        d['checks'].append((name, bool(ok), detail))

    check('no clipping', clip == 0, '%d samples at full scale' % clip)
    check('dc offset', abs(d['dc']) < 0.002, '%.6f' % d['dc'])
    check('headroom', peak <= 0.99, 'peak %.2f dBFS' % (20 * np.log10(peak + 1e-12)))

    if loop:
        # A. junction step vs the 99.9th percentile step everywhere else
        ring = np.concatenate([mono, mono[:1]])
        step = np.abs(np.diff(ring))
        seam_step = float(step[-1])
        p999 = float(np.percentile(step[:-1], 99.9))
        d['seam_step'], d['step_p999'] = seam_step, p999
        check('seam is a normal step', seam_step <= p999,
              'junction %.6f vs 99.9%% elsewhere %.6f' % (seam_step, p999))

        # B. short-window level across the junction
        k = int(0.020 * SR)
        rms_all = np.array([np.sqrt(np.mean(mono[i:i + k] ** 2))
                            for i in range(0, n - k, k)])
        seam_win = np.concatenate([mono[n - k // 2:], mono[:k // 2]])
        r = float(np.sqrt(np.mean(seam_win ** 2)))
        pct = 100.0 * float((rms_all < r).mean())
        d['seam_pct'] = pct
        check('seam level is normal', 2.0 < pct < 98.0,
              '20 ms window sits at %.1f percentile (a fade/notch would sit near 0)'
              % pct)

        # C. head vs tail level, catches a one-sided fade
        kk = int(0.500 * SR)
        h = float(np.sqrt(np.mean(mono[:kk] ** 2)))
        t = float(np.sqrt(np.mean(mono[-kk:] ** 2)))
        ratio = h / (t + 1e-9)
        d['head_tail_ratio'] = ratio
        check('head/tail level match', 0.60 < ratio < 1.70,
              '0.5 s rms head %.4f / tail %.4f  ratio %.2f' % (h, t, ratio))

    f = welch_fracs(mono)
    d['bands'] = f
    mid = 0.5 * (L + R)
    side = 0.5 * (L - R)
    d['width'] = float(np.sqrt((side ** 2).mean()) / (np.sqrt((mid ** 2).mean()) + 1e-9))
    return d


def format_report(d, loop=True):
    out = []
    out.append('=== %s ===' % os.path.basename(d['path']))
    out.append('  duration %.2f s | peak %.2f dBFS | rms %.2f dBFS | crest %.1f dB'
               % (d['dur'], 20 * np.log10(d['peak'] + 1e-12),
                  20 * np.log10(d['rms'] + 1e-12), 20 * np.log10(d['crest'])))
    out.append('  band balance (Welch averaged):')
    for nm, v in zip(LABELS, d['bands']):
        out.append('     %-9s %5.1f%%   %s' % (nm, 100 * v, '#' * int(round(v * 50))))
    out.append('  stereo width (side/mid): %.2f' % d['width'])
    if loop and 'seam_step' in d:
        out.append('  seam step %.6f  vs 99.9%% elsewhere %.6f'
                   % (d['seam_step'], d['step_p999']))
        out.append('  seam window percentile: %.1f' % d['seam_pct'])
    out.append('  checks:')
    for name, ok, detail in d['checks']:
        out.append('     [%s] %-22s %s' % ('PASS' if ok else 'FAIL', name, detail))
    bad = [c for c in d['checks'] if not c[1]]
    out.append('  VERDICT: %s' % ('ALL PASS' if not bad else '%d CHECK(S) FAILED' % len(bad)))
    out.append('')
    return out


def run(paths, loop=True, as_string=False):
    text = []
    failed = 0
    for p in paths:
        if not os.path.exists(p):
            text.append('!! missing: %s' % p)
            failed += 1
            continue
        d = analyze(p, loop=loop)
        text += format_report(d, loop=loop)
        failed += len([c for c in d['checks'] if not c[1]])
    body = '\n'.join(text)
    if as_string:
        return body, failed
    print(body)
    return 0 if failed == 0 else 1


def main():
    args = [a for a in sys.argv[1:] if not a.startswith('--')]
    loop = '--no-loop' not in sys.argv
    if not args:
        print(__doc__)
        return 2
    return run(args, loop=loop)


if __name__ == '__main__':
    sys.exit(main())
