"""Tests for the hold audio analyzer.

Audio signals are synthesized so tests run without fixture WAV files:
  - silence: zeros
  - hold music: sum of a few sustained sine tones (tonal -> low flatness)
  - speech-like: band-limited noise bursts (broadband, variable amplitude)

For IVR loop detection, tests inject deterministic stub fingerprinters
instead of running real ASR or speaker embedding.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np

from src.backend.controller.hold_audio_analyzer import (
    AnalyzerConfig,
    CallState,
    HoldAudioAnalyzer,
    NoopVoiceEmbedder,
    TextFingerprinter,
    VoiceEmbedder,
)

SAMPLE_RATE = 8000
FRAME_SECONDS = 0.1
FRAME_SIZE = int(SAMPLE_RATE * FRAME_SECONDS)


def _silence_frame() -> np.ndarray:
    return np.zeros(FRAME_SIZE, dtype=np.float32)


def _music_frame(offset_samples: int) -> np.ndarray:
    t = (np.arange(FRAME_SIZE) + offset_samples) / SAMPLE_RATE
    signal = (
        0.30 * np.sin(2 * np.pi * 440.0 * t)
        + 0.25 * np.sin(2 * np.pi * 554.37 * t)
        + 0.20 * np.sin(2 * np.pi * 659.25 * t)
    )
    return signal.astype(np.float32)


_SPEECH_PHASE = {"phi": 0.0}


def _speech_frame(rng: np.random.Generator) -> np.ndarray:
    """Produce a speech-like signal: AM formants + broadband noise.

    Formants keep the waveform zero-crossing rate in the voiced-speech range
    (roughly 0.05-0.30) that the EnergyVAD accepts. The additive broadband
    noise, plus random per-frame pitch jitter and a non-sustained amplitude
    envelope, keeps spectral flatness well above the music threshold so the
    signal is not misclassified as hold music.
    """
    t = np.arange(FRAME_SIZE) / SAMPLE_RATE
    f0 = 110.0 + 15.0 * float(rng.standard_normal())
    formants = (
        0.30 * np.sin(2 * np.pi * f0 * t + _SPEECH_PHASE["phi"])
        + 0.20 * np.sin(2 * np.pi * (f0 * 4.5) * t + _SPEECH_PHASE["phi"])
        + 0.15 * np.sin(2 * np.pi * (f0 * 9.0) * t + _SPEECH_PHASE["phi"])
    )
    _SPEECH_PHASE["phi"] = (_SPEECH_PHASE["phi"] + 2 * np.pi * f0 * FRAME_SECONDS) % (2 * np.pi)
    noise = 0.65 * rng.standard_normal(FRAME_SIZE).astype(np.float32)
    noise_lp = np.empty_like(noise)
    noise_lp[0] = noise[0]
    for i in range(1, noise.size):
        noise_lp[i] = 0.5 * noise_lp[i - 1] + 0.5 * noise[i]
    envelope = (0.5 + 0.5 * np.sin(2 * np.pi * 6.0 * t)).astype(np.float32)
    signal = (formants.astype(np.float32) + noise_lp) * envelope
    return (0.35 * signal / (np.max(np.abs(signal)) + 1e-9)).astype(np.float32)


def _feed(analyzer: HoldAudioAnalyzer, frames: list[np.ndarray]) -> list[CallState]:
    return [analyzer.process(frame).state for frame in frames]


def test_silence_classifies_as_silence() -> None:
    analyzer = HoldAudioAnalyzer()
    states = _feed(analyzer, [_silence_frame() for _ in range(10)])
    assert all(state == CallState.SILENCE for state in states)


def test_sustained_music_classifies_as_hold_music() -> None:
    analyzer = HoldAudioAnalyzer()
    frames = [_music_frame(i * FRAME_SIZE) for i in range(20)]
    states = _feed(analyzer, frames)
    music_count = sum(1 for state in states if state == CallState.HOLD_MUSIC)
    assert music_count >= 15


def test_long_speech_with_no_fingerprint_history_flags_human() -> None:
    analyzer = HoldAudioAnalyzer(AnalyzerConfig(speech_seconds_required=2.0))
    rng = np.random.default_rng(42)
    frames = [_speech_frame(rng) for _ in range(30)]
    states = _feed(analyzer, frames)
    assert CallState.HUMAN_DETECTED in states
    human_index = states.index(CallState.HUMAN_DETECTED)
    assert human_index >= int(2.0 / FRAME_SECONDS) - 1


def test_short_speech_bursts_do_not_flag_human() -> None:
    analyzer = HoldAudioAnalyzer(AnalyzerConfig(speech_seconds_required=8.0))
    rng = np.random.default_rng(0)
    frames: list[np.ndarray] = []
    for _ in range(5):
        frames.extend(_speech_frame(rng) for _ in range(10))
        frames.extend(_silence_frame() for _ in range(10))
    states = _feed(analyzer, frames)
    assert CallState.HUMAN_DETECTED not in states


def test_human_state_is_sticky() -> None:
    analyzer = HoldAudioAnalyzer(AnalyzerConfig(speech_seconds_required=1.0))
    rng = np.random.default_rng(7)
    frames = [_speech_frame(rng) for _ in range(15)]
    frames.extend(_silence_frame() for _ in range(10))
    states = _feed(analyzer, frames)
    assert states[-1] == CallState.HUMAN_DETECTED


@dataclass
class _ScriptedTextFingerprinter(TextFingerprinter):
    """Returns a fixed transcript for every window. Simulates an IVR loop."""

    transcript: str

    def fingerprint(self, window: np.ndarray, sample_rate_hz: int) -> str | None:
        del window, sample_rate_hz
        return self.transcript


class _ScriptedVoiceEmbedder(VoiceEmbedder):
    def __init__(self, vector: np.ndarray) -> None:
        self._vector = vector

    def embed(self, window: np.ndarray, sample_rate_hz: int) -> np.ndarray | None:
        del window, sample_rate_hz
        return self._vector


def test_repeated_ivr_transcript_is_filtered() -> None:
    config = AnalyzerConfig(speech_seconds_required=1.0, fingerprint_window_seconds=1.0)
    analyzer = HoldAudioAnalyzer(
        config,
        text_fingerprinter=_ScriptedTextFingerprinter(
            transcript="your call is very important to us please hold",
        ),
        voice_embedder=NoopVoiceEmbedder(),
    )
    rng = np.random.default_rng(11)
    frames = [_speech_frame(rng) for _ in range(40)]
    states = _feed(analyzer, frames)
    assert CallState.IVR in states
    assert CallState.HUMAN_DETECTED not in states


def test_repeated_voice_embedding_is_filtered() -> None:
    config = AnalyzerConfig(
        speech_seconds_required=1.0,
        fingerprint_window_seconds=1.0,
        voice_embedding_match_threshold=0.90,
    )
    vector = np.ones(128, dtype=np.float32) / np.sqrt(128)
    analyzer = HoldAudioAnalyzer(
        config,
        voice_embedder=_ScriptedVoiceEmbedder(vector),
    )
    rng = np.random.default_rng(13)
    frames = [_speech_frame(rng) for _ in range(40)]
    states = _feed(analyzer, frames)
    assert CallState.IVR in states
    assert CallState.HUMAN_DETECTED not in states


def test_distinct_voice_after_ivr_flags_human() -> None:
    config = AnalyzerConfig(
        speech_seconds_required=1.0,
        fingerprint_window_seconds=1.0,
        voice_embedding_match_threshold=0.90,
    )
    ivr_vector = np.zeros(8, dtype=np.float32)
    ivr_vector[0] = 1.0
    human_vector = np.zeros(8, dtype=np.float32)
    human_vector[-1] = 1.0

    call_count = {"n": 0}

    class _TwoVoicesEmbedder(VoiceEmbedder):
        def embed(self, window: np.ndarray, sample_rate_hz: int) -> np.ndarray | None:
            del window, sample_rate_hz
            call_count["n"] += 1
            return ivr_vector if call_count["n"] < 4 else human_vector

    analyzer = HoldAudioAnalyzer(config, voice_embedder=_TwoVoicesEmbedder())
    rng = np.random.default_rng(17)
    frames = [_speech_frame(rng) for _ in range(80)]
    states = _feed(analyzer, frames)
    assert CallState.HUMAN_DETECTED in states


def test_music_prior_guard_blocks_human_until_music_observed() -> None:
    config = AnalyzerConfig(
        speech_seconds_required=1.0,
        music_required_prior_seconds=0.5,
    )
    analyzer = HoldAudioAnalyzer(config)
    rng = np.random.default_rng(23)
    frames = [_speech_frame(rng) for _ in range(25)]
    states = _feed(analyzer, frames)
    assert CallState.HUMAN_DETECTED not in states

    analyzer2 = HoldAudioAnalyzer(config)
    music_frames = [_music_frame(i * FRAME_SIZE) for i in range(10)]
    speech_frames = [_speech_frame(rng) for _ in range(25)]
    states2 = _feed(analyzer2, music_frames + speech_frames)
    assert CallState.HUMAN_DETECTED in states2
