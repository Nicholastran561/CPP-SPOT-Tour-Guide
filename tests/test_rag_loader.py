from pathlib import Path

import pandas as pd

from rag.rag_loader import (
    GENERAL_ROUTE_ORDER,
    dataframe_to_documents,
    get_location_name_for_route_order,
    get_total_stops,
    load_locations_csv,
)


def test_csv_loading_and_required_columns() -> None:
    df = load_locations_csv(Path("locations.csv"))
    assert not df.empty
    assert "id" in df.columns
    assert "title" in df.columns
    assert "fact_scope" in df.columns
    assert "route_order" in df.columns
    assert "aliases" in df.columns


def test_document_conversion_stable_ids() -> None:
    df = load_locations_csv(Path("locations.csv"))
    docs, ids = dataframe_to_documents(df)
    assert docs
    assert ids
    assert ids[0] == str(int(df.iloc[0]["id"]))


def test_document_content_uses_human_stop_numbers() -> None:
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "title": "Lobby",
                "fact_scope": "tour_stop",
                "route_order": 0,
                "location_name": "Lobby",
                "aliases": "entrance",
                "short_description": "short",
                "long_description": "long",
                "tags": "tag",
            },
        ]
    )

    docs, _ids = dataframe_to_documents(df)

    assert "Tour Stop Number: 1" in docs[0].page_content
    assert "Route Order: 0" not in docs[0].page_content
    assert docs[0].metadata["route_order"] == 0
    assert docs[0].metadata["tour_stop_number"] == 1


def test_general_facts_do_not_count_as_tour_stops() -> None:
    df = pd.DataFrame(
        [
            {
                "id": 1,
                "title": "Stop fact",
                "fact_scope": "tour_stop",
                "route_order": 0,
                "location_name": "Lobby",
                "aliases": "entrance",
                "short_description": "short",
                "long_description": "long",
                "tags": "tag",
            },
            {
                "id": 2,
                "title": "School fact",
                "fact_scope": "general",
                "route_order": 0,
                "location_name": "Cal Poly Pomona",
                "aliases": "CPP",
                "short_description": "short",
                "long_description": "long",
                "tags": "general",
            },
        ]
    )

    docs, _ids = dataframe_to_documents(df)

    assert get_total_stops(df) == 1
    assert get_location_name_for_route_order(df, 0) == "Lobby"
    assert docs[1].metadata["fact_scope"] == "general"
    assert docs[1].metadata["route_order"] == GENERAL_ROUTE_ORDER
