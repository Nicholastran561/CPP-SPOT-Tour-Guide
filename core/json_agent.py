"""JSON instruction artifact creation and persistence."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Dict


class InstructionSerializationError(RuntimeError):
    """Raised when instruction JSON cannot be serialized."""


def build_instruction_json(
    instruction_type: str,
    raw_text: str,
    parsed_data: Dict[str, object] | None = None,
) -> Dict[str, object]:
    """Build the minimal instruction object with ISO timestamp."""
    # Timestamp is added here so raw transcript and parsed instruction stay tied together.
    return {
        "instruction_type": instruction_type,
        "raw_text": raw_text,
        "parsed_data": parsed_data or {},
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }


def save_instruction_json(instruction: Dict[str, object], output_path: Path) -> Path:
    """Serialize and persist instruction JSON with a validation round-trip."""
    try:
        # Validate by round-tripping JSON before writing to disk.
        payload = json.dumps(instruction, indent=2)
        json.loads(payload)
    except Exception as exc:  # noqa: BLE001
        raise InstructionSerializationError(f"Malformed JSON payload: {exc}") from exc

    output_path.write_text(payload, encoding="utf-8")
    return output_path
