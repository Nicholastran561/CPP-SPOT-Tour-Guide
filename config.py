"""Configuration for the offline SPOT tour guide prototype."""

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent

# Audio settings
# Input recording sample rate (Hz). Higher can improve quality but increases data size.
AUDIO_SAMPLE_RATE = 16_000
# Number of microphone channels to record. Use 1 for mono speech capture.
AUDIO_CHANNELS = 1
# NumPy dtype used by sounddevice stream.
AUDIO_DTYPE = "float32"

# STT settings
# Whisper model size: larger models are usually more accurate but slower/heavier.
WHISPER_MODEL_SIZE = "base"
# Compute backend precision for Whisper inference.
WHISPER_COMPUTE_TYPE = "int8"
# When True, Whisper refuses online downloads and uses local cache only.
WHISPER_LOCAL_FILES_ONLY = True
# Device for Whisper inference (\"cpu\" avoids CUDA dependency issues).
WHISPER_DEVICE = "cpu"
# Language hint for transcription.
WHISPER_LANGUAGE = "en"
# Prompt bias to improve recognition of project-specific command phrases.
WHISPER_INITIAL_PROMPT = (
    "This is a SPOT tour assistant. Possible voice commands include: "
    "end the tour spot, continue, move on, next stop."
)
# Beam search width: higher can improve accuracy, but increases latency.
WHISPER_BEAM_SIZE = 5

# Data / RAG settings
CSV_PATH = PROJECT_ROOT / "locations.csv"
CHROMA_PERSIST_DIR = PROJECT_ROOT / "chroma_db"
CHROMA_COLLECTION_NAME = "spot_tour_locations"
# Local Ollama generation model used to answer questions.
OLLAMA_LLM_MODEL = "llama3.1:8b"
# Local Ollama embedding model used for vector indexing/retrieval.
OLLAMA_EMBED_MODEL = "mxbai-embed-large"
# Number of retrieved vector documents per query (higher = broader context, more noise risk).
RAG_RETRIEVER_K = 4
# LLM creativity/variance (0 = deterministic, higher = more diverse responses).
RAG_LLM_TEMPERATURE = 0.0

# TTS settings
# Toggle speech output to the Raspberry Pi TTS client. Disabled preserves current behavior.
TTS_ENABLED = False
# Match TTS/host.py: the tour guide laptop listens, and TTS/tts.py connects from the Pi.
TTS_HOST = "0.0.0.0"
TTS_PORT = 852
# Before the tour loop starts, wait this long for the Pi and send the startup message.
TTS_STARTUP_WAIT_SECONDS = 5.0
TTS_STARTUP_MESSAGE = "Welcome. The SPOT tour guide is ready to begin."

# Parser settings
END_TOUR_EXACT_PHRASE = "end the tour spot"
# When True, non-empty unrecognized transcripts are answered as questions.
ASSUME_UNKNOWN_INSTRUCTIONS_ARE_QUESTIONS = False

# Artifact naming
TIMESTAMP_FORMAT = "%Y-%m-%d_%H-%M-%S"
ARTIFACTS_DIR = PROJECT_ROOT / "artifacts"
