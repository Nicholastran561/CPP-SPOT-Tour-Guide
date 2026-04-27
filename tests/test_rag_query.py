from langchain_core.documents import Document

from rag.rag_query import (
    RAG_CONTEXT_OUTPUT_SEPARATOR,
    format_retrieved_context,
    print_retrieved_context,
    prioritize_current_location,
    retrieve_documents,
)


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


def test_print_retrieved_context_outputs_debug_block(capsys) -> None:
    print_retrieved_context("[1] Tour Stop Number: 1")

    captured = capsys.readouterr()

    assert "RETRIEVED CONTEXT" in captured.out
    assert RAG_CONTEXT_OUTPUT_SEPARATOR in captured.out
    assert "[1] Tour Stop Number: 1" in captured.out
