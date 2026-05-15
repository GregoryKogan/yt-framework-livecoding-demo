#!/usr/bin/env python3
import json
import os
import sys

from omegaconf import OmegaConf

from ytjobs.config import get_config_path
from ytjobs.s3.client import S3Client


def _s3_secrets() -> dict[str, str]:
    download_ak = os.environ.get("S3_DOWNLOAD_ACCESS_KEY", "")
    download_sk = os.environ.get("S3_DOWNLOAD_SECRET_KEY", "")
    return {
        "S3_ENDPOINT": os.environ.get("S3_ENDPOINT", ""),
        "S3_DOWNLOAD_ACCESS_KEY": download_ak,
        "S3_DOWNLOAD_SECRET_KEY": download_sk,
        "S3_UPLOAD_ACCESS_KEY": os.environ.get("S3_UPLOAD_ACCESS_KEY") or download_ak,
        "S3_UPLOAD_SECRET_KEY": os.environ.get("S3_UPLOAD_SECRET_KEY") or download_sk,
    }


def main() -> None:
    config = OmegaConf.load(get_config_path())
    lines: list[str] = []

    for raw in sys.stdin:
        line = raw.strip()
        if not line:
            continue
        row = json.loads(line)
        conversation = row["conversation"]
        lines.append(json.dumps(conversation, ensure_ascii=False))
        print(json.dumps(row), flush=True)

    body = ("\n".join(lines) + "\n").encode("utf-8")
    s3 = S3Client.create(secrets=_s3_secrets(), client_type="upload")
    s3.upload(
        body,
        config.job.json_bucket,
        config.job.json_key,
        content_type="application/x-ndjson",
    )


if __name__ == "__main__":
    main()
