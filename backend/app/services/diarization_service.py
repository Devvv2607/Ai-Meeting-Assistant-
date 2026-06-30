"""Post-meeting (offline/batch) speaker diarization.

Runs pyannote.audio on the COMPLETE recording to get speaker turns, then aligns
those turns to the existing Groq transcript segments by timestamp overlap so the
final transcript reads "Speaker 1: … / Speaker 2: …". Diarization is
language-agnostic (it works on voice, not words) so the multilingual transcript
is unaffected.

Environment notes (this box / Windows):
- torchcodec's native DLL fails to load, so we DON'T let pyannote read the file
  itself. We load audio with soundfile and pass a pre-loaded waveform dict to the
  pipeline (the documented torchcodec bypass).
- The installed pyannote API uses ``token=`` (not ``use_auth_token=``).
- The HF token must have ACCEPTED the user conditions for
  ``pyannote/speaker-diarization-3.1`` and ``pyannote/segmentation-3.0`` on their
  model pages, or the load fails with an auth error. Weights download on first use.

Resilience: the pipeline is lazy-loaded (import never crashes app boot), input is
length-capped so runtime is bounded, and ANY failure returns no turns so callers
degrade to the current single-speaker transcript — diarization never 500s the
transcript path.
"""

import logging
import os
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)

PYANNOTE_MODEL = "pyannote/speaker-diarization-3.1"
# Cap diarization input so runtime is bounded (Windows has no SIGALRM for a hard
# timeout). Beyond this many seconds we diarize a prefix and log it.
MAX_DIARIZE_SECONDS = int(os.getenv("MAX_DIARIZE_SECONDS", "1800"))

Turn = Tuple[str, float, float]  # (speaker_label, start, end)


class DiarizationService:
    """Lazy pyannote diarizer + transcript alignment. Fails soft (returns [])."""

    def __init__(self):
        self._pipeline = None
        self._load_failed = False

    def _get_pipeline(self):
        if self._pipeline is not None:
            return self._pipeline
        if self._load_failed:
            return None
        try:
            from pyannote.audio import Pipeline
            token = os.getenv("HF_TOKEN") or os.getenv("HUGGINGFACE_TOKEN")
            if not token:
                logger.warning("No HF token set — speaker diarization disabled")
                self._load_failed = True
                return None
            self._pipeline = Pipeline.from_pretrained(PYANNOTE_MODEL, token=token)
            logger.info("pyannote diarization pipeline loaded")
            return self._pipeline
        except Exception as e:
            logger.error(f"pyannote pipeline load failed (diarization disabled): {e}")
            self._load_failed = True
            return None

    def diarize(self, audio_path: str) -> List[Turn]:
        """Return [(speaker_label, start, end)] for the audio, or [] on any failure."""
        try:
            pipeline = self._get_pipeline()
            if pipeline is None:
                return []
            if not audio_path or not os.path.exists(audio_path):
                logger.warning(f"diarize: audio not found: {audio_path}")
                return []

            import numpy as np
            import soundfile as sf
            import torch

            data, sr = sf.read(audio_path, dtype="float32")
            if getattr(data, "ndim", 1) > 1:  # downmix stereo → mono
                data = data.mean(axis=1)
            max_samples = MAX_DIARIZE_SECONDS * sr
            if len(data) > max_samples:
                logger.warning(
                    f"diarize input {len(data)/sr:.0f}s exceeds cap "
                    f"{MAX_DIARIZE_SECONDS}s — truncating"
                )
                data = data[:max_samples]

            waveform = torch.from_numpy(np.ascontiguousarray(data)).unsqueeze(0)  # (1, time)
            # Pre-loaded waveform dict bypasses torchcodec entirely.
            out = pipeline({"waveform": waveform, "sample_rate": int(sr)})
            annotation = getattr(out, "speaker_diarization", out)

            turns: List[Turn] = [
                (str(label), float(seg.start), float(seg.end))
                for seg, _, label in annotation.itertracks(yield_label=True)
            ]
            turns.sort(key=lambda t: t[1])
            logger.info(
                f"diarization: {len(turns)} turns, "
                f"{len({t[0] for t in turns if t[0] != 'UNKNOWN'})} speakers"
            )
            return turns
        except Exception as e:
            logger.error(f"diarization failed for {audio_path}: {e}", exc_info=True)
            return []

    @staticmethod
    def align_speakers(segments: List[Dict], turns: List[Turn]) -> List[Dict]:
        """Assign each transcript segment a stable ``Speaker N`` by max time-overlap.

        Returns NEW segment dicts (text is never altered). When ``turns`` is empty
        the segments are returned unchanged (caller keeps single-speaker labels).
        """
        if not turns:
            return segments

        # Stable label numbering by first appearance (turns are start-sorted).
        order: List[str] = []
        for label, _, _ in turns:
            if label != "UNKNOWN" and label not in order:
                order.append(label)
        label_map = {lab: f"Speaker {i + 1}" for i, lab in enumerate(order)}
        label_map["UNKNOWN"] = "Unknown"

        def overlap(a0: float, a1: float, b0: float, b1: float) -> float:
            return max(0.0, min(a1, b1) - max(a0, b0))

        labeled: List[Dict] = []
        for seg in segments:
            s0 = float(seg.get("start_time", 0.0) or 0.0)
            s1 = float(seg.get("end_time", 0.0) or 0.0)
            if s1 <= s0:
                s1 = s0 + 0.01

            best_label, best_ov = None, 0.0
            for label, t0, t1 in turns:
                ov = overlap(s0, s1, t0, t1)
                if ov > best_ov:
                    best_ov, best_label = ov, label

            if best_label is None:  # segment falls in a gap → nearest turn by midpoint
                mid = (s0 + s1) / 2.0
                best_label = min(
                    turns, key=lambda t: min(abs(mid - t[1]), abs(mid - t[2]))
                )[0]

            new = dict(seg)
            new["speaker"] = label_map.get(best_label, "Speaker 1")
            labeled.append(new)
        return labeled

    @staticmethod
    def merge_consecutive(segments: List[Dict]) -> List[Dict]:
        """Merge consecutive same-speaker segments into one row for cleaner rendering."""
        if not segments:
            return segments
        merged = [dict(segments[0])]
        for seg in segments[1:]:
            if seg.get("speaker") == merged[-1].get("speaker"):
                joined = f"{merged[-1].get('text', '')} {seg.get('text', '')}".strip()
                merged[-1]["text"] = joined
                merged[-1]["end_time"] = seg.get("end_time", merged[-1].get("end_time"))
            else:
                merged.append(dict(seg))
        return merged


# Module-level singleton (pipeline lazy-loads on first diarize()).
diarization_service = DiarizationService()
