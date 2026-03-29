"""Command-line interface for subs-downloader."""

import argparse
import logging
import sys
from pathlib import Path

from . import __version__
from .config import DEFAULT_LANGUAGES
from .downloader import process_directory
from .providers import PROVIDER_REGISTRY, AbstractProvider
from .scanner import scan_videos

# Ensure provider modules are imported so they register themselves
from .providers import opensubtitles as _  # noqa: F401

logger = logging.getLogger("subs_downloader")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="subs-dl",
        description="Scan directories for video files and download matching subtitles.",
    )
    parser.add_argument(
        "path",
        nargs="?",
        default=".",
        help="Directory to scan for video files (default: current directory)",
    )
    parser.add_argument(
        "--languages",
        nargs="+",
        default=DEFAULT_LANGUAGES,
        help=f"Subtitle languages to download (default: {' '.join(DEFAULT_LANGUAGES)})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Show what would be downloaded without actually downloading",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Overwrite existing subtitle files",
    )
    parser.add_argument(
        "--verbose", "-v",
        action="store_true",
        help="Enable verbose/debug logging",
    )
    parser.add_argument(
        "--providers",
        nargs="+",
        default=["opensubtitles"],
        help=f"Providers to use (available: {', '.join(PROVIDER_REGISTRY.keys())})",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    return parser


def setup_logging(verbose: bool):
    level = logging.DEBUG if verbose else logging.INFO
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(logging.Formatter("%(levelname)-8s %(message)s"))
    logger.setLevel(level)
    logger.addHandler(handler)


def main(argv: list[str] | None = None):
    parser = build_parser()
    args = parser.parse_args(argv)

    setup_logging(args.verbose)

    root = Path(args.path).resolve()
    if not root.is_dir():
        logger.error("Not a directory: %s", root)
        sys.exit(2)

    # Instantiate providers
    providers: list[AbstractProvider] = []
    for name in args.providers:
        if name not in PROVIDER_REGISTRY:
            logger.error("Unknown provider: %s (available: %s)", name, ", ".join(PROVIDER_REGISTRY.keys()))
            sys.exit(2)
        try:
            providers.append(PROVIDER_REGISTRY[name]())
        except Exception as e:
            logger.error("Failed to initialize provider '%s': %s", name, e)
            sys.exit(2)

    if not providers:
        logger.error("No providers available")
        sys.exit(2)

    # Scan for videos
    logger.info("Scanning: %s", root)
    videos = scan_videos(root)
    if not videos:
        logger.info("No video files found in: %s", root)
        sys.exit(0)

    logger.info("Found %d video file(s)", len(videos))
    if args.dry_run:
        logger.info("=== DRY RUN MODE ===")

    # Process
    summary = process_directory(
        videos=videos,
        languages=args.languages,
        providers=providers,
        dry_run=args.dry_run,
        overwrite=args.overwrite,
    )

    # Print summary
    print("\n--- Summary ---")
    print(f"Videos scanned:       {summary.videos_found}")
    print(f"Subtitles downloaded: {summary.subtitles_downloaded}")
    print(f"Skipped:              {summary.subtitles_skipped}")
    print(f"Errors:               {summary.errors}")

    if summary.results:
        print("\nDetails:")
        for r in summary.results:
            status_parts = []
            if r.downloaded:
                status_parts.append(f"{len(r.downloaded)} downloaded")
            if r.skipped:
                status_parts.append(f"{len(r.skipped)} skipped")
            if r.errors:
                status_parts.append(f"{len(r.errors)} errors")
            status = ", ".join(status_parts) if status_parts else "no action"
            print(f"  {r.video.name}: {status}")

    # Close providers
    for p in providers:
        if hasattr(p, "close"):
            p.close()

    # Exit code
    if summary.errors > 0 and summary.subtitles_downloaded == 0:
        sys.exit(1)
    sys.exit(0)


if __name__ == "__main__":
    main()
