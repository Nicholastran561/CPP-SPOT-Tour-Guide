from rag.rag_chain import build_prompt_template


def test_prompt_uses_human_current_stop_number() -> None:
    prompt = build_prompt_template()

    rendered = prompt.invoke(
        {
            "current_stop_number": 1,
            "total_stops": 5,
            "current_location_name": "Lobby",
            "retrieved_context": "Tour Stop Number: 1\nLocation Name: Lobby",
            "question": "What is the first stop?",
        }
    )
    human_message = rendered.messages[-1].content

    assert "current_stop_number: 1" in human_message
    assert "current_location_index" not in human_message
