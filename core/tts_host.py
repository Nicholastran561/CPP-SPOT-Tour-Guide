"""Socket host used to send narration text to the Raspberry Pi TTS client."""

from __future__ import annotations

import logging
import socket
import threading

LOGGER = logging.getLogger(__name__)


class TtsHost:
    """Minimal socket server matching the protocol demonstrated in TTS/host.py."""

    def __init__(self, host: str, port: int, enabled: bool) -> None:
        self.host = host
        self.port = port
        self.enabled = enabled
        self.bound_port = port
        self._server_socket: socket.socket | None = None
        self._connection: socket.socket | None = None
        self._lock = threading.Lock()
        self._stop_event = threading.Event()
        self._connected_event = threading.Event()
        self._thread: threading.Thread | None = None

    def start(self) -> None:
        """Start listening for the Raspberry Pi client without blocking the tour loop."""
        if not self.enabled:
            return

        try:
            server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            server_socket.bind((self.host, self.port))
            server_socket.listen(1)
            server_socket.settimeout(0.5)
        except OSError as exc:
            self.enabled = False
            LOGGER.warning("TTS host could not listen on %s:%s: %s", self.host, self.port, exc)
            return

        self._server_socket = server_socket
        self.bound_port = int(server_socket.getsockname()[1])
        self._thread = threading.Thread(target=self._accept_loop, daemon=True)
        self._thread.start()
        LOGGER.info("TTS host listening on %s:%s", self.host, self.bound_port)

    def wait_for_connection(self, timeout_seconds: float) -> bool:
        """Wait briefly for the Raspberry Pi TTS client to connect."""
        if not self.enabled:
            return False

        with self._lock:
            if self._connection is not None:
                return True

        return self._connected_event.wait(timeout=timeout_seconds)

    def send_text(self, text: str) -> None:
        """Send one newline-terminated narration string if a Pi client is connected."""
        if not self.enabled:
            return

        message = text.strip()
        if not message:
            return

        with self._lock:
            connection = self._connection

        if connection is None:
            LOGGER.warning("TTS enabled, but Raspberry Pi TTS client is not connected.")
            return

        try:
            # TTS/host.py sends UTF-8 bytes with a trailing newline; keep that wire format.
            connection.sendall(message.encode("utf-8") + b"\n")
        except OSError as exc:
            LOGGER.warning("TTS send failed; continuing without speech output: %s", exc)
            self._close_connection()

    def close(self) -> None:
        """Close sockets used by the optional TTS integration."""
        self._stop_event.set()
        self._close_connection()

        if self._server_socket is not None:
            try:
                self._server_socket.close()
            except OSError:
                pass
            self._server_socket = None

        if self._thread is not None:
            self._thread.join(timeout=1.0)

    def _accept_loop(self) -> None:
        assert self._server_socket is not None

        while not self._stop_event.is_set():
            try:
                connection, address = self._server_socket.accept()
            except socket.timeout:
                continue
            except OSError:
                break

            with self._lock:
                if self._connection is not None:
                    try:
                        self._connection.close()
                    except OSError:
                        pass
                self._connection = connection

            self._connected_event.set()
            LOGGER.info("Raspberry Pi TTS client connected from %s", address)

    def _close_connection(self) -> None:
        with self._lock:
            connection = self._connection
            self._connection = None
            self._connected_event.clear()

        if connection is not None:
            try:
                connection.close()
            except OSError:
                pass
