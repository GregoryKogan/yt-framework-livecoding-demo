#!/usr/bin/env python3
import os
from pathlib import Path
from typing import Any, Iterator

from chatml import ChatMLSingleConversation, ImageInfo
from omegaconf import OmegaConf

from ytjobs.config import get_config_path
from ytjobs.mapper import StreamMapper
from ytjobs.s3.client import S3Client

from stages.build_chatml.src.video_frames import first_and_last_frames


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


def process_row(row: dict[str, Any], **kwargs: object) -> Iterator[dict[str, Any]]:
    config = kwargs["config"]
    s3_download = kwargs["s3_download"]
    s3_upload = kwargs["s3_upload"]

    bucket = row["bucket"]
    path = row["path"]
    video = row["video"]
    captions = row["caption"]
    if not captions:
        return

    video_bytes = s3_download.download(bucket, path)
    img_format = config.job.image_format
    first_bytes, fw, fh, last_bytes, lw, lh = _unpack_frames(
        first_and_last_frames(video_bytes, video, img_format)
    )

    stem = Path(video).stem
    prefix = str(config.job.images_prefix).rstrip("/")
    images_bucket = config.job.images_bucket
    first_key = f"{prefix}/{stem}_first.{img_format}"
    last_key = f"{prefix}/{stem}_last.{img_format}"

    s3_upload.upload(first_bytes, images_bucket, first_key, content_type=f"image/{img_format}")
    s3_upload.upload(last_bytes, images_bucket, last_key, content_type=f"image/{img_format}")

    first_uri = f"s3://{images_bucket}/{first_key}"
    last_uri = f"s3://{images_bucket}/{last_key}"
    question = config.job.question
    shard = config.job.reduce_shard

    for caption, uri, w, h in (
        (captions[0], first_uri, fw, fh),
        (captions[-1], last_uri, lw, lh),
    ):
        conv = ChatMLSingleConversation()
        conv.add_qa(
            question,
            caption,
            images=[ImageInfo(path=uri, width=w, height=h)],
        )
        yield {"shard": shard, "conversation": conv.data}


def _unpack_frames(
    frames: tuple[tuple[bytes, int, int], tuple[bytes, int, int]],
) -> tuple[bytes, int, int, bytes, int, int]:
    (fb, fw, fh), (lb, lw, lh) = frames
    return fb, fw, fh, lb, lw, lh


def main() -> None:
    config = OmegaConf.load(get_config_path())
    secrets = _s3_secrets()
    kwargs = {
        "config": config,
        "s3_download": S3Client.create(secrets=secrets, client_type="download"),
        "s3_upload": S3Client.create(secrets=secrets, client_type="upload"),
    }
    StreamMapper().map(process_row, **kwargs)


if __name__ == "__main__":
    main()
