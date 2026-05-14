# rag/

Offline retrieval-augmented generation. The tour's knowledge base lives in [../locations.csv](../locations.csv); this folder turns it into a vector index, retrieves relevant facts at runtime, and asks a local Ollama model to write a grounded answer.

What "RAG" means: instead of letting the model answer from its training data alone, we **retrieve** matching facts from our CSV first and pass them into the prompt as **context**. The model **generates** an answer grounded in those facts. Result: more accurate, more consistent campus-tour answers, and everything runs offline.

## Pipeline

```
locations.csv  ──(rag_loader)──>  LangChain Documents
                                       │
                                       ▼
                           (rebuild_chroma_from_csv.py — one-off)
                                       │
                                       ▼
                                  chroma_db/   ←── persisted vector index
                                       │
   user question ─────────────────────►│
                                       │ (rag_query.RagService.answer_question)
                                       ▼
                            similarity search (k = 6)
                                       │
                                       ▼
                          rag_chain.build_prompt(...)
                                       │
                                       ▼
                               Ollama llama3.1:8b
                                       │
                                       ▼
                                    answer
```

## Files

| File | Purpose |
|---|---|
| [rag_loader.py](rag_loader.py) | Reads [../locations.csv](../locations.csv), validates the schema, and converts each row into a LangChain `Document` with a stable ID. Splits rows by `fact_scope` (`tour_stop` vs `general`). |
| [rag_chain.py](rag_chain.py) | Builds the `ChatPromptTemplate`. Slots: `current_location_index`, `total_stops`, `current_location_name`, `retrieved_context`, `question`. This is where the assistant's tone and answer style are defined. |
| [rag_query.py](rag_query.py) | `RagService` — loads the persisted Chroma index at startup, runs similarity search per question (prioritizing docs at the current tour stop), and calls Ollama via LangChain. Raises `RagUnavailableError` if the index or Ollama is missing. |

## Models and tunables

All set in [../config.py](../config.py):

| Constant | Default | What it controls |
|---|---|---|
| `OLLAMA_LLM_MODEL` | `llama3.1:8b` | Generation model. Pull with `ollama pull llama3.1:8b`. |
| `OLLAMA_EMBED_MODEL` | `mxbai-embed-large` | Embedding model used at index build and retrieval. |
| `RAG_RETRIEVER_K` | `6` | How many docs to pull per question. Higher = more context, more noise. |
| `RAG_LLM_TEMPERATURE` | `0.0` | LLM creativity. 0 = deterministic. |
| `CHROMA_PERSIST_DIR` | `./chroma_db` | Where the vector index lives on disk. |
| `CHROMA_COLLECTION_NAME` | `spot_tour_locations` | Chroma collection name. |

## Index lifecycle

The Chroma index is a **generated artifact** — it does not auto-update when [../locations.csv](../locations.csv) changes. The CSV is the source of truth.

Rebuild after any CSV edit:

```powershell
python rebuild_chroma_from_csv.py
```

That script drops the old collection and re-embeds every row. Document IDs come from the CSV `id` column so the index is reproducible.

For full CSV schema documentation, see the "CSV and vector index behavior" section of [../README.md](../README.md).

## Extension points

- **Retrieval tuning** — change `RAG_RETRIEVER_K` in [../config.py](../config.py), or switch to MMR / metadata filters inside `RagService` in [rag_query.py](rag_query.py).
- **Prompt rewrites** — the assistant's voice, response length, and refusal behavior all live in [rag_chain.py](rag_chain.py). Edit the system message there.
- **Swap LLM or embedding model** — change the Ollama model names in [../config.py](../config.py), then `ollama pull <new-model>`. If you change the embedding model, **rerun `rebuild_chroma_from_csv.py`** — old embeddings are no longer compatible.
- **New fact scope** — beyond `tour_stop` and `general`, add a new value to the `fact_scope` column in the CSV. Then update [rag_loader.py](rag_loader.py) to recognize it and [rag_query.py](rag_query.py) to decide when to surface it.
- **Conversation memory** — a sliding window of recent Q/A pairs could be passed into the prompt template for follow-up questions. The slot would need to be added in [rag_chain.py](rag_chain.py) and threaded from [../main.py](../main.py).

## Related

- [../README.md](../README.md) — first-time setup (Ollama install, model pulls, index build) and CSV schema.
- [../rebuild_chroma_from_csv.py](../rebuild_chroma_from_csv.py) — the index builder script.
- [../core/controller.py](../core/controller.py) — calls `RagService.answer_question` when an instruction is classified as a `question`.
- [../CODEBASE_REFERENCE.md](../CODEBASE_REFERENCE.md) — full function-level reference.
