"""Live-meeting audio persistence.

Reconstructs ONE valid, decodable audio file from the standalone WebM/Opus
segments the browser streams over the websocket.

Why decode-to-PCM (strategy a) and not raw concatenation:
    Each incoming segment is its OWN WebM container (its own EBML header).
    Concatenating the raw segments produces a multi-header WebM that will not
    decode. Instead we decode each segment to raw PCM16 (16 kHz mono) with
    ffmpeg and append the PCM samples to a per-meeting `.pcm` file, then wrap
    the accumulated PCM in a SINGLE WAV header on finalize. WAV is universally
    decodable (soundfile / pydub / pyannote read it natively) — no Opus,
    ffprobe, or multi-header pitfalls.

STORAGE NOTE: local disk, single-instance / dev only. Files under
``settings.LIVE_AUDIO_DIR`` are EPHEMERAL on Cloud Run (lost on instance
restart) — same constraint as the #1 module-state blocker. GCS is the
deploy-time replacement; it is intentionally NOT built here.
"""

import logging
import os
import subprocess
import tempfile
import wave
from pathlib import Path

from app.config import settings

logger = logging.getLogger(__name__)

# Whisper/pyannote-friendly target format.
PCM_RATE = 16000
PCM_CHANNELS = 1
PCM_SAMPLE_WIDTH = 2  # bytes (int16)


def _ffmpeg_exe() -> str:
    """Locate the ffmpeg binary (bundled imageio-ffmpeg, else system)."""
    try:
        import imageio_ffmpeg
        exe = imageio_ffmpeg.get_ffmpeg_exe()
        if exe and os.path.exists(exe):
            return exe
    except Exception:
        pass
    from shutil import which
    return which("ffmpeg") or "ffmpeg"


class LiveAudioRecorder:
    """Accumulates a live session's audio into one decodable WAV, keyed by meeting id."""

    def __init__(self):
        self.dir = Path(settings.LIVE_AUDIO_DIR).resolve()
        self.dir.mkdir(parents=True, exist_ok=True)
        self._ffmpeg = _ffmpeg_exe()

    def _pcm_path(self, meeting_id: int) -> Path:
        return self.dir / f"meeting_{meeting_id}.pcm"

    def _wav_path(self, meeting_id: int) -> Path:
        return self.dir / f"meeting_{meeting_id}.wav"

    def append_segment(self, meeting_id: int, webm_bytes: bytes) -> bool:
        """Decode a standalone WebM segment to PCM and append to the session's raw file.

        Returns True if PCM was appended. Designed to run in a worker thread
        (blocking ffmpeg call) so it never stalls the event loop.
        """
        if not webm_bytes:
            return False

        tmp = tempfile.NamedTemporaryFile(suffix=".webm", delete=False)
        try:
            tmp.write(webm_bytes)
            tmp.close()
            proc = subprocess.run(
                [
                    self._ffmpeg, "-hide_banner", "-loglevel", "error",
                    "-i", tmp.name,
                    "-f", "s16le", "-ar", str(PCM_RATE), "-ac", str(PCM_CHANNELS),
                    "pipe:1",
                ],
                capture_output=True,
            )
            if proc.returncode != 0 or not proc.stdout:
                logger.warning(
                    f"ffmpeg decode failed for meeting {meeting_id} "
                    f"(rc={proc.returncode}): {proc.stderr[:200]!r}"
                )
                return False
            with open(self._pcm_path(meeting_id), "ab") as f:
                f.write(proc.stdout)
            return True
        except Exception as e:
            logger.error(f"Error appending live audio for meeting {meeting_id}: {e}")
            return False
        finally:
            try:
                os.remove(tmp.name)
            except Exception:
                pass

    def finalize(self, meeting_id: int):
        """Wrap accumulated PCM into ONE valid WAV. Returns absolute path, or None
        if nothing was captured. Removes the .pcm partial afterward."""
        pcm = self._pcm_path(meeting_id)
        if not pcm.exists() or pcm.stat().st_size == 0:
            self.discard(meeting_id)
            return None

        wav = self._wav_path(meeting_id)
        try:
            with open(pcm, "rb") as pf, wave.open(str(wav), "wb") as wf:
                wf.setnchannels(PCM_CHANNELS)
                wf.setsampwidth(PCM_SAMPLE_WIDTH)
                wf.setframerate(PCM_RATE)
                wf.writeframes(pf.read())
        except Exception as e:
            logger.error(f"Failed to finalize WAV for meeting {meeting_id}: {e}")
            return None
        finally:
            self.discard(meeting_id)  # remove the .pcm partial either way

        logger.info(f"Finalized live audio for meeting {meeting_id}: {wav}")
        return str(wav)

    def discard(self, meeting_id: int) -> None:
        """Remove the partial .pcm for a session (cleanup on abnormal end / after finalize)."""
        try:
            pcm = self._pcm_path(meeting_id)
            if pcm.exists():
                pcm.unlink()
        except Exception as e:
            logger.warning(f"Could not clean up partial audio for meeting {meeting_id}: {e}")


# Module-level singleton (stateless except the storage dir).
live_audio_recorder = LiveAudioRecorder()
