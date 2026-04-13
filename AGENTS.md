# AGENTS.md

## Purpose
This repository contains an offline Python prototype for a Boston Dynamics SPOT tour guide assistant.

## Non-negotiable constraints
- Runtime must work fully offline.
- Target OS is Windows.
- Use Python 3.10+.
- Do not introduce cloud services or internet-dependent runtime components.
- Save audio, transcript, and instruction JSON artifacts to disk.
- Keep implementations simple, readable, and easy to debug.

## Architecture boundaries
- STT uses `faster-whisper`.
- Parser is plain Python and rule-based.
- Controller is plain Python.
- RAG uses LangChain + Ollama + ChromaDB.
- Use LangChain only inside the RAG subsystem.
- Do not move parser or controller logic into LangChain.

## Command model
The parser must emit exactly one of:
- `question`
- `walk_command`
- `end_tour`
- `unknown`

Behavior:
- `end_tour` should trigger only on the exact phrase `end the tour spot`.
- `walk_command` means advance to the next fixed tour stop only.
- `unknown` should produce no action other than a fallback log/print.

## Tour state
- `main.py` owns `current_location_index`.
- A `walk_command` increments `current_location_index` by exactly 1.
- Tours are fixed-sequence, not dynamic destination navigation.

## Parser rules
- Keep all parser phrases, regexes, and rule lists centralized in one easy-to-edit file.
- Do not scatter command phrases across multiple modules.
- Favor explicit, editable rules over hidden behavior.

## Data and RAG
- The CSV is the source knowledge base for tour locations and location facts.
- Include aliases in the CSV schema.
- Questions are always answered through RAG.
- Pass current-location context from the controller into the RAG flow.
- Use LangChain `ChatPromptTemplate` for RAG prompt construction.
- Persist the ChromaDB index locally.

## CSV to vector DB workflow
- The CSV is the source of truth.
- The ChromaDB index is a generated artifact built from the CSV.
- The vector store does not auto-update when the CSV changes.
- Rebuild the index with `rebuild_chroma_from_csv.py` whenever the CSV changes.
- Use stable document IDs based on `location_index`.

## File layout and persistence
- Do not create extra folders unless explicitly requested.
- Save files in the project root with timestamp-based names:
  - `YYYY-MM-DD_HH-MM-SS.wav`
  - `YYYY-MM-DD_HH-MM-SS.txt`
  - `YYYY-MM-DD_HH-MM-SS.json`

## Preferred libraries
- Audio: `sounddevice`, `soundfile`, `keyboard`
- STT: `faster-whisper`
- CSV/data: `pandas`
- RAG: `langchain`, `langchain-ollama`, `langchain-chroma`, `chromadb`
- LLM/embeddings: Ollama
- Testing: `pytest`

## Coding style
- Prefer small, single-purpose functions.
- Use `pathlib` for paths.
- Use `logging` for visibility into each stage.
- Add docstrings where they help.
- Prefer clarity over clever abstraction.
- Add targeted error handling for missing microphone, failed transcription, missing CSV, missing vector index, Ollama failures, and empty retrieval results.

## Validation
Before considering work complete:
- run or provide tests for parser classification
- verify walk-command increment logic
- verify end-tour exact-phrase handling
- verify basic CSV load and RAG retrieval behavior
- verify the rebuild script can recreate the Chroma index from the CSV

## Future-facing notes
- Do not implement real SPOT control yet.
- Do not implement TTS yet.
- Keep extension points clear for future SPOT API and TTS integration.
