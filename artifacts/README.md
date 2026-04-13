# Artifacts Folder

This folder stores generated runtime artifacts for the SPOT tour prototype.

## File types
- `YYYY-MM-DD_HH-MM-SS.wav` - raw recorded microphone audio
- `YYYY-MM-DD_HH-MM-SS.txt` - transcript generated from the matching WAV
- `YYYY-MM-DD_HH-MM-SS.json` - parsed instruction object from the matching transcript

All three files from one interaction share the same timestamp stem.

## Other generated files
- `pytest_tmp/` may appear here when tests run.
- `pytest_cache/` appears only if pytest cache-provider is explicitly re-enabled.

## Safe cleanup
You can safely delete old artifact files when they are no longer needed.
