"""Tests for the download orchestration module."""

from pathlib import Path
from unittest.mock import MagicMock

from subs_downloader.downloader import process_directory, process_video
from subs_downloader.providers import SubtitleResult


def test_process_video_downloads_subtitles(video_dir: Path, mock_provider: MagicMock):
    video = video_dir / "Movie.2024.1080p.mp4"
    result = process_video(video, ["eng", "ell"], [mock_provider])

    assert len(result.downloaded) == 2
    subs_dir = video.parent / "subs"
    assert subs_dir.exists()
    assert (subs_dir / "Movie.2024.1080p.ENG.001.srt").exists()
    assert (subs_dir / "Movie.2024.1080p.GR.001.srt").exists()


def test_process_video_dry_run(video_dir: Path, mock_provider: MagicMock):
    video = video_dir / "Movie.2024.1080p.mp4"
    result = process_video(video, ["eng", "ell"], [mock_provider], dry_run=True)

    assert len(result.downloaded) == 0
    assert len(result.skipped) == 2
    subs_dir = video.parent / "subs"
    assert not subs_dir.exists()
    mock_provider.download.assert_not_called()


def test_process_video_skip_existing(video_dir: Path, mock_provider: MagicMock):
    video = video_dir / "Movie.2024.1080p.mp4"
    subs_dir = video.parent / "subs"
    subs_dir.mkdir()
    (subs_dir / "Movie.2024.1080p.ENG.001.srt").write_text("existing")

    result = process_video(video, ["eng", "ell"], [mock_provider])

    # English should get 002 since 001 exists
    assert (subs_dir / "Movie.2024.1080p.ENG.002.srt").exists()
    # Greek should get 001
    assert (subs_dir / "Movie.2024.1080p.GR.001.srt").exists()


def test_process_video_overwrite(video_dir: Path, mock_provider: MagicMock):
    video = video_dir / "Movie.2024.1080p.mp4"
    subs_dir = video.parent / "subs"
    subs_dir.mkdir()
    (subs_dir / "Movie.2024.1080p.ENG.001.srt").write_text("old content")

    result = process_video(video, ["eng", "ell"], [mock_provider], overwrite=True)

    content = (subs_dir / "Movie.2024.1080p.ENG.001.srt").read_text()
    assert content != "old content"


def test_process_video_no_results(video_dir: Path, mock_provider: MagicMock):
    mock_provider.search_by_hash.return_value = []
    mock_provider.search_by_name.return_value = []

    video = video_dir / "Movie.2024.1080p.mp4"
    result = process_video(video, ["eng"], [mock_provider])

    assert len(result.downloaded) == 0
    assert len(result.errors) > 0


def test_process_video_fallback_to_name_search(video_dir: Path, mock_provider: MagicMock):
    mock_provider.search_by_hash.return_value = []
    mock_provider.search_by_name.return_value = [
        SubtitleResult(
            provider="mock", subtitle_id="3", language="eng",
            filename="test.srt", file_id=200, score=5.0, download_count=100,
        )
    ]

    video = video_dir / "Movie.2024.1080p.mp4"
    result = process_video(video, ["eng"], [mock_provider])

    mock_provider.search_by_name.assert_called_once()
    assert len(result.downloaded) == 1


def test_process_directory_summary(video_dir: Path, mock_provider: MagicMock):
    from subs_downloader.scanner import scan_videos
    videos = scan_videos(video_dir)

    summary = process_directory(videos, ["eng", "ell"], [mock_provider])

    assert summary.videos_found == 4
    assert summary.subtitles_downloaded > 0
