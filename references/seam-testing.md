# Seam testing

How to prove a loop actually loops. Read this together with
`references/mixing-rules.md` §4 and §5.

---

## The trap: absolute seam numbers lie

The obvious test is "compare the first sample with the last sample". It is also
almost worthless:

| render | `|first − last|` | actually seamless? |
|---|---|---|
| tail-folded correctly | small | yes |
| hard cut at a zero crossing | **0.00000** | no — reverb cliff remains |
| both ends faded to silence | **0.00000** | no — level notch on every repeat |
| only one end faded | large | no |

A perfect `0.00000` is the signature of a **forced** boundary, not of a clean
loop. That is why every seam figure in this skill is printed next to the
distribution of the same measurement taken everywhere else in the track.

**Rule: a seam verdict is only meaningful as a percentile, never as a raw value.**

---

## The three tests in `scripts/seam_test.py`

The file is treated as a ring: sample `n-1` is followed by sample `0`.

### A — is the junction an ordinary sample step?

```python
ring = concat(mono, mono[:1])
step = |diff(ring)|
seam_step            = step[-1]                  # across the junction
p999_everywhere_else = percentile(step[:-1], 99.9)
```

Pass when `seam_step <= p999`. This catches **discontinuities** — a waveform
that jumps where it should not.

### B — is the junction at an ordinary level?

Slide a 5 / 20 / 50 ms window around the ring and compute RMS for each. Then
take the window centred on the junction and ask what percentile it sits at.

Pass when the percentile is between roughly 2 and 98.

This is the test that catches **fades and notches**, which A cannot see: a notch
is continuous, so `step` stays small, but the level collapses.

### C — is the junction spectrally ordinary?

2048-point FFT centred on the junction, high band (>3 kHz) energy, compared with
the median window. Pass when the ratio is roughly 0.5–2.0.

This catches a seam that is level-correct but has lost its reverb tail — the
"cliff" case, where the loop suddenly goes dry.

**A, B and C must be read together.** Any one alone can be passed by a broken
render.

---

## `scripts/seam_focus.py` — is it a defect or just a sparse arrangement?

`seam_test.py` can flag a B failure on a perfectly good loop, because the last
section of an arrangement may simply be quieter than the average. `seam_focus`
prints the RMS of the windows on either side of the junction so you can tell the
two apart:

```
  win -2  0.19121  0.94x
  win -1  0.19593  0.96x   <-- SEAM
  win +0  0.24596  1.20x
  win +1  0.25503  1.25x
  min 0.17443 (0.85x) at win -5 | spread 1.46x
  verdict: OK - the junction sits at the level of its neighbours, not a notch
```

| shape | reading |
|---|---|
| flat across the junction, min elsewhere | arrangement is sparse there — **fine** |
| **V** dipping exactly at the junction | real notch — the defect is in the boundary treatment |
| step up/down with no dip | one-sided fade still applied |

Note the asymmetry you *should* expect: the window just after the junction is
usually a little louder than the one just before, because the tail was folded
onto the head. A mild `+0.2x` step is normal; a `+3x` step is not.

---

## Checklist before shipping a loop

1. `seam_ramp` is `0.0` for the looping render (`presets.build(..., clean=True)`
   sets this for you).
2. Noise beds are added **after** the fold — confirm by checking that the head
   and tail 0.5 s RMS ratio in QA is close to 1.00. A ratio above ~1.3 means the
   beds were mixed in too early.
3. `len(arr)` is a whole multiple of `len(prog) * chord_bars`.
4. `seam_test.py`: A, B and C all pass.
5. `seam_focus.py`: no V shape at the junction.
6. `qa_music.py --loop`: `head/tail level match` passes.

If 2 fails, go to `mixing-rules.md` §1. If 4B or 5 fails, the boundary
treatment is wrong — check that no fade is being applied to the loop.

---

## What "seamless" does not mean

A tail-fold makes the **reverb** continuous across the junction. It does not:

- make the harmony match if the bar count is not a whole chord cycle (§7);
- hide an arrangement that ends much louder than it starts;
- survive lossy re-encoding *perfectly* — MP3 frame boundaries can shift the
  junction by a few samples, so a loop intended for sample-exact use should be
  shipped as WAV. For web/background use the mp3 is fine; the QA percentile
  tests run on the decoded mp3 too and still pass.
