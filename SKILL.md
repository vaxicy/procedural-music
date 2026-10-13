---
name: procedural-music
description: "Generate background music from scratch as pure Python DSP — every sample synthesised by script, with no samples, no soundfont, no DAW and no music model. Bundles a preset library (Y2K dreamy / nocturnal / digital, lo-fi minimal, ambient drift, chiptune playful), seamless reverb-tail-folded loops, iterative Welch-PSD band balancing, and a mandatory loop-seam self-check suite. Use this skill whenever the user asks to create, generate or fix background music / BGM / a looping score, needs royalty-free audio for a website, app or video, wants a track in a named style or mood, or reports a defect in an already-rendered track such as a click at the loop point, hiss at the start, a level notch on every repeat, or unbalanced frequency bands. 中文：程序化背景音乐生成器 —— 纯代码合成音色、无缝循环、频段自动配平、自带接缝 QA。"
agent_created: true
---

# Procedural Music Generator

## Overview

This skill turns a short brief into a finished audio file without leaving Python.
Everything is synthesised from first principles: instruments are additive sine
stacks with hand-written envelopes, effects are FFT convolution reverb and a
ping-pong delay, and loops are made seamless by folding the reverb tail back
onto the head.

There is **no** music model, sample library, soundfont or DAW involved. That
matters for three reasons: the output is unambiguously licence-clean, it is
fully reproducible from a seed, and any parameter the user dislikes can be
changed rather than re-prompted.

The engine is a port of a production track (`03 Pixel Bloom`) that shipped for a
real storefront, so the defaults already sound finished. The bundled reference
files record the defects that were found and fixed along the way — read them
before changing the engine.

## When To Use

Trigger this skill when the user:

- Asks to create, generate or compose background music / BGM / a soundtrack /
  a looping score / ambient audio.
- Needs royalty-free audio for a website, app, game, video, podcast intro or
  social post, and wants a specific mood rather than a file they have to source.
- Names a style or era: Y2K, lo-fi, chill, dreamy, nocturnal, ambient, chiptune,
  8-bit, study music, minimal.
- Wants a specific tempo, key or duration ("93 BPM in A major, about a minute,
  looping").
- Reports a defect in a rendered track: a click or bump at the loop point, hiss
  louder at the start than elsewhere, a level drop on every repeat, muddy or
  harsh frequency balance, an instrument that is too loud or inaudible.
- Asks to change something about a track this skill previously produced.

Do **not** use this skill for speech, singing, sound effects (whooshes, impacts,
UI bleeps) or audio restoration — it is a music synthesiser, not a general audio
toolkit.

## Prerequisites

- Python 3.10+ with `numpy` (`pip install -r requirements.txt`).
- `ffmpeg` on `PATH` for mp3 output. WAV output needs nothing extra.
- Rendering is CPU-bound and single-threaded. Budget roughly **1 second of
  render time per 4 seconds of audio**; a 3-minute track takes about 40 s.

## Workflow (mandatory loop)

Follow this cycle for every request. Do not skip step 3 — an unverified loop is
the single most common failure mode of this skill.

1. **Pick a preset.** Run `python scripts/render_track.py --list` and choose the
   closest match to the brief. If nothing fits, adapt the nearest preset (see
   *Adapting a preset* below) rather than starting from a blank file.
2. **Render.**
   ```bash
   # seamless loop, clean (no noise beds), verified
   python scripts/render_track.py --preset y2k-digital --out ./out --loop --clean --qa

   # full-length arrangement with intro / build / main / bridge / main / outro
   python scripts/render_track.py --preset lofi-minimal --out ./out --full --qa

   # reproducible, specific length
   python scripts/render_track.py --preset ambient-drift --out ./out --bars 32 --seed 7
   ```
3. **Self-check.** `--qa` prints a report. Read every line; do not skim to the
   verdict. Then, for any looping render, also run:
   ```bash
   python scripts/seam_test.py out/track.wav
   python scripts/seam_focus.py out/track.wav
   ```
   For a loop to ship, `seam_test.py` must pass A, B **and** C, and
   `seam_focus.py` must not show a V shape at the junction.
4. **Fix at the right layer.** Use `references/mixing-rules.md`'s
   symptom → cause → fix table. Never "fix" a band-balance problem by pushing
   the EQ harder — see rule 3 in that file.
5. **Re-render and repeat step 3.** Always re-verify after any change.
6. **Deliver.** Report the file path, duration, BPM, key, and the QA verdict.
   Mention the seed so the user can reproduce or re-roll it.

## Engine guarantees

These hold as long as `synth_engine.py` is not reordered. Each is a defect that
was actually shipped once, and each has a dedicated section in
`references/mixing-rules.md`.

| Guarantee | Rule |
|---|---|
| No hiss swell at the start of a loop | Noise beds are mixed **after** the tail fold (§1) |
| Auto-balance converges to something meaningful | Bands measured with an averaged Welch PSD (§2) |
| No audible level notch on every repeat | `seam_ramp = 0` for looping renders (§4) |
| Harmony matches when the loop wraps | Bar count is a whole number of chord cycles (§7) |
| Seam verdicts cannot be faked | All seam numbers are percentiles, never absolute values (§5) |
| The shipped MP3 itself has headroom | Master bus normalises to −1.0 dBFS (`MASTER_CEIL = 0.89`) |

### MP3 headroom — do not raise the ceiling

The master bus normalises to **−1.0 dBFS** (`synth_engine.MASTER_CEIL = 0.89`),
not the −0.63 dBFS a "leave about 5 %" rule of thumb suggests. MP3 is a lossy
transform, so the decoded waveform can overshoot the encoded peak by up to
~0.6 dB on bass-heavy material. This was measured, not guessed: at 0.93 a
`lofi-minimal --full` render decoded to 0.990 and failed the `headroom` check
(`peak <= 0.99`) with zero actual clipping.

`--qa` validates **every file written** — the MP3 first, then the WAV if it is
kept. Validating only the WAV hides this whole class of problem, because the WAV
is produced *before* the lossy step.

## Script reference

All scripts live in `scripts/` and are runnable directly. They import each other
by path, so run them from the skill directory (or with `scripts/` on
`PYTHONPATH`).

| Script | Purpose |
|---|---|
| `synth_engine.py` | The engine. Instruments, FX, measurement, `render()`, file output. |
| `presets.py` | Six style presets plus the `pat8()` / `sections()` arrangement builders. |
| `render_track.py` | CLI: preset → WAV + MP3. `--list`, `--loop`, `--full`, `--bars`, `--seed`, `--clean`, `--qa`. |
| `qa_music.py` | Self-check: peak / RMS / crest / clipping / DC / seam / band balance / stereo width. Accepts WAV and MP3. Pass `--no-loop` when checking a full (faded) render — otherwise the loop checks run and fail spuriously. |
| `seam_test.py` | Three independent loop-seam tests (step, level, spectrum). |
| `seam_focus.py` | Tells a real seam notch apart from a deliberately sparse arrangement. |

### Useful flags

| Flag | Effect |
|---|---|
| `--clean` | Drops all three noise beds and the loop fades. This is the variant to ship for a "pure / seamless" deliverable. |
| `--bars N` | Loop length. Rounded **up** to the next whole chord cycle automatically. |
| `--seed N` | Makes the render byte-reproducible. Without it, noise beds and the reverb IR are random each run. |
| `--no-wav` | MP3 only (removes the intermediate WAV). |
| `--artist` / `--album` | ID3 tags. |

## Preset reference

| Key | BPM / key | Character |
|---|---|---|
| `y2k-dreamy` | 88, D major | Soft pad bed plus bell arpeggios. Warm, nostalgic, slightly sweet. |
| `y2k-nocturnal` | 85, B minor | Minor, slower and deeper. Thick low end, long reverb, sparse drums. |
| `y2k-digital` | 93, A major | Bitcrushed square/triangle arpeggio with occasional glitch drops. |
| `lofi-minimal` | 90, F major | Almost drumless: electric piano, tape hiss and vinyl crackle. |
| `ambient-drift` | 68, C major | Very slow, drumless, wide. Dark low end, almost no attack. |
| `chiptune-playful` | 118, G major | Fast, bright 8-bit lead on top of a busy beat. Almost no reverb. |

## Adapting a preset

Most briefs are a small delta from an existing preset. Change these, in order:

1. **`bpm` and `prog`** — the chord progression is a list of note-name lists,
   one per chord. Chord changes happen every `chord_bars` bars. Keep the first
   note low (the bass plays `prog[n][0] - 12`).
2. **`lead_kind`** — `'blip'` for 8-bit, `'bell'` for dreamy/celesta.
3. **`lead_div` per section** — `4` = quarter notes (sparse), `8` = eighths,
   `16` = sixteenths (busy, and unlocks the `glitch` drops).
4. **`rev_mix` / `rev_t`** — reverb size. Above ~0.45 the mix turns to mush;
   pair a big reverb with `rev_damp` around 6000–7000 so it does not get harsh.
5. **`targets`** — the five-band balance. Keep the sum at 1.0. See the
   per-style table at the end of `references/synthesis-cookbook.md`.
6. **Noise beds** — `vinyl_amp` ~0.05 for lo-fi, ~0.008 for subtle, `0.0` for
   clean.

Only after those, consider writing a new instrument; the recipe is documented at
the end of `references/synthesis-cookbook.md`.

## Reference files

| File | Read it when |
|---|---|
| `references/mixing-rules.md` | Debugging any defect, or before editing the engine. Contains the symptom → cause → fix table. |
| `references/seam-testing.md` | Any looping render. Explains why absolute seam numbers lie. |
| `references/synthesis-cookbook.md` | Changing a timbre, adding an instrument, or choosing band targets. |

## Reporting results

When handing a track back, state: the preset and any overrides, the seed, the
duration / BPM / key, the output paths, and the QA verdict including the seam
tests. If a check failed and you could not fix it at the correct layer, say so
explicitly rather than presenting the track as finished.

## Portability

This folder follows the common **Agent Skills** convention, so it loads
unchanged in Claude Code (`~/.claude/skills/`), OpenAI Codex
(`$CODEX_HOME/skills/`, default `~/.codex/skills/`), the shared `.agents`
convention (`~/.agents/skills/`), WorkBuddy (`~/.workbuddy/skills/`) and
CodeBuddy (`~/.codebuddy/skills/`), plus their project-level equivalents.
Keep four rules in mind when editing:

- **The folder name must equal the frontmatter `name`.** Both are
  `procedural-music`. Claude Code and Codex verify this.
- `agent_created: true` is WorkBuddy-specific; other hosts ignore it. The
  `description` is kept under 1,024 characters because that is the shared cap.
- `agents/openai.yaml` is optional and Codex-only (display name + default
  prompt). Deleting it changes nothing about how the skill runs.
- `.claude-plugin/marketplace.json` is optional and Claude Code-only, so the
  repo can be added with `/plugin marketplace add`. Leave the `source` field
  pointing at `./` — the marketplace root and the skill root are the same
  folder on purpose.

Install it everywhere at once with `python install.py` from the repo root
(`--list` first to see which hosts were detected, `--uninstall` to reverse it).
Default mode links rather than copies, so one `git pull` refreshes every host.

Only `SKILL.md`, `scripts/` and `references/` are part of the standard. The
`examples/` folder is a plain extra directory — harmless everywhere, because a
host only loads what `SKILL.md` tells it to.
