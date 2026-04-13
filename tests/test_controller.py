from core.controller import handle_instruction


def _dummy_qna(question: str, idx: int) -> str:
    return f"q={question}, idx={idx}"


def test_controller_walk_increment() -> None:
    result = handle_instruction(
        instruction={"instruction_type": "walk_command", "raw_text": "continue"},
        current_location_index=2,
        question_handler=_dummy_qna,
    )
    assert result.updated_location_index == 3
    assert result.end_tour is False


def test_controller_unknown_noop() -> None:
    result = handle_instruction(
        instruction={"instruction_type": "unknown", "raw_text": "blah"},
        current_location_index=5,
        question_handler=_dummy_qna,
    )
    assert result.updated_location_index == 5
    assert result.end_tour is False
