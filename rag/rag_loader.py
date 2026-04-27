"""RAG data loading and CSV-to-Document conversion."""

from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import pandas as pd
from langchain_core.documents import Document

REQUIRED_COLUMNS = {
    "id",
    "title",
    "fact_scope",
    "route_order",
    "location_name",
    "aliases",
    "short_description",
    "long_description",
    "tags",
}

FACT_SCOPE_TOUR_STOP = "tour_stop"
FACT_SCOPE_GENERAL = "general"
ALLOWED_FACT_SCOPES = {FACT_SCOPE_TOUR_STOP, FACT_SCOPE_GENERAL}
GENERAL_ROUTE_ORDER = -1


class CsvDataError(RuntimeError):
    """Raised when CSV data cannot be loaded or validated."""


def load_locations_csv(csv_path: Path) -> pd.DataFrame:
    """Load locations CSV and verify required schema columns exist."""
    if not csv_path.exists():
        raise CsvDataError(f"CSV not found: {csv_path}")

    df = pd.read_csv(csv_path)
    # Fail fast on schema mismatch so indexing/retrieval does not silently degrade.
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        missing_cols = ", ".join(sorted(missing))
        raise CsvDataError(f"CSV missing required columns: {missing_cols}")

    scopes = df["fact_scope"].fillna("").map(_normalize_fact_scope)
    invalid_scopes = sorted({scope for scope in scopes.unique() if scope not in ALLOWED_FACT_SCOPES})
    if invalid_scopes:
        raise CsvDataError(
            "CSV contains invalid fact_scope values: "
            f"{', '.join(invalid_scopes)}. "
            f"Allowed values: {', '.join(sorted(ALLOWED_FACT_SCOPES))}"
        )

    return df


def _normalize_fact_scope(value: object) -> str:
    return str(value).strip().lower()


def _route_order_for_row(row: dict) -> int:
    fact_scope = _normalize_fact_scope(row["fact_scope"])
    if fact_scope == FACT_SCOPE_GENERAL:
        return GENERAL_ROUTE_ORDER
    return int(row["route_order"])


def dataframe_to_documents(df: pd.DataFrame) -> Tuple[List[Document], List[str]]:
    """Convert dataframe rows into LangChain Documents with stable IDs."""
    documents: List[Document] = []
    ids: List[str] = []

    for row in df.to_dict(orient="records"):
        row_id = int(row["id"])
        title = str(row["title"]).strip()
        fact_scope = _normalize_fact_scope(row["fact_scope"])
        route_order = _route_order_for_row(row)
        # Stable IDs are row-level so each location can have multiple independent facts.
        doc_id = str(row_id)
        ids.append(doc_id)

        # Keep full textual context in page_content for embeddings + answer grounding.
        content = (
            f"ID: {row_id}\n"
            f"Title: {title}\n"
            f"Fact Scope: {fact_scope}\n"
            f"Route Order: {route_order}\n"
            f"Location Name: {row['location_name']}\n"
            f"Aliases: {row['aliases']}\n"
            f"Short Description: {row['short_description']}\n"
            f"Long Description: {row['long_description']}\n"
            f"Tags: {row['tags']}"
        )

        metadata = {
            "id": row_id,
            "title": title,
            "fact_scope": fact_scope,
            "route_order": route_order,
            "location_name": str(row["location_name"]),
            "aliases": str(row["aliases"]),
            "tags": str(row["tags"]),
        }
        documents.append(Document(page_content=content, metadata=metadata))

    return documents, ids


def get_location_name_for_route_order(df: pd.DataFrame, route_order: int) -> str:
    """Return location name for route order if known, otherwise 'Unknown'."""
    # Controller state can reference unknown indexes; return a safe fallback name.
    tour_stop_df = df[df["fact_scope"].map(_normalize_fact_scope) == FACT_SCOPE_TOUR_STOP]
    matches = tour_stop_df[tour_stop_df["route_order"] == route_order]
    if matches.empty:
        return "Unknown"
    return str(matches.iloc[0]["location_name"])


def get_total_stops(df: pd.DataFrame) -> int:
    """Return total unique stop count from route_order values."""
    tour_stop_df = df[df["fact_scope"].map(_normalize_fact_scope) == FACT_SCOPE_TOUR_STOP]
    return int(tour_stop_df["route_order"].nunique())
