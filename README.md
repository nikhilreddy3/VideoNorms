# VideoNorms (Cleaned Release)

Cleaned, documented, and ready-to-share version of the **VideoNorms** dataset:
cultural-norm annotations of 15-second clips from popular **US** and **Chinese**
TV shows, each labeled for norm **adherence vs. violation** with supporting
**verbal** and **non-verbal** evidence.

> **Source paper:** Varimalla, Xu, Wang, Saakyan, Muresan.
> *VideoNorms: Benchmarking Socio-Cultural Norm Understanding of Video Language Models.*
> arXiv:2510.08543 — <https://arxiv.org/abs/2510.08543>
> License: CC BY 4.0 (per the arXiv posting).

This release contains the cleaned annotations (formatting normalized, encoding
bugs fixed, schema unified, metadata attached) plus a script to rebuild the
video clips from their public YouTube links. Nothing in the underlying judgments
was altered.

---

## What's in this folder

```
VideoNorms_clean/
├── README.md                                   <- this file
├── clip_videos.py                              downloads + clips the source videos
├── offsets.json                                per-section start offsets (multi-section videos)
├── benchmark/                                  VideoNorms-Benchmark (consensus subset)
│   ├── videonorms_benchmark_all.json           542 items (EN + ZH)
│   └── videonorms_benchmark.csv                542 items, flat
└── full/                                       VideoNorms-Full (raw 3-annotator set)
    ├── videonorms_full_all.json                1,012 items (EN + ZH)
    └── videonorms_full_annotations_long.csv    3,035 rows, one row per annotator
```

### Which file should I use?

| Use case | File |
|---|---|
| Benchmarking / evaluating a model (single gold label) | `benchmark/videonorms_benchmark_all.json` or `.csv` |
| Studying annotator disagreement / pluralistic labels | `full/videonorms_full_all.json` |
| Quick analysis in pandas / Excel | the `.csv` files |
| US-only or China-only experiments | filter any file by `language` (`en`/`zh`) or `culture` |

---

## The two datasets

### 1. `benchmark/` — VideoNorms-Benchmark (542 items)

The **high-reliability subset** used for model evaluation in the paper. These are
items where all three annotators agreed on context, category, subject, specific
norm, and adherence/violation (2-vs-1 splits were resolved by two additional
meta-annotators via 4/5 majority vote). Each item carries **one gold label**.

- **US (EN):** 273 items — 174 Adherence / 99 Violation
- **China (ZH):** 269 items — 223 遵守 (adherence) / 46 违反 (violation)

### 2. `full/` — VideoNorms-Full (1,012 items, 3,035 judgments)

The **complete set of raw human annotations** (the paper's "over 3,000 human
judgments"), released for the study of disagreement and pluralistic approaches.
Every item was independently annotated by **3 monocultural annotators**, so each
item contains up to three parallel judgments, preserved in an `annotations` list.

- **US (EN):** 511 items
- **China (ZH):** 501 items

---

## Field reference

### Shared metadata (both datasets)

| Field | Type | Description |
|---|---|---|
| `item_id` | string | Stable id. Benchmark: `en_0`, `zh_0`, … ; Full: `en_full_0`, `zh_full_0`, … |
| `language` | string | `en` (US shows) or `zh` (Chinese shows) |
| `culture` | string | `US` or `China` |
| `show` | string | Human-readable show title (see mapping below) |
| `show_key` | string | Original folder key from `video_file` |
| `genre` | string | `Comedy` or `Drama` |
| `setting` | string | `Workplace` (formal) or `Informal` |
| `video_file` | string | Relative path to the 15-second clip |
| `youtube_link_unclipped` | string | YouTube URL for the full source video |
| `segment_start`, `segment_end` | int | Clip window (seconds) within the source part |
| `timestamp_start`, `timestamp_end` | string | Time of the norm event within the clip (`m:ss`) |
| `transcript` | string | Spoken-dialogue transcript of the 15-second clip (same for all annotations sharing a clip) |

### Benchmark-only annotation fields (single gold label)

| Field | Type | Description |
|---|---|---|
| `norm_category` | string | Norm category, e.g. *Expressing criticism*, *Requesting information* (Chinese categories kept in Chinese) |
| `specific_norm` | string | Precise articulation of the expected behavior |
| `norm_adherence` | string | **Original label, verbatim.** EN: `Adherence`/`Violation`; ZH: `遵守`/`违反` |
| `verbal_evidence` | string | Spoken-content evidence (quotes, tone) |
| `nonverbal_evidence` | string | Visual evidence (gaze, gesture, expression) |

### Full-set-only fields (3 annotators per item)

| Field | Type | Description |
|---|---|---|
| `num_annotators` | int | Number of annotators who provided a non-empty judgment (≤ 3) |
| `adherence_labels` | list | The per-annotator adherence labels (abstentions → `null`) |
| `adherence_agreement` | string | Agreement **on the adherence label only**: `unanimous`, `majority`, `split`, or `insufficient` (<2 valid labels) |
| `annotations` | list of objects | One object per annotator, each with `annotator_index`, `norm_category`, `specific_norm`, `norm_adherence`, `verbal_evidence`, `nonverbal_evidence` |

> Note: `adherence_agreement` measures agreement on the adherence label alone, so
> it is naturally higher than the paper's "all 3 agree" rate, which requires
> agreement across *all* fields.

---

## Show → metadata mapping (paper §3.1)

| `show_key` | Show | Culture | Genre | Setting |
|---|---|---|---|---|
| `friends_videos` | Friends | US | Comedy | Informal |
| `bbt_videos` | The Big Bang Theory | US | Comedy | Informal |
| `office_videos` | The Office | US | Comedy | Workplace |
| `suits_videos` | Suits | US | Drama | Workplace |
| `ipartment_clips_all` | iPartment | China | Comedy | Informal |
| `hwk_clips_all` | Home with Kids | China | Comedy | Informal |
| `amazing_night_clips_all` | Amazing Night | China | Comedy | Workplace |
| `legal_clips_all` | The Best Partner | China | Drama | Workplace |

---

## Cleaning steps applied

1. **Fixed URL encoding.** Decoded HTML entities (`&amp;` → `&`) and repaired a
   double-encoding bug in some Chinese URLs (`&amp%3B` → `&`). Remaining `%3B` /
   `%3D` are valid YouTube query encodings and were left intact.
2. **Normalized empty / abstention values** (`""`, `N/A`, `None`, `无`/`無`) to
   JSON `null` so missing data is unambiguous.
3. **Typed the numeric fields** — `segment_start` / `segment_end` are integers.
4. **Collapsed per-annotator timestamp lists** in the full set to the shared value.
5. **Attached metadata** — `language`, `culture`, `show`, `genre`, `setting`.
6. **Unified the schema** across EN and ZH; dropped the always-empty
   `correct_annotation` field from the Chinese benchmark file.
7. **Restructured the full set** from five parallel per-annotator lists into a
   clean `annotations` list, and added `adherence_agreement`.
8. **Preserved original labels verbatim** — Chinese adherence labels remain
   `遵守` / `违反` (not translated).

Adherence-agreement breakdown of the full set after cleaning:

| | unanimous | majority | split | insufficient |
|---|---|---|---|---|
| US (EN) | 387 | 120 | 4 | 0 |
| China (ZH) | 362 | 109 | 14 | 16 |

---

## Reconstructing the video clips

The dataset ships text annotations and links only — not the video files. To
rebuild the 15-second clips locally (into the exact `video_file` paths), use the
included [`clip_videos.py`](clip_videos.py). It downloads each public source
video (`youtube_link_unclipped`) once and cuts every segment with ffmpeg.

Requires `yt-dlp` and `ffmpeg`:

```bash
pip install yt-dlp          # or: brew install yt-dlp
brew install ffmpeg         # or your package manager
```

Then, from inside `VideoNorms_clean/`:

```bash
python3 clip_videos.py --dry-run --limit 5     # preview the plan
python3 clip_videos.py                          # clip everything into ./clips
python3 clip_videos.py --input benchmark/videonorms_benchmark_all.json
python3 clip_videos.py --cookies-from-browser chrome   # if YouTube asks to sign in
```

Clips are written under `clips/<video_file>`, mirroring the dataset paths, e.g.
`clips/friends_videos/friends_videos_clips/friends_video1/friends_video1_part_0015-0030.mp4`.
The run is idempotent (existing clips are skipped; `--overwrite` to force) and
each source video is cached in `_source_cache/` so it downloads only once.

**Section-relative timing — handled automatically.** Some source videos were
originally split into several 2-3 minute sections (visible when one URL maps to
multiple `*_clipN` folders). For those, the public `segment_start`/`segment_end`
restart at 0 within each section, so a frame-accurate cut needs that section's
start offset in the full video. Those offsets are shipped in
[`offsets.json`](offsets.json) (a mapping of `srcdir -> start-offset-seconds`)
and `clip_videos.py` loads it automatically, so multi-section clips are cut from
the correct position out of the box. Pass `--offsets ''` to disable, or
`--offsets path.json` to override.

---

## Citation

```bibtex
@article{varimalla2026videonorms,
  title   = {VideoNorms: Benchmarking Socio-Cultural Norm Understanding of Video Language Models},
  author  = {Varimalla, Nikhil Reddy and Xu, Yunfei and Wang, Meng Fan and Saakyan, Arkadiy and Muresan, Smaranda},
  journal = {arXiv preprint arXiv:2510.08543},
  year    = {2026},
  url     = {https://arxiv.org/abs/2510.08543}
}
```

## Responsible use

The dataset treats "US" and "China" as broad cultural contexts for research
convenience; it does **not** capture full intra-cultural diversity. Per the
authors, it should not be used for stereotyping or to infer individual-level
traits from national-level data (ecological fallacy). Video content belongs to
the respective rights holders; only URLs and clip references are distributed.
