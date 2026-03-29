"""Download orchestration: ties together scanning, metadata, providers, and file saving."""

import logging
from dataclasses import dataclass, field
from pathlib import Path

from .config import LANGUAGE_DISPLAY, SUBS_FOLDER_NAME
from .exceptions import DownloadError, ProviderError, SubsDownloaderError
from .metadata import compute_hash, parse_video_name
from .providers import AbstractProvider, SubtitleResult

logger = logging.getLogger(__name__)


@dataclass
class DownloadResult:
    """Result of processing a single video file."""

    video: Path
    downloaded: list[Path] = field(default_factory=list)
    skipped: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class Summary:
    """Summary of a full download run."""

    videos_found: int = 0
    subtitles_downloaded: int = 0
    subtitles_skipped: int = 0
    errors: int = 0
    results: list[DownloadResult] = field(default_factory=list)


def _get_next_counter(subs_dir: Path, video_stem: str, lang_display: str) -> int:
    """Find the next available counter for a subtitle file."""
    counter = 1
    while True:
        filename = f"{video_stem}.{lang_display}.{counter:03d}.srt"
        if not (subs_dir / filename).exists():
            return counter
        counter += 1


def _pick_best(results: list[SubtitleResult], language: str) -> SubtitleResult | None:
    """Pick the best subtitle result for a given language."""
    matches = [r for r in results if r.language == language]
    if not matches:
        return None
    # Already sorted by (download_count, score) descending from provider
    return matches[0]


def process_video(
    video: Path,
    languages: list[str],
    providers: list[AbstractProvider],
    dry_run: bool = False,
    overwrite: bool = False,
) -> DownloadResult:
    """Process a single video file: search and download subtitles.

    Args:
        video: Path to the video file.
        languages: List of language codes to download.
        providers: List of provider instances to search.
        dry_run: If True, only log what would be done.
        overwrite: If True, overwrite existing subtitle files.

    Returns:
        DownloadResult with details of what was downloaded/skipped/errored.
    """
    result = DownloadResult(video=video)
    video_stem = video.stem
    subs_dir = video.parent / SUBS_FOLDER_NAME
    meta = parse_video_name(video)

    # Try to compute file hash
    file_hash = None
    filesize = video.stat().st_size
    try:
        file_hash = compute_hash(video)
        logger.debug("Computed hash for %s: %s", video.name, file_hash)
    except ValueError:
        logger.debug("File too small for hash: %s", video.name)

    # Search across providers
    all_results: list[SubtitleResult] = []
    for provider in providers:
        try:
            # Hash-based search first
            if file_hash:
                hash_results = provider.search_by_hash(file_hash, filesize, languages)
                all_results.extend(hash_results)

            # Fallback to name-based search if hash found nothing
            if not all_results:
                name_results = provider.search_by_name(
                    meta["query"], languages,
                    season=meta.get("season"),
                    episode=meta.get("episode"),
                )
                all_results.extend(name_results)

        except ProviderError as e:
            logger.warning("Provider %s failed for %s: %s", provider.name, video.name, e)
            result.errors.append(f"{provider.name}: {e}")

    if not all_results:
        logger.info("No subtitles found for: %s", video.name)
        result.errors.append("No subtitles found")
        return result

    # Download best subtitle for each language
    for lang in languages:
        lang_display = LANGUAGE_DISPLAY.get(lang, lang.upper())
        best = _pick_best(all_results, lang)

        if not best:
            logger.info("No %s subtitles found for: %s", lang_display, video.name)
            result.skipped.append(f"No {lang_display} subtitles found")
            continue

        # Determine output path
        if overwrite:
            counter = 1
        else:
            counter = _get_next_counter(subs_dir, video_stem, lang_display)

        filename = f"{video_stem}.{lang_display}.{counter:03d}.srt"
        output_path = subs_dir / filename

        # Check if we should skip
        if not overwrite and output_path.exists():
            logger.info("Already exists, skipping: %s", filename)
            result.skipped.append(filename)
            continue

        if dry_run:
            logger.info("[DRY RUN] Would download: %s (from %s)", filename, best.provider)
            result.skipped.append(f"[dry-run] {filename}")
            continue

        # Download
        try:
            # Find the provider that produced this result
            provider_instance = next(
                (p for p in providers if p.name == best.provider), providers[0]
            )
            content = provider_instance.download(best)

            subs_dir.mkdir(parents=True, exist_ok=True)
            output_path.write_bytes(content)
            logger.info("Downloaded: %s", filename)
            result.downloaded.append(output_path)

        except (DownloadError, ProviderError, SubsDownloaderError) as e:
            logger.error("Failed to download %s: %s", filename, e)
            result.errors.append(f"Download failed for {filename}: {e}")

    return result


def process_directory(
    videos: list[Path],
    languages: list[str],
    providers: list[AbstractProvider],
    dry_run: bool = False,
    overwrite: bool = False,
) -> Summary:
    """Process all video files in a list.

    Args:
        videos: List of video file paths.
        languages: Language codes to download.
        providers: Provider instances.
        dry_run: If True, only log what would be done.
        overwrite: If True, overwrite existing files.

    Returns:
        Summary of the entire run.
    """
    summary = Summary(videos_found=len(videos))

    for video in videos:
        logger.info("Processing: %s", video.name)
        result = process_video(video, languages, providers, dry_run, overwrite)
        summary.results.append(result)
        summary.subtitles_downloaded += len(result.downloaded)
        summary.subtitles_skipped += len(result.skipped)
        summary.errors += len(result.errors)

    return summary
