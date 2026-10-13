#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Objective seam test for a looping render.

A loop is clean when the junction looks statistically like any other point in
the track. Three independent checks:

  A. sample-difference check — treat the file as a ring. The |step| across the
     junction must not exceed the 99.9th percentile of |step| everywhere else.
  B. short-window level check — a 5 / 20 / 50 ms window centred on the junction
     must sit inside the distribution of all windows of that size. This is what
     catches fades and notches, which check A cannot see.
  C. spectral continuity — high-band (>3 kHz) energy in a 2048-point window
     centred on the junction, compared with the median window.

IMPORTANT: every one of these is a RELATIVE test. A file whose first and last
samples were both forced to zero reports a junction step of 0.00000 and passes
A trivially — which is why B and C exist and why all three run together.

Usage
-----
  python scripts/seam_test.py out/track.wav [more.wav ...]
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_music import read_audio, SR


def test(path, label=None):
    a = read_audio(path)
    L = a[:, 0]
    R = a[:, 1] if a.shape[1] > 1 else a[:, 0]
    m = 0.5 * (L + R)
    n = len(m)
    label = label or os.path.basename(path)
    out = []
    out.append('=== %s ===' % label)
    out.append('  samples %d  (%.3f s)' % (n, n / SR))

    ring = np.concatenate([m, m[:1]])
    step = np.abs(np.diff(ring))
    seam_step = float(step[-1])
    p999 = float(np.percentile(step[:-1], 99.9))
    out.append('  A) junction |step|      : %.6f' % seam_step)
    out.append('     99.9%% |step| elsewhere: %.6f' % p999)
    okA = seam_step <= p999
    out.append('     verdict               : %s'
               % ('OK  (junction is an ordinary sample step)' if okA
                  else '*** DISCONTINUITY ***'))

    okB = True
    for ms in (5, 20, 50):
        k = int(ms / 1000.0 * SR)
        rms_all = np.array([np.sqrt(np.mean(m[i:i + k] ** 2))
                            for i in range(0, n - k, k)])
        seam = np.concatenate([m[n - k // 2:], m[:k // 2]])
        r = float(np.sqrt(np.mean(seam ** 2)))
        pct = 100.0 * float((rms_all < r).mean())
        if not (2.0 < pct < 98.0):
            okB = False
        out.append('  B) %3d ms window rms   : %.5f  -> %.1f percentile of all windows'
                   % (ms, r, pct))
    out.append('     (a fade or notch at the seam would push this toward percentile 0)')
    if not okB:
        out.append('     *** LEVEL ANOMALY AT THE SEAM ***')

    def hi(x):
        X = np.fft.rfft(x)
        fr = np.fft.rfftfreq(len(x), 1 / SR)
        X[fr < 3000] = 0
        return float(np.sqrt(np.mean(np.fft.irfft(X, len(x)) ** 2)))

    k = 2048
    seam = np.concatenate([m[n - k // 2:], m[:k // 2]])
    hs = hi(seam)
    allh = np.array([hi(m[i:i + k]) for i in range(0, n - k, k)])
    med = float(np.median(allh))
    ratio = hs / (med + 1e-30)
    out.append('  C) seam 2048pt hi>3k    : %.6f  (median %.6f, ratio %.3f)'
               % (hs, med, ratio))
    okC = 0.5 < ratio < 2.0
    if not okC:
        out.append('     *** SPECTRAL SPIKE / HOLE AT THE SEAM ***')

    peak = max(np.abs(L).max(), np.abs(R).max())
    out.append('  D) peak %.4f dBFS  rms %.4f dBFS  dc %.6f  clip %d'
               % (20 * np.log10(peak + 1e-12),
                  20 * np.log10(np.sqrt(np.mean(m ** 2)) + 1e-12),
                  float(m.mean()),
                  int(np.sum((np.abs(L) >= 0.999) | (np.abs(R) >= 0.999)))))
    verdict = okA and okB and okC
    out.append('  VERDICT: %s' % ('SEAM OK' if verdict else 'SEAM NEEDS WORK'))
    out.append('')
    return out, verdict


def main():
    paths = [a for a in sys.argv[1:] if not a.startswith('--')]
    if not paths:
        print(__doc__)
        return 2
    bad = 0
    for p in paths:
        if not os.path.exists(p):
            print('!! missing: %s' % p)
            bad += 1
            continue
        lines, ok = test(p)
        print('\n'.join(lines))
        if not ok:
            bad += 1
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
