#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Style presets for the procedural engine.

A preset is a dict with:
  label      human name
  blurb      one-line description
  base       the render spec (bpm, key, chord progression, mix + fx values)
  loop       an 8-bar arrangement spec, expanded to N bars for looping renders
  full       a [(n_bars, spec), ...] section list for full-length renders

Arrange with `pat8()` / `sections()`; render with synth_engine.render(build(...)).
"""
from __future__ import annotations

# --------------------------------------------------------------- arrangement
def _expand(k, val, i):
    """Resolve one arrangement value for bar offset `i`.

    kick_beats is special: a plain list means the same beats in every bar, a
    list of lists means a different kick pattern per bar. Every other list is
    treated as a repeating per-bar pattern whose period is len(val).
    """
    if k == 'kick_beats':
        if isinstance(val, (list, tuple)):
            if val and isinstance(val[0], (list, tuple)):
                return list(val[i % len(val)])
            return list(val)
        return val
    if isinstance(val, (list, tuple)):
        if not val:
            return val
        return val[i % len(val)]
    return val


def _expand_spec(spec, i):
    return {k: _expand(k, v, i) for k, v in spec.items()}


def pat8(spec, bars=None):
    """Expand a period-8 spec into a per-bar list of `bars` entries."""
    spec = dict(spec)                      # never mutate the caller's dict
    bars = bars if bars is not None else spec.pop('_bars', 16)
    spec.pop('_bars', None)
    return [_expand_spec(spec, b) for b in range(bars)]


def sections(seq):
    """[(n_bars, spec), ...] -> flat per-bar list. Patterns repeat per section."""
    out = []
    for cnt, spec in seq:
        for i in range(cnt):
            out.append(_expand_spec(spec, i))
    return out


# --------------------------------------------------------------- shared specs
LOOP_SPEC_BEATY = dict(
    bass=True, lead=True, sparkle=True,
    kick_beats=[0, 2],
    hat=[0, 0, 1, 1, 1, 1, 1, 1],
    clap=[0, 0, 1, 1, 1, 1, 1, 1],
    hat16=[0, 0, 0, 0, 0, 0, 1, 1],
)
LOOP_SPEC_SPARSE = dict(
    bass=True, lead=True, sparkle=True,
    kick_beats=[0], hat=[0, 0, 0, 1, 0, 0, 0, 1], clap=False,
)
LOOP_SPEC_DRUMLESS = dict(
    bass=True, rhodes=True,
    lead=[0, 0, 1, 1, 0, 0, 1, 1], lead_div=8,
    sparkle=[0, 0, 0, 0, 1, 1, 1, 1],
    kick_beats=[], hat=False, clap=False,
)

# --------------------------------------------------------------- presets
PRESETS = {}

# ---- 1. Y2K dreamy -------------------------------------------------------
PRESETS['y2k-dreamy'] = dict(
    label='Y2K Dreamy',
    blurb='Soft pad bed plus bell arpeggios. Warm, nostalgic, slightly sweet.',
    base=dict(
        bpm=88, key_name='D major', chord_bars=2,
        prog=[['D3', 'A3', 'F#4', 'C#5', 'E5'], ['B2', 'F#3', 'D4', 'A4', 'C#5'],
              ['G2', 'D3', 'B3', 'F#4', 'A4'], ['A2', 'E3', 'C#4', 'F#4', 'B4']],
        lead_kind='bell', arp_div=8, arp_oct=12, lead_amp=1.05, lead_pan=0.18,
        pad_gain=0.95, shim_gain=0.30, bass_amp=0.30,
        kick_amp=0.55, clap_amp=0.30, hat_amp=0.21, hat16_amp=0.10,
        rev_t=2.6, rev_mix=0.32, rev_damp=10000,
        dly_t=0.34, dly_fb=0.40, dly_mix=0.24,
        air_amp=0.085, vinyl_amp=0.018, hiss_amp=0.004, sparkle_amp=0.13,
        targets=[0.25, 0.30, 0.26, 0.14, 0.05],
    ),
    loop=LOOP_SPEC_BEATY,
    full=sections([
        (8,  dict(bass=[0, 1, 1, 1, 1, 1, 1, 1], lead=[0, 0, 0, 0, 1, 1, 1, 1],
                  lead_div=8, lead_scale=0.62, sparkle=True, sparkle_n=2,
                  kick_beats=[], hat=False, hat16=False, clap=False, noise=0.45)),
        (8,  dict(bass=True, lead=True, lead_div=8, lead_scale=0.90, sparkle=True,
                  kick_beats=[0], hat=False, hat16=False, clap=False, noise=0.80)),
        (16, dict(bass=True, lead=True, lead_div=8, sparkle=True,
                  kick_beats=[0, 2], hat=[0, 0, 1, 1, 1, 1, 1, 1],
                  clap=[0, 0, 1, 1, 1, 1, 1, 1],
                  hat16=[0, 0, 0, 0, 0, 0, 1, 1], noise=1.00)),
        (8,  dict(bass=True, lead=True, lead_div=4, lead_scale=0.80, sparkle=True,
                  sparkle_n=3, kick_beats=[], hat=False, hat16=False,
                  clap=False, noise=0.60)),
        (16, dict(bass=True, lead=True, lead_div=8, sparkle=True, sparkle_n=3,
                  kick_beats=[0, 2], hat=[0, 0, 1, 1, 1, 1, 1, 1],
                  clap=[0, 0, 1, 1, 1, 1, 1, 1],
                  hat16=[0, 0, 0, 0, 0, 0, 1, 1], noise=1.00)),
        (8,  dict(bass=True, lead=[1, 1, 1, 1, 0, 0, 0, 0], lead_div=8,
                  lead_scale=0.70, sparkle=[0, 0, 1, 1, 1, 1, 1, 1],
                  kick_beats=[], hat=False, hat16=False, clap=False, noise=0.70)),
    ]),
)

# ---- 2. Y2K nocturnal ----------------------------------------------------
PRESETS['y2k-nocturnal'] = dict(
    label='Y2K Nocturnal',
    blurb='Minor, slower and deeper. Thick low end, long reverb, sparse drums.',
    base=dict(
        bpm=85, key_name='B minor', chord_bars=2,
        prog=[['B2', 'F#3', 'D4', 'A4', 'C#5'], ['G2', 'D3', 'B3', 'F#4', 'A4'],
              ['E2', 'B2', 'G3', 'D4', 'F#4'], ['A2', 'E3', 'C#4', 'G4', 'B4']],
        lead_kind='bell', arp_div=8, arp_oct=24, lead_amp=0.78, lead_pan=-0.22,
        pad_gain=1.05, shim_gain=0.22, pad_atk=1.25, pad_lfo=0.07, bass_amp=0.34,
        kick_amp=0.46, kick_lo=44.0, kick_dec=6.0, hat_amp=0.10,
        rev_t=3.6, rev_mix=0.42, rev_damp=7000, rev_decay=2.6,
        dly_t=0.47, dly_fb=0.46, dly_mix=0.30,
        air_amp=0.055, vinyl_amp=0.012, hiss_amp=0.0045, sparkle_amp=0.11,
        targets=[0.30, 0.32, 0.24, 0.11, 0.03],
    ),
    loop=LOOP_SPEC_SPARSE,
    full=sections([
        (8,  dict(bass=[0, 1, 1, 1, 1, 1, 1, 1], lead=[0, 0, 0, 0, 0, 0, 1, 1],
                  lead_div=4, lead_scale=0.55, sparkle=True, sparkle_n=1,
                  kick_beats=[], hat=False, hat16=False, clap=False, noise=0.40)),
        (16, dict(bass=True, lead=True, lead_div=8, sparkle=True, sparkle_n=2,
                  kick_beats=[0], hat=[0, 0, 0, 1, 0, 0, 0, 1], clap=False, noise=0.80)),
        (16, dict(bass=True, lead=True, lead_div=8, sparkle=True, sparkle_n=2,
                  kick_beats=[0, 2], hat=[0, 0, 0, 1, 0, 0, 0, 1],
                  clap=[0, 0, 0, 1, 0, 0, 0, 1], noise=1.00)),
        (8,  dict(bass=True, lead=[1, 1, 1, 1, 0, 0, 0, 0], lead_div=4,
                  lead_scale=0.50, sparkle=True, sparkle_n=3,
                  kick_beats=[], hat=False, hat16=False, clap=False, noise=0.55)),
        (16, dict(bass=True, lead=True, lead_div=8, sparkle=True, sparkle_n=3,
                  kick_beats=[0, 2], hat=[0, 0, 0, 1, 0, 0, 0, 1],
                  clap=[0, 0, 0, 1, 0, 0, 0, 1], noise=1.00)),
    ]),
)

# ---- 3. Y2K digital ------------------------------------------------------
PRESETS['y2k-digital'] = dict(
    label='Y2K Digital',
    blurb='Bitcrushed square/triangle arpeggio with occasional glitch drops.',
    base=dict(
        bpm=93, key_name='A major', chord_bars=2,
        prog=[['A2', 'E3', 'C#4', 'G#4', 'B4'], ['F#2', 'C#3', 'A3', 'E4', 'G#4'],
              ['D3', 'A3', 'F#4', 'C#5', 'E5'], ['E2', 'B2', 'G#3', 'D4', 'F#4']],
        lead_kind='blip', arp_div=16, arp_oct=12,
        lead_amp=0.62, lead_pan=0.20, glitch=True,
        pad_gain=0.62, shim_gain=0.28, bass_amp=0.28,
        kick_amp=0.52, clap_amp=0.28, hat_amp=0.18, hat16_amp=0.10,
        rev_t=2.0, rev_mix=0.24, rev_damp=11000,
        dly_t=0.258, dly_fb=0.38, dly_mix=0.28,
        air_amp=0.085, vinyl_amp=0.008, hiss_amp=0.003, sparkle_amp=0.12,
        targets=[0.22, 0.28, 0.28, 0.17, 0.05],
    ),
    loop=LOOP_SPEC_BEATY,
    full=sections([
        (8,  dict(bass=[0, 1, 1, 1, 1, 1, 1, 1], lead=[0, 0, 0, 0, 1, 1, 1, 1],
                  lead_div=8, lead_scale=0.62, sparkle=True, sparkle_n=2,
                  kick_beats=[], hat=False, hat16=False, clap=False, noise=0.45)),
        (8,  dict(bass=True, lead=True, lead_div=16, lead_scale=0.90, sparkle=True,
                  kick_beats=[0], hat=False, hat16=False, clap=False, noise=0.80)),
        (16, dict(bass=True, lead=True, lead_div=16, sparkle=True,
                  kick_beats=[0, 2], hat=[0, 0, 1, 1, 1, 1, 1, 1],
                  clap=[0, 0, 1, 1, 1, 1, 1, 1],
                  hat16=[0, 0, 0, 0, 0, 0, 1, 1], noise=1.00)),
        (8,  dict(bass=True, lead=[1, 1, 1, 1, 1, 1, 1, 1], lead_div=8, lead_scale=0.85,
                  sparkle=True, sparkle_n=3, kick_beats=[], hat=False, hat16=False,
                  clap=False, noise=0.60)),
        (16, dict(bass=True, lead=True, lead_div=16, sparkle=True, sparkle_n=3,
                  kick_beats=[0, 2], hat=[0, 0, 1, 1, 1, 1, 1, 1],
                  clap=[0, 0, 1, 1, 1, 1, 1, 1],
                  hat16=[0, 0, 0, 0, 0, 0, 1, 1], noise=1.00)),
        (8,  dict(bass=True, lead=[1, 1, 1, 1, 0, 0, 0, 0], lead_div=8, lead_scale=0.70,
                  sparkle=[0, 0, 1, 1, 1, 1, 1, 1], kick_beats=[], hat=False,
                  hat16=False, clap=False, noise=0.70)),
    ]),
)

# ---- 4. Lo-fi minimal ----------------------------------------------------
PRESETS['lofi-minimal'] = dict(
    label='Lo-fi Minimal',
    blurb='Almost drumless: electric piano, tape hiss and vinyl crackle.',
    base=dict(
        bpm=90, key_name='F major', chord_bars=2,
        prog=[['F3', 'C4', 'A4', 'E5', 'G5'], ['D3', 'A3', 'F4', 'C5', 'E5'],
              ['A#2', 'F3', 'D4', 'A4', 'C5'], ['C3', 'G3', 'E4', 'A4', 'D5']],
        lead_kind='bell', arp_div=8, arp_oct=12, lead_amp=0.55, lead_pan=0.10,
        pad_gain=0.90, shim_gain=0.26, bass_amp=0.28, rhodes_amp=0.58,
        rev_t=2.4, rev_mix=0.31, rev_damp=9000,
        dly_t=0.333, dly_fb=0.36, dly_mix=0.22,
        air_amp=0.075, vinyl_amp=0.050, hiss_amp=0.009, sparkle_amp=0.12,
        targets=[0.22, 0.34, 0.28, 0.13, 0.03],
    ),
    loop=LOOP_SPEC_DRUMLESS,
    full=sections([
        (8,  dict(bass=[0, 1, 1, 1, 1, 1, 1, 1], rhodes=True, lead=0,
                  sparkle=[0, 0, 0, 0, 1, 1, 1, 1], sparkle_n=2,
                  kick_beats=[], hat=False, hat16=False, clap=False)),
        (8,  dict(bass=True, rhodes=True, lead=[0, 0, 0, 0, 1, 1, 1, 1], lead_div=8,
                  lead_scale=0.70, sparkle=True, sparkle_n=2,
                  kick_beats=[], hat=False, hat16=False, clap=False)),
        (16, dict(bass=True, rhodes=True, lead=True, lead_div=8, lead_scale=1.00,
                  sparkle=True, sparkle_n=3,
                  kick_beats=[], hat=False, hat16=False, clap=False)),
        (8,  dict(bass=True, rhodes=True, lead=[1, 1, 1, 1, 1, 1, 1, 1], lead_div=4,
                  lead_scale=0.60, sparkle=[0, 0, 1, 1, 1, 1, 1, 1], sparkle_n=3,
                  kick_beats=[], hat=False, hat16=False, clap=False)),
        (16, dict(bass=True, rhodes=True, lead=True, lead_div=8, lead_scale=1.12,
                  sparkle=True, sparkle_n=4,
                  kick_beats=[], hat=False, hat16=False, clap=False)),
        (8,  dict(bass=True, rhodes=True, lead=[1, 1, 1, 1, 0, 0, 0, 0], lead_div=8,
                  lead_scale=0.60, sparkle=[0, 0, 1, 1, 1, 1, 1, 1], sparkle_n=2,
                  kick_beats=[], hat=False, hat16=False, clap=False)),
    ]),
)

# ---- 5. Ambient drift ----------------------------------------------------
PRESETS['ambient-drift'] = dict(
    label='Ambient Drift',
    blurb='Very slow, drumless, wide. Dark low end, almost no attack.',
    base=dict(
        bpm=68, key_name='C major', chord_bars=4, prog=[
            ['C2', 'G3', 'E4', 'B4', 'D5'], ['A2', 'E3', 'C4', 'G4', 'B4'],
            ['F2', 'C3', 'A3', 'E4', 'G4'], ['G2', 'D3', 'B3', 'F#4', 'A4']],
        lead_kind='bell', arp_div=4, arp_oct=12, lead_amp=0.40, lead_pan=0.30,
        pad_atk=2.0, pad_lfo=0.05, pad_gain=1.10, shim_gain=0.34, bass_amp=0.30,
        rev_t=5.0, rev_mix=0.50, rev_damp=6000, rev_decay=2.8,
        dly_t=0.62, dly_fb=0.48, dly_mix=0.28,
        air_amp=0.070, vinyl_amp=0.006, hiss_amp=0.003, sparkle_amp=0.10,
        targets=[0.31, 0.33, 0.23, 0.10, 0.03],
    ),
    loop=dict(bass=True, lead=[0, 0, 0, 0, 1, 1, 1, 1], lead_div=4,
              sparkle=[0, 0, 0, 0, 1, 1, 1, 1], sparkle_n=2,
              kick_beats=[], hat=False, clap=False),
    full=sections([
        (8,  dict(bass=[0, 1, 1, 1, 1, 1, 1, 1], sparkle=True, sparkle_n=1,
                  kick_beats=[], hat=False, clap=False, noise=0.35)),
        (16, dict(bass=True, lead=[0, 0, 0, 0, 1, 1, 1, 1], lead_div=4,
                  sparkle=True, sparkle_n=2, kick_beats=[], hat=False, clap=False,
                  noise=0.75)),
        (16, dict(bass=True, lead=True, lead_div=4, sparkle=True, sparkle_n=3,
                  kick_beats=[], hat=False, clap=False, noise=1.00)),
        (8,  dict(bass=True, sparkle=True, sparkle_n=4, kick_beats=[], hat=False,
                  clap=False, noise=0.55)),
        (16, dict(bass=True, lead=True, lead_div=4, sparkle=True, sparkle_n=2,
                  kick_beats=[], hat=False, clap=False, noise=0.90)),
    ]),
)

# ---- 6. Chiptune playful -------------------------------------------------
PRESETS['chiptune-playful'] = dict(
    label='Chiptune Playful',
    blurb='Fast, bright 8-bit lead on top of a busy beat. Almost no reverb.',
    base=dict(
        bpm=118, key_name='G major', chord_bars=2, prog=[
            ['G2', 'D4', 'B4', 'G5', 'B5'], ['E2', 'B3', 'G4', 'E5', 'B5'],
            ['C3', 'G3', 'E4', 'C5', 'E5'], ['D3', 'A3', 'F#4', 'D5', 'F#5']],
        lead_kind='blip', arp_div=16, arp_oct=12, glitch=True,
        lead_amp=0.72, lead_pan=0.12,
        pad_gain=0.40, shim_gain=0.18, bass_amp=0.32,
        kick_amp=0.60, clap_amp=0.34, hat_amp=0.22, hat16_amp=0.14,
        rev_t=1.2, rev_mix=0.12, rev_damp=13000,
        dly_t=0.127, dly_fb=0.30, dly_mix=0.20,
        air_amp=0.030, vinyl_amp=0.0, hiss_amp=0.0, sparkle_amp=0.10,
        targets=[0.20, 0.26, 0.32, 0.18, 0.04],
    ),
    loop=dict(bass=True, lead=True, sparkle=True, kick_beats=[0, 2],
              hat=[0, 1, 1, 1, 1, 1, 1, 1], clap=[0, 1, 1, 1, 1, 1, 1, 1],
              hat16=True),
    full=sections([
        (8,  dict(bass=[0, 1, 1, 1, 1, 1, 1, 1], lead=[0, 0, 0, 0, 1, 1, 1, 1],
                  lead_div=8, lead_scale=0.70, sparkle=True, sparkle_n=1,
                  kick_beats=[0], hat=False, clap=False, noise=0.30)),
        (16, dict(bass=True, lead=True, lead_div=16, sparkle=True, sparkle_n=2,
                  kick_beats=[0, 2], hat=[0, 1, 1, 1, 1, 1, 1, 1],
                  clap=[0, 1, 1, 1, 1, 1, 1, 1], hat16=True, noise=1.00)),
        (8,  dict(bass=True, lead=True, lead_div=8, lead_scale=0.85, sparkle=True,
                  sparkle_n=3, kick_beats=[], hat=False, clap=False, noise=0.55)),
        (16, dict(bass=True, lead=True, lead_div=16, sparkle=True, sparkle_n=3,
                  kick_beats=[0, 2], hat=[0, 1, 1, 1, 1, 1, 1, 1],
                  clap=[0, 1, 1, 1, 1, 1, 1, 1], hat16=True, noise=1.00)),
        (8,  dict(bass=True, lead=[1, 1, 1, 1, 0, 0, 0, 0], lead_div=8,
                  lead_scale=0.70, sparkle=[0, 0, 1, 1, 1, 1, 1, 1],
                  kick_beats=[0], hat=False, clap=False, noise=0.60)),
    ]),
)


def list_presets():
    """Return [(name, label, blurb), ...]."""
    return [(k, v['label'], v['blurb']) for k, v in PRESETS.items()]


def build(name, bars=None, loop=True, clean=False, **overrides):
    """Turn a preset into a renderable spec.

    name     preset key, e.g. 'y2k-dreamy'
    bars     loop length in bars (default 24). Rounded to whole chord cycles.
    loop     True -> seamless loop render, False -> full-length arrangement.
    clean    drop all three noise beds and use seam_ramp=0. This is the setting
             to ship for a "pure / seamless" deliverable.
    """
    p = PRESETS[name]
    v = dict(p['base'])
    if loop:
        n = bars or 24
        cycle = len(v['prog']) * v.get('chord_bars', 2)
        if n % cycle:
            n += cycle - (n % cycle)
        arr = pat8(p['loop'], bars=n)
        v.update(arr=arr, loop=True)
    else:
        v.update(arr=p['full'], loop=False)
    if clean:
        v.update(air_amp=0.0, vinyl_amp=0.0, hiss_amp=0.0)
        if loop:
            v['seam_ramp'] = 0.0
    v.update(overrides)
    return v


if __name__ == '__main__':
    for k, label, blurb in list_presets():
        print('%-18s %-18s %s' % (k, label, blurb))
