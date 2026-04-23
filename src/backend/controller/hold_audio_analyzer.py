"""Streaming classifier that decides whether a live human is on the line.

The analyzer consumes short PCM16 audio frames (one call leg at a time) and
emits a ``CallState`` after each frame. It composes four pluggable building
blocks, each behind a ``Protocol`` so production can swap in Silero VAD,
faster-whisper, and Resemblyzer while unit tests use deterministic stubs:

  - ``VoiceActivityDetector``: is the frame speech?
  - ``MusicDetector``: does the frame look like music / hold tones?
  - ``TextFingerprinter``: produces short text fingerprints (e.g. ASR n-grams).
  - ``VoiceEmbedder``: produces speaker embeddings.

Decision rule (MVP, tuned by ``AnalyzerConfig``):

  HUMAN when all hold:
    1. Continuous speech >= ``speech_seconds_required`` (filters beeps/prompts).
    2. Not classified as music in that window.
    3. Neither text nor voice fingerprint matches the rolling buffer
       (filters IVR loops which repeat).
    4. (Optional) Hold music was present in the prior
       ``music_required_prior_seconds`` seconds.
"""

from __future__ import annotations

import math
from collections import deque
from dataclasses import dataclass, field
from enum import Enum
from typing import Protocol, runtime_checkable

import numpy as np


class CallState(str, Enum):
    """Coarse classification of the live audio stream."""

    UNKNOWN = "unknown"
    SILENCE = "silence"
    HOLD_MUSIC = "hold_music"
    IVR = "ivr"
    HUMAN_DETECTED = "human_detected"


@dataclass(frozen=True)
class AnalyzerConfig:
    """Tunable thresholds for the hold analyzer."""

    sample_rate_hz: int = 8000
    speech_seconds_required: float = 8.0
    music_required_prior_seconds: float = 0.0
    fingerprint_buffer_seconds: float = 300.0
    fingerprint_window_seconds: float = 3.0
    text_fingerprint_match_threshold: float = 0.6
    voice_embedding_match_threshold: float = 0.85
    silence_rms_threshold: float = 0.004


@dataclass(frozen=True)
class FrameDecision:
    """Per-frame output of the analyzer."""

    state: CallState
    is_speech: bool
    is_music: bool
    continuous_speech_seconds: float
    matched_fingerprint: bool


@runtime_checkable
class VoiceActivityDetector(Protocol):
    """Return True if the frame contains voiced speech."""

    def is_speech(self, frame: np.ndarray, sample_rate_hz: int) -> bool: ...


@runtime_checkable
class MusicDetector(Protocol):
    """Return True if the frame looks like music or sustained tonal hold."""

    def is_music(self, frame: np.ndarray, sample_rate_hz: int) -> bool: ...


@runtime_checkable
class TextFingerprinter(Protocol):
    """Return a short textual fingerprint for a speech window, or None."""

    def fingerprint(self, window: np.ndarray, sample_rate_hz: int) -> str | None: ...


@runtime_checkable
class VoiceEmbedder(Protocol):
    """Return a unit-normalized speaker embedding for a speech window."""

    def embed(self, window: np.ndarray, sample_rate_hz: int) -> np.ndarray | None: ...


class EnergyVAD:
    """Lightweight fallback VAD based on RMS and zero-crossing rate.

    Not as accurate as Silero, but dependency-free and good enough for unit
    tests and early tuning on recorded fixtures.
    """

    def __init__(self, rms_threshold: float = 0.01, zcr_min: float = 0.02, zcr_max: float = 0.35) -> None:
        self._rms_threshold = rms_threshold
        self._zcr_min = zcr_min
        self._zcr_max = zcr_max

    def is_speech(self, frame: np.ndarray, sample_rate_hz: int) -> bool:
        del sample_rate_hz
        if frame.size == 0:
            return False
        rms = float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))))
        if rms < self._rms_threshold:
            return False
        signs = np.signbit(frame)
        zero_crossings = int(np.sum(signs[1:] != signs[:-1]))
        zcr = zero_crossings / max(frame.size - 1, 1)
        return self._zcr_min <= zcr <= self._zcr_max


class SpectralFlatnessMusicDetector:
    """Declare music when spectral flatness is low (tonal) and energy is high.

    Hold music is tonally rich and sustained; speech has broadband, bursty
    energy. Spectral flatness (geometric_mean / arithmetic_mean of the power
    spectrum) near 0 means tonal; near 1 means noise-like.
    """

    def __init__(self, flatness_max: float = 0.15, rms_min: float = 0.01) -> None:
        self._flatness_max = flatness_max
        self._rms_min = rms_min

    def is_music(self, frame: np.ndarray, sample_rate_hz: int) -> bool:
        del sample_rate_hz
        if frame.size < 64:
            return False
        rms = float(np.sqrt(np.mean(np.square(frame, dtype=np.float64))))
        if rms < self._rms_min:
            return False
        spectrum = np.abs(np.fft.rfft(frame * np.hanning(frame.size)))
        power = np.square(spectrum) + 1e-12
        geo_mean = math.exp(float(np.mean(np.log(power))))
        arith_mean = float(np.mean(power))
        flatness = geo_mean / arith_mean
        return flatness < self._flatness_max


class NoopTextFingerprinter:
    """Fallback that never produces fingerprints.

    Swap in an ASR-backed implementation (faster-whisper) in production.
    """

    def fingerprint(self, window: np.ndarray, sample_rate_hz: int) -> str | None:
        del window, sample_rate_hz
        return None


class NoopVoiceEmbedder:
    """Fallback that never produces voice embeddings."""

    def embed(self, window: np.ndarray, sample_rate_hz: int) -> np.ndarray | None:
        del window, sample_rate_hz
        return None


def _jaccard(a: str, b: str) -> float:
    tokens_a = set(a.split())
    tokens_b = set(b.split())
    if not tokens_a or not tokens_b:
        return 0.0
    return len(tokens_a & tokens_b) / len(tokens_a | tokens_b)


def _cosine(a: np.ndarray, b: np.ndarray) -> float:
    denom = float(np.linalg.norm(a) * np.linalg.norm(b))
    if denom == 0.0:
        return 0.0
    return float(np.dot(a, b) / denom)


@dataclass
class _RollingBuffer:
    """Fixed-duration buffer of fingerprint observations, timestamped in seconds."""

    retain_seconds: float
    texts: deque[tuple[float, str]] = field(default_factory=deque)
    embeddings: deque[tuple[float, np.ndarray]] = field(default_factory=deque)

    def add_text(self, t_seconds: float, text: str) -> None:
        self.texts.append((t_seconds, text))
        self._evict(t_seconds)

    def add_embedding(self, t_seconds: float, embedding: np.ndarray) -> None:
        self.embeddings.append((t_seconds, embedding))
        self._evict(t_seconds)

    def _evict(self, now_seconds: float) -> None:
        cutoff = now_seconds - self.retain_seconds
        while self.texts and self.texts[0][0] < cutoff:
            self.texts.popleft()
        while self.embeddings and self.embeddings[0][0] < cutoff:
            self.embeddings.popleft()

    def text_match(self, text: str, threshold: float) -> bool:
        return any(_jaccard(text, prev) >= threshold for _, prev in self.texts)

    def embedding_match(self, embedding: np.ndarray, threshold: float) -> bool:
        return any(_cosine(embedding, prev) >= threshold for _, prev in self.embeddings)


class HoldAudioAnalyzer:
    """Stateful streaming analyzer. One instance per call session."""

    def __init__(
        self,
        config: AnalyzerConfig | None = None,
        *,
        vad: VoiceActivityDetector | None = None,
        music_detector: MusicDetector | None = None,
        text_fingerprinter: TextFingerprinter | None = None,
        voice_embedder: VoiceEmbedder | None = None,
    ) -> None:
        self._config = config or AnalyzerConfig()
        self._vad = vad or EnergyVAD()
        self._music_detector = music_detector or SpectralFlatnessMusicDetector()
        self._text_fingerprinter = text_fingerprinter or NoopTextFingerprinter()
        self._voice_embedder = voice_embedder or NoopVoiceEmbedder()
        self._buffer = _RollingBuffer(retain_seconds=self._config.fingerprint_buffer_seconds)
        self._elapsed_seconds: float = 0.0
        self._continuous_speech_seconds: float = 0.0
        self._last_music_seconds: float | None = None
        self._speech_window: list[np.ndarray] = []
        self._speech_window_seconds: float = 0.0
        self._human_detected: bool = False
        self._fingerprints_this_stretch: int = 0
        self._last_fingerprint_matched: bool = False

    @property
    def elapsed_seconds(self) -> float:
        return self._elapsed_seconds

    def process(self, frame: np.ndarray) -> FrameDecision:
        """Consume one PCM16-normalized float frame in [-1, 1] and emit a decision."""
        if frame.dtype != np.float32 and frame.dtype != np.float64:
            frame = frame.astype(np.float32) / 32768.0
        sample_rate = self._config.sample_rate_hz
        frame_seconds = frame.size / sample_rate
        self._elapsed_seconds += frame_seconds

        is_music = self._music_detector.is_music(frame, sample_rate)
        if is_music:
            self._last_music_seconds = self._elapsed_seconds

        is_speech = (not is_music) and self._vad.is_speech(frame, sample_rate)

        if is_speech:
            self._continuous_speech_seconds += frame_seconds
            self._speech_window.append(frame)
            self._speech_window_seconds += frame_seconds
        else:
            self._continuous_speech_seconds = 0.0
            self._speech_window.clear()
            self._speech_window_seconds = 0.0
            self._fingerprints_this_stretch = 0
            self._last_fingerprint_matched = False

        matched_fingerprint = False
        if self._speech_window_seconds >= self._config.fingerprint_window_seconds:
            window = np.concatenate(self._speech_window)
            emitted, matched_fingerprint = self._check_and_record_fingerprints(window, sample_rate)
            if emitted:
                self._fingerprints_this_stretch += 1
                self._last_fingerprint_matched = matched_fingerprint
            self._speech_window.clear()
            self._speech_window_seconds = 0.0

        state = self._decide_state(is_speech=is_speech, is_music=is_music, matched_fingerprint=matched_fingerprint)
        return FrameDecision(
            state=state,
            is_speech=is_speech,
            is_music=is_music,
            continuous_speech_seconds=self._continuous_speech_seconds,
            matched_fingerprint=matched_fingerprint,
        )

    def _check_and_record_fingerprints(self, window: np.ndarray, sample_rate: int) -> tuple[bool, bool]:
        """Return (emitted_any, matched_any).

        ``emitted_any`` is True when at least one fingerprinter produced output
        for this window, which is how we know the IVR-loop filter is active.
        """
        emitted = False
        matched = False
        text = self._text_fingerprinter.fingerprint(window, sample_rate)
        if text:
            emitted = True
            if self._buffer.text_match(text, self._config.text_fingerprint_match_threshold):
                matched = True
            self._buffer.add_text(self._elapsed_seconds, text)

        embedding = self._voice_embedder.embed(window, sample_rate)
        if embedding is not None and embedding.size > 0:
            emitted = True
            if self._buffer.embedding_match(embedding, self._config.voice_embedding_match_threshold):
                matched = True
            self._buffer.add_embedding(self._elapsed_seconds, embedding)
        return emitted, matched

    def _decide_state(self, *, is_speech: bool, is_music: bool, matched_fingerprint: bool) -> CallState:
        if self._human_detected:
            return CallState.HUMAN_DETECTED

        cfg = self._config
        if matched_fingerprint:
            return CallState.IVR
        if is_music:
            return CallState.HOLD_MUSIC

        if self._continuous_speech_seconds >= cfg.speech_seconds_required:
            prior_music_ok = True
            if cfg.music_required_prior_seconds > 0:
                if self._last_music_seconds is None:
                    prior_music_ok = False
                else:
                    since_music = self._elapsed_seconds - self._last_music_seconds
                    prior_music_ok = since_music <= (cfg.music_required_prior_seconds + self._continuous_speech_seconds)
            # If the fingerprinter is active (any output was emitted for this
            # stretch), require >=2 observations and the most recent one to
            # be a non-match. The first window of any new voice never matches
            # (empty buffer or different voice), so insisting on 2 lets a
            # genuine IVR repeat itself while still reacting to voice changes.
            loop_filter_ok = self._fingerprints_this_stretch == 0 or (
                self._fingerprints_this_stretch >= 2 and not self._last_fingerprint_matched
            )
            if prior_music_ok and loop_filter_ok:
                self._human_detected = True
                return CallState.HUMAN_DETECTED
            if not loop_filter_ok:
                return CallState.IVR if self._last_fingerprint_matched else CallState.UNKNOWN
            return CallState.IVR

        if is_speech:
            return CallState.IVR if self._buffer.texts or self._buffer.embeddings else CallState.UNKNOWN

        return CallState.SILENCE


__all__ = [
    "AnalyzerConfig",
    "CallState",
    "EnergyVAD",
    "FrameDecision",
    "HoldAudioAnalyzer",
    "MusicDetector",
    "NoopTextFingerprinter",
    "NoopVoiceEmbedder",
    "SpectralFlatnessMusicDetector",
    "TextFingerprinter",
    "VoiceActivityDetector",
    "VoiceEmbedder",
]
