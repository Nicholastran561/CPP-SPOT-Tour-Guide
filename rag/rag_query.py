"""RAG querying over a persisted ChromaDB index with Ollama models."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Iterable, List

from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_core.output_parsers import StrOutputParser
from langchain_ollama import ChatOllama, OllamaEmbeddings

from config import RAG_LLM_TEMPERATURE, RAG_RETRIEVER_K
from rag.rag_chain import build_prompt_template
from rag.rag_loader import (
    CsvDataError,
    dataframe_to_documents,
    get_location_name_for_route_order,
    get_total_stops,
    load_locations_csv,
)

LOGGER = logging.getLogger(__name__)
RAG_CONTEXT_OUTPUT_SEPARATOR = "-" * 72
RAG_QUESTION_OUTPUT_SEPARATOR = "=" * 72


class RagUnavailableError(RuntimeError):
    """Raised when RAG dependencies or local index are unavailable."""


def retrieve_documents(retriever, question: str) -> List[Document]:
    """Retrieve top documents for question using the provided retriever."""
    # Wrapper function keeps retrieval easy to unit-test with fake retrievers.
    docs = retriever.invoke(question)
    return list(docs)


def prioritize_current_location(
    docs: Iterable[Document],
    current_location_index: int,
) -> List[Document]:
    """Prioritize docs matching current location index while preserving others."""
    matching: List[Document] = []
    non_matching: List[Document] = []
    for doc in docs:
        if doc.metadata.get("route_order") == current_location_index:
            matching.append(doc)
        else:
            non_matching.append(doc)
    return matching + non_matching


def get_current_location_documents(locations_df, current_location_index: int) -> List[Document]:
    """Return full CSV-backed documents for the current tour stop."""
    tour_stop_mask = locations_df["fact_scope"].astype(str).str.strip().str.lower() == "tour_stop"
    current_stop_df = locations_df[
        tour_stop_mask & (locations_df["route_order"].astype(int) == current_location_index)
    ]
    if current_stop_df.empty:
        return []

    documents, _ids = dataframe_to_documents(current_stop_df)
    return documents


def merge_unique_documents(
    primary_docs: Iterable[Document],
    secondary_docs: Iterable[Document],
) -> List[Document]:
    """Merge document groups, preserving order and removing duplicate rows."""
    merged: List[Document] = []
    seen = set()

    for doc in [*primary_docs, *secondary_docs]:
        doc_id = doc.metadata.get("id")
        key = f"id:{doc_id}" if doc_id is not None else f"content:{doc.page_content}"
        if key in seen:
            continue
        seen.add(key)
        merged.append(doc)

    return merged


def format_retrieved_context(docs: Iterable[Document]) -> str:
    """Render retrieved docs into compact context text."""
    chunks = []
    for idx, doc in enumerate(docs, start=1):
        chunks.append(f"[{idx}] {doc.page_content}")
    return "\n\n".join(chunks)


def print_retrieved_context(context: str) -> None:
    """Print retrieved RAG context for operator debugging."""
    context_text = context if context else "(no retrieved context)"
    print(
        "\n".join(
            [
                "",
                RAG_CONTEXT_OUTPUT_SEPARATOR,
                "RETRIEVED CONTEXT",
                RAG_CONTEXT_OUTPUT_SEPARATOR,
                context_text,
                RAG_CONTEXT_OUTPUT_SEPARATOR,
            ]
        )
    )


def print_question(question: str) -> None:
    """Print the user question for operator debugging."""
    print(
        "\n".join(
            [
                "",
                RAG_QUESTION_OUTPUT_SEPARATOR,
                "QUESTION",
                RAG_QUESTION_OUTPUT_SEPARATOR,
                question,
                RAG_QUESTION_OUTPUT_SEPARATOR,
            ]
        )
    )


def remove_trailing_question_sentences(answer: str) -> str:
    """Remove trailing model follow-up questions from an answer."""
    text = answer.strip()
    while text.endswith("?"):
        sentence_start = max(text.rfind(". "), text.rfind("! "), text.rfind("\n"))
        if sentence_start == -1:
            return ""
        if text[sentence_start] == "\n":
            text = text[:sentence_start].rstrip()
        else:
            text = text[: sentence_start + 1].rstrip()
    return text


class RagService:
    """Runtime RAG service bound to a persisted local Chroma index."""

    def __init__(
        self,
        csv_path: Path,
        persist_directory: Path,
        collection_name: str,
        embedding_model: str,
        llm_model: str,
    ) -> None:
        # Main runtime should only query an already-built local index.
        if not persist_directory.exists():
            raise RagUnavailableError(
                f"Chroma index directory not found: {persist_directory}. "
                "Run rebuild_chroma_from_csv.py first."
            )

        try:
            self.locations_df = load_locations_csv(csv_path)
            self.total_stops = get_total_stops(self.locations_df)
        except CsvDataError as exc:
            raise RagUnavailableError(str(exc)) from exc

        try:
            # Embeddings + vector store + model are initialized once per process.
            self.embeddings = OllamaEmbeddings(model=embedding_model)
            self.vector_store = Chroma(
                collection_name=collection_name,
                persist_directory=str(persist_directory),
                embedding_function=self.embeddings,
            )
            self.retriever = self.vector_store.as_retriever(search_kwargs={"k": RAG_RETRIEVER_K})
            self.llm = ChatOllama(model=llm_model, temperature=RAG_LLM_TEMPERATURE)
        except Exception as exc:  # noqa: BLE001
            raise RagUnavailableError(f"Failed to initialize RAG components: {exc}") from exc

        self.prompt = build_prompt_template()
        self.chain = self.prompt | self.llm | StrOutputParser()

    def answer_question(self, question: str, current_location_index: int) -> str:
        """Answer a question using retrieved CSV-backed context only."""
        try:
            docs = retrieve_documents(self.retriever, question)
        except Exception as exc:  # noqa: BLE001
            raise RagUnavailableError(f"Retrieval failed (is Ollama running?): {exc}") from exc

        # Current location CSV details are always included so broad "what is here"
        # questions can use the full stop description even when vector ranking is noisy.
        current_location_docs = get_current_location_documents(
            self.locations_df, current_location_index
        )
        retrieved_docs = prioritize_current_location(docs, current_location_index)
        context_docs = merge_unique_documents(current_location_docs, retrieved_docs)
        context = format_retrieved_context(context_docs) if context_docs else ""
        print_retrieved_context(context)
        print_question(question)
        current_location_name = get_location_name_for_route_order(
            self.locations_df, current_location_index
        )

        try:
            response = self.chain.invoke(
                {
                    "current_stop_number": current_location_index + 1,
                    "current_location_name": current_location_name,
                    "total_stops": self.total_stops,
                    "retrieved_context": context,
                    "question": question,
                }
            )
        except Exception as exc:  # noqa: BLE001
            raise RagUnavailableError(f"Answer generation failed (is Ollama available?): {exc}") from exc

        final_text = remove_trailing_question_sentences(str(response))
        if not final_text:
            return "I am not sure, but I can try to help with another question."

        LOGGER.debug("RAG response: %s", final_text)
        return final_text
