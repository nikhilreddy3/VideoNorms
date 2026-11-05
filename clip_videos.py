#!/usr/bin/env python3
"""
clip_videos.py
==============

Download the source YouTube videos for the VideoNorms dataset and cut them into
the 15-second clips described by each record, saving them under the exact
`video_file` paths used in the dataset.

For every record we use:
  * `youtube_link_unclipped`  -- the public source video to download
  * `segment_start`, `segment_end` -- the clip window (seconds)
  * `video_file`              -- the relative output path to save the clip to

Example output layout (mirrors the dataset's `video_file` field):

  clips/
    friends_videos/friends_videos_clips/friends_video1/friends_video1_part_0015-0030.mp4
    ipartment_clips_all/ipartment_video1_clip1/ipartment_video1_clip1_part_0060-0075.mp4
    ...

Requirements (external tools):
  * yt-dlp  ->  pip install yt-dlp   (or: brew install yt-dlp)
  * ffmpeg  ->  brew install ffmpeg  (or your package manager)

Basic usage:
  python3 clip_videos.py                         # clips everything into ./clips
  python3 clip_videos.py --limit 5 --dry-run     # preview the first 5
  python3 clip_videos.py --input benchmark/videonorms_benchmark_all.json
  python3 clip_videos.py --cookies-from-browser chrome   # if YouTube blocks you

Notes / caveats:
  * Each source video is downloaded only once and cached (see --source-cache),
    then all of its clips are cut with ffmpeg. Re-running is idempotent: clips
    that already exist are skipped (use --overwrite to force).
  * Some source videos were originally divided into several 2-3 minute sections
    (seen when one URL maps to multiple `*_clipN` folders). For those, the
    public segment times restart at 0 within each section, so the section's
    offset within the full video is required for a frame-accurate cut. That
    offset is not part of the public fields. If you have them, pass a mapping
    with --offsets offsets.json (see --help) and they will be added to the
    segment start. Without it, such clips are cut from the raw segment time.
"""

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from urllib.parse import urlparse, parse_qs

HERE = os.path.dirname(os.path.abspath(__file__))
DEFAULT_INPUT = os.path.join(HERE, "full", "videonorms_full_all.json")


# --------------------------------------------------------------------------- #
# Helpers
# --------------------------------------------------------------------------- #
def have(cmd):
    return shutil.which(cmd) is not None


def video_id(url):
    """Best-effort stable cache key from a YouTube URL."""
    try:
        u = urlparse(url)
        if "youtu.be" in u.netloc:
            return u.path.strip("/").split("/")[0]
        if "/embed/" in u.path:
            return u.path.split("/embed/")[1].split("/")[0]
        q = parse_qs(u.query)
        if "v" in q:
            return q["v"][0]
    except Exception:
        pass
    # fallback: hash of the url
    import hashlib
    return "vid_" + hashlib.md5((url or "").encode()).hexdigest()[:12]


def srcdir_of(video_file):
    return "/".join(video_file.split("/")[:-1])


def run(cmd, quiet=True):
    return subprocess.run(
        cmd,
        stdout=(subprocess.DEVNULL if quiet else None),
        stderr=(subprocess.PIPE if quiet else None),
        text=True,
    )


# --------------------------------------------------------------------------- #
# Core
# --------------------------------------------------------------------------- #
def download_source(url, cache_dir, extra_ytdlp, quiet=True):
    """Download a source video once; return the local file path (or None)."""
    vid = video_id(url)
    os.makedirs(cache_dir, exist_ok=True)

    # already cached?
    for f in os.listdir(cache_dir):
        if f.startswith(vid + "."):
            return os.path.join(cache_dir, f)

    out_tmpl = os.path.join(cache_dir, vid + ".%(ext)s")
    cmd = [
        "yt-dlp",
        "--no-playlist",
        "-f", "bv*+ba/b",
        "--merge-output-format", "mp4",
        "-o", out_tmpl,
        *extra_ytdlp,
        url,
    ]
    res = run(cmd, quiet=quiet)
    if res.returncode != 0:
        if quiet and res.stderr:
            sys.stderr.write(res.stderr.splitlines()[-1] + "\n" if res.stderr.strip() else "")
        return None

    for f in os.listdir(cache_dir):
        if f.startswith(vid + "."):
            return os.path.join(cache_dir, f)
    return None


def cut_clip(src, start, duration, out_path, quiet=True):
    """Cut [start, start+duration] from src into out_path (re-encoded)."""
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    cmd = ["ffmpeg", "-y", "-ss", str(start), "-i", src]
    if duration is not None:
        cmd += ["-t", str(duration)]
    cmd += [
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "20",
        "-c:a", "aac", "-movflags", "+faststart",
        "-avoid_negative_ts", "make_zero",
        out_path,
    ]
    res = run(cmd, quiet=quiet)
    return res.returncode == 0


def load_records(input_path):
    """Return de-duplicated clip jobs: one per unique video_file."""
    data = json.load(open(input_path, encoding="utf-8"))
    jobs = {}
    skipped = 0
    for rec in data:
        vf = rec.get("video_file")
        url = rec.get("youtube_link_unclipped")
        ss, se = rec.get("segment_start"), rec.get("segment_end")
        if not vf or not url or ss is None:
            skipped += 1
            continue
        if vf not in jobs:
            jobs[vf] = {
                "video_file": vf,
                "url": url,
                "segment_start": ss,
                "segment_end": se,
                "srcdir": srcdir_of(vf),
            }
    return list(jobs.values()), skipped


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def main():
    ap = argparse.ArgumentParser(
        description="Clip VideoNorms source videos into per-segment mp4 files.",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    ap.add_argument("--input", default=DEFAULT_INPUT,
                    help="Cleaned dataset JSON to read clip jobs from.")
    ap.add_argument("--output-dir", default=os.path.join(HERE, "clips"),
                    help="Root directory for saved clips (mirrors video_file).")
    ap.add_argument("--source-cache", default=os.path.join(HERE, "_source_cache"),
                    help="Directory to cache downloaded source videos.")
    ap.add_argument("--offsets", default=os.path.join(HERE, "offsets.json"),
                    help="JSON mapping srcdir -> start-offset seconds, added to each "
                         "segment_start (for multi-section videos). Defaults to the "
                         "bundled offsets.json; pass '' to disable.")
    ap.add_argument("--limit", type=int, default=None, help="Process at most N clips.")
    ap.add_argument("--overwrite", action="store_true", help="Re-cut clips that already exist.")
    ap.add_argument("--keep-sources", action="store_true", default=True,
                    help="Keep cached source videos after clipping.")
    ap.add_argument("--delete-sources", dest="keep_sources", action="store_false",
                    help="Delete each source video once all its clips are cut.")
    ap.add_argument("--cookies-from-browser", default=None,
                    help="Pass a browser name to yt-dlp (e.g. chrome) for auth.")
    ap.add_argument("--cookies", default=None, help="Path to a cookies.txt for yt-dlp.")
    ap.add_argument("--dry-run", action="store_true", help="Show what would happen; no downloads.")
    ap.add_argument("--verbose", action="store_true", help="Show yt-dlp/ffmpeg output.")
    args = ap.parse_args()

    quiet = not args.verbose

    # dependency check (skipped for dry-run)
    if not args.dry_run:
        missing = [t for t in ("yt-dlp", "ffmpeg") if not have(t)]
        if missing:
            sys.exit(
                "Missing required tool(s): " + ", ".join(missing) +
                "\n  yt-dlp: pip install yt-dlp\n  ffmpeg: brew install ffmpeg"
            )

    offsets = {}
    if args.offsets and os.path.exists(args.offsets):
        offsets = json.load(open(args.offsets, encoding="utf-8"))

    extra_ytdlp = []
    if args.cookies_from_browser:
        extra_ytdlp += ["--cookies-from-browser", args.cookies_from_browser]
    if args.cookies:
        extra_ytdlp += ["--cookies", args.cookies]

    jobs, skipped = load_records(args.input)
    if args.limit:
        jobs = jobs[:args.limit]

    # group by source url so each video downloads once
    by_url = defaultdict(list)
    for j in jobs:
        by_url[j["url"]].append(j)

    print(f"Input:        {args.input}")
    print(f"Clip jobs:    {len(jobs)} unique clips from {len(by_url)} source videos "
          f"({skipped} records skipped for missing url/segment)")
    print(f"Output dir:   {args.output_dir}")
    print(f"Source cache: {args.source_cache}")
    if offsets:
        print(f"Offsets:      {len(offsets)} srcdir overrides loaded")
    print()

    n_done = n_skipexist = n_dl_fail = n_cut_fail = 0

    for url, group in by_url.items():
        # which outputs still need cutting?
        todo = []
        for j in group:
            out_path = os.path.join(args.output_dir, j["video_file"])
            if os.path.exists(out_path) and not args.overwrite:
                n_skipexist += 1
            else:
                todo.append((j, out_path))
        if not todo:
            continue

        if args.dry_run:
            for j, out_path in todo:
                off = offsets.get(j["srcdir"], 0)
                start = j["segment_start"] + off
                dur = None if j["segment_end"] is None else j["segment_end"] - j["segment_start"]
                print(f"[dry] {video_id(url)} ss={start} dur={dur} -> {j['video_file']}")
            continue

        print(f"Downloading source {video_id(url)} ({len(todo)} clips to cut)...")
        src = download_source(url, args.source_cache, extra_ytdlp, quiet=quiet)
        if not src:
            n_dl_fail += len(todo)
            print(f"  ! download failed: {url}")
            continue

        for j, out_path in todo:
            off = offsets.get(j["srcdir"], 0)
            start = j["segment_start"] + off
            dur = None if j["segment_end"] is None else j["segment_end"] - j["segment_start"]
            ok = cut_clip(src, start, dur, out_path, quiet=quiet)
            if ok:
                n_done += 1
            else:
                n_cut_fail += 1
                print(f"  ! ffmpeg failed: {j['video_file']}")

        if not args.keep_sources:
            try:
                os.remove(src)
            except OSError:
                pass

    print()
    print("=== Summary ===")
    print(f"  clips written:       {n_done}")
    print(f"  skipped (existing):  {n_skipexist}")
    print(f"  download failures:   {n_dl_fail}")
    print(f"  ffmpeg failures:     {n_cut_fail}")
    if args.dry_run:
        print("  (dry-run: nothing downloaded or written)")


if __name__ == "__main__":
    main()
