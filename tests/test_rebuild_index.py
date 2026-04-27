import shutil
from pathlib import Path

import rebuild_chroma_from_csv


def test_rebuild_index_calls_chroma_with_stable_ids(monkeypatch) -> None:
    calls = {}

    def fake_load_locations_csv(csv_path: Path):
        import pandas as pd

        return pd.DataFrame(
            [
                {
                    "id": 7,
                    "title": "Test Fact 7",
                    "fact_scope": "tour_stop",
                    "route_order": 7,
                    "location_name": "Test",
                    "aliases": "alias",
                    "short_description": "short",
                    "long_description": "long",
                    "tags": "tag",
                }
            ]
        )

    def fake_embeddings(model: str):
        calls["embed_model"] = model
        return object()

    class FakeChroma:
        @staticmethod
        def from_documents(documents, ids, collection_name, embedding, persist_directory):
            calls["ids"] = ids
            calls["collection_name"] = collection_name
            calls["persist_directory"] = persist_directory
            assert documents
            assert embedding is not None

    monkeypatch.setattr(rebuild_chroma_from_csv, "load_locations_csv", fake_load_locations_csv)
    monkeypatch.setattr(rebuild_chroma_from_csv, "OllamaEmbeddings", fake_embeddings)
    monkeypatch.setattr(rebuild_chroma_from_csv, "Chroma", FakeChroma)

    workspace_tmp = Path("test_tmp_rebuild")
    if workspace_tmp.exists():
        shutil.rmtree(workspace_tmp)
    workspace_tmp.mkdir(parents=True, exist_ok=True)
    persist = workspace_tmp / "chroma_db"

    rebuild_chroma_from_csv.rebuild_index(
        csv_path=workspace_tmp / "locations.csv",
        persist_dir=persist,
        collection_name="test_collection",
        embedding_model="mxbai-embed-large",
    )

    assert calls["ids"] == ["7"]
    assert calls["collection_name"] == "test_collection"
    assert calls["persist_directory"] == str(persist)
    assert calls["embed_model"] == "mxbai-embed-large"

    shutil.rmtree(workspace_tmp)
