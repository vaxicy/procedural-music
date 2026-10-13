# Procedural Music Generator

> No music model, no sample library, no soundfont, no DAW — every sample is computed by Python, loops are seamless by construction, and the seam is measured before anything is delivered.

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python: 3.10+">
  <img src="https://img.shields.io/badge/numpy-required-orange.svg" alt="numpy">
  <img src="https://img.shields.io/badge/ffmpeg-mp3%20export-lightgrey.svg" alt="ffmpeg">
</p>

**English** | [简体中文](README.zh-CN.md)

**Keywords:** background music · BGM · procedural music · seamless loop · pure-code synthesis · additive synthesis · agent skill · Claude Code · Codex · WorkBuddy

An **Agent Skill** that turns a short brief into a finished audio file without leaving Python: pick a preset, render, read the self-check report, fix the right layer if something fails, hand back the track plus its seed.

One folder, four hosts — Claude Code, OpenAI Codex, WorkBuddy and CodeBuddy all read the same `SKILL.md` + `scripts/` + `references/` layout.

---

## Listen first

Both demos are clean renders (no noise beds). Click to play or download:

| Demo | Preset | Mode | Length | Size |
|---|---|---|---|---|
| [demo-y2k-digital-loop-21s.mp3](examples/demo-y2k-digital-loop-21s.mp3) | `y2k-digital` | seamless loop, 8 bars | 0:21 | 0.47 MB |
| [demo-lofi-minimal-full-176s.mp3](examples/demo-lofi-minimal-full-176s.mp3) | `lofi-minimal` | full arrangement, 64 bars | 2:55 | 4.02 MB |

Regenerate them, byte for byte, with the commands in [`examples/README.md`](examples/README.md). That is not a figure of speech: the committed MP3s re-render to the **same SHA-256**, because the seed pins the noise beds and the reverb impulse response.

---

## Install

### One command, every host on the machine

```bash
git clone https://github.com/vaxicy/procedural-music.git
cd procedural-music
python install.py
```

`install.py` probes the skill directories that exist on this machine and installs into all of them:

```
skill   : /path/to/procedural-music
command : install (link)

  claude     Claude Code                link  ~/.claude/skills/procedural-music
  codex      OpenAI Codex               link  ~/.codex/skills/procedural-music
  workbuddy  WorkBuddy                  link  ~/.workbuddy/skills/procedural-music
  codebuddy  CodeBuddy                  link  ~/.codebuddy/skills/procedural-music
```

Default mode is **`link`** (Windows directory junction / POSIX symlink), so the clone stays the single source of truth — one `git pull` updates every host at once. `--copy` writes independent copies instead; if a host cannot hold a link the installer falls back to a copy and says so.

| Flag | Effect |
|---|---|
| `--copy` | Independent copies rather than links |
| `--hosts claude,codex` | Only these hosts (adds `agents` for the shared `~/.agents/skills` convention) |
| `--list` | Show what was detected, change nothing |
| `--dry-run` | Print the plan |
| `--uninstall` | Remove the skill from every host it was installed into |

A destination that already holds this skill is replaced. A destination that holds something else is left alone and reported — `--force` overrides that. Restart the host afterwards so it rescans its skills folder.

### Host skill directories

| Host | User level | Project level |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| OpenAI Codex | `$CODEX_HOME/skills/` (default `~/.codex/skills/`) | `.codex/skills/` |
| Shared `.agents` convention | `~/.agents/skills/` | `.agents/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` | `.workbuddy/skills/` |
| CodeBuddy | `~/.codebuddy/skills/` | `.codebuddy/skills/` |

⚠️ Claude Code and Codex require the **folder name to equal the `name` field** in `SKILL.md`. Both are `procedural-music` here — if you rename the folder, update the frontmatter too.

### Manual install

```bash
# option A — clone straight into a host
git clone https://github.com/vaxicy/procedural-music.git ~/.claude/skills/procedural-music
git clone https://github.com/vaxicy/procedural-music.git ~/.codex/skills/procedural-music

# option B — one clone, linked everywhere
git clone https://github.com/vaxicy/procedural-music.git ~/src/procedural-music
ln -s ~/src/procedural-music ~/.claude/skills/procedural-music     # macOS / Linux
ln -s ~/src/procedural-music ~/.codex/skills/procedural-music
```

On Windows, use a junction (no admin rights needed):

```powershell
cmd /c mklink /J "%USERPROFILE%\.claude\skills\procedural-music" "C:\src\procedural-music"
cmd /c mklink /J "%USERPROFILE%\.codex\skills\procedural-music"  "C:\src\procedural-music"
```

### Claude Code, through the plugin marketplace

```
/plugin marketplace add vaxicy/procedural-music
/plugin install procedural-music@procedural-music
```

The repo root holds both the marketplace manifest (`.claude-plugin/marketplace.json`) and the skill, so no second repository is involved.

### Codex notes

Codex reads the folder directly from `$CODEX_HOME/skills/procedural-music`. The bundled `agents/openai.yaml` supplies the display name and default prompt; other hosts ignore it. A skill can be switched off again with a `[[skills.config]]` entry in `config.toml`.

### Requirements

```bash
pip install -r requirements.txt     # numpy
```

- Python 3.10+ (developed on 3.14). On Windows, `py -3` works if the `python` alias is not set up.
- `ffmpeg` on `PATH` for MP3 output. WAV output needs nothing beyond numpy.
- CPU only, single-threaded, no network calls and no API keys.

---

## Quick start

```bash
python scripts/render_track.py --list

# seamless loop, clean (no noise beds), self-checked
python scripts/render_track.py --preset y2k-digital --out ./out --loop --bars 8 --clean --qa

# full arrangement: intro / build / main / bridge / main / outro
python scripts/render_track.py --preset lofi-minimal --out ./out --full --clean --qa

# reproducible, specific length
python scripts/render_track.py --preset ambient-drift --out ./out --bars 32 --seed 7

# loop-seam specialists, on any render
python scripts/seam_test.py  out/track.wav
python scripts/seam_focus.py out/track.wav
```

| Flag | Effect |
|---|---|
| `--loop` / `--full` | Seamless loop (default) or the full-length arrangement |
| `--bars N` | Loop length, rounded **up** to whole chord cycles so the harmony still matches when it wraps |
| `--seed N` | Byte-reproducible render. Without it, noise beds and the reverb IR are random each run |
| `--clean` | Drops all noise beds and loop fades — the variant to ship for a pure, seamless deliverable |
| `--qa` | Runs the self-check on **every file written** |
| `--no-wav` / `--no-mp3` | Keep only one of the two outputs |
| `--artist` / `--album` | ID3 tags |
| `--name` | Output file stem (default: preset + duration) |

---

## Presets

| Key | BPM / key | Character |
|---|---|---|
| `y2k-dreamy` | 88, D major | Soft pad bed plus bell arpeggios. Warm, nostalgic, slightly sweet. |
| `y2k-nocturnal` | 85, B minor | Minor, slower, deeper. Thick low end, long reverb, sparse drums. |
| `y2k-digital` | 93, A major | Bitcrushed square/triangle arpeggio with occasional glitch drops. |
| `lofi-minimal` | 90, F major | Almost drumless: electric piano, tape hiss and vinyl crackle. |
| `ambient-drift` | 68, C major | Very slow, drumless, wide. Dark low end, almost no attack. |
| `chiptune-playful` | 118, G major | Fast, bright 8-bit lead over a busy beat. Almost no reverb. |

Most briefs are a small delta from one of these — `bpm`, `prog`, `lead_kind`, `lead_div`, `rev_mix` / `rev_t`, `targets`. The order to change them in, and the band targets per style, are in `references/synthesis-cookbook.md`.

---

## What the self-check actually reports

`--qa` on a real render:

```
$ python scripts/render_track.py --preset chiptune-playful --out ./out --bars 8 --seed 1 --clean --qa

=== chiptune-playful_loop_16s.mp3 ===

  duration 16.27 s | peak -0.96 dBFS | rms -14.38 dBFS | crest 13.4 dB
  band balance (Welch averaged):
     sub/bass   19.9%   ##########
     low-mid    23.6%   ############
     mid        37.2%   ###################
     high       15.3%   ########
     air         4.0%   ##
  stereo width (side/mid): 0.07
  seam step 0.063171  vs 99.9% elsewhere 0.493868
  seam window percentile: 54.6
  checks:
     [PASS] no clipping            0 samples at full scale
     [PASS] dc offset              -0.000050
     [PASS] headroom               peak -0.96 dBFS
     [PASS] seam is a normal step  junction 0.063171 vs 99.9% elsewhere 0.493868
     [PASS] seam level is normal   20 ms window sits at 54.6 percentile (a fade/notch would sit near 0)
     [PASS] head/tail level match  0.5 s rms head 0.1827 / tail 0.1812  ratio 1.01
  VERDICT: ALL PASS
```

For a loop to ship, `seam_test.py` must pass all three of its independent checks (step, short-window level, spectral continuity) and `seam_focus.py` must not show a V shape at the junction. Every seam number is a **percentile against the rest of the track**, never an absolute value — a file whose head and tail were both forced to silence reports a junction step of `0.00000` and would pass a naive check for the wrong reason.

The self-check reads the **MP3 first, then the WAV**. Validating only the WAV hides a whole class of problem, because the lossy step comes afterwards.

---

## Defects this skill encodes

Each of these was real, found, and fixed — the details are in `references/mixing-rules.md`:

| Symptom | Cause | Fix |
|---|---|---|
| The first seconds of a loop are clearly louder | Noise bed mixed in **before** the tail fold, so the tail's noise piled onto the head (+3 dB) | Fold first, add noise last (§1) |
| Auto-balance never converges | Bands measured from a single-frame FFT | Measure with an averaged Welch PSD (§2) |
| A band sits at 0.0% forever | The arrangement has nothing in that band | Add an instrument, don't push the EQ (§3) |
| A level notch on every repeat | A fade-out left on a looping render | `seam_ramp = 0` when looping (§4) |
| Junction step reads `0.00000` but it still clicks | Both ends forced to zero — a **false pass** | Judge by percentile, never absolute (§5) |

---

## How it works

1. **Additive synthesis.** A timbre is a stack of sines. The partial ratios set the colour, and letting **each partial decay on its own** sets the material. Integer ratios read as pitched (strings, winds, pads); non-integer ratios read as struck metal — `bell` uses 1 : 2.756 : 5.404 to approximate a bar.
2. **8-bit lead.** Triangle and square mixed, then quantised in **both** amplitude (bitcrush) and time (sample-rate decimation). Doing one alone sounds like a bug; doing both is the Y2K sound.
3. **Convolution reverb.** A procedurally generated exponentially decaying noise impulse response, convolved by FFT, with mid and side handled separately.
4. **Seamless loops by tail-folding.** Render 3.2 s past the end, fold the tail back onto the head, cut to a whole number of bars. The reverb tail therefore never gets chopped at the loop point, and the bar count is rounded up to whole chord cycles so the harmony still lines up when it wraps.
5. **Automatic band balance.** An averaged Welch PSD measures five bands (30–120 / 120–500 / 500–2k / 2k–8k / 8–17k), compares them with the target curve, and applies a log-interpolated EQ within ±8 dB per pass, up to 5 passes, stopping under 0.8 dB of error.
6. **Master bus.** Normalise → `tanh` soft clip (drive 1.15) → normalise to −1.0 dBFS, which leaves room for MP3 inter-sample overshoot. Raising that ceiling is a known way to fail the headroom check.

---

## Layout

```
procedural-music/
├── SKILL.md                    skill definition (triggers + mandatory workflow)
├── install.py                  one-command installer for every host on the machine
├── agents/openai.yaml          Codex display name + default prompt (optional)
├── .claude-plugin/
│   └── marketplace.json        Claude Code plugin marketplace manifest
├── README.md / README.zh-CN.md
├── LICENSE, requirements.txt
├── scripts/
│   ├── synth_engine.py         instruments / FX / measurement / render / output
│   ├── presets.py              six style presets + arrangement builders
│   ├── render_track.py         CLI: preset → WAV + MP3
│   ├── qa_music.py             self-check: levels, clipping, seam, bands, stereo width
│   ├── seam_test.py            three independent loop-seam tests
│   └── seam_focus.py           a real notch vs. an arrangement that is sparse there
├── references/
│   ├── mixing-rules.md         the eight rules + symptom → cause → fix table
│   ├── seam-testing.md         why absolute seam numbers cannot be trusted
│   └── synthesis-cookbook.md   partial ratios, envelopes and band targets
└── examples/                   two committed demo renders
```

## Speed and cost

Measured on this repo's own demos, single-threaded on a laptop CPU:

| Render | Length | Wall time |
|---|---|---|
| `y2k-digital --loop --bars 8` | 0:21 | 4.2 s |
| `lofi-minimal --full` | 2:55 | 37.2 s |

Roughly 4–5× faster than real time. No GPU, no network, no per-render cost.

## License

MIT — see [LICENSE](LICENSE). The generated audio is yours, with no attribution required.
