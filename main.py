"""Offline SPOT tour guide prototype main loop."""

from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path

from core.audio_recorder import ExitRequestedError, RecordingError, record_until_space_toggle
from config import (
    AUDIO_CHANNELS,
    AUDIO_DTYPE,
    AUDIO_SAMPLE_RATE,
    ARTIFACTS_DIR,
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    CSV_PATH,
    OLLAMA_EMBED_MODEL,
    OLLAMA_LLM_MODEL,
    TIMESTAMP_FORMAT,
    WHISPER_COMPUTE_TYPE,
    WHISPER_DEVICE,
    WHISPER_BEAM_SIZE,
    WHISPER_INITIAL_PROMPT,
    WHISPER_LANGUAGE,
    WHISPER_LOCAL_FILES_ONLY,
    WHISPER_MODEL_SIZE,
)
from core.controller import handle_instruction
from core.instruction_json import build_instruction_json, save_instruction_json
from core.parser_rules import parse_instruction
from rag.rag_query import RagService, RagUnavailableError
from core.transcriber import TranscriptionError, transcribe_audio

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)


def _timestamp_stem() -> str:
    return datetime.now().strftime(TIMESTAMP_FORMAT)


def _save_transcript(transcript: str, txt_path: Path) -> Path:
    txt_path.write_text(transcript, encoding="utf-8")
    return txt_path


def main() -> None:
    """Run the offline loop until an end_tour instruction is received."""
    # Keep runtime artifacts grouped in one place for easier debugging/replay.
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

    try:
        # Load persisted RAG index at startup so failures surface early.
        rag_service = RagService(
            csv_path=CSV_PATH,
            persist_directory=CHROMA_PERSIST_DIR,
            collection_name=CHROMA_COLLECTION_NAME,
            embedding_model=OLLAMA_EMBED_MODEL,
            llm_model=OLLAMA_LLM_MODEL,
        )
    except RagUnavailableError as exc:
        LOGGER.error("RAG initialization failed: %s", exc)
        LOGGER.error("If index is missing, run: python rebuild_chroma_from_csv.py")
        return

    current_location_index = 0
    LOGGER.info("SPOT offline assistant started. current_location_index=%s", current_location_index)

    while True:
        # One timestamp stem ties together WAV, transcript, and instruction JSON.
        stem = _timestamp_stem()
        wav_path = ARTIFACTS_DIR / f"{stem}.wav"
        txt_path = ARTIFACTS_DIR / f"{stem}.txt"
        json_path = ARTIFACTS_DIR / f"{stem}.json"

        try:
            # Record synchronously so downstream steps always work from saved audio.
            record_until_space_toggle(
                output_path=wav_path,
                sample_rate=AUDIO_SAMPLE_RATE,
                channels=AUDIO_CHANNELS,
                dtype=AUDIO_DTYPE,
            )
        except ExitRequestedError:
            LOGGER.info("ESC pressed while waiting to record. Exiting main loop.")
            break
        except RecordingError as exc:
            LOGGER.error("Recording failed: %s", exc)
            continue

        try:
            # Transcribe from file to keep the pipeline reproducible per run.
            transcript = transcribe_audio(
                audio_path=wav_path,
                model_size=WHISPER_MODEL_SIZE,
                compute_type=WHISPER_COMPUTE_TYPE,
                local_files_only=WHISPER_LOCAL_FILES_ONLY,
                device=WHISPER_DEVICE,
                language=WHISPER_LANGUAGE,
                initial_prompt=WHISPER_INITIAL_PROMPT,
                beam_size=WHISPER_BEAM_SIZE,
            )
            _save_transcript(transcript, txt_path)
        except TranscriptionError as exc:
            LOGGER.error("Transcription failed: %s", exc)
            # Keep a placeholder transcript file so operators can correlate artifacts.
            txt_path.write_text("", encoding="utf-8")
            continue

        # Parse to one of the fixed command types before dispatch.
        parsed = parse_instruction(transcript)
        instruction = build_instruction_json(
            instruction_type=str(parsed["instruction_type"]),
            raw_text=transcript,
            parsed_data=dict(parsed.get("parsed_data", {})),
        )

        try:
            # Persist exactly what controller receives for audit/debug.
            save_instruction_json(instruction, json_path)
        except Exception as exc:  # noqa: BLE001
            LOGGER.error("Instruction JSON write failed: %s", exc)
            continue

        # Dispatch immediately using in-memory instruction object.
        result = handle_instruction(
            instruction=instruction,
            current_location_index=current_location_index,
            question_handler=rag_service.answer_question,
        )
        current_location_index = result.updated_location_index

        if result.end_tour:
            break

    LOGGER.info("Main loop ended.")


if __name__ == "__main__":
    main()
