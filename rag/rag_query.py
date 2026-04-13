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
from rag.rag_loader import CsvDataError, get_location_name_for_route_order, get_total_stops, load_locations_csv

LOGGER = logging.getLogger(__name__)


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


def format_retrieved_context(docs: Iterable[Document]) -> str:
    """Render retrieved docs into compact context text."""
    chunks = []
    for idx, doc in enumerate(docs, start=1):
        chunks.append(f"[{idx}] {doc.page_content}")
    return "\n\n".join(chunks)


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

        # Current location context is promoted to the front to improve local relevance.
        prioritized_docs = prioritize_current_location(docs, current_location_index)
        context = format_retrieved_context(prioritized_docs) if prioritized_docs else ""
        current_location_name = get_location_name_for_route_order(
            self.locations_df, current_location_index
        )

        try:
            response = self.chain.invoke(
                {
                    "current_location_index": current_location_index,
                    "current_location_name": current_location_name,
                    "total_stops": self.total_stops,
                    "retrieved_context": context,
                    "question": question,
                }
            )
        except Exception as exc:  # noqa: BLE001
            raise RagUnavailableError(f"Answer generation failed (is Ollama available?): {exc}") from exc

        final_text = str(response).strip()
        if not final_text:
            return "I am not sure, but I can try to help with another question."

        LOGGER.debug("RAG response: %s", final_text)
        return final_text
