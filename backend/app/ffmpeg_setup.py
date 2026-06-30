"""Configure ffmpeg for the application.

The project depends on ffmpeg for audio decoding/encoding (pydub for WebM->WAV
conversion, and the ffmpeg subprocess calls in WhisperService for large-file
chunking/compression). A system-wide ffmpeg is often not installed on Windows
dev machines, so we ship a bundled binary via the ``imageio-ffmpeg`` package
and point everything at it.

This module is imported by ``app.config`` so it runs once, very early, before
any pydub conversion takes place.
"""

import logging
import os

logger = logging.getLogger(__name__)


def configure_ffmpeg() -> bool:
    """Locate a usable ffmpeg binary and wire it into pydub and PATH.

    Returns:
        True if an ffmpeg binary was configured, False otherwise.
    """
    ffmpeg_exe = None

    # Prefer the bundled imageio-ffmpeg binary (no system install required).
    try:
        import imageio_ffmpeg
        ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as e:  # pragma: no cover - only hit when package missing
        logger.warning(f"imageio-ffmpeg not available: {e}")

    # Fall back to a system ffmpeg already on PATH.
    if not ffmpeg_exe or not os.path.exists(ffmpeg_exe):
        from shutil import which
        ffmpeg_exe = which("ffmpeg")

    if not ffmpeg_exe or not os.path.exists(ffmpeg_exe):
        logger.warning(
            "No ffmpeg binary found. Audio conversion (pydub) and large-file "
            "transcription chunking will be unavailable. Live transcription via "
            "Groq still works (Groq decodes audio server-side)."
        )
        return False

    # Point pydub at the binary so AudioSegment.from_file / export work.
    try:
        from pydub import AudioSegment
        AudioSegment.converter = ffmpeg_exe
        AudioSegment.ffmpeg = ffmpeg_exe
    except Exception as e:
        logger.warning(f"Could not configure pydub with ffmpeg: {e}")

    # Make `ffmpeg` resolvable for subprocess calls in WhisperService.
    ffmpeg_dir = os.path.dirname(ffmpeg_exe)
    if ffmpeg_dir and ffmpeg_dir not in os.environ.get("PATH", ""):
        os.environ["PATH"] = ffmpeg_dir + os.pathsep + os.environ.get("PATH", "")

    logger.info(f"ffmpeg configured: {ffmpeg_exe}")
    return True
