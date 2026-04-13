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
) -> ControllerResult:
    """Dispatch instruction by type and return updated state."""
    instruction_type = str(instruction.get("instruction_type", "unknown"))
    raw_text = str(instruction.get("raw_text", "")).strip()

    if instruction_type == "question":
        # All question answering is delegated to the RAG service passed in by main.
        answer = question_handler(raw_text, current_location_index)
        LOGGER.info("RAG answer: %s", answer)
        print(f"Answer: {answer}")
        # Future extension point: invoke TTS here after answer generation.
        return ControllerResult(current_location_index, False)

    if instruction_type == "walk_command":
        # Fixed-sequence tour behavior: each walk command advances exactly one stop.
        next_index = current_location_index + 1
        LOGGER.info("Moving to next tour stop. current_location_index=%s", next_index)
        print(f"Moved to next stop. current_location_index={next_index}")
        # Future extension point: trigger navigation side effects before committing index.
        return ControllerResult(next_index, False)

    if instruction_type == "end_tour":
        LOGGER.info("Received end_tour. Exiting main loop.")
        print("Ending tour.")
        return ControllerResult(current_location_index, True)

    # Unknown instructions are intentional no-ops to avoid accidental actions.
    LOGGER.info("Unknown instruction. No action taken.")
    print("Unknown instruction; no action taken.")
    return ControllerResult(current_location_index, False)
