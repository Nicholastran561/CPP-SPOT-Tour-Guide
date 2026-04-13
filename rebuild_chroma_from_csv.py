"""Rebuild the persisted Chroma index from the CSV source of truth."""

from __future__ import annotations

import logging
import shutil
from pathlib import Path

from langchain_chroma import Chroma
from langchain_ollama import OllamaEmbeddings

from config import (
    CHROMA_COLLECTION_NAME,
    CHROMA_PERSIST_DIR,
    CSV_PATH,
    OLLAMA_EMBED_MODEL,
)
from rag.rag_loader import CsvDataError, dataframe_to_documents, load_locations_csv

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
LOGGER = logging.getLogger(__name__)


def rebuild_index(
    csv_path: Path = CSV_PATH,
    persist_dir: Path = CHROMA_PERSIST_DIR,
    collection_name: str = CHROMA_COLLECTION_NAME,
    embedding_model: str = OLLAMA_EMBED_MODEL,
) -> None:
    """Rebuild local Chroma index from CSV using stable fact-level document IDs."""
    try:
        df = load_locations_csv(csv_path)
    except CsvDataError as exc:
        raise RuntimeError(f"CSV load failed: {exc}") from exc

    documents, ids = dataframe_to_documents(df)
    if not documents:
        raise RuntimeError("CSV loaded but no rows were available to index.")

    # Rebuild policy is full reset: remove old index and regenerate from CSV source of truth.
    if persist_dir.exists():
        shutil.rmtree(persist_dir)
    persist_dir.mkdir(parents=True, exist_ok=True)

    try:
        embeddings = OllamaEmbeddings(model=embedding_model)
        Chroma.from_documents(
            documents=documents,
            ids=ids,
            collection_name=collection_name,
            embedding=embeddings,
            persist_directory=str(persist_dir),
        )
    except Exception as exc:  # noqa: BLE001
        raise RuntimeError(f"Index rebuild failed (is Ollama running?): {exc}") from exc

    LOGGER.info("Rebuilt Chroma index at: %s", persist_dir)


if __name__ == "__main__":
    rebuild_index()
