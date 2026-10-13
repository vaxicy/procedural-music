# Synthesis cookbook

Every instrument in `scripts/synth_engine.py` is an additive sine stack with a
hand-written envelope. There is no wavetable, no sample, no soundfont. This file
explains *why* each harmonic recipe sounds like the instrument it is imitating,
so new sounds can be built the same way.

---

## Why additive

A harmonic series `[1.0, 0.34, 0.17, ...]` is a spectrum. Change the ratios and
you change the timbre; change the decay rate **per harmonic** and you change how
the note evolves. That is enough to cover everything this engine needs, and it
costs one `np.sin` per partial.

**Integer ratios** → harmonic, "musical": strings, organs, pads, square leads.
**Non-integer ratios** → inharmonic, "metallic": bells, gongs, cymbals, glass.
The further the ratios from integers, the less pitch you perceive and the more
you hear "material".

---

## The instruments

### `pad_chord(midis, dur, atk=0.8, rel=1.0, lfo_hz=0.11, det=0.0026)`

```
spectrum   HARM = [1.0, 0.34, 0.17, 0.105, 0.065, 0.042]   (6 partials)
width      harmonics 1–2 are tripled at ±0.26 % detune
motion     0.11 Hz amplitude LFO, phase-offset by the root note
```

The detuned triple is what makes it sound wide rather than thick — three
slightly-out-of-tune copies beat against each other slowly. The LFO is
deliberately below 0.2 Hz so it reads as "breathing" rather than as vibrato.
**Slow the LFO further (`pad_lfo=0.05`) for ambient; speed it up and the pad
starts to feel nervous.**

### `shimmer_chord(midis, dur, atk=1.1, rel=1.2, gain=1.0)`

An octave up with a 3-partial spectrum. Its job is the 2–8 kHz band: pads alone
leave a hole there, and the auto-balancer cannot fill a hole (§3 of
mixing-rules). Always send it with a small stereo offset — the engine adds it
twice, 13 ms apart, panned ±0.25.

### `bell(m, dur=2.0, amp=1.0)`

```
ratios  1 : 2.756 : 5.404   with decays 2.6 / 5.5 / 9.0
```

**2.756 and 5.404 are not integers on purpose.** They approximate the partial
ratios of a struck metal bar, which is why this reads as a bell/celesta instead
of an organ. The high partials must decay **faster** than the fundamental —
that is what "the strike" is. A short 5 ms attack ramp prevents a click.

### `rhodes(m, dur=2.6, amp=1.0)`

```
ratios  1 : 2.001 : 3 : 4 : 6   with decays 1.5 / 3.4 / 6 / 9 / 14
tremolo 0.06 depth at 4.6 Hz
```

The `2.001` is the trick: 1 Hz off a true octave at ~200 Hz gives the slow
beating that electric pianos have. Keep the ratios near-integer here — you want
the note to have clear pitch, unlike the bell.

### `blip(m, dur=0.20, amp=0.55, crush=6)`

```
wave      0.6 * triangle + 0.4 * square
then      bitcrush to 6 bits  ->  sample-and-hold decimate by 3
envelope  exp(-t * 10)
```

This is the 8-bit lead. Two separate degradations are needed: `bitcrush`
quantises **amplitude**, `sr_crush` quantises **time**. Doing only one sounds
like a mistake; doing both sounds like 1999. Lower `crush` (4–5) for coarser
grit, raise it (8) to clean it up.

### `sub_bass(m, dur, amp=0.34)`

Fundamental plus a 16 % second harmonic. The second harmonic is what makes a
sub audible on speakers that cannot reproduce the fundamental — without it the
track simply loses its low end on laptop speakers.

### `kick(amp, dur=0.52, f_hi=130.0, f_lo=48.0, dec=7.5)`

Sine with an exponential pitch sweep from 130 Hz down to 48 Hz, integrated to
phase (`np.cumsum(f) / SR`, **not** `sin(t · f)`), plus a noise click that
decays over ~3 ms. The sweep is the punch; the click is the beater.

### `clap(amp, dur=0.40, lo=900, hi=5200, dec=45.0)`

Three band-passed noise bursts offset by 0 / 9 / 19 ms with descending gains.
A single burst sounds like a snare; the offsets are what make it a clap.

### `hat(amp, dur=0.055, open_=False)`

7.5–17 kHz noise, decaying over `d/3.4`. `open_=True` multiplies the duration by
7. Past 17 kHz there is nothing to hear, so the band stops there.

---

## The noise beds

| function | what it imitates | how |
|---|---|---|
| `air_layer` | room / tape breathing | 3–15 kHz noise under a 0.037 Hz LFO |
| `vinyl` | record crackle | ~42 short bursts per second, each a 4 ms decaying noise click |
| `hiss` | tape hiss | 250 Hz–9 kHz noise, constant |

**All three are added after the loop fold, gated by `noise_envelope()`.** See
§1 of `mixing-rules.md` — getting this order wrong is the single most common
defect in this engine.

Set `vinyl_amp=0.05` for lo-fi, `0.008` for subtle Y2K, and `0.0` for a "clean"
shipping variant.

---

## Adding a new instrument

1. Write `def my_voice(m, dur, ...)` returning a 1-D `float64` array of
   `int(dur * SR)` samples in roughly ±1.
2. Choose integer ratios for pitched sounds, non-integer for metallic ones.
3. Give each partial its **own** decay rate — uniform decay sounds synthetic.
4. Always start with a 2–5 ms ramp to avoid a DC click:
   ```python
   k = int(0.003 * SR); out[:k] *= np.linspace(0, 1, k)
   ```
5. Wire it into `render()` as an arrangement key (`if s.get('my_voice'):`), with
   an amp override read from `v.get('my_voice_amp', ...)`.
6. Run the QA. If the band you are targeting is still at 0 %, the voice is not
   reaching it — check the ratios, not the mixer.

---

## Band targets per style

The `targets` list is `[sub/bass, low-mid, mid, high, air]` and must sum to 1.0.

| preset | targets | character |
|---|---|---|
| `y2k-digital` | 0.22 / 0.28 / 0.28 / 0.17 / 0.05 | bright, mid-forward |
| `y2k-dreamy` | 0.25 / 0.30 / 0.26 / 0.14 / 0.05 | balanced, soft |
| `y2k-nocturnal` | 0.30 / 0.32 / 0.24 / 0.11 / 0.03 | dark, thick low end |
| `lofi-minimal` | 0.22 / 0.34 / 0.28 / 0.13 / 0.03 | warm midrange, rolled-off top |
| `ambient-drift` | 0.31 / 0.33 / 0.23 / 0.10 / 0.03 | very dark, wide |
| `chiptune-playful` | 0.20 / 0.26 / 0.32 / 0.18 / 0.04 | thin bass, bright mid |

Raising the `air` target above ~0.07 always costs you level headroom, because
the air band has almost no perceived loudness for the energy it carries.
