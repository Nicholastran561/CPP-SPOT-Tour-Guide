"""Audio recording utilities for start/stop on SPACE in a focused terminal."""

from __future__ import annotations

import logging
import threading
from pathlib import Path
from typing import List

import keyboard
import numpy as np
import sounddevice as sd
import soundfile as sf

LOGGER = logging.getLogger(__name__)


class RecordingError(RuntimeError):
    """Raised when audio recording cannot be completed."""


class ExitRequestedError(RuntimeError):
    """Raised when ESC is pressed while waiting to start recording."""


def _ensure_input_device_available() -> None:
    """Validate that at least one input device is available."""
    # Fail early with a clear message instead of opening a stream that cannot record.
    devices = sd.query_devices()
    has_input = any(device.get("max_input_channels", 0) > 0 for device in devices)
    if not has_input:
        raise RecordingError("No microphone/input device was detected.")


def _wait_for_start_key() -> None:
    """Wait for SPACE to start recording or ESC to exit the application."""
    while True:
        event = keyboard.read_event()
        if event.event_type != keyboard.KEY_DOWN:
            continue
        if event.name == "space":
            return
        if event.name == "esc":
            raise ExitRequestedError("ESC pressed while waiting to start recording.")


def record_until_space_toggle(
    output_path: Path,
    sample_rate: int,
    channels: int,
    dtype: str,
) -> Path:
    """Record audio between two SPACE key presses and save a WAV file."""
    _ensure_input_device_available()

    LOGGER.info("Press SPACE to start recording (or ESC to exit).")
    _wait_for_start_key()
    LOGGER.info("Recording started. Press SPACE again to stop.")

    stop_event = threading.Event()
    # Buffer raw chunks from the callback and stitch them into one waveform at the end.
    frames: List[np.ndarray] = []

    def callback(indata: np.ndarray, frame_count: int, time_info, status) -> None:  # noqa: ANN001
        if status:
            LOGGER.warning("Recording stream status: %s", status)
        frames.append(indata.copy())

    try:
        with sd.InputStream(
            samplerate=sample_rate,
            channels=channels,
            dtype=dtype,
            callback=callback,
        ):
            keyboard.wait("space")
            stop_event.set()
    except Exception as exc:  # noqa: BLE001
        raise RecordingError(f"Failed during recording: {exc}") from exc

    if not stop_event.is_set() or not frames:
        raise RecordingError("Recording did not capture any audio frames.")

    # Save one contiguous array so downstream STT reads a normal WAV file.
    audio = np.concatenate(frames, axis=0)
    try:
        sf.write(output_path, audio, sample_rate)
    except Exception as exc:  # noqa: BLE001
        raise RecordingError(f"Failed to save WAV file: {exc}") from exc

    LOGGER.info("Saved audio to %s", output_path)
    return output_path
