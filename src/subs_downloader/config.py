"""Constants and default configuration."""

VIDEO_EXTENSIONS = {".mp4", ".mkv", ".avi", ".mov"}

DEFAULT_LANGUAGES = ["eng", "ell"]

SUBS_FOLDER_NAME = "subs"

OPENSUBTITLES_BASE_URL = "https://api.opensubtitles.com/api/v1"

# Language code display mapping (for subtitle filenames)
LANGUAGE_DISPLAY = {
    "eng": "ENG",
    "ell": "GR",
    "gre": "GR",  # alias
}

# OpenSubtitles hash constants
HASH_CHUNK_SIZE = 65536  # 64KB
