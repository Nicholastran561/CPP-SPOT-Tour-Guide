"""Speech transcription with faster-whisper."""

from __future__ import annotations

import logging
from pathlib import Path

from faster_whisper import WhisperModel

LOGGER = logging.getLogger(__name__)


class TranscriptionError(RuntimeError):
    """Raised when transcription fails."""


def transcribe_audio(
    audio_path: Path,
    model_size: str,
    compute_type: str,
    local_files_only: bool,
    device: str,
    language: str,
    initial_prompt: str,
    beam_size: int,
) -> str:
    """Transcribe an audio file and return a normalized transcript string."""
    if not audio_path.exists():
        raise TranscriptionError(f"Audio file not found: {audio_path}")

    try:
        # Model creation is explicit so device/compute/offline behavior is controlled in config.
        model = WhisperModel(
            model_size,
            device=device,
            compute_type=compute_type,
            local_files_only=local_files_only,
        )
        # Initial prompt biases recognition toward this project's command vocabulary.
        segments, _ = model.transcribe(
            str(audio_path),
            beam_size=beam_size,
            language=language,
            initial_prompt=initial_prompt,
            condition_on_previous_text=False,
        )
    except Exception as exc:  # noqa: BLE001
        raise TranscriptionError(
            "Transcription failed. Ensure the faster-whisper model is already "
            f"available locally for offline use. Details: {exc}"
        ) from exc

    # Merge segment text into a single controller-friendly transcript string.
    text = " ".join(segment.text.strip() for segment in segments).strip()
    if not text:
        raise TranscriptionError("Transcription was empty.")

    LOGGER.info("Transcript: %s", text)
    return text
