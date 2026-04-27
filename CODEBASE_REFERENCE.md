# Codebase Reference

This document is a complete implementation reference for the offline SPOT tour guide prototype.

## 1) System Overview

The system has two phases: setup and runtime.

Setup flow:

1. Configure runtime values in `config.py` (models, file paths, audio and parser settings).
2. Install Python dependencies from `requirements.txt`.
3. Ensure local Ollama models are available (`llama3.1:8b`, `mxbai-embed-large`) and start `ollama serve` (skip if Ollama is already running from computer startup).
4. Build the local vector index by running `rebuild_chroma_from_csv.py`, which reads `locations.csv` and writes `chroma_db/`.

Runtime flow:

1. Start `main.py`, which loads `RagService` from `rag/rag_query.py` against the persisted `chroma_db/`.
2. Record microphone audio when `SPACE` is pressed (`core/audio_recorder.py`).
3. Save audio artifact (`.wav`) under `artifacts/`.
4. Transcribe audio with `faster-whisper` (`core/transcriber.py`) and save transcript (`.txt`).
5. Parse transcript into exactly one instruction type (`core/parser_rules.py`) and save instruction payload (`.json`) via `core/instruction_json.py`.
6. Dispatch instruction in `core/controller.py`.
7. For `question`, query local CSV-backed RAG (Chroma + Ollama via LangChain in `rag/` modules).
8. Repeat until exact phrase `end the tour spot` is spoken.

Key invariant: `main.py` owns and updates `current_location_index`.

## Operator Runbook (Setup and Runtime)

This runbook is for day-to-day operation on Windows.

### Purpose

Run and troubleshoot the offline SPOT tour assistant reliably.

### Key files used during operations

- `main.py`
- `config.py`
- `rebuild_chroma_from_csv.py`
- `locations.csv`

### 1) Setup (install + one-time prep)

#### 1.1 Create and activate virtual environment

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
```

#### 1.2 Install dependencies

```powershell
python -m pip install -r requirements.txt
```

#### 1.3 Prepare local model services

Start Ollama:

```powershell
ollama serve
```

If Ollama is configured to launch at computer startup and is already running, this step can be skipped.

Pull required local models once (while online):

```powershell
ollama pull llama3.1:8b
ollama pull mxbai-embed-large
```

Cache the `faster-whisper` model once:

```powershell
python -c "from faster_whisper import WhisperModel; WhisperModel('base', compute_type='int8')"
```

#### 1.4 Build vector index from CSV

```powershell
python rebuild_chroma_from_csv.py
```

Result: `chroma_db/` is generated from `locations.csv`.

#### 1.5 Optional setup validation

```powershell
.\.venv\Scripts\python.exe -m pytest
```

### 2) Runtime (daily operation)

#### 2.1 Start services each run session

```powershell
.\.venv\Scripts\Activate.ps1
ollama serve
python main.py
```

If Ollama is already running from startup, you can skip `ollama serve`.

#### 2.2 Voice interaction cycle

1. Press `SPACE` to start recording.
2. Speak command or question.
3. Press `SPACE` again to stop recording and process input.
4. Review terminal output.

#### 2.2.1 Parser keywords and phrase rules

- Walk-command keywords/phrases:
  - `next`, `continue`, `move on`, `walk`, `advance`, `keep going`, `go ahead`, `let's go`
- Question prefixes:
  - `what`, `where`, `when`, `why`, `how`, `who`, `is`, `are`, `can`, `could`, `tell me`, `give me`, `explain`, `describe`, `overview`
- Question punctuation:
  - Any transcript ending with `?` is classified as `question`.
- End-tour exact phrase:
  - Only `end the tour spot` is classified as `end_tour`.

#### 2.2.2 Ending the tour with a recording

1. Press `SPACE` to start recording.
2. Say the exact phrase `end the tour spot`.
3. Press `SPACE` again to stop recording.
4. The parser emits `end_tour`, and `main.py` exits the loop.

#### 2.3 Expected artifacts per interaction

Saved in `artifacts/` with the same timestamp stem:

- `.wav` recorded audio
- `.txt` transcript
- `.json` parsed instruction payload

#### 2.4 Runtime command behavior

- `question`: answered through local RAG + local Ollama model
- `walk_command`: increments `current_location_index` by exactly 1
- `end_tour`: exits only on exact phrase `end the tour spot`
- `unknown`: no action besides fallback log/print

#### 2.5 When CSV changes

After editing `locations.csv`, rebuild before next run:

```powershell
python rebuild_chroma_from_csv.py
```

### 3) Runtime troubleshooting quick actions

#### 3.1 Startup fails with RAG/index error

```powershell
python rebuild_chroma_from_csv.py
ollama serve
python main.py
```

#### 3.2 Recording fails

Check Windows microphone device and permissions. Ensure an input device is active.

#### 3.3 Transcription fails

Verify local `faster-whisper` model cache exists and microphone audio is valid.

#### 3.4 Answers seem outdated or irrelevant

Update CSV content and rebuild:

```powershell
python rebuild_chroma_from_csv.py
```

#### 3.5 End command is not recognized

Speak the exact phrase: `end the tour spot`.

## 2) File-by-File Reference

### `main.py`

Purpose: entrypoint and orchestrator for the end-to-end runtime loop.

Key functions:

- `_timestamp_stem() -> str`
  - Uses `config.TIMESTAMP_FORMAT`.
  - Keeps `.wav`, `.txt`, `.json` aligned by shared timestamp stem.
- `_save_transcript(transcript: str, txt_path: Path) -> Path`
  - Writes UTF-8 transcript file.
- `main() -> None`
  - Creates artifacts directory.
  - Initializes `RagService`.
  - Sets `current_location_index = 0`.
  - Loops forever until controller returns `end_tour=True`.
  - Handles per-stage failures with targeted logging and safe continuation.

Main control flow details:

- Recording failure (`RecordingError`): logs and continues loop.
- Transcription failure (`TranscriptionError`): logs, writes empty transcript file, continues loop.
- JSON save failure: logs and continues loop.
- Controller response:
  - updates `current_location_index` using `result.updated_location_index`
  - breaks loop only when `result.end_tour` is `True`

### `config.py`

Purpose: single source for runtime configuration constants.

Sections:

- Audio: `AUDIO_SAMPLE_RATE`, `AUDIO_CHANNELS`, `AUDIO_DTYPE`
- STT (`faster-whisper`): model size, compute type, offline-only flag, device, language, prompt, beam size
- RAG/data: CSV path, Chroma settings, Ollama model names, retriever `k`, LLM temperature
- Parser: `END_TOUR_EXACT_PHRASE = "end the tour spot"`, `ASSUME_UNKNOWN_INSTRUCTIONS_ARE_QUESTIONS`
- Artifacts: timestamp format and artifacts directory path

Notable behavior:

- `WHISPER_LOCAL_FILES_ONLY = True` enforces offline model loading.
- `PROJECT_ROOT` is derived from `config.py` location and reused for all local paths.

### `rebuild_chroma_from_csv.py`

Purpose: regenerate local Chroma index from CSV source of truth.

Key function:

- `rebuild_index(csv_path, persist_dir, collection_name, embedding_model) -> None`
  - Loads and validates CSV (`load_locations_csv`).
  - Converts rows to LangChain `Document` objects and stable IDs.
  - Deletes old persisted index directory if it exists.
  - Rebuilds from scratch via `Chroma.from_documents`.
  - Raises `RuntimeError` with actionable messages for CSV and Ollama/index failures.

Operational note:

- Must be re-run manually any time `locations.csv` changes.

### `core/audio_recorder.py`

Purpose: microphone capture using `SPACE` start/stop toggle.

Classes:

- `RecordingError(RuntimeError)`: recording-specific failure wrapper.

Key functions:

- `_ensure_input_device_available() -> None`
  - Uses `sounddevice.query_devices()`.
  - Fails fast if no input channels are detected.
- `record_until_space_toggle(output_path, sample_rate, channels, dtype) -> Path`
  - Waits for first `SPACE` to start recording.
  - Records via `sounddevice.InputStream` callback.
  - Waits for second `SPACE` to stop.
  - Concatenates frame chunks and writes WAV with `soundfile`.
  - Returns saved audio path.

### `core/transcriber.py`

Purpose: local speech-to-text using `faster-whisper`.

Classes:

- `TranscriptionError(RuntimeError)`: transcription failure wrapper.

Key function:

- `transcribe_audio(audio_path, model_size, compute_type, local_files_only, device, language, initial_prompt, beam_size) -> str`
  - Validates audio file exists.
  - Instantiates `WhisperModel`.
  - Calls `model.transcribe(...)` with project prompt bias.
  - Joins segment text into a single transcript string.
  - Raises on empty transcript.

### `core/parser_rules.py`

Purpose: centralized, editable instruction classification rules.

Constants/rules:

- `INSTRUCTION_TYPES = {"question", "walk_command", "end_tour", "unknown"}`
- `WALK_COMMAND_REGEXES`: phrase regex list for movement intent
- `QUESTION_PREFIXES`: fallback question-start words

Key functions:

- `normalize_text(text: str) -> str`
  - Lowercases, strips punctuation except `?`, normalizes whitespace.
- `classify_instruction_type(raw_text: str, assume_unknown_as_question: bool | None = None) -> str`
  - Exact match first for `end_tour` phrase.
  - Empty text -> `unknown`.
  - Question detection by trailing `?` or prefix.
  - Walk regex checks after question checks so question text containing movement words does not advance the tour.
  - Otherwise returns `question` when `assume_unknown_as_question` / `ASSUME_UNKNOWN_INSTRUCTIONS_ARE_QUESTIONS` is enabled, or `unknown` when disabled.
- `parse_instruction(raw_text: str, assume_unknown_as_question: bool | None = None) -> Dict[str, object]`
  - Returns `{instruction_type, raw_text, parsed_data}`.
  - `parsed_data` is currently empty by design, but reserved for future structured extraction.

### `core/instruction_json.py`

Purpose: build and persist instruction JSON artifacts.

Classes:

- `InstructionSerializationError(RuntimeError)`: invalid JSON serialization wrapper.

Key functions:

- `build_instruction_json(instruction_type, raw_text, parsed_data=None) -> Dict[str, object]`
  - Produces canonical instruction payload with ISO timestamp.
- `save_instruction_json(instruction, output_path) -> Path`
  - Performs JSON dump + load round-trip validation before writing.
  - Writes UTF-8 formatted JSON.

### Instruction JSON Schema

Purpose: canonical payload saved to `artifacts/YYYY-MM-DD_HH-MM-SS.json` and passed into the controller.

Top-level shape:

```json
{
  "instruction_type": "question | walk_command | end_tour | unknown",
  "raw_text": "string",
  "parsed_data": {},
  "timestamp": "YYYY-MM-DDTHH:MM:SS"
}
```

Field definitions:

- `instruction_type`
  - One of: `question`, `walk_command`, `end_tour`, `unknown`.
- `raw_text`
  - Original transcript text from STT.
- `parsed_data`
  - Structured extraction bucket for future parser upgrades.
  - Exists so we can attach explicit values parsed out of the transcript (for example `location_index`, `target_location`, numeric arguments, or flags) without changing top-level schema.
  - Current implementation intentionally leaves this as `{}`.
- `timestamp`
  - ISO local timestamp with second precision (`datetime.now().isoformat(timespec="seconds")`).

Examples by instruction type:

```json
{
  "instruction_type": "question",
  "raw_text": "what is this building",
  "parsed_data": {},
  "timestamp": "2026-04-13T09:10:11"
}
```

```json
{
  "instruction_type": "walk_command",
  "raw_text": "continue",
  "parsed_data": {},
  "timestamp": "2026-04-13T09:10:45"
}
```

```json
{
  "instruction_type": "end_tour",
  "raw_text": "end the tour spot",
  "parsed_data": {},
  "timestamp": "2026-04-13T09:11:20"
}
```

```json
{
  "instruction_type": "unknown",
  "raw_text": "banana blue",
  "parsed_data": {},
  "timestamp": "2026-04-13T09:11:58"
}
```

### `core/controller.py`

Purpose: dispatch parsed instruction and manage side effects/state transitions.

Data class:

- `ControllerResult`
  - `updated_location_index: int`
  - `end_tour: bool`

Key function:

- `handle_instruction(instruction, current_location_index, question_handler) -> ControllerResult`
  - `question`: calls injected `question_handler(question, current_location_index)`, prints answer, no index change
  - `walk_command`: increments index by exactly 1, prints/logs new index
  - `end_tour`: sets `end_tour=True`, no index change
  - `unknown`: no-op except fallback log/print

Important invariant:

- Controller does not own persistent state; `main.py` remains source of truth for `current_location_index`.

### `rag/rag_loader.py`

Purpose: CSV schema validation and conversion to retrievable documents.

Constants:

- `REQUIRED_COLUMNS` includes:
  - `id`, `title`, `fact_scope`, `route_order`, `location_name`, `aliases`, `short_description`, `long_description`, `tags`

Classes:

- `CsvDataError(RuntimeError)`: CSV missing/invalid schema wrapper.

Key functions:

- `load_locations_csv(csv_path) -> pd.DataFrame`
  - Validates file exists.
  - Reads CSV with pandas.
  - Enforces required columns.
  - Validates `fact_scope` values are `tour_stop` or `general`.
- `dataframe_to_documents(df) -> Tuple[List[Document], List[str]]`
  - Converts each row to one LangChain `Document`.
  - Uses stable document ID derived from row `id`.
  - Packs major row fields into `page_content` and metadata.
  - Stores `general` facts with route order `-1` so they are retrievable but not treated as tour stops.
- `get_location_name_for_route_order(df, route_order) -> str`
  - Returns matching `tour_stop` location or `"Unknown"`.
- `get_total_stops(df) -> int`
  - Unique `route_order` count for `tour_stop` rows only.

### `rag/rag_chain.py`

Purpose: prompt template construction for question answering.

Key function:

- `build_prompt_template() -> ChatPromptTemplate`
  - Defines system behavior, response style, and safety constraints.
  - Defines human message slots for:
    - `current_location_index`
    - `total_stops`
    - `current_location_name`
    - `retrieved_context`
    - `question`

### `rag/rag_query.py`

Purpose: runtime retrieval + answer generation over persisted local Chroma index.

Classes:

- `RagUnavailableError(RuntimeError)`: wraps startup/retrieval/generation failures.
- `RagService`: long-lived runtime RAG object.

Helper functions:

- `retrieve_documents(retriever, question) -> List[Document]`
  - Calls retriever and normalizes result to `list`.
- `prioritize_current_location(docs, current_location_index) -> List[Document]`
  - Stable partition so matching `route_order` docs appear first.
- `format_retrieved_context(docs) -> str`
  - Formats docs into `[n] ...` chunks for prompt context.

`RagService` lifecycle:

- `__init__(...)`
  - Validates persisted Chroma directory exists.
  - Loads CSV and computes total stops.
  - Initializes Ollama embeddings, Chroma vector store, retriever, and ChatOllama LLM.
  - Builds runnable chain (`prompt | llm | StrOutputParser()`).
- `answer_question(question, current_location_index) -> str`
  - Retrieves docs.
  - Prioritizes docs matching current stop.
  - Adds current location name and tour metadata to prompt inputs.
  - Invokes chain and returns trimmed text.
  - Returns fallback sentence if model output is empty.

### `tests/test_parser.py`

Validates parser behavior:

- exact `end_tour` phrase handling
- walk command classification
- question classification without wake-word stripping
- unknown fallback behavior
- unknown-as-question toggle behavior

### `tests/test_controller.py`

Validates controller behavior:

- `walk_command` increments index by exactly one
- `unknown` instruction is a no-op

### `tests/test_rag_loader.py`

Validates data loading/conversion:

- CSV loads and required columns exist
- generated document IDs are stable (`id`-based string)

### `tests/test_rag_query.py`

Validates RAG helper behavior:

- current-location prioritization order
- retrieval helper returns expected fake retriever output

### `tests/test_rebuild_index.py`

Validates rebuild pipeline wiring with monkeypatch:

- embedding model arg is passed through
- `Chroma.from_documents` receives stable IDs and expected collection/persist args

### `pytest.ini`

Pytest config:

- test discovery path: `tests`
- quiet mode
- disabled cache provider
- base temp directory under `artifacts/pytest_tmp`

### `locations.csv`

Purpose: source-of-truth knowledge base for stops/facts.

Required schema:

- `id`
- `title`
- `fact_scope`
- `route_order`
- `location_name`
- `aliases`
- `short_description`
- `long_description`
- `tags`

Column definitions:

- `id`
  - Stable numeric row identifier.
  - Used as the persisted vector document ID (converted to string during indexing).
  - Recommendation: unique integer per row/fact.
- `title`
  - Short human-readable label for the fact row.
  - Example style: `Building overview`, `Hours and access`.
- `fact_scope`
  - Either `tour_stop` for route-stop facts or `general` for school-wide facts.
  - Only `tour_stop` rows count toward the fixed tour sequence.
- `route_order`
  - Integer stop index used for fixed tour sequencing and current-stop context.
  - Multiple rows may share the same `route_order` for multiple facts at one stop.
  - Use `-1` for `general` facts.
- `location_name`
  - Canonical stop/location name spoken or shown to users.
- `aliases`
  - Alternate names, nicknames, abbreviations, or common misspellings.
  - Recommended format: pipe-separated values, for example `SCE|Student Center East|Center East`.
- `short_description`
  - One concise summary sentence for fast grounding.
- `long_description`
  - Richer detail used for deeper answers.
- `tags`
  - Keywords for retrieval signal (topics, departments, categories).
  - Recommended format: comma-separated values, for example `dining,student-services,hours`.

Example CSV:

```csv
id,title,fact_scope,route_order,location_name,aliases,short_description,long_description,tags
101,Building overview,tour_stop,3,Student Center East,SCE|Student Center East|Center East,Student Center East is a major campus hub.,Student Center East includes dining spaces student services and common gathering areas for visitors and students.,"dining,student-services,hub"
201,University overview,general,-1,Cal Poly Pomona,CPP|Cal Poly Pomona|the university,Cal Poly Pomona is a public polytechnic university.,Cal Poly Pomona is known for learn-by-doing education and career-focused academic programs.,"general,university,overview"
```

Indexing behavior:

- each CSV row becomes one vector document
- vector DB is generated artifact and does not auto-sync

### `artifacts/README.md`

Documents generated runtime files and safe cleanup expectations for local artifacts.

### `requirements.txt`

Minimal dependency list covering:

- local audio capture
- offline STT
- local RAG stack
- testing

## 3) Runtime Artifacts and Persistence

The runtime saves three per-interaction files under `artifacts/`:

- `YYYY-MM-DD_HH-MM-SS.wav`
- `YYYY-MM-DD_HH-MM-SS.txt`
- `YYYY-MM-DD_HH-MM-SS.json`

All three share the same timestamp stem for correlation.

Chroma index persists under `chroma_db/` and is rebuilt via `rebuild_chroma_from_csv.py`.

## 4) Error Handling Strategy

The codebase favors explicit stage-specific failures:

- recording issues -> `RecordingError`
- transcription issues -> `TranscriptionError`
- CSV validation issues -> `CsvDataError`
- RAG startup/query issues -> `RagUnavailableError`
- JSON serialization issues -> `InstructionSerializationError`

Main loop behavior is resilient:

- logs failures
- avoids unsafe actions on unknown input
- continues operation except for startup-fatal RAG initialization failures or explicit end-tour command

## 5) Extension Points

Current intentional stubs:

- SPOT mobility control can be added in `core/controller.py` walk-command branch.
- TTS output can be added after question answers in `core/controller.py`.
- A short conversation context window can be added for follow-up questions by storing recent Q/A turns in `main.py` and threading that history through `rag/rag_query.py` into the prompt in `rag/rag_chain.py`.

The architecture keeps parser and controller outside LangChain, with LangChain isolated to `rag/`.
