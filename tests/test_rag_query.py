import pandas as pd
from langchain_core.documents import Document

from rag.rag_query import (
    RAG_CONTEXT_OUTPUT_SEPARATOR,
    RAG_QUESTION_OUTPUT_SEPARATOR,
    RagService,
    format_retrieved_context,
    get_current_location_documents,
    merge_unique_documents,
    print_question,
    print_retrieved_context,
    prioritize_current_location,
    retrieve_documents,
    remove_trailing_question_sentences,
)


def location_row(
    *,
    row_id: int = 1,
    route_order: int = 0,
    location_name: str = "Lobby",
    long_description: str = "The lobby has a welcome desk and seating.",
) -> dict:
    return {
        "id": row_id,
        "title": f"{location_name} Overview",
        "fact_scope": "tour_stop",
        "route_order": route_order,
        "location_name": location_name,
        "aliases": location_name.lower(),
        "short_description": "short",
        "long_description": long_description,
        "tags": "tag",
    }


def test_prioritize_current_location_prefers_matching_doc() -> None:
    docs = [
        Document(page_content="A", metadata={"route_order": 4}),
        Document(page_content="B", metadata={"route_order": 1}),
    ]

    ordered = prioritize_current_location(docs, current_location_index=1)
    assert ordered[0].metadata["route_order"] == 1


def test_retrieve_documents_returns_relevant_row() -> None:
    class FakeRetriever:
        def invoke(self, question: str):
            if "reception" in question.lower():
                return [Document(page_content="Reception Desk details", metadata={"route_order": 1})]
            return []

    docs = retrieve_documents(FakeRetriever(), "Tell me about reception")
    assert docs
    assert docs[0].metadata["route_order"] == 1


def test_format_retrieved_context_keeps_document_text() -> None:
    docs = [Document(page_content="Tour Stop Number: 1\nLocation Name: Lobby", metadata={})]

    context = format_retrieved_context(docs)

    assert "Tour Stop Number: 1" in context


def test_get_current_location_documents_keeps_full_description() -> None:
    df = pd.DataFrame(
        [
            location_row(
                row_id=1,
                route_order=0,
                location_name="Conference Room",
                long_description="This room has a lectern, a white board, and a black phone near the door.",
            ),
            location_row(row_id=2, route_order=1, location_name="Desk Row"),
        ]
    )

    docs = get_current_location_documents(df, current_location_index=0)

    assert len(docs) == 1
    assert docs[0].metadata["location_name"] == "Conference Room"
    assert "black phone near the door" in docs[0].page_content


def test_merge_unique_documents_keeps_current_context_first_without_duplicates() -> None:
    current_doc = Document(
        page_content="Current stop full description",
        metadata={"id": 1, "route_order": 0},
    )
    duplicate_retrieved_doc = Document(
        page_content="Current stop full description",
        metadata={"id": 1, "route_order": 0},
    )
    other_doc = Document(page_content="Other stop", metadata={"id": 2, "route_order": 1})

    docs = merge_unique_documents([current_doc], [other_doc, duplicate_retrieved_doc])

    assert docs == [current_doc, other_doc]


def test_print_retrieved_context_outputs_debug_block(capsys) -> None:
    print_retrieved_context("[1] Tour Stop Number: 1")

    captured = capsys.readouterr()

    assert "RETRIEVED CONTEXT" in captured.out
    assert RAG_CONTEXT_OUTPUT_SEPARATOR in captured.out
    assert "[1] Tour Stop Number: 1" in captured.out


def test_print_question_outputs_debug_block(capsys) -> None:
    print_question("what is this")

    captured = capsys.readouterr()

    assert "QUESTION" in captured.out
    assert RAG_QUESTION_OUTPUT_SEPARATOR in captured.out
    assert "what is this" in captured.out


def test_answer_question_prints_context_before_question(capsys) -> None:
    class FakeRetriever:
        def invoke(self, _question: str):
            return [Document(page_content="Tour Stop Number: 1", metadata={"route_order": 0})]

    class FakeChain:
        def invoke(self, _payload: dict) -> str:
            return "Lobby answer"

    service = object.__new__(RagService)
    service.retriever = FakeRetriever()
    service.locations_df = pd.DataFrame([location_row(location_name="Lobby")])
    service.total_stops = 1
    service.chain = FakeChain()

    answer = service.answer_question("what is this", current_location_index=0)

    captured = capsys.readouterr()

    assert answer == "Lobby answer"
    assert captured.out.index("RETRIEVED CONTEXT") < captured.out.index("QUESTION")


def test_remove_trailing_question_sentences_removes_follow_up_question() -> None:
    answer = remove_trailing_question_sentences(
        "This is the main welcome area of Building 8. Would you like to continue?"
    )

    assert answer == "This is the main welcome area of Building 8."
