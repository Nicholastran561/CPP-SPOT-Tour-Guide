import socket
import time

from core.tts_host import TtsHost


def test_tts_host_disabled_is_noop() -> None:
    host = TtsHost("127.0.0.1", 0, enabled=False)

    host.start()
    host.send_text("hello")
    host.close()

    assert host.enabled is False


def test_tts_host_sends_newline_terminated_text() -> None:
    host = TtsHost("127.0.0.1", 0, enabled=True)
    host.start()

    try:
        with socket.create_connection(("127.0.0.1", host.bound_port), timeout=2) as client:
            client.settimeout(2)
            assert host.wait_for_connection(timeout_seconds=2) is True

            for _ in range(20):
                host.send_text("hello spot")
                try:
                    data = client.recv(1024)
                except socket.timeout:
                    time.sleep(0.05)
                    continue

                assert data == b"hello spot\n"
                break
            else:
                raise AssertionError("TTS host did not send data to connected client")
    finally:
        host.close()


def test_tts_host_wait_for_connection_times_out_without_client() -> None:
    host = TtsHost("127.0.0.1", 0, enabled=True)
    host.start()

    try:
        assert host.wait_for_connection(timeout_seconds=0.01) is False
    finally:
        host.close()
