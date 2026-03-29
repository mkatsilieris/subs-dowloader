"""OpenSubtitles REST API v1 provider."""

import logging
import os
import time

import httpx

from ..config import OPENSUBTITLES_BASE_URL
from ..exceptions import AuthenticationError, DownloadError, ProviderError, RateLimitError
from . import AbstractProvider, SubtitleResult, register_provider

logger = logging.getLogger(__name__)

MAX_RETRIES = 3
RETRY_BACKOFF = 1.5  # seconds, multiplied each retry


@register_provider("opensubtitles")
class OpenSubtitlesProvider(AbstractProvider):
    """OpenSubtitles.com REST API v1 provider.

    Requires OPENSUBTITLES_API_KEY environment variable.
    Optionally uses OPENSUBTITLES_USERNAME and OPENSUBTITLES_PASSWORD
    for authenticated downloads (higher quotas).
    """

    def __init__(self):
        self.api_key = os.environ.get("OPENSUBTITLES_API_KEY", "")
        if not self.api_key:
            raise ProviderError(
                "OPENSUBTITLES_API_KEY environment variable is required. "
                "Get a free API key at https://www.opensubtitles.com/en/consumers"
            )

        self.username = os.environ.get("OPENSUBTITLES_USERNAME", "")
        self.password = os.environ.get("OPENSUBTITLES_PASSWORD", "")
        self.token: str | None = None
        self._last_request_time = 0.0
        self._min_request_interval = 0.2  # 5 req/s rate limit

        self.client = httpx.Client(
            base_url=OPENSUBTITLES_BASE_URL,
            headers={
                "Api-Key": self.api_key,
                "Content-Type": "application/json",
                "User-Agent": "subs-downloader v0.1.0",
            },
            timeout=30.0,
        )

    def _rate_limit(self):
        """Enforce rate limiting between requests."""
        elapsed = time.monotonic() - self._last_request_time
        if elapsed < self._min_request_interval:
            time.sleep(self._min_request_interval - elapsed)
        self._last_request_time = time.monotonic()

    def _request(self, method: str, path: str, **kwargs) -> httpx.Response:
        """Make an API request with rate limiting and retry logic."""
        for attempt in range(MAX_RETRIES):
            self._rate_limit()
            try:
                response = self.client.request(method, path, **kwargs)

                if response.status_code == 429:
                    wait = RETRY_BACKOFF * (2**attempt)
                    logger.warning("Rate limited, waiting %.1fs before retry", wait)
                    time.sleep(wait)
                    continue

                if response.status_code == 401:
                    raise AuthenticationError("Authentication failed. Check your API key.")

                response.raise_for_status()
                return response

            except httpx.HTTPStatusError:
                raise
            except httpx.HTTPError as e:
                if attempt < MAX_RETRIES - 1:
                    wait = RETRY_BACKOFF * (2**attempt)
                    logger.warning("Request failed: %s. Retrying in %.1fs", e, wait)
                    time.sleep(wait)
                else:
                    raise ProviderError(f"Request failed after {MAX_RETRIES} retries: {e}") from e

        raise RateLimitError("Rate limit exceeded after all retries")

    def _authenticate(self):
        """Authenticate and store JWT token (optional, for higher quotas)."""
        if not self.username or not self.password:
            logger.debug("No credentials provided, using unauthenticated mode")
            return

        if self.token:
            return

        logger.debug("Authenticating with OpenSubtitles...")
        response = self._request(
            "POST", "/login", json={"username": self.username, "password": self.password}
        )
        data = response.json()
        self.token = data.get("token")
        if self.token:
            self.client.headers["Authorization"] = f"Bearer {self.token}"
            logger.info("Authenticated successfully")
        else:
            logger.warning("Login returned no token, continuing unauthenticated")

    def _parse_results(self, data: dict) -> list[SubtitleResult]:
        """Parse API search response into SubtitleResult objects."""
        results = []
        for item in data.get("data", []):
            attrs = item.get("attributes", {})
            lang = attrs.get("language", "")
            files = attrs.get("files", [])
            if not files:
                continue

            file_info = files[0]
            results.append(
                SubtitleResult(
                    provider="opensubtitles",
                    subtitle_id=str(item.get("id", "")),
                    language=lang,
                    filename=attrs.get("release", file_info.get("file_name", "")),
                    file_id=file_info.get("file_id"),
                    score=float(attrs.get("ratings", 0)),
                    download_count=int(attrs.get("download_count", 0)),
                    hearing_impaired=bool(attrs.get("hearing_impaired", False)),
                    attributes=attrs,
                )
            )

        # Sort by download count (most popular first) then rating
        results.sort(key=lambda r: (r.download_count, r.score), reverse=True)
        return results

    def search_by_hash(
        self, file_hash: str, filesize: int, languages: list[str]
    ) -> list[SubtitleResult]:
        """Search subtitles by file hash."""
        self._authenticate()
        logger.debug("Searching by hash: %s (size: %d)", file_hash, filesize)

        params = {
            "moviehash": file_hash,
            "languages": ",".join(languages),
        }
        response = self._request("GET", "/subtitles", params=params)
        results = self._parse_results(response.json())
        logger.debug("Hash search returned %d results", len(results))
        return results

    def search_by_name(
        self, query: str, languages: list[str], season: int | None = None, episode: int | None = None
    ) -> list[SubtitleResult]:
        """Search subtitles by query string."""
        self._authenticate()
        logger.debug("Searching by name: '%s'", query)

        params: dict = {
            "query": query,
            "languages": ",".join(languages),
        }
        if season is not None:
            params["season_number"] = season
        if episode is not None:
            params["episode_number"] = episode

        response = self._request("GET", "/subtitles", params=params)
        results = self._parse_results(response.json())
        logger.debug("Name search returned %d results", len(results))
        return results

    def download(self, subtitle: SubtitleResult) -> bytes:
        """Download a subtitle file by its file_id."""
        self._authenticate()

        if not subtitle.file_id:
            raise DownloadError(f"No file_id for subtitle {subtitle.subtitle_id}")

        logger.debug("Downloading subtitle file_id=%d", subtitle.file_id)
        response = self._request("POST", "/download", json={"file_id": subtitle.file_id})
        data = response.json()

        download_link = data.get("link")
        if not download_link:
            raise DownloadError(f"No download link in response for file_id={subtitle.file_id}")

        # Download the actual subtitle file from the CDN link
        self._rate_limit()
        file_response = httpx.get(download_link, timeout=30.0, follow_redirects=True)
        file_response.raise_for_status()

        remaining = data.get("remaining")
        if remaining is not None:
            logger.info("Download quota remaining: %s", remaining)

        return file_response.content

    def close(self):
        """Close the HTTP client."""
        self.client.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
