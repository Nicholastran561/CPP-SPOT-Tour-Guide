"""Centralized parser rules and classification logic."""

from __future__ import annotations

import re
from typing import Dict, List

from config import END_TOUR_EXACT_PHRASE

INSTRUCTION_TYPES = {"question", "walk_command", "end_tour", "unknown"}

# Editable walk-command language lives here so behavior can be tuned without code rewrites.
WALK_COMMAND_REGEXES: List[str] = [
    r"\b(next|continue|move on|walk|advance|keep going|go ahead)\b",
    r"\b(let'?s go)\b",
]

QUESTION_PREFIXES: List[str] = [
    "what",
    "where",
    "when",
    "why",
    "how",
    "who",
    "is",
    "are",
    "can",
    "could",
    "tell me",
    "explain",
    "describe",
    "Give",
    "Overview",
]


def normalize_text(text: str) -> str:
    """Lowercase and normalize whitespace while keeping question marks."""
    cleaned = text.lower().strip()
    cleaned = re.sub(r"[^a-z0-9?\s]", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    return cleaned


def classify_instruction_type(raw_text: str) -> str:
    """Classify raw transcript into one supported instruction type."""
    normalized = normalize_text(raw_text)

    # Exact phrase requirement is checked against original normalized text.
    if normalized == END_TOUR_EXACT_PHRASE:
        return "end_tour"

    if not normalized:
        return "unknown"

    # Walk commands are matched before question heuristics to keep action phrases deterministic.
    for pattern in WALK_COMMAND_REGEXES:
        if re.search(pattern, normalized):
            return "walk_command"

    if normalized.endswith("?"):
        return "question"

    # Prefix-based fallback catches question phrasing that lacks a trailing question mark.
    if any(normalized.startswith(prefix) for prefix in QUESTION_PREFIXES):
        return "question"

    return "unknown"


def parse_instruction(raw_text: str) -> Dict[str, object]:
    """Parse raw transcript into a minimal instruction payload."""
    instruction_type = classify_instruction_type(raw_text)
    parsed_data: Dict[str, object] = {}
    return {
        "instruction_type": instruction_type,
        "raw_text": raw_text,
        "parsed_data": parsed_data,
    }
