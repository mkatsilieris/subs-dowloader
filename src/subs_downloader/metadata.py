"""Video file metadata extraction: hash computation, name parsing."""

import re
import struct
from pathlib import Path

from .config import HASH_CHUNK_SIZE


def compute_hash(filepath: Path) -> str:
    """Compute the OpenSubtitles hash for a video file.

    Algorithm: read first and last 64KB, interpret as little-endian uint64 array,
    sum all values together with the file size, return lower 64 bits as hex.

    Args:
        filepath: Path to the video file.

    Returns:
        16-character lowercase hex string.
    """
    filesize = filepath.stat().st_size
    if filesize < HASH_CHUNK_SIZE * 2:
        raise ValueError(f"File too small for hash computation: {filepath}")

    hash_value = filesize
    fmt = f"<{HASH_CHUNK_SIZE // 8}Q"  # little-endian uint64 array

    with open(filepath, "rb") as f:
        # Read first 64KB
        buf = f.read(HASH_CHUNK_SIZE)
        for val in struct.unpack(fmt, buf):
            hash_value = (hash_value + val) & 0xFFFFFFFFFFFFFFFF

        # Read last 64KB
        f.seek(-HASH_CHUNK_SIZE, 2)
        buf = f.read(HASH_CHUNK_SIZE)
        for val in struct.unpack(fmt, buf):
            hash_value = (hash_value + val) & 0xFFFFFFFFFFFFFFFF

    return f"{hash_value:016x}"


def parse_video_name(filepath: Path) -> dict:
    """Extract metadata from a video filename.

    Tries to extract title, year, season, and episode from common naming patterns.

    Args:
        filepath: Path to the video file.

    Returns:
        Dict with keys: query (cleaned search string), title, year, season, episode.
    """
    stem = filepath.stem
    result: dict = {"query": stem, "title": None, "year": None, "season": None, "episode": None}

    # Try to extract S01E02 pattern
    ep_match = re.search(r"[Ss](\d{1,2})[Ee](\d{1,2})", stem)
    if ep_match:
        result["season"] = int(ep_match.group(1))
        result["episode"] = int(ep_match.group(2))

    # Try to extract year (4 digits, likely 19xx or 20xx)
    year_match = re.search(r"[\.\s\-\(]?((?:19|20)\d{2})[\.\s\-\)\]]?", stem)
    if year_match:
        result["year"] = int(year_match.group(1))

    # Clean the stem for search: replace dots/underscores with spaces, strip junk
    cleaned = stem
    # Remove everything after common quality/codec tags
    cleaned = re.split(
        r"[\.\s\-](?:720p|1080p|2160p|4[Kk]|BRRip|BluRay|WEB[\-\.]?(?:DL|Rip)|HDRip|DVDRip|x264|x265|H\.?264|H\.?265|HEVC|AAC|DTS|YIFY|RARBG|XviD)",
        cleaned,
    )[0]
    # Replace separators with spaces
    cleaned = re.sub(r"[\.\-_]", " ", cleaned)
    # Remove extra whitespace
    cleaned = re.sub(r"\s+", " ", cleaned).strip()

    result["query"] = cleaned
    if not result["title"]:
        # Title is everything before year or SxxExx
        title = cleaned
        if result["year"]:
            title = title.split(str(result["year"]))[0].strip()
        if ep_match:
            title = re.split(r"[Ss]\d", title)[0].strip()
        result["title"] = title

    return result
