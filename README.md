# subs-downloader

CLI tool that scans directories for video files and automatically downloads matching subtitles in English and Greek.

## Prerequisites

- Python 3.12+
- [uv](https://docs.astral.sh/uv/getting-started/installation/)
- An OpenSubtitles API key (free at <https://www.opensubtitles.com/en/consumers>)

## Setup

```bash
# Clone and install dependencies
git clone <repo-url>
cd subs-dowloader
uv sync
```

Set your OpenSubtitles API key as an environment variable:

```bash
# Linux/macOS
export OPENSUBTITLES_API_KEY="your-api-key"

# Windows (PowerShell)
$env:OPENSUBTITLES_API_KEY="your-api-key"

# Windows (cmd)
set OPENSUBTITLES_API_KEY=your-api-key
```

Optionally, for higher download quotas, also set:

```bash
export OPENSUBTITLES_USERNAME="your-username"
export OPENSUBTITLES_PASSWORD="your-password"
```

## Usage

```bash
# Scan current directory
uv run subs-dl

# Scan a specific directory
uv run subs-dl /path/to/videos

# Preview what would be downloaded (no actual downloads)
uv run subs-dl /path/to/videos --dry-run

# Verbose output for debugging
uv run subs-dl /path/to/videos --verbose

# Download only English subtitles
uv run subs-dl /path/to/videos --languages eng

# Overwrite existing subtitle files
uv run subs-dl /path/to/videos --overwrite
```

### CLI Options

| Option | Default | Description |
|---|---|---|
| `path` | `.` | Directory to scan for video files |
| `--languages` | `eng ell` | Subtitle languages (ISO 639-2/B codes) |
| `--dry-run` | off | Show what would be downloaded without downloading |
| `--overwrite` | off | Overwrite existing subtitle files |
| `--verbose`, `-v` | off | Enable debug logging |
| `--providers` | `opensubtitles` | Which subtitle providers to use |
| `--version` | | Show version and exit |

## Supported Video Formats

`.mp4`, `.mkv`, `.avi`, `.mov`

## Output

Subtitles are saved in a `subs/` folder next to each video file:

```
movies/
  The.Matrix.1999.1080p.mp4
  subs/
    The.Matrix.1999.1080p.ENG.001.srt
    The.Matrix.1999.1080p.GR.001.srt
```

If multiple subtitles exist for the same language, the counter increments (`002`, `003`, etc.).

## How It Works

1. Recursively scans the given directory for video files
2. For each video, computes an OpenSubtitles file hash
3. Searches by hash first for accurate matching, falls back to filename-based search
4. Downloads the best-ranked subtitle for each requested language
5. Saves subtitles with a structured naming convention

## Running Tests

```bash
uv run pytest
uv run pytest -v          # verbose
uv run pytest --cov       # with coverage
```

## Adding a New Provider

Create a new file in `src/subs_downloader/providers/` and use the `@register_provider` decorator:

```python
from . import AbstractProvider, register_provider

@register_provider("my-provider")
class MyProvider(AbstractProvider):
    def search_by_hash(self, file_hash, filesize, languages):
        ...

    def search_by_name(self, query, languages, season=None, episode=None):
        ...

    def download(self, subtitle):
        ...
```

Then import it in `cli.py` and it becomes available via `--providers my-provider`.

## License

MIT
