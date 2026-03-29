"""Shared test fixtures."""

import os
from pathlib import Path
from unittest.mock import MagicMock

import pytest

from subs_downloader.providers import AbstractProvider, SubtitleResult


@pytest.fixture
def video_dir(tmp_path: Path) -> Path:
    """Create a temp directory with dummy video files."""
    # Create video files (need to be large enough for hash: 128KB+)
    for name in ["Movie.2024.1080p.mp4", "Show.S01E02.mkv", "documentary.avi"]:
        f = tmp_path / name
        f.write_bytes(os.urandom(200_000))  # 200KB

    # Create a nested directory with another video
    nested = tmp_path / "season1"
    nested.mkdir()
    (nested / "Show.S01E03.mov").write_bytes(os.urandom(200_000))

    # Create a non-video file that should be ignored
    (tmp_path / "readme.txt").write_text("not a video")

    # Create a hidden directory that should be skipped
    hidden = tmp_path / ".hidden"
    hidden.mkdir()
    (hidden / "secret.mp4").write_bytes(os.urandom(200_000))

    return tmp_path


@pytest.fixture
def mock_provider() -> MagicMock:
    """Create a mock subtitle provider."""
    provider = MagicMock(spec=AbstractProvider)
    provider.name = "mock"

    provider.search_by_hash.return_value = [
        SubtitleResult(
            provider="mock",
            subtitle_id="1",
            language="eng",
            filename="Movie.2024.srt",
            file_id=100,
            score=8.5,
            download_count=5000,
        ),
        SubtitleResult(
            provider="mock",
            subtitle_id="2",
            language="ell",
            filename="Movie.2024.gr.srt",
            file_id=101,
            score=7.0,
            download_count=1200,
        ),
    ]

    provider.download.return_value = b"1\n00:00:01,000 --> 00:00:02,000\nHello\n"
    return provider
