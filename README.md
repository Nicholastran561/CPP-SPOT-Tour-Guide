# SPOT Tour Assistant (Offline Prototype)

This repository contains an offline Python prototype for a Boston Dynamics SPOT tour guide assistant at Cal Poly Pomona that uses local LLM models and a local RAG pipeline backed by `locations.csv`, so users can talk to SPOT and ask tour questions with more relevant, accurate responses.

## Operational Summary
- Waits in a focused terminal for `SPACE` to record or `ESC` to exit while idle.
- Records audio locally and saves `artifacts/YYYY-MM-DD_HH-MM-SS.wav`.
- Transcribes with `faster-whisper` and saves `artifacts/YYYY-MM-DD_HH-MM-SS.txt`.
- Parses transcript into one instruction type and saves `artifacts/YYYY-MM-DD_HH-MM-SS.json`.
- Dispatches instruction in plain Python controller logic.
- Answers `question` instructions through local CSV-backed RAG (LangChain + Ollama + ChromaDB),
  while also handling general visitor questions with the local model when tour context is not relevant.

## What is RAG?
RAG stands for **Retrieval-Augmented Generation**.

In simple terms, instead of only asking the language model to answer from its general training,
the app first retrieves relevant project knowledge and then gives that context to the model.

In this project, the flow is:
- retrieve relevant tour facts from the local Chroma index built from `locations.csv`
- pass those facts (plus current stop context) into the prompt
- generate a grounded answer with the local Ollama model

This improves answer relevance and consistency for campus-tour questions, while staying fully offline.

For more detailed information on RAG here is an [AWS Article](https://aws.amazon.com/what-is/retrieval-augmented-generation/)

## Command model
Parser emits exactly one of:
- `question`
- `walk_command`
- `end_tour`
- `unknown`

Rules:
- `end_tour` triggers only on exact phrase `end the tour spot`.
- `walk_command` means move to the next fixed stop only.
- `unknown` performs no action except fallback logging/printing.

## Files
- `main.py` - main loop and artifact orchestration
- `config.py` - project settings
- `core/audio_recorder.py` - SPACE-toggle audio capture
- `core/transcriber.py` - faster-whisper transcription
- `core/parser_rules.py` - centralized parser rules
- `core/instruction_json.py` - instruction JSON creation/persistence
- `core/controller.py` - instruction dispatch and tour state updates
- `rag/rag_loader.py` - CSV load and Document conversion
- `rag/rag_chain.py` - `ChatPromptTemplate` construction
- `rag/rag_query.py` - persisted Chroma retrieval + answer generation
- `rebuild_chroma_from_csv.py` - CSV -> Chroma rebuild script
- `locations.csv` - source of truth knowledge base
- `tests/` - pytest suite

Full module/function documentation is available in `CODEBASE_REFERENCE.md`.

## Windows setup (Python 3.10+)
### First-time setup and first run
1. Create and activate venv:
```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```
2. Install dependencies:
```powershell
python -m pip install -r requirements.txt
```
3. Install Ollama locally (Windows app/installer), then run:
```powershell
ollama serve
```
If Ollama is configured to launch automatically at computer startup, this command may not be needed.
4. Pull local models once (while online), then use offline:
```powershell
ollama pull llama3.1:8b
ollama pull mxbai-embed-large
```
5. Cache the faster-whisper model once while online (required for offline runtime):
```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('base', compute_type='int8')"
```
6. Build vector index from CSV:
```powershell
python rebuild_chroma_from_csv.py
```
7. Start app:
```powershell
python main.py
```

### Normal run (after first-time setup)
Each time you start working:
1. Activate venv:
```powershell
.\.venv\Scripts\Activate.ps1
```
2. Start Ollama:
```powershell
ollama serve
```
If Ollama is already running from startup, you can skip this step.
3. Start app:
```powershell
python main.py
```

Only when `locations.csv` changes, rebuild the Chroma index before running:
```powershell
python rebuild_chroma_from_csv.py
```

## CSV and vector index behavior
- `locations.csv` is the source of truth.
- CSV supports multiple fact rows per location using:
  - `id` (stable numeric row/document ID)
  - `title` (short fact label for readability)
  - `route_order` (tour stop order used for temporal tour context)
- Required CSV columns are:
  - `id`
  - `title`
  - `route_order`
  - `location_name`
  - `aliases`
  - `short_description`
  - `long_description`
  - `tags`
- Column meaning:
  - `id`: unique numeric row ID used as stable vector document ID.
  - `title`: short label for the fact row.
  - `route_order`: integer stop index in fixed tour sequence.
  - `location_name`: canonical stop name.
  - `aliases`: alternate names (recommended pipe-separated list).
  - `short_description`: concise one-line summary.
  - `long_description`: detailed explanation/facts.
  - `tags`: retrieval keywords (recommended comma-separated list).
- Example CSV row:
```csv
id,title,route_order,location_name,aliases,short_description,long_description,tags
101,Building overview,3,Student Center East,SCE|Student Center East|Center East,Student Center East is a major campus hub.,Student Center East includes dining spaces student services and common gathering areas for visitors and students.,"dining,student-services,hub"
```
- Chroma index is generated artifact in `chroma_db`.
- Index does **not** auto-update on CSV edits.
- After CSV changes, rerun:
```powershell
python rebuild_chroma_from_csv.py
```

## Running tests
```powershell
pytest
```

Pytest is configured via `pytest.ini` to:
- run tests from `tests/`
- write temporary test files under `artifacts/pytest_tmp`
- disable pytest cache-provider output that previously created noisy root cache folders

## Current extension points
- Future SPOT API integration: add robot control calls in `core/controller.py` walk-command branch.
- Future TTS integration: add speech output after question answers in `core/controller.py`.
- Future context window support: keep a short sliding history of recent Q/A turns (for follow-up questions) and pass it into `rag/rag_query.py` + `rag/rag_chain.py` from `main.py`.

No real SPOT control and no TTS are implemented in this prototype.
