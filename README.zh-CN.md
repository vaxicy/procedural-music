# 程序化背景音乐生成器

> 不用音乐模型、不用采样库、不用 SoundFont、不用 DAW —— 每个采样都由 Python 现场算出来，循环本身就是无缝的，而且接缝在交付前会实测一遍。

<p align="center">
  <a href="LICENSE"><img src="https://img.shields.io/badge/License-MIT-yellow.svg" alt="License: MIT"></a>
  <img src="https://img.shields.io/badge/Python-3.10+-blue.svg" alt="Python: 3.10+">
  <img src="https://img.shields.io/badge/numpy-required-orange.svg" alt="numpy">
  <img src="https://img.shields.io/badge/ffmpeg-mp3%20export-lightgrey.svg" alt="ffmpeg">
</p>

[English](README.md) | **简体中文**

**关键词：** 背景音乐 · BGM · 程序化合成 · 无缝循环 · 纯代码音乐 · 加法合成 · Agent Skill · Claude Code · Codex · WorkBuddy

这是一个 **Agent Skill**：给一句需求，它全程待在 Python 里把音频做完 —— 挑预设、渲染、读自检报告，哪一项没过就回到正确的那一层去改，最后交回文件、时长、BPM、调性和 seed。

一份文件夹，四个宿主通用：Claude Code、OpenAI Codex、WorkBuddy、CodeBuddy 读的都是同一套 `SKILL.md` + `scripts/` + `references/` 结构。

---

## 先听

两首 demo 都是 clean 模式（不带噪声床），点开即可试听或下载：

| 文件 | 预设 | 模式 | 时长 | 体积 |
|---|---|---|---|---|
| [demo-y2k-digital-loop-21s.mp3](examples/demo-y2k-digital-loop-21s.mp3) | `y2k-digital` | 无缝循环 8 小节 | 0:21 | 0.47 MB |
| [demo-lofi-minimal-loop-43s.mp3](examples/demo-lofi-minimal-loop-43s.mp3) | `lofi-minimal` | 无缝循环 16 小节 | 0:43 | 0.98 MB |

按 [`examples/README.md`](examples/README.md) 里的命令重新渲染，得到的 MP3 与仓库里这两个文件**逐字节相同**（SHA-256 一致）。这不是修辞：seed 固定了噪声床和混响脉冲响应，所以同一 seed 就是同一个文件。

---

## 安装

### 一条命令装到本机所有宿主

```bash
git clone https://github.com/vaxicy/procedural-music.git
cd procedural-music
python install.py
```

`install.py` 会先探测本机存在哪些 skill 目录，然后逐一装进去：

```
skill   : /path/to/procedural-music
command : install (link)

  claude     Claude Code                link  ~/.claude/skills/procedural-music
  codex      OpenAI Codex               link  ~/.codex/skills/procedural-music
  workbuddy  WorkBuddy                  link  ~/.workbuddy/skills/procedural-music
  codebuddy  CodeBuddy                  link  ~/.codebuddy/skills/procedural-music
```

默认走 **`link`**（Windows 目录联接 / macOS、Linux 软链）：几个宿主都指向 clone 下来的这一份，`git pull` 一次，所有宿主同时更新。加 `--copy` 改成各自独立的副本；某个宿主建不了链接时会自动退回复制，并在输出里说明。

| 参数 | 作用 |
|---|---|
| `--copy` | 用独立副本代替链接 |
| `--hosts claude,codex` | 只装这几个宿主（再加 `agents` 可写进通用的 `~/.agents/skills` 约定目录） |
| `--list` | 看看探测到什么，不做任何改动 |
| `--dry-run` | 只打印计划 |
| `--uninstall` | 从装过的宿主里移除本 skill |

目标位置已经放着本 skill 会被替换；放着别的东西则原样保留并报出来，要覆盖得显式加 `--force`。装完重启宿主，让它重新扫描 skills 目录。

### 各宿主的 skill 目录

| 宿主 | 用户级 | 项目级 |
|---|---|---|
| Claude Code | `~/.claude/skills/` | `.claude/skills/` |
| OpenAI Codex | `$CODEX_HOME/skills/`（默认 `~/.codex/skills/`） | `.codex/skills/` |
| 通用 `.agents` 约定 | `~/.agents/skills/` | `.agents/skills/` |
| WorkBuddy | `~/.workbuddy/skills/` | `.workbuddy/skills/` |
| CodeBuddy | `~/.codebuddy/skills/` | `.codebuddy/skills/` |

⚠️ Claude Code 和 Codex 都要求**文件夹名与 `SKILL.md` 里的 `name` 完全一致**，这里两边都是 `procedural-music`。改了文件夹名，记得同步改 frontmatter。

### 手动安装

```bash
# 方式一：直接 clone 进某个宿主
git clone https://github.com/vaxicy/procedural-music.git ~/.claude/skills/procedural-music
git clone https://github.com/vaxicy/procedural-music.git ~/.codex/skills/procedural-music

# 方式二：clone 一份，到处链接
git clone https://github.com/vaxicy/procedural-music.git ~/src/procedural-music
ln -s ~/src/procedural-music ~/.claude/skills/procedural-music     # macOS / Linux
ln -s ~/src/procedural-music ~/.codex/skills/procedural-music
```

Windows 用目录联接，不需要管理员权限：

```powershell
cmd /c mklink /J "%USERPROFILE%\.claude\skills\procedural-music" "C:\src\procedural-music"
cmd /c mklink /J "%USERPROFILE%\.codex\skills\procedural-music"  "C:\src\procedural-music"
```

### Claude Code 走插件市场

```
/plugin marketplace add vaxicy/procedural-music
/plugin install procedural-music@procedural-music
```

市场清单（`.claude-plugin/marketplace.json`）和 skill 本体在同一个仓库根目录，不需要第二个仓库。

### Codex 说明

Codex 直接读 `$CODEX_HOME/skills/procedural-music` 这个文件夹。仓库里带的 `agents/openai.yaml` 提供显示名和默认提示词，其它宿主会忽略它。想临时关掉这个 skill，可以在 `config.toml` 里加一条 `[[skills.config]]`。

### 依赖

```bash
pip install -r requirements.txt     # numpy
```

- Python 3.10+（开发环境是 3.14）。Windows 上如果 `python` 别名没配好，用 `py -3`。
- MP3 输出需要 `ffmpeg` 在 `PATH` 上；只出 WAV 的话，除 numpy 外不需要任何东西。
- 纯 CPU、单线程，不联网，不需要任何 API key。

---

## 快速开始

```bash
python scripts/render_track.py --list

# 无缝循环（默认即纯净版 / 无噪声床）+ 自检
python scripts/render_track.py --preset y2k-digital --out ./out --loop --bars 8 --qa

# 完整长度：前奏 / 推进 / 主歌 / 间奏 / 主歌 / 尾奏
python scripts/render_track.py --preset lofi-minimal --out ./out --full --qa

# 可复现 + 指定长度
python scripts/render_track.py --preset ambient-drift --out ./out --bars 32 --seed 7

# 接缝专项检测，任何渲染都能跑
python scripts/seam_test.py  out/track.wav
python scripts/seam_focus.py out/track.wav
```

| 参数 | 作用 |
|---|---|
| `--loop` / `--full` | 无缝循环（默认）或完整长度编曲 |
| `--bars N` | 循环小节数，会自动**向上**取整到整数个和弦周期，这样绕回来时和声仍然对得上 |
| `--seed N` | 渲染结果可按字节复现；不传的话，噪声床和混响脉冲响应每次都是随机的 |
| `--noise` | 保留三路噪声床（air / vinyl / hiss）。**默认就是纯净版**；只有确实要 lo-fi / 磁带质感才加 |
| `--clean` | 默认纯净版的显式写法，仅为向后兼容保留 |
| `--qa` | 对**写出的每一个文件**跑自检 |
| `--no-wav` / `--no-mp3` | 只保留其中一种输出 |
| `--artist` / `--album` | 写 ID3 标签 |
| `--name` | 输出文件名（默认是预设名 + 时长） |

---

## 内置预设

| Key | BPM / 调 | 特点 |
|---|---|---|
| `y2k-dreamy` | 88, D major | 柔和 pad 铺底加铃铛琶音，暖、怀旧、微甜 |
| `y2k-nocturnal` | 85, B minor | 小调，更慢更深，低频厚、混响长、鼓点稀疏 |
| `y2k-digital` | 93, A major | 方波与三角波 bitcrush 琶音，偶尔卡碟停顿 |
| `lofi-minimal` | 90, F major | 几乎没有鼓：电钢、磁带嘶声、黑胶噼啪 |
| `ambient-drift` | 68, C major | 极慢、无鼓、极宽，低频暗，几乎无起音 |
| `chiptune-playful` | 118, G major | 快而亮的 8-bit 主音配密集鼓组，几乎无混响 |

大多数需求都只是这些预设的一次小改动 —— `bpm`、`prog`、`lead_kind`、`lead_div`、`rev_mix` / `rev_t`、`targets`。改动的先后顺序和各风格的频段目标写在 `references/synthesis-cookbook.md`。

---

## 自检到底报了什么

`--qa` 在一次真实渲染里的输出：

```
$ python scripts/render_track.py --preset chiptune-playful --out ./out --bars 8 --seed 1 --qa

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

循环要能交付，`seam_test.py` 的三项独立检查（步进、短窗电平、频谱连续性）必须全过，`seam_focus.py` 在接缝处不能出现 V 形。所有接缝数字都是**相对整首曲子其它位置算出的百分位**，不是绝对值 —— 首尾被强行归零的文件，接缝步进会报 `0.00000`，反而会骗过一个只看绝对值的检查。

自检会**先读 MP3 再读 WAV**。只验 WAV 会漏掉一整类问题，因为有损编码发生在它之后。

---

## 这个 skill 里固化下来的坑

下面每一条都是真实踩过、修掉的，细节在 `references/mixing-rules.md`：

| 症状 | 成因 | 处理 |
|---|---|---|
| 循环开头几秒明显更吵 | 噪声床在 tail-fold **之前**就混进去了，末尾噪声叠到开头（+3 dB） | 先折叠，噪声最后加（§1） |
| 自动配平怎么都不收敛 | 用单帧 FFT 测频段 | 改用 Welch 平均 PSD（§2） |
| 某个频段永远是 0.0% | 编曲里根本没有这个频段的内容 | 回内容层加音源，别推 EQ（§3） |
| 每次循环都有音量凹口 | 循环渲染还带着收尾淡出 | 循环时 `seam_ramp = 0`（§4） |
| 接缝跳变报 `0.00000` 却仍有咔哒声 | 两端被强制归零的**假通过** | 一律用百分位判别，不看绝对值（§5） |

---

## 工作方式

1. **加法合成。** 一个音色就是一叠正弦波：泛音比例定音色，**每个泛音独立衰减**定材质。整数比听感是乐音（弦、管、铺底），非整数比是敲击金属 —— `bell` 用 1 : 2.756 : 5.404 去逼近金属棒。
2. **8-bit 主音。** 三角波和方波混起来，再同时做**幅度量化**（bitcrush）和**时间量化**（采样率压缩）。只做一样像失误，两样一起才是千禧年的电子味。
3. **卷积混响。** 程序生成一段指数衰减的噪声脉冲响应，用 FFT 卷积，中侧声道分开处理。
4. **尾折无缝循环。** 多渲染 3.2 秒尾巴，折回开头，再截到整数小节。混响尾音因此不会在循环点被切断；小节数同时向上取整到整数个和弦周期，绕回来时和声仍然对得上。
5. **自动频段配平。** Welch 平均 PSD 测五个频段（30–120 / 120–500 / 500–2k / 2k–8k / 8–17k）的能量占比，与目标曲线比较，每遍做 ±8 dB 以内的对数插值 EQ，最多 5 遍，误差小于 0.8 dB 就停。
6. **母带。** 归一化 → `tanh` 软限幅（drive 1.15）→ 归一化到 −1.0 dBFS，给 MP3 的过采样峰值留余量。抬高这个上限是通不过 headroom 检查的已知做法。

---

## 目录结构

```
procedural-music/
├── SKILL.md                    skill 定义（触发条件 + 强制工作流）
├── install.py                  一条命令装到本机所有宿主的安装器
├── agents/openai.yaml          Codex 的显示名与默认提示词（可选）
├── .claude-plugin/
│   └── marketplace.json        Claude Code 插件市场清单
├── README.md / README.zh-CN.md
├── LICENSE, requirements.txt
├── scripts/
│   ├── synth_engine.py         乐器 / FX / 测量 / render / 输出
│   ├── presets.py              六套风格预设 + 编曲构建器
│   ├── render_track.py         CLI：预设 → WAV + MP3
│   ├── qa_music.py             自检：电平 / 削波 / 接缝 / 频段 / 立体声宽度
│   ├── seam_test.py             三项独立的循环接缝检测
│   └── seam_focus.py            区分「真凹口」和「编曲本来就稀疏」
├── references/
│   ├── mixing-rules.md        八条铁律 + 症状 → 成因 → 处理表
│   ├── seam-testing.md          为什么绝对接缝数值不可信
│   └── synthesis-cookbook.md    泛音比、包络配方与频段目标
└── examples/                    两份已提交的 demo 渲染
```

## 速度与成本

用仓库里自己的 demo 实测，笔记本 CPU 单线程：

| 渲染 | 时长 | 耗时 |
|---|---|---|
| `y2k-digital --loop --bars 8` | 0:21 | 4.1 秒 |
| `lofi-minimal --loop --bars 16` | 0:43 | 9.4 秒 |

大约是实时速度的 4–5 倍。不需要 GPU，不联网，每次渲染零成本。

## 许可证

MIT，见 [LICENSE](LICENSE)。生成的音频归你所有，不需要署名。
