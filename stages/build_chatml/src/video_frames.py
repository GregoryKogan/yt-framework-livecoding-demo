import tempfile
from pathlib import Path

import cv2


def extract_frame_bytes(
    video_bytes: bytes,
    frame_index: int,
    suffix: str,
    img_format: str,
) -> tuple[bytes, int, int]:
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        tmp.write(video_bytes)
        tmp.flush()

        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise RuntimeError("Cannot open video")

        cap.set(cv2.CAP_PROP_POS_FRAMES, frame_index)
        ok, frame = cap.read()
        if not ok:
            raise RuntimeError(f"Failed to read frame {frame_index}")

        height, width = frame.shape[:2]
        success, encoded = cv2.imencode(f".{img_format}", frame)
        cap.release()
        if not success:
            raise RuntimeError("Failed to encode frame")
        return encoded.tobytes(), width, height


def first_and_last_frames(
    video_bytes: bytes,
    video_name: str,
    img_format: str,
) -> tuple[tuple[bytes, int, int], tuple[bytes, int, int]]:
    suffix = Path(video_name).suffix or ".avi"
    with tempfile.NamedTemporaryFile(delete=True, suffix=suffix) as tmp:
        tmp.write(video_bytes)
        tmp.flush()
        cap = cv2.VideoCapture(tmp.name)
        if not cap.isOpened():
            raise RuntimeError("Cannot open video")
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        cap.release()

    if frame_count < 1:
        raise RuntimeError("Video has no frames")

    first = extract_frame_bytes(video_bytes, 0, suffix, img_format)
    last = extract_frame_bytes(video_bytes, frame_count - 1, suffix, img_format)
    return first, last
