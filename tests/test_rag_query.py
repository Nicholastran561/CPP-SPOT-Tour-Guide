from langchain_core.documents import Document

from rag.rag_query import prioritize_current_location, retrieve_documents


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
