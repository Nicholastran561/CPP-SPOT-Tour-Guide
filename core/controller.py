"""Instruction dispatch controller."""

from __future__ import annotations

import logging
from dataclasses import dataclass
from typing import Callable, Dict

LOGGER = logging.getLogger(__name__)


@dataclass
class ControllerResult:
    """Result of handling one instruction."""

    updated_location_index: int
    end_tour: bool


def handle_instruction(
    instruction: Dict[str, object],
    current_location_index: int,
    question_handler: Callable[[str, int], str],
    narration_handler: Callable[[str], None] | None = None,
) -> ControllerResult:
    """Dispatch instruction by type and return updated state."""
    instruction_type = str(instruction.get("instruction_type", "unknown"))
    raw_text = str(instruction.get("raw_text", "")).strip()

    if instruction_type == "question":
        # All question answering is delegated to the RAG service passed in by main.
        answer = question_handler(raw_text, current_location_index)
        LOGGER.info("RAG answer: %s", answer)
        _present_text(f"Answer: {answer}", narration_handler)
        return ControllerResult(current_location_index, False)

    if instruction_type == "walk_command":
        # Fixed-sequence tour behavior: each walk command advances exactly one stop.
        next_index = current_location_index + 1
        LOGGER.info("Moving to next tour stop. current_location_index=%s", next_index)
        _present_text(f"Moved to next stop. current_location_index={next_index}", narration_handler)
        # Future extension point: trigger navigation side effects before committing index.
        return ControllerResult(next_index, False)

    if instruction_type == "end_tour":
        LOGGER.info("Received end_tour. Exiting main loop.")
        _present_text("Ending tour.", narration_handler)
        return ControllerResult(current_location_index, True)

    # Unknown instructions are intentional no-ops to avoid accidental actions.
    LOGGER.info("Unknown instruction. No action taken.")
    _present_text("Unknown instruction; no action taken.", narration_handler)
    return ControllerResult(current_location_index, False)


def _present_text(text: str, narration_handler: Callable[[str], None] | None) -> None:
    """Print guide text and optionally mirror it to the TTS integration."""
    print(text)
    if narration_handler is None:
        return

    try:
        narration_handler(text)
    except Exception as exc:  # noqa: BLE001
        LOGGER.warning("TTS narration failed; continuing without speech output: %s", exc)
