"""Custom exception hierarchy."""


class SubsDownloaderError(Exception):
    """Base exception for subs-downloader."""


class ProviderError(SubsDownloaderError):
    """Error from a subtitle provider."""


class AuthenticationError(ProviderError):
    """Failed to authenticate with a provider."""


class RateLimitError(ProviderError):
    """Rate limit exceeded."""


class DownloadError(SubsDownloaderError):
    """Failed to download a subtitle file."""
