"""Tests for the CLI module."""

import os
from pathlib import Path
from unittest.mock import patch

import pytest

from subs_downloader.cli import build_parser, main


def test_parser_defaults():
    parser = build_parser()
    args = parser.parse_args([])
    assert args.path == "."
    assert args.languages == ["eng", "ell"]
    assert args.dry_run is False
    assert args.overwrite is False
    assert args.verbose is False
    assert args.providers == ["opensubtitles"]


def test_parser_custom_args():
    parser = build_parser()
    args = parser.parse_args([
        "/some/path", "--languages", "eng", "--dry-run",
        "--overwrite", "--verbose", "--providers", "opensubtitles"
    ])
    assert args.path == "/some/path"
    assert args.languages == ["eng"]
    assert args.dry_run is True
    assert args.overwrite is True
    assert args.verbose is True


def test_main_nonexistent_directory():
    with pytest.raises(SystemExit) as exc_info:
        main(["/nonexistent/path/abc123"])
    assert exc_info.value.code == 2


def test_main_no_api_key(tmp_path: Path):
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("OPENSUBTITLES_API_KEY", None)
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path)])
        assert exc_info.value.code == 2


def test_main_empty_directory(tmp_path: Path):
    with patch.dict(os.environ, {"OPENSUBTITLES_API_KEY": "test"}):
        with pytest.raises(SystemExit) as exc_info:
            main([str(tmp_path)])
        assert exc_info.value.code == 0
