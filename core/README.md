# core/

I/O and control plane for the tour assistant. Everything that captures input, turns it into a structured instruction, dispatches it, and speaks back lives here. The RAG question-answering is in [../rag/](../rag/); SPOT motion is in [../navigation/](../navigation/); the Pi-side TTS client is in [../tts/](../tts/).

## Files

| File | Purpose |
|---|---|
| [audio_recorder.py](audio_recorder.py) | Microphone capture. `SPACE` toggles record start/stop, `ESC` exits the loop. Writes a 16 kHz mono WAV via `sounddevice` + `soundfile`. |
| [transcriber.py](transcriber.py) | Offline STT via `faster-whisper`. Loads the cached `base` model (int8, CPU) and returns plain text. Refuses online downloads when `WHISPER_LOCAL_FILES_ONLY=True`. |
| [parser_rules.py](parser_rules.py) | Classifies a transcript into exactly one of `question`, `walk_command`, `end_tour`, `unknown`. Keyword and prefix lists live here — see the root README "Parser keywords and phrase rules" section. |
| [controller.py](controller.py) | Dispatches the parsed instruction: questions go to the RAG service, `walk_command` increments `current_location_index`, `end_tour` breaks the main loop. Returns an updated state object to [../main.py](../main.py). |
| [instruction_json.py](instruction_json.py) | Builds the JSON artifact (`artifacts/YYYY-MM-DD_HH-MM-SS.json`) that records what the controller received for every interaction. Used for audit and debug. |
| [tts_host.py](tts_host.py) | Background socket server that the Raspberry Pi connects to. Sends narration text over a single TCP connection — see [../tts/README.md](../tts/README.md) for the client side. |

## How it fits together

[../main.py](../main.py) drives a loop: `audio_recorder` → `transcriber` → `parser_rules` → `instruction_json` → `controller`. The controller calls the RAG service ([../rag/rag_query.py](../rag/rag_query.py)) for questions and pushes narration through `tts_host` when TTS is enabled.

## Extension points

- **New instruction type** — add the keyword/prefix detection in [parser_rules.py](parser_rules.py), then add a branch in [controller.py](controller.py) that handles it. Add a test in [../tests/test_parser.py](../tests/test_parser.py) and [../tests/test_controller.py](../tests/test_controller.py).
- **Hook SPOT motion into `walk_command`** — the `walk_command` branch in [controller.py](controller.py) currently only bumps `current_location_index`. Call `GraphNavWrapper.navigate_to(...)` from [../navigation/tour_nav.py](../navigation/tour_nav.py) here, using the new index to look up the target waypoint ID.
- **Different audio source** — replace [audio_recorder.py](audio_recorder.py) with something that yields a WAV path. Keep the `ExitRequestedError` / `RecordingError` contract so [../main.py](../main.py) doesn't need to change.
- **Swap STT backend** — match the `transcribe_audio(...)` signature in [transcriber.py](transcriber.py). It only needs to take a WAV path and return a string.
- **More TTS protocols** — `TtsHost` exposes `start()` / `wait_for_connection()` / `send_text()` / `close()`. Anything matching that surface area can replace it without touching [../main.py](../main.py).

## Related

- [../rag/README.md](../rag/README.md) — how `question` instructions get answered.
- [../tts/README.md](../tts/README.md) — the Raspberry Pi side that talks to `tts_host.py`.
- [../navigation/README.md](../navigation/README.md) — SPOT motion wrapper for the future `walk_command` hookup.
- [../CODEBASE_REFERENCE.md](../CODEBASE_REFERENCE.md) — full function-level reference if you need more depth.
