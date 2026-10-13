#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Is the seam a NOTCH, or is the arrangement just sparse there?

seam_test.py tells you *that* the junction level looks unusual. This tells you
*why*. It prints the short-window RMS for the windows immediately before and
after the junction, laid out on a ring so the seam sits in the middle.

A real defect shows a V shape that dips exactly at the junction.
An arrangement that is simply quiet at that point stays flat across it — which
is fine, and is common when the last section thins out on purpose.

Usage
-----
  python scripts/seam_focus.py out/track.wav [more.wav ...] [--win 20] [--span 8]
"""
from __future__ import annotations

import os
import sys

import numpy as np

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from qa_music import read_audio, SR


def focus(path, label=None, win_ms=20, span=8):
    a = read_audio(path)
    m = 0.5 * (a[:, 0] + (a[:, 1] if a.shape[1] > 1 else a[:, 0]))
    n = len(m)
    label = label or os.path.basename(path)
    k = int(win_ms / 1000.0 * SR)
    ring = np.concatenate([m, m])              # two laps, so we can straddle the seam
    start = n - span * k                       # `span` windows before the junction
    vals = []
    for i in range(2 * span):
        seg = ring[start + i * k: start + (i + 1) * k]
        vals.append(float(np.sqrt(np.mean(seg ** 2))))
    base = float(np.median(vals))

    out = ['=== %s  (%d ms windows, junction between win -1 and win 0) ==='
           % (label, win_ms)]
    for i, v in enumerate(vals):
        tag = '  <-- SEAM' if i == span - 1 else ''
        out.append('  win %+2d  %.5f  %.2fx  %-26s%s'
                   % (i - span, v, v / base, '#' * int(round(v / base * 24)), tag))
    lo = min(vals)
    at = vals.index(lo)
    out.append('  min %.5f (%.2fx) at win %+d | max %.5f (%.2fx) | spread %.2fx'
               % (lo, lo / base, at - span, max(vals), max(vals) / base, max(vals) / lo))
    ok = lo / base > 0.72
    out.append('  verdict: %s'
               % ('OK - the junction sits at the level of its neighbours, not a notch'
                  if ok else
                  '*** V-SHAPED DIP: there is a notch at the seam ***'))
    if not ok and at == span - 1:
        out.append('  note: the minimum is exactly at the junction, so this is a real '
                   'seam defect, not a sparse arrangement.')
    elif not ok:
        out.append('  note: the minimum is NOT at the junction, so this is the '
                   'arrangement being sparse here rather than a seam defect.')
    out.append('')
    return out, ok


def main():
    argv = sys.argv[1:]
    win, span = 20, 8
    paths = []
    i = 0
    while i < len(argv):
        if argv[i] == '--win':
            win = int(argv[i + 1]); i += 2; continue
        if argv[i] == '--span':
            span = int(argv[i + 1]); i += 2; continue
        if not argv[i].startswith('--'):
            paths.append(argv[i])
        i += 1
    if not paths:
        print(__doc__)
        return 2
    bad = 0
    for p in paths:
        if not os.path.exists(p):
            print('!! missing: %s' % p)
            bad += 1
            continue
        lines, ok = focus(p, win_ms=win, span=span)
        print('\n'.join(lines))
        if not ok:
            bad += 1
    return 0 if bad == 0 else 1


if __name__ == '__main__':
    sys.exit(main())
