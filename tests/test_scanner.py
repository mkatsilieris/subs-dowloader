"""Tests for the video scanner module."""

from pathlib import Path

import pytest

from subs_downloader.scanner import scan_videos


def test_scan_finds_all_video_files(video_dir: Path):
    videos = scan_videos(video_dir)
    names = [v.name for v in videos]
    assert "Movie.2024.1080p.mp4" in names
    assert "Show.S01E02.mkv" in names
    assert "documentary.avi" in names
    assert "Show.S01E03.mov" in names


def test_scan_ignores_non_video_files(video_dir: Path):
    videos = scan_videos(video_dir)
    names = [v.name for v in videos]
    assert "readme.txt" not in names


def test_scan_skips_hidden_directories(video_dir: Path):
    videos = scan_videos(video_dir)
    names = [v.name for v in videos]
    assert "secret.mp4" not in names


def test_scan_finds_nested_videos(video_dir: Path):
    videos = scan_videos(video_dir)
    names = [v.name for v in videos]
    assert "Show.S01E03.mov" in names


def test_scan_returns_sorted_results(video_dir: Path):
    videos = scan_videos(video_dir)
    assert videos == sorted(videos)


def test_scan_empty_directory(tmp_path: Path):
    videos = scan_videos(tmp_path)
    assert videos == []


def test_scan_nonexistent_directory():
    with pytest.raises(FileNotFoundError):
        scan_videos(Path("/nonexistent/path"))


def test_scan_custom_extensions(video_dir: Path):
    videos = scan_videos(video_dir, extensions={".mp4"})
    names = [v.name for v in videos]
    assert "Movie.2024.1080p.mp4" in names
    assert "Show.S01E02.mkv" not in names
