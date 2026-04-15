from types import SimpleNamespace

import pytest

import core.audio_recorder as audio_recorder


def test_wait_for_start_key_returns_on_space(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        audio_recorder.keyboard,
        "read_event",
        lambda: SimpleNamespace(event_type=audio_recorder.keyboard.KEY_DOWN, name="space"),
    )

    audio_recorder._wait_for_start_key()


def test_wait_for_start_key_raises_on_esc(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        audio_recorder.keyboard,
        "read_event",
        lambda: SimpleNamespace(event_type=audio_recorder.keyboard.KEY_DOWN, name="esc"),
    )

    with pytest.raises(audio_recorder.ExitRequestedError):
        audio_recorder._wait_for_start_key()
