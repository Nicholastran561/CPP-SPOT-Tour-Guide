# SPOT Tour Assistant (Offline Prototype)

This project is a local-only Python prototype for a Boston Dynamics SPOT tour guide assistant.

## What it does
- Waits in a focused terminal for `SPACE` key toggle.
- Records audio locally and saves `artifacts/YYYY-MM-DD_HH-MM-SS.wav`.
- Transcribes with `faster-whisper` and saves `artifacts/YYYY-MM-DD_HH-MM-SS.txt`.
- Parses transcript into one instruction type and saves `artifacts/YYYY-MM-DD_HH-MM-SS.json`.
- Dispatches instruction in plain Python controller logic.
- Answers `question` instructions through local CSV-backed RAG (LangChain + Ollama + ChromaDB),
  while also handling general visitor questions with the local model when tour context is not relevant.

## Command model
Parser emits exactly one of:
- `question`
- `walk_command`
- `end_tour`
- `unknown`

Rules:
- Wake word `spot` is stripped before classification.
- `end_tour` triggers only on exact phrase `end the tour spot`.
- `walk_command` means move to the next fixed stop only.
- `unknown` performs no action except fallback logging/printing.

## Files
- `main.py` - main loop and artifact orchestration
- `config.py` - project settings
- `core/audio_recorder.py` - SPACE-toggle audio capture
- `core/transcriber.py` - faster-whisper transcription
- `core/parser_rules.py` - centralized parser rules
- `core/json_agent.py` - instruction JSON creation/persistence
- `core/controller.py` - instruction dispatch and tour state updates
- `rag/rag_loader.py` - CSV load and Document conversion
- `rag/rag_chain.py` - `ChatPromptTemplate` construction
- `rag/rag_query.py` - persisted Chroma retrieval + answer generation
- `rebuild_chroma_from_csv.py` - CSV -> Chroma rebuild script
- `locations.csv` - source of truth knowledge base
- `tests/` - pytest suite

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

No real SPOT control and no TTS are implemented in this prototype.
