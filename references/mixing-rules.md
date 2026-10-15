# Mixing rules

These are not style preferences. Each one was learned by shipping a track that
had the defect, and each one is encoded in `scripts/synth_engine.py`. Read this
file before changing the engine or debugging a render.

---

## 1. Fold the reverb tail before you add the noise beds

**Symptom:** the first 2–3 seconds of a loop sound noisier than the rest. On a
spectral plot the noise floor is ~3 dB (√2) higher in the opening seconds.

**Cause:** a seamless loop is made by rendering `bars × bar` plus a tail, then
adding the tail back onto the head. If the continuous noise beds (tape hiss,
air, vinyl) are already mixed in when that happens, the last few seconds of
noise get **added** to the first few seconds. Two uncorrelated noise signals at
equal level sum to +3 dB.

**Fix:** keep the fold on a musical bus only, then add the noise beds
afterwards, gated by a per-bar envelope:

```python
# engine order — do not reorder
xl, xr = fold(xl, xr, loop_n)          # 1. musical bus, tail folded
env = noise_envelope(arr, bar, out_n)  # 2. per-bar gain, cross-faded
xl += air_layer(out_n, amp=...) * env  # 3. noise beds last
```

Verified numbers from the original defect: front RMS **0.0523** vs **0.0361**
elsewhere. After the fix the ratio is ~1.00.

---

## 2. Measure band balance with an averaged Welch PSD

**Symptom:** the auto-balancer "converges" and the track still sounds wrong.

**Cause:** a single-frame FFT is dominated by whatever transient happens to sit
in that frame. On music it is essentially random.

**Fix:** accumulate the magnitude-squared spectrum over many overlapping frames
before summing the bands. The engine uses 16 384-sample frames with 50 % overlap
and a Hann window:

```python
acc = sum(|rfft(frame * hann)| ** 2 for every frame)   # then sum per band
```

`render()` prints one line per balancing iteration so you can watch it converge.
The `targets` in `presets.py` use these exact five bands:

| band | range | typical share |
|---|---|---|
| sub/bass | 30–120 Hz | 0.20–0.31 |
| low-mid | 120–500 Hz | 0.26–0.34 |
| mid | 500–2 000 Hz | 0.23–0.32 |
| high | 2 000–8 000 Hz | 0.10–0.18 |
| air | 8 000–17 000 Hz | 0.03–0.05 |

---

## 3. EQ can only amplify what already exists

**Symptom:** a band sits at 0.0 % and no amount of correction moves it.

**Cause:** nothing in the arrangement generates energy there. Boosting a band
that is empty multiplies the existing noise floor, so you get a hiss swell
instead of music.

**Fix:** go back to the content layer. Add a source in that register —
`shimmer_chord` for 2–8 kHz, `sparkle` bells for the air band, `sub_bass` +
`kick` for the low end — then let the balancer do its job. `eq_curve()` is
clamped to ±8 dB per iteration for the same reason: a big correction on a near
empty band is always a mistake in disguise.

---

## 4. A looping render gets `seam_ramp = 0`

**Symptom:** every repeat of the loop has an audible level notch at the
junction.

**Cause:** the tail was already folded onto the head, so the waveform is
continuous across the junction on its own. Adding a fade-in/fade-out at the
boundaries punches a hole in the middle of that continuity.

**Fix:** `seam_ramp` defaults to `0.0` when `loop=True`, and to 12 ms when
`loop=False`. Non-looping renders also get a musical 5 s fade-out. The three
noise beds are set to `0.0` by default — see `presets.build(..., clean=True)`,
which is the default path; `clean=False` (CLI `--noise`) opts back in.

---

## 5. Never judge a seam in absolute terms

**Symptom:** the QA output says `seam jump: 0.00000` and you conclude the loop
is fine.

**Cause:** a file whose first and last samples were both forced to silence also
reports `0.00000`. So does a file with a hard truncation that happens to land on
a zero crossing.

**Fix:** every seam figure must be printed next to the distribution of the same
measurement taken everywhere else. See `references/seam-testing.md`.

---

## 6. `kick_beats` has two different meanings

```python
kick_beats=[0, 2]              # same two beats in every bar
kick_beats=[[0, 2], [0]]       # a different pattern per bar, cycling
```

A plain list is applied verbatim to every bar; a list **of lists** is indexed
per bar. Every other arrangement key is treated as a repeating per-bar pattern
with period `len(value)`.

---

## 7. Bars must be a whole number of chord cycles

`render()` asserts `BARS % (len(prog) * chord_bars) == 0`. A loop that ends
mid-progression cannot be seamless — the harmony will not match when it wraps.
`presets.build()` rounds the requested bar count up to the next whole cycle
automatically, so pass `--bars` freely.

---

## 8. Symptom → cause → fix

| Symptom | Cause | Fix |
|---|---|---|
| Opening seconds sound noisy | Noise beds mixed before the tail fold | Fold first, noise beds after (§1) |
| Auto-balance never converges | Single-frame FFT | Averaged Welch PSD (§2) |
| A band stays at 0 % | No source in that register | Add content, not EQ (§3) |
| Level notch on every repeat | Boundary fade on a loop | `seam_ramp = 0` (§4) |
| `seam jump 0.00000` but audible click | Both ends forced to zero | Use the percentile tests (§5) |
| Kick pattern identical in every bar | Passed a flat list | Nest the list (§6) |
| Loop "jumps" harmonically | Bars not a whole chord cycle | Round the bar count (§7) |
