# yt-framework-livecoding-demo

Demo pipeline for building **MSVD → ChatML** multimodal training data with **[YT Framework](https://yt-framework.readthedocs.io/)** on **[YTsaurus](https://ytsaurus.tech/)**.

## About

This repo walks through a small but realistic data-prep flow: discover videos in S3, join them with MSVD captions on YT, then run a distributed **map-reduce** job that downloads each clip, extracts first/last frames, uploads images to S3, and emits ChatML conversations plus a consolidated NDJSON export.

Captions and videos trace back to the original [MSVD dataset on Hugging Face](https://huggingface.co/datasets/friedrichor/MSVD) (`friedrichor/MSVD`); this pipeline reads a prepared copy from S3 (see **load_msvd** config).

The same stage code runs in **dev** (local JSONL under `.dev/`) and **prod** (YT tables and cluster operations). Prod is the default in [`configs/config.yaml`](configs/config.yaml).

| Stage | What it does |
|-------|----------------|
| **list_s3** | List `.avi` files under an S3 prefix; write `bucket`, `path`, `video` to a YT table |
| **load_msvd** | Load MSVD caption JSON from S3; inner-join with listed videos on `video` via YQL |
| **build_chatml** | Map-reduce (`StreamMapper`): first/last frames via OpenCV, S3 image upload, ChatML rows, NDJSON export |

## Prerequisites

- Python 3.10+
- S3 access (download for videos/JSON, upload for frames and output JSONL)
- **Prod:** YTsaurus cluster access (`YT_PROXY`, `YT_TOKEN` in `configs/secrets.env`)
- **`chatml/`** package at repo root (gitignored; install or copy from your ChatML tooling before running **build_chatml**)

## Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

cp configs/secrets.example.env configs/secrets.env
# Edit configs/secrets.env — see below.
```

### Secrets (`configs/secrets.env`)

| Variable | Purpose |
|----------|---------|
| `S3_ENDPOINT` | S3-compatible endpoint |
| `S3_DOWNLOAD_ACCESS_KEY` / `S3_DOWNLOAD_SECRET_KEY` | Read videos and MSVD JSON |
| `S3_UPLOAD_ACCESS_KEY` / `S3_UPLOAD_SECRET_KEY` | Write frame images and output JSONL (falls back to download keys if omitted) |
| `YT_PROXY` / `YT_TOKEN` | Required for **prod** mode (included in [`configs/secrets.example.env`](configs/secrets.example.env)) |

Do not commit `configs/secrets.env`.

## Run

```bash
python pipeline.py
```

Without a filled `configs/secrets.env`, the pipeline fails early (e.g. `S3_ENDPOINT is not set`).

### Dev mode

Set `pipeline.mode: dev` in [`configs/config.yaml`](configs/config.yaml). Stages write intermediate tables as JSONL under [`.dev/`](.dev/) instead of submitting YT operations.

| File | Stage | Contents |
|------|-------|----------|
| `s3_avi_paths.jsonl` | list_s3 | `bucket`, `path`, `video` |
| `msvd_train.jsonl` | load_msvd | `video`, `caption` |
| `msvd_s3_joined.jsonl` | load_msvd | Joined rows (`bucket`, `path`, `video`, `caption`) |
| `msvd_chatml_conversations.jsonl` | build_chatml | `shard`, `conversation` (2× per input row) |

### Prod mode (default)

Stages use YT paths from stage configs. **build_chatml** runs map-reduce with **`map_job_count: 500`**, reduces by **`shard`**, and allows up to **`max_failed_job_count: 10`** (see [`stages/build_chatml/config.yaml`](stages/build_chatml/config.yaml)).

Example cluster tables (adjust in stage YAML for your environment):

- `//home/visiondata/users/gregorykogan/YT-DEMO/s3_avi_paths`
- `//home/visiondata/users/gregorykogan/YT-DEMO/msvd_train`
- `//home/visiondata/users/gregorykogan/YT-DEMO/msvd_s3_joined`
- `//home/visiondata/users/gregorykogan/YT-DEMO/msvd_chatml_conversations`

Code and dependencies are uploaded to `pipeline.build_folder` on each run.

## Outputs (build_chatml)

Configured in [`stages/build_chatml/config.yaml`](stages/build_chatml/config.yaml) under `job.*`:

| Setting | Default |
|---------|---------|
| `images_bucket` / `images_prefix` | Frame images at `s3://d-gigachat-vision-1/users/gregorykogan/YT-DEMO/MSVD/images/v1/` |
| `json_bucket` / `json_key` | NDJSON at `s3://d-gigachat-vision-1/users/gregorykogan/YT-DEMO/MSVD/json/v1/MSVD.jsonl` |
| `image_format` | `jpg` |
| `question` | User prompt for each QA pair |
| `reduce_shard` | Shard key for reduce (`all` → single reducer group) |

Each input row produces two ChatML conversations: first frame + first caption, last frame + last caption. Images are named `{stem}_first.{format}` and `{stem}_last.{format}`. The reducer writes full rows to the YT output table and uploads a single NDJSON file (one `conversation` JSON object per line) to S3.

## Configuration

| File | Role |
|------|------|
| [`configs/config.yaml`](configs/config.yaml) | Enabled stages, `pipeline.mode`, `build_folder`, `upload_modules` |
| [`stages/list_s3/config.yaml`](stages/list_s3/config.yaml) | S3 bucket/prefix, `avi` filter, output table |
| [`stages/load_msvd/config.yaml`](stages/load_msvd/config.yaml) | MSVD JSON URI, `output_table`, join paths |
| [`stages/build_chatml/config.yaml`](stages/build_chatml/config.yaml) | Map-reduce I/O, `map_job_count`, `reduce_shard`, `image_format`, S3 buckets/keys |

Use `max_files` in **list_s3** config to limit listing during local testing.

## Project layout

```
configs/           # Pipeline + secrets
stages/
  list_s3/         # S3 listing stage
  load_msvd/       # MSVD load + YQL join
  build_chatml/    # Map-reduce: mapper.py, reducer.py, video_frames.py
chatml/            # Local ChatML package (not in git)
pipeline.py        # Entry point
```

## Links

- [MSVD (original dataset)](https://huggingface.co/datasets/friedrichor/MSVD) — Hugging Face
- [YT Framework docs](https://yt-framework.readthedocs.io/)
- [Map operations](https://yt-framework.readthedocs.io/en/latest/operations/map.html)
- [YTsaurus](https://ytsaurus.tech/)
