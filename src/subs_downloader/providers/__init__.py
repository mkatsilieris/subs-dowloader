"""Subtitle provider abstraction layer."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field


@dataclass
class SubtitleResult:
    """A single subtitle search result."""

    provider: str
    subtitle_id: str
    language: str  # ISO 639-2/B (eng, ell)
    filename: str
    file_id: int | None = None
    download_url: str | None = None
    score: float = 0.0
    download_count: int = 0
    hearing_impaired: bool = False
    attributes: dict = field(default_factory=dict)


class AbstractProvider(ABC):
    """Base class for subtitle providers."""

    name: str = "base"

    @abstractmethod
    def search_by_hash(
        self, file_hash: str, filesize: int, languages: list[str]
    ) -> list[SubtitleResult]:
        """Search for subtitles using file hash."""

    @abstractmethod
    def search_by_name(
        self, query: str, languages: list[str], season: int | None = None, episode: int | None = None
    ) -> list[SubtitleResult]:
        """Search for subtitles using filename/query string."""

    @abstractmethod
    def download(self, subtitle: SubtitleResult) -> bytes:
        """Download subtitle content."""


# Provider registry: maps name -> provider class
PROVIDER_REGISTRY: dict[str, type[AbstractProvider]] = {}


def register_provider(name: str):
    """Decorator to register a provider class."""
    def decorator(cls: type[AbstractProvider]):
        cls.name = name
        PROVIDER_REGISTRY[name] = cls
        return cls
    return decorator
