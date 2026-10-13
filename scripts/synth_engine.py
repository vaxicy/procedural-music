#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Procedural music engine — every sample is synthesised in Python.

No samples, no soundfonts, no DAW, no music model. Instruments are additive
sine stacks with hand-tuned envelopes; effects are FFT convolution reverb and a
ping-pong delay; band balance is measured with an averaged Welch PSD and
corrected by an iterative EQ curve; seamless loops come from folding the reverb
tail back onto the head.

Sections
--------
  helpers        bandpass / midi2hz / n2m / bitcrush / sr_crush
  instruments    pad_chord shimmer_chord bell blip rhodes sub_bass kick clap hat
  noise beds     air_layer vinyl hiss
  fx             make_ir conv pingpong
  measurement    welch_fracs eq_curve apply_curve auto_balance
  engine         Track noise_envelope render
  output         write_wav encode_mp3

See references/mixing-rules.md for the rules this file encodes, and
references/synthesis-cookbook.md for the harmonic recipes.
"""
from __future__ import annotations

import math
import os
import subprocess
import wave

import numpy as np

SR = 44100

# Five measurement bands. Everything (auto-balance targets, QA reports) uses
# these same edges so the numbers stay comparable.
BANDS = [(30, 120), (120, 500), (500, 2000), (2000, 8000), (8000, 17000)]
BAND_LABELS = ["sub/bass", "low-mid", "mid", "high", "air"]

# Peak the master bus is normalised to, in linear amplitude (0.89 == -1.0 dBFS).
#
# Do NOT raise this to 0.93 (-0.63 dBFS): MP3 is a lossy transform, so the
# decoded waveform can overshoot the encoded peak by up to ~0.6 dB on
# bass-heavy material. At 0.93 a lo-fi full render decoded to 0.990, tripping
# the QA headroom check (peak <= 0.99) with no actual clipping. -1.0 dBFS
# leaves enough room for the encoder while staying perceptually identical.
MASTER_CEIL = 0.89

# Additive spectra. HARM is the pad stack, SHIM the upper shimmer layer.
HARM = [1.0, 0.34, 0.17, 0.105, 0.065, 0.042]
SHIM = [1.0, 0.30, 0.13]

rng = np.random.default_rng(20261012)


def set_seed(seed):
    """Reseed the module RNG. Call before rendering to make a track reproducible."""
    global rng
    rng = np.random.default_rng(seed)
    return rng


# --------------------------------------------------------------- helpers
def bandpass(x, lo, hi):
    """Zero-phase brick-wall band filter via FFT. Fine for short noise bursts."""
    X = np.fft.rfft(x)
    f = np.fft.rfftfreq(len(x), 1.0 / SR)
    X[(f < lo) | (f > hi)] = 0.0
    return np.fft.irfft(X, len(x))


def midi2hz(m):
    return 440.0 * (2.0 ** ((m - 69) / 12.0))


_N = {'C': 0, 'C#': 1, 'Db': 1, 'D': 2, 'D#': 3, 'Eb': 3, 'E': 4, 'F': 5,
      'F#': 6, 'Gb': 6, 'G': 7, 'G#': 8, 'Ab': 8, 'A': 9, 'A#': 10, 'Bb': 10, 'B': 11}


def n2m(s):
    """Note name -> MIDI number.  n2m('A2') == 45, n2m('F#3') == 54."""
    s = s.strip()
    if len(s) >= 3 and s[1] in '#b':
        return 12 * (int(s[2:]) + 1) + _N[s[:2]]
    return 12 * (int(s[1:]) + 1) + _N[s[0]]


def bitcrush(x, bits=6):
    """Quantise amplitude to `bits` — the main source of chiptune grit."""
    lv = float(2 ** bits)
    return np.round(x * lv) / lv


def sr_crush(x, factor=3):
    """Sample-and-hold decimation, i.e. a fake lower sample rate."""
    n = len(x)
    idx = (np.arange(n) // factor) * factor
    return x[np.clip(idx, 0, n - 1)]


# --------------------------------------------------------------- instruments
def pad_chord(midis, dur, atk=0.8, rel=1.0, lfo_hz=0.11, det=0.0026):
    """Wide sustained pad. Low harmonics are tripled with +/- detune for width."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in midis:
        f = midi2hz(m)
        for h, a in enumerate(HARM, start=1):
            if h <= 2:
                for d in (-det, 0.0, det):
                    out += a * np.sin(2 * np.pi * f * h * (1 + d) * t)
            else:
                out += a * np.sin(2 * np.pi * f * h * t)
    out /= max((len(midis) ** 0.5) * 2.1, 1e-9)
    e = np.ones(n)
    a = min(int(atk * SR), n)
    e[:a] *= np.linspace(0, 1, a) ** 1.4
    r = min(int(rel * SR), n)
    e[n - r:] *= np.linspace(1, 0, r) ** 1.1
    return out * e * (1 + 0.05 * np.sin(2 * np.pi * lfo_hz * t + midis[0]))


def shimmer_chord(midis, dur, atk=1.1, rel=1.2, gain=1.0):
    """Glassier upper-octave layer that sits behind the pad."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    out = np.zeros(n)
    for m in midis:
        f = midi2hz(m) * 2.0
        for h, a in enumerate(SHIM, start=1):
            out += a * np.sin(2 * np.pi * f * h * t)
    out /= max((len(midis) ** 0.5) * 2.4, 1e-9)
    e = np.ones(n)
    a = min(int(atk * SR), n)
    e[:a] *= np.linspace(0, 1, a) ** 1.3
    r = min(int(rel * SR), n)
    e[n - r:] *= np.linspace(1, 0, r) ** 1.1
    return out * e * gain


def bell(m, dur=2.0, amp=1.0):
    """Bell/celesta. The 2.756 / 5.404 ratios are what make it read as metal."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi2hz(m)
    out = (np.sin(2 * np.pi * f * t) * np.exp(-t * 2.6)
           + 0.36 * np.sin(2 * np.pi * f * 2.756 * t) * np.exp(-t * 5.5)
           + 0.16 * np.sin(2 * np.pi * f * 5.404 * t) * np.exp(-t * 9.0))
    k = int(0.005 * SR)
    out[:k] *= np.linspace(0, 1, k)
    return out * amp / 1.5


def blip(m, dur=0.20, amp=0.55, crush=6):
    """Square/triangle hybrid, bitcrushed and decimated -> 8-bit lead."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi2hz(m)
    ph = (t * f) % 1.0
    tri = 2 * np.abs(2 * ph - 1) - 1
    sq = np.sign(np.sin(2 * np.pi * f * t))
    out = sr_crush(bitcrush(0.6 * tri + 0.4 * sq, crush), 3)
    e = np.exp(-t * 10.0)
    k = int(0.002 * SR)
    e[:k] *= np.linspace(0, 1, k)
    return out * e * amp


def rhodes(m, dur=2.6, amp=1.0):
    """Electric piano. Near-integer partials + a 4.6 Hz tremolo."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi2hz(m)
    out = (np.sin(2 * np.pi * f * t) * np.exp(-t * 1.5)
           + 0.42 * np.sin(2 * np.pi * f * 2.001 * t) * np.exp(-t * 3.4)
           + 0.20 * np.sin(2 * np.pi * f * 3.0 * t) * np.exp(-t * 6.0)
           + 0.11 * np.sin(2 * np.pi * f * 4.0 * t) * np.exp(-t * 9.0)
           + 0.06 * np.sin(2 * np.pi * f * 6.0 * t) * np.exp(-t * 14.0))
    k = int(0.004 * SR)
    out[:k] *= np.linspace(0, 1, k)
    return out * (1 + 0.06 * np.sin(2 * np.pi * 4.6 * t)) * amp / 1.8


def sub_bass(m, dur, amp=0.34):
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = midi2hz(m)
    out = np.sin(2 * np.pi * f * t) + 0.16 * np.sin(2 * np.pi * f * 2 * t)
    e = np.ones(n)
    a = min(int(0.03 * SR), n)
    e[:a] = np.linspace(0, 1, a)
    r = min(int(0.22 * SR), n)
    e[n - r:] *= np.linspace(1, 0, r)
    return out * e * amp


def kick(amp=1.0, dur=0.52, f_hi=130.0, f_lo=48.0, dec=7.5):
    """Sine with an exponential pitch sweep 130 -> 48 Hz, plus a noise click."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    f = f_lo + f_hi * np.exp(-t * 28.0)
    ph = 2 * np.pi * np.cumsum(f) / SR
    body = np.sin(ph) * np.exp(-t * dec)
    click = rng.standard_normal(n) * np.exp(-t * 300.0) * 0.13
    return (body + click) * amp


def clap(amp=0.5, dur=0.40, lo=900, hi=5200, dec=45.0):
    """Three offset noise bursts through a band-pass — the classic clap trick."""
    n = int(dur * SR)
    t = np.arange(n) / SR
    e = np.zeros(n)
    for o, g in ((0.0, 1.0), (0.009, 0.8), (0.019, 0.6)):
        e += g * np.exp(-np.maximum(t - o, 0) * dec) * (t >= o)
    return bandpass(rng.standard_normal(n), lo, hi) * e * amp


def hat(amp=0.28, dur=0.055, open_=False):
    d = dur * (7 if open_ else 1)
    n = int(d * SR)
    x = bandpass(rng.standard_normal(n), 7500, 17000)
    return x * np.exp(-np.arange(n) / SR / (d / 3.4)) * amp


# --------------------------------------------------------------- noise beds
def air_layer(n, amp=0.085):
    """Slow-breathing high noise that gives the mix 'room'."""
    x = bandpass(rng.standard_normal(n), 3000, 15000)
    t = np.arange(n) / SR
    return x * (0.55 + 0.45 * np.sin(2 * np.pi * 0.037 * t)) * amp


def vinyl(n, rate=42.0, amp=0.055, dur=0.004):
    """Vinyl crackle: short decaying noise bursts at `rate` per second."""
    out = np.zeros(n)
    cnt = int(rate * n / SR)
    if cnt <= 0:
        return out
    L = int(dur * SR)
    seg = rng.standard_normal((cnt, L)) * np.exp(-np.arange(L) / (0.0011 * SR))
    pos = rng.integers(0, max(n - L, 1), cnt)
    for i in range(cnt):
        p = pos[i]
        out[p:p + L] += seg[i]
    return out * amp


def hiss(n, amp=0.006):
    """Tape hiss."""
    return bandpass(rng.standard_normal(n), 250, 9000) * amp


# --------------------------------------------------------------- fx
def make_ir(seconds=2.5, decay=2.3, pre=0.018, damp=6500):
    """Synthesise a reverb impulse response: decaying noise, band-limited."""
    n = int(seconds * SR)
    ir = rng.standard_normal(n) * np.exp(-np.arange(n) / SR / (seconds / decay))
    ir[:int(pre * SR)] = 0.0
    ir = bandpass(ir, 130.0, damp)
    return ir / (np.sqrt(np.sum(ir ** 2)) + 1e-9)


def conv(x, ir):
    """FFT convolution."""
    n = len(x) + len(ir) - 1
    N = 1 << (n - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * np.fft.rfft(ir, N), N)[:n]


def pingpong(src, t_l, fb, mix, taps=5):
    """Alternating left/right delay taps with feedback gain `fb`."""
    d = int(t_l * SR)
    n = len(src)
    L = np.zeros(n)
    R = np.zeros(n)
    g = 1.0
    for k in range(1, taps + 1):
        idx = k * d
        if idx >= n:
            break
        g *= fb
        seg = src[:n - idx] * g
        if k % 2:
            L[idx:] += seg
        else:
            R[idx:] += seg
    return L * mix, R * mix


# --------------------------------------------------------------- measurement
def welch_fracs(x, frame=16384, hop=None):
    """Fraction of energy per band, using an averaged (Welch) PSD.

    A single-frame FFT is not trustworthy on music — it is dominated by whatever
    transient happens to sit in that frame. Always average.
    """
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


def eq_curve(fr, fracs, targets, max_db=8.0):
    """Log-interpolated correction curve, clamped to +/- max_db."""
    g = np.sqrt(np.array(targets) / (np.array(fracs) + 1e-30))
    db = np.clip(20 * np.log10(g + 1e-30), -max_db, max_db)
    g = 10 ** (db / 20.0)
    centers = np.array([math.sqrt(lo * hi) for lo, hi in BANDS])
    return np.interp(np.log10(np.maximum(fr, 15.0)), np.log10(centers),
                     g, left=g[0], right=g[-1])


def apply_curve(x, curve):
    N = 1 << (len(x) - 1).bit_length()
    return np.fft.irfft(np.fft.rfft(x, N) * curve, N)[:len(x)]


def auto_balance(L, R, targets, iters=5, verbose=True):
    """Iteratively EQ the mix until the band balance matches `targets`.

    Only the bands that already carry energy can be moved. If a band measures
    0.0% it means nothing was ever generated there — boosting it just raises
    whatever noise floor exists. Fix that in the arrangement, not here.
    Never returns -inf: the correction is capped at max_db per iteration.
    """
    N = 1 << (max(len(L), len(R)) - 1).bit_length()
    fr = np.fft.rfftfreq(N, 1 / SR)
    for it in range(iters):
        f0 = welch_fracs(0.5 * (L + R))
        if verbose:
            _log("    iter %d  frac=%s" % (it + 1, " ".join("%4.1f" % (100 * v) for v in f0)))
        need = 20 * np.log10(np.sqrt(np.array(targets) / (f0 + 1e-30)) + 1e-30)
        if np.max(np.abs(need)) < 0.8:
            break
        curve = eq_curve(fr, f0, targets)
        L = apply_curve(L, curve)
        R = apply_curve(R, curve)
    return L, R


# --------------------------------------------------------------- engine
_LOG = []


def _log(s):
    _LOG.append(str(s))


class Track:
    """Stereo accumulator. `add()` places a mono signal at time t with a pan."""

    def __init__(self, seconds):
        self.n = int(seconds * SR)
        self.L = np.zeros(self.n)
        self.R = np.zeros(self.n)

    def add(self, sig, t, pan=0.0, gain=1.0):
        i = int(t * SR)
        if i >= self.n:
            return
        m = min(len(sig), self.n - i)
        a = (pan + 1) * math.pi / 4
        self.L[i:i + m] += sig[:m] * math.cos(a) * gain
        self.R[i:i + m] += sig[:m] * math.sin(a) * gain


def noise_envelope(arr, bar, n):
    """Per-bar gain for the noise beds, cross-faded so it never steps abruptly.

    The region past the last bar (the ring-out tail) keeps the last value.
    """
    g = [float(s.get('noise', 1.0)) for s in arr]
    env = np.full(n, g[-1] if g else 1.0)
    bl = int(round(bar * SR))
    ramp = int(0.6 * SR)
    for i, bi in enumerate(range(len(g))):
        i0 = i * bl
        if i0 >= n:
            break
        i1 = min(i0 + bl, n)
        cur = g[bi]
        prev = g[bi - 1] if bi > 0 else cur
        seg = np.full(i1 - i0, cur)
        r = min(ramp, i1 - i0)
        if r > 0:
            seg[:r] = np.linspace(prev, cur, r)
        env[i0:i1] = seg
    return env


def render(v, verbose=True):
    """Render one track spec to interleaved int16 stereo. Returns (samples, n).

    v keys: bpm prog arr chord_bars loop + the per-instrument and fx overrides
    documented in presets.py.
    """
    global _LOG
    _LOG = []
    bpm = v['bpm']
    spb = 60.0 / bpm
    bar = 4 * spb
    arr = v['arr']
    BARS = len(arr)
    LOOP = v.get('loop', True)
    # Extra time rendered past the end: for a loop this is the reverb tail that
    # gets folded back onto the head; for a one-shot it is the natural ring-out.
    tail = 3.2 if LOOP else 5.0
    total = BARS * bar + tail

    tr = Track(total)
    prog = [[n2m(x) for x in ch] for ch in v['prog']]
    nch = len(prog)
    chord_bars = v.get('chord_bars', 2)
    assert BARS % (nch * chord_bars) == 0, 'bars must be whole chord cycles'

    padsend, shimsend, bellsend = [], [], []

    for b in range(BARS):
        t0 = b * bar
        ch = prog[(b // chord_bars) % nch]
        s = arr[b]

        if b % chord_bars == 0:
            dur = bar * chord_bars + 1.2
            padsend.append((pad_chord(ch, dur, atk=v.get('pad_atk', 0.85), rel=1.1,
                                      lfo_hz=v.get('pad_lfo', 0.11)), t0))
            shimsend.append((shimmer_chord(ch, dur,
                                           atk=v.get('pad_atk', 0.85) * 1.3, rel=1.2), t0))

        if s.get('bass'):
            tr.add(sub_bass(ch[0] - 12, bar * 0.96, amp=v.get('bass_amp', 0.34)), t0)

        if s.get('rhodes'):
            for j, m in enumerate(ch):
                tr.add(rhodes(m, dur=bar * 1.6, amp=v.get('rhodes_amp', 0.55)),
                       t0 + 0.02 * j, pan=(-0.35 + 0.22 * j))

        if s.get('lead'):
            steps = s.get('lead_div', v.get('arp_div', 8))
            step = spb * (4.0 / steps)
            pool = sorted(ch) + [sorted(ch)[0] + 12, sorted(ch)[1] + 12]
            oct_ = v.get('arp_oct', 12)
            lscale = s.get('lead_scale', 1.0)
            for k in range(steps):
                m = pool[(k + b * (1 if steps == 8 else 3)) % len(pool)] + oct_
                sig = (blip(m, amp=v.get('lead_amp', 0.55) * lscale)
                       if v.get('lead_kind') == 'blip'
                       else bell(m, amp=v.get('lead_amp', 0.85) * lscale))
                vel = 0.80 + 0.26 * ((k * 5 + b * 3) % 7) / 6.0
                # glitch: drop the last 16th of every 4th step now and then
                if steps == 16 and k % 4 == 3 and v.get('glitch') and (b + k) % 5 == 0:
                    continue
                tr.add(sig, t0 + k * step, pan=v.get('lead_pan', 0.16), gain=vel)
                if steps == 8:
                    bellsend.append((sig, t0 + k * step))

        kb = s.get('kick_beats')
        if kb:
            for beat in kb:
                tr.add(kick(amp=v.get('kick_amp', 0.55), f_lo=v.get('kick_lo', 48.0),
                            dec=v.get('kick_dec', 7.5)), t0 + beat * spb)
        if s.get('clap'):
            for beat in (1, 3):
                tr.add(clap(amp=v.get('clap_amp', 0.30)), t0 + beat * spb, pan=0.06)
        if s.get('hat'):
            for k in range(8):
                if k % 2 == 1:
                    tr.add(hat(amp=v.get('hat_amp', 0.20)), t0 + k * spb / 2.0, pan=0.30)
        if s.get('hat16'):
            for k in range(16):
                if k in (2, 6, 10, 14):
                    tr.add(hat(amp=v.get('hat16_amp', 0.10)), t0 + k * spb / 4.0, pan=-0.30)

        if s.get('sparkle'):
            for k in range(s.get('sparkle_n', v.get('sparkle_n', 2))):
                m = ch[(k + b) % len(ch)] + 24 + (12 if (b + k) % 3 == 0 else 0)
                tr.add(bell(m, dur=1.6, amp=v.get('sparkle_amp', 0.12)),
                       t0 + ((b * 3 + k * 5) % 4) * spb + 0.19, pan=0.45 - 0.25 * k)

    for p, t0 in padsend:
        tr.add(p, t0, pan=0.0, gain=v.get('pad_gain', 0.9))
    for p, t0 in shimsend:
        tr.add(p, t0, pan=0.25, gain=v.get('shim_gain', 0.30))
        tr.add(p, t0 + 0.013, pan=-0.25, gain=v.get('shim_gain', 0.30) * 0.8)

    # ---------------- reverb + delay on the MUSICAL bus only
    dry = 0.5 * (tr.L + tr.R)
    ir = make_ir(seconds=v.get('rev_t', 2.6), decay=v.get('rev_decay', 2.3),
                 damp=v.get('rev_damp', 9000))
    wet = conv(dry, ir)[:tr.n] * v.get('rev_mix', 0.34)
    wet2 = conv(0.5 * (tr.L - tr.R), ir)[:tr.n] * v.get('rev_mix', 0.34)
    tr.L += wet + wet2 * 0.7
    tr.R += wet - wet2 * 0.7

    bsrc = np.zeros(tr.n)
    for sig, t0 in bellsend:
        i = int(t0 * SR)
        if i >= tr.n:
            continue
        m = min(len(sig), tr.n - i)
        bsrc[i:i + m] += sig[:m] * 0.9
    dl, dr = pingpong(bsrc, v.get('dly_t', 0.34), v.get('dly_fb', 0.40),
                      v.get('dly_mix', 0.26))
    tr.L += dl
    tr.R += dr

    # ---------------- loop fold (musical bus only)
    if LOOP:
        loop_n = int(BARS * bar * SR)
        xl, xr = tr.L.copy(), tr.R.copy()
        extra = len(xl) - loop_n
        if extra > 0:
            xl[:extra] += xl[loop_n:]
            xr[:extra] += xr[loop_n:]
        xl, xr = xl[:loop_n], xr[:loop_n]
        out_n = loop_n
    else:
        xl, xr = tr.L.copy(), tr.R.copy()
        out_n = len(xl)

    # ---------------- noise beds AFTER the fold, with a section envelope
    # This ordering is load-bearing. If the continuous noise beds are mixed in
    # before the fold, the last few seconds of noise get added onto the first
    # few seconds and the opening noise floor rises by ~3 dB (sqrt(2)).
    env = noise_envelope(arr, bar, out_n)
    if env.shape[0] > out_n:
        env = env[:out_n]
    air = air_layer(out_n, amp=v.get('air_amp', 0.085)) * env
    xl += air * 0.9
    xr += air * 1.1
    xl += vinyl(out_n, amp=v.get('vinyl_amp', 0.0)) * env
    xr += vinyl(out_n, amp=v.get('vinyl_amp', 0.0)) * env
    xl += hiss(out_n, amp=v.get('hiss_amp', 0.0)) * env
    xr += hiss(out_n, amp=v.get('hiss_amp', 0.0)) * env

    xl, xr = auto_balance(xl, xr, v['targets'], verbose=verbose)

    # ---------------- master
    peak = max(np.abs(xl).max(), np.abs(xr).max()) + 1e-9
    xl, xr = xl / peak, xr / peak
    drive = 1.15
    xl = np.tanh(xl * drive) / np.tanh(drive)
    xr = np.tanh(xr * drive) / np.tanh(drive)
    xl *= MASTER_CEIL / (np.abs(xl).max() + 1e-9)
    xr *= MASTER_CEIL / (np.abs(xr).max() + 1e-9)

    # -------- boundary treatment
    # For a LOOP the tail was already folded onto the head, so the waveform is
    # continuous across the junction on its own. Any fade here would only punch
    # an audible level notch into every repeat -> seam_ramp defaults to 0 for
    # looping renders. One-shots get a 12 ms soft start plus a musical fade-out.
    sr_ramp = v.get('seam_ramp', 0.0 if LOOP else 0.012)
    k = int(sr_ramp * SR)
    if k > 0:
        ramp = np.linspace(0, 1, k)
        xl[:k] *= ramp
        xr[:k] *= ramp
    if LOOP:
        if k > 0:
            xl[-k:] *= ramp[::-1]
            xr[-k:] *= ramp[::-1]
    else:
        fo = int(v.get('fade_out', 5.0) * SR)
        fo = min(fo, out_n)
        curve = np.linspace(1, 0, fo) ** 1.8
        xl[out_n - fo:] *= curve
        xr[out_n - fo:] *= curve

    st = np.empty(out_n * 2, dtype=np.int16)
    st[0::2] = np.clip(xl * 32767, -32768, 32767).astype(np.int16)
    st[1::2] = np.clip(xr * 32767, -32768, 32767).astype(np.int16)
    if verbose:
        for line in _LOG:
            print(line)
    return st, out_n


# --------------------------------------------------------------- output
def write_wav(path, st):
    os.makedirs(os.path.dirname(os.path.abspath(path)) or '.', exist_ok=True)
    with wave.open(path, 'wb') as f:
        f.setnchannels(2)
        f.setsampwidth(2)
        f.setframerate(SR)
        f.writeframes(st.tobytes())
    return path


def encode_mp3(wav_path, mp3_path, title=None, artist='', album='', bitrate='192k'):
    """WAV -> MP3 via ffmpeg/libmp3lame. Returns True on success."""
    os.makedirs(os.path.dirname(os.path.abspath(mp3_path)) or '.', exist_ok=True)
    cmd = ['ffmpeg', '-y', '-loglevel', 'error', '-i', wav_path,
           '-codec:a', 'libmp3lame', '-b:a', bitrate]
    if artist:
        cmd += ['-metadata', 'artist=%s' % artist]
    if album:
        cmd += ['-metadata', 'album=%s' % album]
    if title:
        cmd += ['-metadata', 'title=%s' % title]
    cmd.append(mp3_path)
    r = subprocess.run(cmd, capture_output=True, text=True)
    if r.returncode != 0:
        raise RuntimeError('ffmpeg failed: %s' % r.stderr[:400])
    return True


def render_to_files(v, outdir, stem=None, as_wav=True, as_mp3=True,
                    artist='', album='', keep_intermediate_wav=True):
    """Render a spec and write <outdir>/<stem>.wav / .mp3. Returns a dict."""
    st, n = render(v)
    stem = stem or v.get('name', 'track').replace('/', '-')
    out = {'duration': n / SR, 'wav': None, 'mp3': None, 'n': n}
    wav_path = os.path.join(outdir, stem + '.wav')
    if as_wav or as_mp3:
        write_wav(wav_path, st)
    if as_wav:
        out['wav'] = wav_path
    if as_mp3:
        mp3_path = os.path.join(outdir, stem + '.mp3')
        encode_mp3(wav_path, mp3_path, title=stem, artist=artist, album=album)
        out['mp3'] = mp3_path
    if not keep_intermediate_wav and not as_wav:
        try:
            os.remove(wav_path)
        except OSError:
            pass
    return out
