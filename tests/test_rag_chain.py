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


def test_system_prompt_uses_dynamic_location_context() -> None:
    prompt = build_prompt_template()

    rendered = prompt.invoke(
        {
            "current_stop_number": 1,
            "total_stops": 5,
            "current_location_name": "Lobby",
            "retrieved_context": "Tour Stop Number: 1\nLocation Name: Lobby",
            "question": "What is here?",
        }
    )
    system_message = rendered.messages[0].content

    assert "tour is limited to Building 8" in system_message
    assert "currently giving a tour of building 8" not in system_message.lower()
    assert "source of truth" in system_message
    assert "current_location_name" in system_message
    assert "two to five clear spoken sentences" in system_message
    assert "Long Description details" in system_message


def test_system_prompt_forbids_off_route_navigation_offers() -> None:
    prompt = build_prompt_template()

    rendered = prompt.invoke(
        {
            "current_stop_number": 1,
            "total_stops": 5,
            "current_location_name": "Lobby",
            "retrieved_context": "Location Name: Advising Center\nRoom: Building 8, Room 306",
            "question": "Where can I get advising?",
        }
    )
    system_message = rendered.messages[0].content

    assert "cannot guide visitors to arbitrary destinations" in system_message
    assert "navigate off the fixed tour route" in system_message
    assert "Only the fixed walk command advances the tour by one stop" in system_message


def test_system_prompt_forbids_follow_up_questions_without_memory() -> None:
    prompt = build_prompt_template()

    rendered = prompt.invoke(
        {
            "current_stop_number": 1,
            "total_stops": 5,
            "current_location_name": "Lobby",
            "retrieved_context": "Tour Stop Number: 1\nLocation Name: Lobby",
            "question": "What is here?",
        }
    )
    system_message = rendered.messages[0].content

    assert "does not keep conversational memory" in system_message
    assert "do not ask the visitor follow-up questions" in system_message
    assert "ask whether they want to continue" in system_message
    assert "End with a direct statement, not a question" in system_message
