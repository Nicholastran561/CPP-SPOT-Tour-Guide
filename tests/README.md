# tests/

Pytest suite. All tests are offline — they do not need a live Ollama server, a real SPOT, or a connected Raspberry Pi.

## Running

From the repo root:

```powershell
pytest
```

Configuration is in [../pytest.ini](../pytest.ini):
- `testpaths = tests`
- `--basetemp=artifacts/pytest_tmp` — temporary files land under [../artifacts/pytest_tmp/](../artifacts/) and can be deleted at any time.
- `-p no:cacheprovider` — pytest cache disabled to avoid noisy `.pytest_cache/` folders in the repo root.

## File-to-coverage map

| Test file | Covers |
|---|---|
| [test_audio_recorder.py](test_audio_recorder.py) | SPACE-toggle recording loop, `ExitRequestedError` on ESC, WAV output shape. |
| [test_parser.py](test_parser.py) | Instruction classification: question prefixes, walk-command keywords, the exact `end the tour spot` phrase, `unknown` fallthrough, `?` punctuation rule. |
| [test_controller.py](test_controller.py) | Instruction dispatch: question routing to a stub handler, `walk_command` incrementing `current_location_index`, `end_tour` setting the loop-end flag, `unknown` no-op behavior. |
| [test_rag_loader.py](test_rag_loader.py) | CSV schema validation, `Document` conversion, stable IDs, `tour_stop` vs `general` scope handling. |
| [test_rag_chain.py](test_rag_chain.py) | Prompt template construction, slot filling (`current_location_index`, `current_location_name`, retrieved context, etc.). |
| [test_rag_query.py](test_rag_query.py) | `RagService` behavior with a stub retriever and stub LLM: scope prioritization for the current tour stop, error handling when the index is missing. |
| [test_rebuild_index.py](test_rebuild_index.py) | [../rebuild_chroma_from_csv.py](../rebuild_chroma_from_csv.py) end-to-end: temp CSV → temp Chroma dir → expected doc count. |
| [test_tts_host.py](test_tts_host.py) | [../core/tts_host.py](../core/tts_host.py) lifecycle: start / accept / `send_text` framing / `close`, with a local socket client. |

## Conventions

- **No network, no Ollama, no SPOT.** Mock or stub external services. `RagService` tests pass in a fake retriever and a fake LLM callable instead of hitting Ollama. The TTS test uses `127.0.0.1` and an ephemeral port.
- **Temp files under `artifacts/pytest_tmp/`.** Use `tmp_path` (pytest fixture) which respects `--basetemp` from [../pytest.ini](../pytest.ini).
- **Deterministic.** No timing-based assertions beyond reasonable socket timeouts. Tests must not flake on a slow CI.
- **One concept per test function.** Prefer multiple small `test_*` functions over one big function that asserts many things.

## Adding a test

1. Pick the right file — match the module under test (`test_<module>.py`). Create a new file if you're adding a whole new module.
2. Name functions `test_<behavior>` so pytest picks them up.
3. If you need a fake RAG, copy the pattern from [test_rag_query.py](test_rag_query.py) — a tiny class with the same method names as the real one.
4. If you need a fake socket peer, copy the pattern from [test_tts_host.py](test_tts_host.py).
5. Run `pytest tests/your_test_file.py -v` while iterating; run the full `pytest` before committing.

## Related

- [../pytest.ini](../pytest.ini) — pytest configuration.
- [../AGENTS.md](../AGENTS.md) — architectural rules (e.g., what counts as the "boundary" tests must hit).
- [../CODEBASE_REFERENCE.md](../CODEBASE_REFERENCE.md) — full function-level reference for the code under test.
