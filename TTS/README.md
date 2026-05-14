# tts/

Raspberry Pi side of the offline text-to-speech pipeline. The laptop (running [../main.py](../main.py)) opens a socket via [../core/tts_host.py](../core/tts_host.py); the Pi runs the client in this folder, receives narration text, and synthesizes it locally with [Piper](https://github.com/rhasspy/piper).

```
laptop:  main.py ──► core/tts_host.py (socket server, port 852)
                                │
                                │ TCP, UTF-8 text + "\n"
                                ▼
   pi:    tts/tts.py  ──► Piper ──► PyAudio ──► speaker
```

## Files

| File | Purpose |
|---|---|
| [tts.py](tts.py) | The Pi-side client. Connects to the laptop, receives newline-terminated UTF-8 strings, synthesizes each with Piper (default voice `en_US-arctic-medium`), and plays through PyAudio. |
| [host.py](host.py) | Reference/demo socket server for testing `tts.py` in isolation. **Not used in production** — the real server is [../core/tts_host.py](../core/tts_host.py). Keep it around for unit testing the Pi client without spinning up the full laptop pipeline. |

## Wire protocol

Trivially simple: the laptop opens a TCP connection on `TTS_PORT` (default `852`), then sends each narration string as UTF-8 bytes terminated by `\n`. The client reads up to 1024 bytes per `recv`, decodes, strips, and speaks.

Both sides agree to:
- one persistent TCP connection per tour run
- single-direction (laptop → Pi), no replies needed
- newline-terminated UTF-8 messages

If you change the protocol on the laptop side ([../core/tts_host.py](../core/tts_host.py)), update [tts.py](tts.py) to match.

## Raspberry Pi setup

These steps replace the old top-level `runpi.txt`.

### One-time setup

1. **Install Piper TTS on the Pi.** Follow the [Piper installation guide](https://github.com/rhasspy/piper) for your Pi OS / architecture. The Python package is `piper-tts` (imports as `piper`). The client also needs `pyaudio` for playback and Python 3.10+.
2. **Download a voice model.** Default is `en_US-arctic-medium` — both the `.onnx` file and the matching `.onnx.json` config. Put them in `piper-voices/` next to [tts.py](tts.py), or in `~/.local/share/piper-voices/`. The lookup paths are in `find_voice()` in [tts.py:16-30](tts.py#L16-L30).
3. **Set the laptop IP.** The client connects to a hard-coded host in [tts.py:13](tts.py#L13):
   ```python
   HOST = "192.168.128.1"  # laptop IP on CPPGuest
   ```
   If you change Wi-Fi networks, update this. Common values noted in the source: `192.168.128.1` (CPPGuest), `10.42.0.169` (spotpi Wi-Fi).
4. **Create the venv on the Pi** (folder convention: `piper-tts/.venv`):
   ```bash
   cd piper-tts
   python3 -m venv .venv
   source .venv/bin/activate
   pip install piper-tts pyaudio numpy
   ```

### Each tour run

On the laptop:
```powershell
python main.py
```
The laptop's [../core/tts_host.py](../core/tts_host.py) starts listening on `0.0.0.0:852` and waits up to `TTS_STARTUP_WAIT_SECONDS` (default `15`, in [../config.py](../config.py)) for the Pi.

On the Pi:
```bash
cd piper-tts
source .venv/bin/activate
python speak.py    # or: python tts.py — whichever you named it on the Pi
```

The Pi prints `Connected to server!` once the socket is up; the laptop logs `Raspberry Pi TTS client connected from <addr>` and then sends the startup greeting (`TTS_STARTUP_MESSAGE` in [../config.py](../config.py)).

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| Pi prints "Connection refused" | Laptop isn't listening yet, or wrong IP | Start [../main.py](../main.py) first. Confirm the IP in [tts.py:13](tts.py#L13) matches the laptop's actual address on the current network. |
| Laptop logs "Pi TTS client did not connect within 15 seconds" | Pi client started too late, or wrong port | Start the Pi client immediately after the laptop. Increase `TTS_STARTUP_WAIT_SECONDS` in [../config.py](../config.py) if you need more slack. |
| Pi connects but no audio | Wrong PyAudio output device, or speaker not selected | Check `aplay -l` and set the right ALSA default. Try the interactive test block at the bottom of [tts.py](tts.py) to confirm Piper works locally. |
| `FileNotFoundError: Voice 'en_US-arctic-medium' not in piper-voices/` | Voice model missing | Download the `.onnx` and `.onnx.json` and put them in `./piper-voices/` next to the script. |
| Speech sounds garbled / clipped | Sample rate mismatch | The stream is opened at `rate=22050` in [tts.py:37](tts.py#L37). Most Piper medium-quality voices are 22.05 kHz; if you switch to a `low`/`high` voice, check its config and update. |

## Extension points

- **Different voice** — drop another `.onnx` + `.onnx.json` into `piper-voices/` and pass its name to `find_voice("voice-name")` in [tts.py:33](tts.py#L33).
- **Stop hard-coding the laptop IP** — read it from a config file or env var, or have the laptop broadcast its address via mDNS.
- **Multiple Pi clients** — [../core/tts_host.py](../core/tts_host.py) currently keeps a single connection (last writer wins). Extend `TtsHost._accept_loop` and `send_text` to fan out to multiple clients if you want stereo / multi-room.
- **Different transport** — swap TCP for a WebSocket or MQTT topic if the network is unstable. Keep the laptop's `send_text(str)` contract intact.

## Related

- [../core/tts_host.py](../core/tts_host.py) — the laptop-side socket server.
- [../config.py](../config.py) — `TTS_ENABLED`, `TTS_HOST`, `TTS_PORT`, `TTS_STARTUP_WAIT_SECONDS`, `TTS_STARTUP_MESSAGE`.
- [../tests/test_tts_host.py](../tests/test_tts_host.py) — tests for the host side.
