"""Unit tests for the pure (non-hardware, non-network) logic in assistant.py.

Hardware (gpiozero, sounddevice) and the OpenAI client are faked in conftest.py,
so these run anywhere — no Raspberry Pi, no API key, no audio device required.
"""

import io
from unittest import mock
from unittest.mock import MagicMock

import numpy as np
import soundfile as sf

import assistant


def test_beep_synthesizes_bounded_tone_at_sample_rate():
    # beep() should build a tone of the requested length at the configured
    # sample rate, as float32, and never exceed its 0.3 amplitude ceiling.
    assistant.sd.play.reset_mock()
    assistant.beep(freq=880, secs=0.15)

    assistant.sd.play.assert_called_once()
    tone, sr = assistant.sd.play.call_args.args
    assert sr == assistant.SAMPLE_RATE
    assert tone.dtype == np.float32
    assert tone.shape[0] == int(assistant.SAMPLE_RATE * 0.15)
    assert np.max(np.abs(tone)) <= 0.3 + 1e-6


def test_transcribe_skips_short_audio_without_calling_api():
    # Clips under 0.5 s carry no useful speech and must not hit the API.
    short = np.zeros((assistant.SAMPLE_RATE // 4, assistant.CHANNELS), dtype="int16")
    with mock.patch.object(assistant, "get_client") as get_client:
        assert assistant.transcribe(short) == ""
        get_client.assert_not_called()


def test_transcribe_packs_valid_wav_and_returns_text():
    # transcribe() should hand the API a valid 16 kHz mono WAV that decodes
    # back to the same sample count, and return the stripped transcript.
    n = assistant.SAMPLE_RATE  # 1 s, comfortably above the 0.5 s guard
    t = np.linspace(0, 1, n, endpoint=False)
    audio = (np.sin(2 * np.pi * 440 * t) * 16000).astype("int16")
    audio = audio.reshape(-1, assistant.CHANNELS)

    captured = {}

    class FakeTranscriptions:
        def create(self, model, file):
            captured["model"] = model
            captured["bytes"] = file.read()
            return MagicMock(text="  hello world  ")

    fake_client = MagicMock()
    fake_client.audio.transcriptions = FakeTranscriptions()

    with mock.patch.object(assistant, "get_client", return_value=fake_client):
        result = assistant.transcribe(audio)

    assert result == "hello world"          # stripped
    assert captured["model"] == assistant.STT_MODEL

    data, sr = sf.read(io.BytesIO(captured["bytes"]), dtype="int16")
    assert sr == assistant.SAMPLE_RATE
    assert data.shape[0] == n               # round-trips intact


def test_get_client_is_lazy_and_cached(monkeypatch):
    assistant._client = None
    sentinel = object()
    monkeypatch.setattr(assistant, "OpenAI", lambda: sentinel)
    try:
        first = assistant.get_client()
        second = assistant.get_client()
        assert first is sentinel
        assert second is sentinel       # cached, not rebuilt
    finally:
        assistant._client = None


def test_init_hook_uses_pullup_and_is_cached():
    assistant.hook = None
    assistant.Button.reset_mock()

    handle = assistant.init_hook()
    assistant.Button.assert_called_once_with(
        assistant.HOOK_GPIO, pull_up=True, bounce_time=0.05
    )
    assert handle is assistant.hook

    assistant.init_hook()               # second call must reuse the handle
    assistant.Button.assert_called_once()


def test_handset_lifted_follows_switch_state():
    fake = MagicMock()
    assistant.hook = fake

    fake.is_pressed = True
    assert assistant.handset_lifted() is True

    fake.is_pressed = False
    assert assistant.handset_lifted() is False
