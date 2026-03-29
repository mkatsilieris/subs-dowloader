"""Tests for the OpenSubtitles provider."""

import os
from unittest.mock import patch

import httpx
import pytest
import respx

from subs_downloader.exceptions import ProviderError
from subs_downloader.providers.opensubtitles import OpenSubtitlesProvider


@pytest.fixture
def api_key_env():
    """Set the API key env var for tests."""
    with patch.dict(os.environ, {"OPENSUBTITLES_API_KEY": "test-key-123"}):
        yield


@pytest.fixture
def provider(api_key_env):
    """Create a provider instance with mocked env."""
    p = OpenSubtitlesProvider()
    yield p
    p.close()


SEARCH_RESPONSE = {
    "data": [
        {
            "id": "123",
            "attributes": {
                "language": "eng",
                "release": "Movie.2024.srt",
                "ratings": 8.5,
                "download_count": 5000,
                "hearing_impaired": False,
                "files": [{"file_id": 100, "file_name": "Movie.2024.srt"}],
            },
        },
        {
            "id": "456",
            "attributes": {
                "language": "ell",
                "release": "Movie.2024.gr.srt",
                "ratings": 7.0,
                "download_count": 1200,
                "hearing_impaired": False,
                "files": [{"file_id": 101, "file_name": "Movie.2024.gr.srt"}],
            },
        },
    ]
}

DOWNLOAD_RESPONSE = {
    "link": "https://cdn.opensubtitles.com/download/abc123",
    "remaining": 95,
}


def test_provider_requires_api_key():
    with patch.dict(os.environ, {}, clear=True):
        os.environ.pop("OPENSUBTITLES_API_KEY", None)
        with pytest.raises(ProviderError, match="API_KEY"):
            OpenSubtitlesProvider()


@respx.mock
def test_search_by_hash(provider):
    respx.get("https://api.opensubtitles.com/api/v1/subtitles").mock(
        return_value=httpx.Response(200, json=SEARCH_RESPONSE)
    )
    results = provider.search_by_hash("abc123", 1000000, ["eng", "ell"])
    assert len(results) == 2
    assert results[0].language == "eng"
    assert results[0].file_id == 100


@respx.mock
def test_search_by_name(provider):
    respx.get("https://api.opensubtitles.com/api/v1/subtitles").mock(
        return_value=httpx.Response(200, json=SEARCH_RESPONSE)
    )
    results = provider.search_by_name("Movie 2024", ["eng", "ell"])
    assert len(results) == 2


@respx.mock
def test_search_by_name_with_season_episode(provider):
    route = respx.get("https://api.opensubtitles.com/api/v1/subtitles").mock(
        return_value=httpx.Response(200, json=SEARCH_RESPONSE)
    )
    provider.search_by_name("Show", ["eng"], season=1, episode=2)
    assert "season_number" in str(route.calls[0].request.url)
    assert "episode_number" in str(route.calls[0].request.url)


@respx.mock
def test_download(provider):
    respx.post("https://api.opensubtitles.com/api/v1/download").mock(
        return_value=httpx.Response(200, json=DOWNLOAD_RESPONSE)
    )
    respx.get("https://cdn.opensubtitles.com/download/abc123").mock(
        return_value=httpx.Response(200, content=b"1\n00:00:01,000 --> 00:00:02,000\nHello\n")
    )

    from subs_downloader.providers import SubtitleResult
    sub = SubtitleResult(
        provider="opensubtitles", subtitle_id="123", language="eng",
        filename="test.srt", file_id=100
    )
    content = provider.download(sub)
    assert b"Hello" in content


@respx.mock
def test_empty_search_results(provider):
    respx.get("https://api.opensubtitles.com/api/v1/subtitles").mock(
        return_value=httpx.Response(200, json={"data": []})
    )
    results = provider.search_by_hash("abc", 1000, ["eng"])
    assert results == []
