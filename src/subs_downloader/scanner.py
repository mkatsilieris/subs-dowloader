"""Recursive video file scanner."""

from pathlib import Path

from .config import VIDEO_EXTENSIONS


def scan_videos(root: Path, extensions: set[str] | None = None) -> list[Path]:
    """Recursively scan a directory for video files.

    Args:
        root: Directory to scan.
        extensions: Set of file extensions to match (including dot).
                    Defaults to VIDEO_EXTENSIONS.

    Returns:
        Sorted list of video file paths.
    """
    if extensions is None:
        extensions = VIDEO_EXTENSIONS

    root = root.resolve()
    if not root.is_dir():
        raise FileNotFoundError(f"Directory not found: {root}")

    videos = []
    for path in root.rglob("*"):
        # Skip hidden directories
        if any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.is_file() and path.suffix.lower() in extensions:
            videos.append(path)

    return sorted(videos)
