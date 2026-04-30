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

### Parser keywords and phrase rules
- Walk-command keywords/phrases: `next`, `continue`, `move on`, `walk`, `advance`, `keep going`, `go ahead`, `let's go`.
- Question prefixes: `what`, `where`, `when`, `why`, `how`, `who`, `is`, `are`, `can`, `could`, `tell me`, `give me`, `explain`, `describe`, `overview`.
- Question punctuation rule: any transcript ending in `?` is treated as `question`.
- End-tour exact phrase: only `end the tour spot` maps to `end_tour`.

### How to end the tour by voice recording
1. Press `SPACE` to start recording.
2. Clearly say: `end the tour spot`.
3. Press `SPACE` again to stop recording and process the command.
4. The app exits only when that exact phrase is recognized.

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

# Navigation
## How it Works
In order to get SPOT to move around the space, a static map was made to define the key points SPOT needed to go. This map directory is located in `navigation/maps/downloaded_graph`. During runtime, the RAG system will update an index value that correlates to a waypoint ID specified on the map. SPOT can dynamically adjust its path based on obstacles it encounters while maintaining its static map route.
## How the map was created
<img width="1082" height="774" alt="image" src="https://github.com/user-attachments/assets/a03df5f5-0123-4fdc-944b-d8ce172fba78" />

  - 1 anchor at the start, due to the small map size
  - 5 fiducials around a square room
  - 2-3 waypoints created between fiducials to allow pausing if space next to the fiducial is occupied
_see graphnav section for more details_
## Implementation
`navigation/tour_nav.py` is a graphnav wrapper that automates terminal commands to navigate directly to a specified waypoint given the ID. IDs are retrieved from the visual map.
<img width="1082" height="774" alt="image" src="https://github.com/user-attachments/assets/8a6a9b90-f36b-4206-8151-480f821cd0e8" />
For example, `waypoint_14` correlates to the south-most waypoint in the room.
### Using Wrapper
After initializing `GraphNavWrapper`, simply use `navigate_to(<waypoint_id>)` to navigate to the specified waypoint.
```python
G = GraphNavWrapper(robot, "navigation/maps/downloaded_graph")
G.navitage_to("waypoint_1")
```
**Important Notes**: `robot` is the Boston Dynamics auth used to connect to the robot. If the variable is passed into the class, it will attempt to authenticate on initialization. 
#### Example
`GraphNavWrapper(map_path=...)` <br>
Initialize Wrapper -> authenticate robot connect (user & password) -> ... -> `navigate_to('waypoint_14')` <br>
Spot will first require you to type your username and password to navigate to waypoint_14 defined on the map. This flow is meant to test the wrapper as a stand-alone program. Larger programs would need to authenticate Spot and perform other tasks before navigating.
```python
sdk = bosdyn.client.create_standard_sdk('GraphNavClient')
robot = sdk.create_robot("192.168.80.3")
GraphNavWrapper(robot=robot, map_path=...)
```
Authenticate robot connect (user & password) -> ... -> Initialize Wrapper -> ... -> `navigate_to('waypoint_14')` <br>
The program can authenticate at any point, run any operation, then initialize the wrapper and navigate to waypoint_14. This flow is essential for larger-scale systems.
### How to use `navigate_to(waypoint)`
`navigate_to(waypoint)`
waypoint: can be filled with any of the following names.

Quick Example:
```python
navigate_to("waypoint_1")
```

## GraphNav
The SpotSDK connects onboard stereo cameras and inertial odometry to create a 3D point cloud of its surroundings. GraphNav processes this point cloud into a series of waypoints and edges. <br>
### Map Creation
#### Waypoints
Waypoints are IDs associated with a location where SPOT takes a "snapshot" of the point cloud. They are created automatically every 2 meters (or less, depending on the path's curvature), but can also be created manually using `CreateWaypoint` during recording. You can edit a pre-recorded map if you enable GPS while recording it. Manually defining a waypoint is useful if you have a specific location where you want SPOT to perform an action.
#### Edges
Edges are the specific directions SPOT needs to go to reach a waypoint. They're created automatically between waypoints, or manually using `CreateEdge`.
### Recording a Map
By using the `recording_command_line` graphnav example in the SDK, you can control Spot using the controller and select recording options like "Create Waypoint", "Start Recording", "Download Recording", Etc. Downloading the recording saves it to whatever path you specified when running the command. 
### Map Processing
When recording your map, Spot will create it in a "Chain" topology. This means it has a start and an end node and will attempt to traverse from the start to the finish. 
#### Loop Closure
If you need Spot to continue after completing its path, the start and end nodes must be connected. GraphNav has a tool that automatically closes a loop if it encounters the same fiducial more than once, or if it walks less than 50 meters and arrives at the same position.
#### Anchoring
Anchoring maps a fiducial or waypoint to the **global map**. As Spot navigates the waypoints normally, it estimates its position relative to the starting node, a technique known as dead reckoning. As Spot gets farther and farther from the starting node, it gets less and less accurate. This is because GraphNav creates an anchor by default at the start node. So, for longer travel distances, setting multiple anchors increases positional and map accuracy.
#### Ensuring Good Maps
  - Large maps need more fiducials to better connect waypoints together
  - Large maps also need more anchors to increase movement precision
  - Each floor needs a fiducial
  - get as close to the fiducials as you can while recording
  - record multiple different paths to a significant waypoint to increase path options
## Future Improvements
For a real-world tour guide scenario. The map would require more waypoints, fiducials, and anchors to create a large, accurate map. Real scenarios would also include multiple Spots working on the same map. This would require significant changes to waypoint validation so more than one Spot wouldn't appear at the same place. 
