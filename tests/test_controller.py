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


def test_controller_mirrors_presented_text_to_narration_handler() -> None:
    spoken: list[str] = []

    result = handle_instruction(
        instruction={"instruction_type": "question", "raw_text": "what is this"},
        current_location_index=1,
        question_handler=_dummy_qna,
        narration_handler=spoken.append,
    )

    assert result.updated_location_index == 1
    assert spoken == ["Answer: q=what is this, idx=1"]


def test_controller_ignores_narration_handler_failure() -> None:
    def broken_narration_handler(_text: str) -> None:
        raise OSError("not connected")

    result = handle_instruction(
        instruction={"instruction_type": "walk_command", "raw_text": "continue"},
        current_location_index=2,
        question_handler=_dummy_qna,
        narration_handler=broken_narration_handler,
    )

    assert result.updated_location_index == 3
    assert result.end_tour is False
