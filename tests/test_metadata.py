"""Tests for the metadata extraction module."""

import os
from pathlib import Path

import pytest

from subs_downloader.metadata import compute_hash, parse_video_name


class TestComputeHash:
    def test_hash_returns_hex_string(self, tmp_path: Path):
        f = tmp_path / "test.mp4"
        f.write_bytes(os.urandom(200_000))
        h = compute_hash(f)
        assert len(h) == 16
        assert all(c in "0123456789abcdef" for c in h)

    def test_hash_is_deterministic(self, tmp_path: Path):
        f = tmp_path / "test.mp4"
        content = os.urandom(200_000)
        f.write_bytes(content)
        assert compute_hash(f) == compute_hash(f)

    def test_hash_rejects_small_files(self, tmp_path: Path):
        f = tmp_path / "tiny.mp4"
        f.write_bytes(b"too small")
        with pytest.raises(ValueError, match="too small"):
            compute_hash(f)

    def test_different_files_different_hashes(self, tmp_path: Path):
        f1 = tmp_path / "a.mp4"
        f2 = tmp_path / "b.mp4"
        f1.write_bytes(os.urandom(200_000))
        f2.write_bytes(os.urandom(200_000))
        assert compute_hash(f1) != compute_hash(f2)


class TestParseVideoName:
    def test_simple_movie(self):
        result = parse_video_name(Path("The.Matrix.1999.1080p.BluRay.mp4"))
        assert result["title"] == "The Matrix"
        assert result["year"] == 1999

    def test_tv_show(self):
        result = parse_video_name(Path("Breaking.Bad.S03E05.720p.mp4"))
        assert result["season"] == 3
        assert result["episode"] == 5
        assert "Breaking Bad" in result["title"]

    def test_no_year_no_episode(self):
        result = parse_video_name(Path("random_movie.mp4"))
        assert result["year"] is None
        assert result["season"] is None
        assert result["episode"] is None

    def test_query_cleaned(self):
        result = parse_video_name(Path("Movie.Name.2020.x264.AAC.mp4"))
        assert result["query"] == "Movie Name 2020"
        assert result["year"] == 2020

    def test_underscores_replaced(self):
        result = parse_video_name(Path("My_Movie_2021.mp4"))
        assert "My Movie" in result["query"]

    def test_episode_lowercase(self):
        result = parse_video_name(Path("show.s01e10.mp4"))
        assert result["season"] == 1
        assert result["episode"] == 10
