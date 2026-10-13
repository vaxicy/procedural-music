# Examples

Two demo renders, both produced in **clean mode** (no air / vinyl / hiss noise beds).

| File | Preset | Mode | Length | Size |
|---|---|---|---|---|
| `demo-y2k-digital-loop-21s.mp3` | `y2k-digital` | seamless loop, 8 bars | 0:21 | 0.47 MB |
| `demo-lofi-minimal-full-176s.mp3` | `lofi-minimal` | full arrangement, 64 bars | 2:55 | 4.02 MB |

Regenerate them exactly:

```bash
python scripts/render_track.py --preset y2k-digital --out examples \
    --loop --bars 8 --clean --seed 1 --name demo-y2k-digital-loop-21s
python scripts/render_track.py --preset lofi-minimal --out examples \
    --full --clean --seed 3 --name demo-lofi-minimal-full-176s
```

`--clean` sets `air_amp` / `vinyl_amp` / `hiss_amp` to zero. Leave it off and the
lo-fi preset keeps its tape hiss and vinyl crackle — right for a track, but the
hiss reads as noise on a storefront or a documentation page.

`.gitignore` excludes `*.wav` and `*.mp3`, so a demo has to be force-added:

```bash
git add -f examples/demo-y2k-digital-loop-21s.mp3
```

Keep committed audio short — a 20 s loop is a few hundred KB, a 3-minute render
is several MB.
