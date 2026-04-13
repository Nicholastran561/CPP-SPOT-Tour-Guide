from pathlib import Path

from rag.rag_loader import dataframe_to_documents, load_locations_csv


def test_csv_loading_and_required_columns() -> None:
    df = load_locations_csv(Path("locations.csv"))
    assert not df.empty
    assert "id" in df.columns
    assert "title" in df.columns
    assert "route_order" in df.columns
    assert "aliases" in df.columns


def test_document_conversion_stable_ids() -> None:
    df = load_locations_csv(Path("locations.csv"))
    docs, ids = dataframe_to_documents(df)
    assert docs
    assert ids
    assert ids[0] == str(int(df.iloc[0]["id"]))
