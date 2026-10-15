#!/usr/bin/env python3
"""Install this skill into every agent host found on the machine.

One clone, several hosts. The skill is plain Agent Skills layout
(``SKILL.md`` + ``scripts/`` + ``references/``), so Claude Code, OpenAI Codex,
WorkBuddy and CodeBuddy all read the same folder.

    python install.py                 # link into every host that exists here
    python install.py --copy          # independent copies instead of links
    python install.py --hosts claude,codex
    python install.py --list          # show what was detected, change nothing
    python install.py --uninstall     # remove this skill from every host

Default mode is ``link`` (Windows directory junction, POSIX symlink) so the
clone stays the single source of truth: ``git pull`` updates every host at
once. ``--copy`` trades that for independent copies. If a host cannot hold a
link, the installer falls back to a copy and says so.

Nothing is overwritten silently: a destination that holds this skill is
replaced, a destination that holds something else is left alone and reported.
"""

from __future__ import annotations

import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

SKILL_NAME = "procedural-music"
HOME = Path.home()
IS_WINDOWS = os.name == "nt"

# host key -> (label, config dir, name of the skills subdirectory)
HOSTS = {
    "claude": ("Claude Code", lambda: HOME / ".claude", "skills"),
    "codex": ("OpenAI Codex", lambda: Path(os.environ.get("CODEX_HOME") or HOME / ".codex"), "skills"),
    "agents": ("shared .agents convention", lambda: HOME / ".agents", "skills"),
    "workbuddy": ("WorkBuddy", lambda: HOME / ".workbuddy", "skills"),
    "codebuddy": ("CodeBuddy", lambda: HOME / ".codebuddy", "skills"),
}
DEFAULT_ORDER = ("claude", "codex", "agents", "workbuddy", "codebuddy")


def read_skill_name(skill_md: Path) -> str | None:
    """Return the `name:` field from a SKILL.md front matter, or None."""
    try:
        text = skill_md.read_text(encoding="utf-8")
    except OSError:
        return None
    if not text.startswith("---"):
        return None
    for line in text.splitlines()[1:]:
        if line.strip() == "---":
            break
        if line.lower().startswith("name:"):
            return line.split(":", 1)[1].strip().strip("\"'")
    return None


def is_link(path: Path) -> bool:
    if os.path.islink(path):
        return True
    return bool(getattr(path, "is_junction", lambda: False)())


def remove_link(path: Path) -> None:
    """Delete a link/junction without touching what it points at."""
    try:
        os.rmdir(path)
    except OSError:
        os.unlink(path)


def make_link(src: Path, dest: Path) -> None:
    """Create a directory link. Raises OSError when the host cannot."""
    if IS_WINDOWS:
        proc = subprocess.run(
            ["cmd", "/c", "mklink", "/J", str(dest), str(src)],
            capture_output=True,
            text=True,
            shell=False,
        )
        if proc.returncode != 0 or not dest.exists():
            raise OSError((proc.stderr or proc.stdout or "mklink failed").strip())
    else:
        os.symlink(src, dest, target_is_directory=True)


def occupancy(dest: Path) -> str:
    """What, if anything, already sits at dest: free / ours-link / ours-copy / other."""
    if not dest.exists() and not is_link(dest):
        return "free"
    if is_link(dest):
        try:
            target = Path(os.path.realpath(dest))
            return "ours-link" if (target / "SKILL.md").exists() else "other"
        except OSError:
            return "other"
    if dest.is_dir():
        name = read_skill_name(dest / "SKILL.md")
        return "ours-copy" if name == SKILL_NAME else "other"
    return "other"


def install(src: Path, dest: Path, mode: str, force: bool, dry: bool) -> str:
    state = occupancy(dest)

    if state == "other" and not force:
        return "skip  (something else is already there: %s)" % dest
    if state == "ours-link":
        try:
            if Path(os.path.realpath(dest)) == src:
                return "ok    (already installed)"
        except OSError:
            pass

    if dry:
        return "would %s %s" % (mode, dest)

    if state in ("ours-link", "ours-copy", "other"):
        if is_link(dest):
            remove_link(dest)
        else:
            shutil.rmtree(dest)

    dest.parent.mkdir(parents=True, exist_ok=True)
    if mode == "copy":
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pm-test"))
        return "copy  %s" % dest

    try:
        make_link(src, dest)
        return "link  %s" % dest
    except OSError as exc:
        why = str(exc).splitlines()[0][:60] if str(exc) else "not supported"
        shutil.copytree(src, dest, ignore=shutil.ignore_patterns(".git", "__pycache__", ".pm-test"))
        return "copy  %s  (link unavailable: %s)" % (dest, why)


def uninstall(dest: Path, dry: bool) -> str:
    state = occupancy(dest)
    if state == "free":
        return "ok    (not installed)"
    if state == "other":
        return "skip  (not our skill, left alone: %s)" % dest
    if dry:
        return "would remove %s" % dest
    if is_link(dest):
        remove_link(dest)
    else:
        shutil.rmtree(dest)
    return "gone  %s" % dest


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(
        prog="install.py",
        description="Install the %s skill into every agent host on this machine." % SKILL_NAME,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            "examples:\n"
            "  python install.py                  link into every host found here\n"
            "  python install.py --copy           independent copies\n"
            "  python install.py --hosts claude,codex\n"
            "  python install.py --list\n"
            "  python install.py --uninstall\n"
        ),
    )
    ap.add_argument("--source", default=None, help="skill folder to install (default: this script's folder)")
    ap.add_argument("--hosts", default=None,
                    help="comma-separated subset of: %s (default: every host found)" % ", ".join(DEFAULT_ORDER))
    ap.add_argument("--mode", choices=("link", "copy"), default="link", help="link (default) or copy")
    ap.add_argument("--list", action="store_true", help="show detected hosts and exit")
    ap.add_argument("--dry-run", action="store_true", help="show what would happen, change nothing")
    ap.add_argument("--uninstall", action="store_true", help="remove this skill from the selected hosts")
    ap.add_argument("--force", action="store_true", help="replace a destination that holds something else")
    args = ap.parse_args(argv)

    src = Path(args.source).expanduser().resolve() if args.source else Path(__file__).resolve().parent
    if not (src / "SKILL.md").is_file():
        print("error: no SKILL.md in %s — point --source at the skill folder" % src, file=sys.stderr)
        return 2
    found_name = read_skill_name(src / "SKILL.md")
    if found_name != SKILL_NAME:
        print("error: SKILL.md name is %r, expected %r" % (found_name, SKILL_NAME), file=sys.stderr)
        return 2

    present = {}
    for key in DEFAULT_ORDER:
        label, config_dir, sub = HOSTS[key]
        root = config_dir()
        present[key] = (label, root / sub, root.exists())
    # present[key] = (label, skills root, host found on this machine)

    if args.hosts:
        wanted = [h.strip().lower() for h in args.hosts.split(",") if h.strip()]
        unknown = [h for h in wanted if h not in HOSTS]
        if unknown:
            print("error: unknown host(s) %s — pick from %s" % (", ".join(unknown), ", ".join(DEFAULT_ORDER)),
                  file=sys.stderr)
            return 2
        selected = wanted
    else:
        selected = [k for k in DEFAULT_ORDER if present[k][2]]

    print("skill   : %s" % src)
    print("command : %s" % ("uninstall" if args.uninstall else "install (%s)" % args.mode))
    print()

    if args.list or not selected:
        print("hosts on this machine:")
        for key in DEFAULT_ORDER:
            label, root, exists = present[key]
            dest = root / SKILL_NAME
            state = occupancy(dest)
            print("  %-10s %-26s %-7s %s" % (
                key, label,
                "found" if exists else "absent",
                ("not installed" if state == "free" else state) + "  ->  " + str(dest),
            ))
        print()
        if not selected and not args.list:
            print("nothing to install into — pass --hosts to create one, e.g. --hosts claude,codex")
        return 0

    results = []
    for key in selected:
        label, root = present[key][0], present[key][1]
        dest = root / SKILL_NAME
        if args.uninstall:
            note = uninstall(dest, args.dry_run)
        elif src == Path(os.path.realpath(dest)):
            note = "ok    (this clone already lives here)"
        else:
            note = install(src, dest, args.mode, args.force, args.dry_run)
        results.append((key, label, note))
        print("  %-10s %-26s %s" % (key, label, note))

    skipped = [r for r in results if r[2].startswith("skip")]
    print()
    if args.dry_run:
        print("dry run — nothing was written")
    if skipped:
        print("%d host(s) skipped (pass --force to replace them)" % len(skipped))

    if not args.uninstall and not args.dry_run and results:
        print("next: ask your agent for a track, or render one directly:")
        print("  python scripts/render_track.py --preset lofi-minimal --out ./out --loop --bars 16 --qa")
        print("restart the host so it rescans its skills folder. Codex can also toggle the skill with")
        print("[[skills.config]] in config.toml; the bundled agents/openai.yaml supplies its display name.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
