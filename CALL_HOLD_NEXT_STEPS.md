# Call-Hold Detector — Next Steps (Agent Handoff)

**Context.** The MVP scaffold has been built and pushed on branch
`claude/call-hold-detection-OkCcw` in this repo. It compiles, lints, and
passes 89 tests. The core streaming analyzer (`HoldAudioAnalyzer`) uses
pluggable Protocols for VAD, music detection, ASR-based text fingerprinting,
and voice embedding — but the defaults are all lightweight CPU-only fallbacks.
Real detection quality requires wiring the production ML adapters and tuning
thresholds against live Twilio calls.

This document is written for an AI agent picking up from here. Steps are
sorted by the order they must be done; skipping infra (step 1) blocks
everything else.

---

## Step 1 — Twilio infra + local tunnel (required before any live test)

**Why first.** Nothing works end-to-end without Twilio credentials and a
publicly reachable HTTPS URL for Twilio to call back. This is pure config,
no code.

**Actions:**
1. Create a free Twilio trial account at twilio.com. Buy one phone number
   (Voice-capable, ~$1/month).
2. Install and authenticate ngrok: `ngrok http 8000`. Copy the `https://…`
   URL it prints.
3. Copy `env.example` → `.env` and fill in:
   ```
   TWILIO_ACCOUNT_SID=ACxxx
   TWILIO_AUTH_TOKEN=xxx
   TWILIO_FROM_NUMBER=+1XXXXXXXXXX   # the Twilio number
   USER_CALLBACK_NUMBER=+1XXXXXXXXXX # your personal number
   PUBLIC_BASE_URL=https://xxxx.ngrok.app
   ```
4. Start the stack: `docker compose up --build` (or `uv run uvicorn
   src.backend.main:app --reload`).
5. Smoke-test: `POST http://localhost:8000/calls` with a support number and
   your callback number. Confirm Twilio places the outbound call and you hear
   hold music. State should be `unknown` initially.

**Scope.** Config only; no code changes.
**Out of scope.** Multi-tenant auth, production hosting, ngrok alternatives
(Cloudflare Tunnel works identically).

---

## Step 2 — Wire Silero VAD adapter

**Why.** The default `EnergyVAD` (RMS + ZCR heuristic) is a rough stand-in.
Silero VAD is a tiny ONNX model (~2 MB) that significantly reduces false
positives on music/IVR noise classified as speech, and false negatives on
soft-spoken agents.

**File to create:** `src/backend/gateway/audio/silero_vad_adapter.py`

**Pattern to follow:**
```python
# Implements VoiceActivityDetector Protocol from hold_audio_analyzer.py
# Lazy-import: `from silero_vad import load_silero_vad` at method call time
# so importing the module doesn't fail when the [audio] extra is absent.
class SileroVADAdapter:
    def __init__(self, threshold: float = 0.5) -> None: ...
    def is_speech(self, frame: np.ndarray, sample_rate_hz: int) -> bool: ...
```

Install: `uv pip install ".[audio]"` (the `[audio]` extra in `pyproject.toml`
already lists `silero-vad>=5.1.0`).

**Wire in:** In `src/backend/main.py` → `_build_call_hold_controller()`, pass
`vad=SileroVADAdapter()` into the `HoldAudioAnalyzer` constructor inside
`CallHoldController`.

**Tests:** Add `src/backend/gateway/audio/silero_vad_adapter_test.py` with
two fixture WAV clips (voiced speech, hold music) and assert is_speech outputs.

**Out of scope.** Replacing the music detector here — that's step 3.

---

## Step 3 — Wire librosa music detector

**Why.** `SpectralFlatnessMusicDetector` uses a single-frame FFT flatness
threshold (0.15). Real hold music (compressed MP3-over-PSTN) can drift above
that threshold, and some IVR tones (DTMF) are narrow-band. A short-term
energy-weighted flatness window over ~0.5 s is more robust.

**File to create:** `src/backend/gateway/audio/librosa_music_detector.py`

**Approach:**
- Buffer the last N frames (default: 25 × 20 ms = 0.5 s).
- On each call, compute `librosa.feature.spectral_flatness` on the buffered
  window and take the median.
- Return `True` if median flatness < threshold AND RMS > floor.
- `librosa` is already in the `[audio]` extra.

**Wire in:** Same place as step 2 — pass `music_detector=LibrosaMusicDetector()`
into `HoldAudioAnalyzer`.

**Tests:** Synthesize 0.5 s of a pure 440 Hz sine (music) and 0.5 s of
formant-noise speech; assert correctly classified.

**Out of scope.** Beat detection, genre classification, or anything that
requires a full-length clip.

---

## Step 4 — Wire faster-whisper text fingerprinter

**Why.** The `NoopTextFingerprinter` is a no-op; the IVR-loop filter has no
text signal until this is wired. faster-whisper `small.en` runs in ~0.3 s per
3-second window on CPU, which is fast enough to not block the WS handler if
run in `asyncio.to_thread`.

**File to create:** `src/backend/gateway/audio/whisper_fingerprinter.py`

```python
# Implements TextFingerprinter Protocol
class WhisperFingerprinter:
    def __init__(self, model_size: str = "small.en") -> None:
        # lazy-load: from faster_whisper import WhisperModel
        ...
    def fingerprint(self, window: np.ndarray, sample_rate_hz: int) -> str | None:
        # Resample to 16 kHz if needed (Whisper expects 16k).
        # Return the stripped lowercased transcript, or None if empty/short.
        ...
```

**Env var:** `CALL_HOLD_WHISPER_MODEL` already in `env.example`; read it in
`main.py` and pass to `WhisperFingerprinter(model_size=...)`.

**Wire in:** `src/backend/main.py` → `HoldAudioAnalyzer(...,
text_fingerprinter=WhisperFingerprinter())`.

**Tests:** Pass a 3-second repeated-IVR fixture through twice; assert Jaccard
score exceeds threshold on the second pass.

**Out of scope.** Multilingual support, diarization, translation.

---

## Step 5 — Wire Resemblyzer voice embedder

**Why.** The `NoopVoiceEmbedder` means the IVR-loop voice-similarity filter
is disabled. Resemblyzer produces 256-dim speaker embeddings and runs in ~50 ms
per 3-second window on CPU.

**File to create:** `src/backend/gateway/audio/resemblyzer_embedder.py`

```python
# Implements VoiceEmbedder Protocol
class ResemblyzerEmbedder:
    def embed(self, window: np.ndarray, sample_rate_hz: int) -> np.ndarray | None:
        # from resemblyzer import VoiceEncoder
        # Resample to 16 kHz; encoder.embed_utterance(wav)
        ...
```

**Wire in:** Same pattern. Pass into `HoldAudioAnalyzer`.

**Tests:** Embed the same 3-second clip twice; assert cosine similarity > 0.95.
Embed two different-speaker clips; assert cosine similarity < 0.7.

**Out of scope.** Real-time diarization across multiple speakers on the same leg.

---

## Step 6 — End-to-end tuning on real calls (MVP validation)

**Why.** This is where the MVP is actually validated or rejected. All the
component tests use synthetic audio; real PSTN audio through Twilio µ-law
compression is noisier and more varied than any fixture.

**Actions:**
1. Enable per-frame logging: in `CallHoldController.ingest_frame`, call
   `append_call_event` (already in `call_repository.py`) on every state
   transition with `state`, `continuous_speech_seconds`, and
   `matched_fingerprint`. This creates a replay log in Postgres.
2. Dial 5–10 real support lines with known short holds. Record the Twilio
   call audio by adding a `<Record>` verb to the TwiML (temporary, for
   debugging only — comply with local call-recording laws).
3. Replay each recording through the analyzer offline and inspect the state
   timeline in `call_events`. Adjust:
   - `CALL_HOLD_VAD_SPEECH_SECONDS` (default 8.0): lower to 5.0 if agents
     speak briefly before silence; raise if IVR greetings are long.
   - `flatness_max` in `LibrosaMusicDetector` (step 3 default ~0.15): raise
     if compressed hold music drifts high; lower if IVR tones are
     misclassified as music.
   - `CALL_HOLD_FINGERPRINT_BUFFER_SECONDS` (default 300): lower to 120 if
     IVR loops are shorter and you want faster loop detection.
4. Target: ≥ 95 % precision on "HUMAN_DETECTED" across your 10 test calls
   before using in production.

**Out of scope.** A/B testing framework, automated threshold search, calls to
emergency lines (111/911/999).

---

## Step 7 — Persist events to Postgres (wires repository into controller)

**Why.** Currently the controller is 100 % in-memory: `_sessions` is a plain
dict. `call_repository.py` exists but nothing calls it yet. Wiring it in
enables call replay (step 6), crash recovery, and the frontend dashboard.

**Actions:**
1. Add a `db_pool: asyncpg.Pool | None = None` parameter to
   `CallHoldController.__init__`.
2. In `start_call`, if pool is not None, call `create_call(conn, ...)`.
3. In `ingest_frame`, on state transitions, call `append_call_event(conn,
   event_type="state_transition", state=..., payload={...})`.
4. In `notify_human_detected`, call `update_call_state(conn, state=
   "human_detected", notified_at=now)`.
5. In `main.py`, pass the asyncpg pool (already available via
   `src.backend.db.postgres`) into the controller.

**Out of scope.** Partitioning, event archival, GDPR deletion.

---

## Step 8 — Minimal web UI

**Why.** The current frontend (`src/frontend/src/main.ts`) is the pypy
template stub. A one-page UI removes the need to use curl to dial and poll
for status.

**Actions:**
1. In `src/frontend/src/main.ts`, replace the demo content with:
   - A form: support number field + submit button → `POST /calls`.
   - A status card that polls `GET /calls/{session_id}` every 2 s and shows
     `DIALING → ON_HOLD → IVR → HUMAN_DETECTED` with a color-coded badge.
   - A green banner + audible alert (`new Audio(…).play()`) on
     `HUMAN_DETECTED`.
2. No new dependencies needed — keep plain TypeScript.

**Out of scope.** Auth, multi-session management, call history list,
mobile-native app.

---

## Step 9 — Twilio request signature validation

**Why.** The TwiML webhook (`POST /calls/{id}/twiml`) and status callback
are currently unauthenticated — anyone who discovers the URL could POST to
them. Twilio signs every request with an HMAC-SHA1 of your auth token.

**Actions:**
1. Add `validate_twilio_signature(request, auth_token)` middleware or a
   FastAPI dependency. The Twilio Python SDK provides
   `twilio.request_validator.RequestValidator`.
2. Wire it into `twiml_webhook` and `twilio_status_callback` in
   `call_handlers.py` via `Depends(...)`.
3. Skip validation in tests by injecting a stub dependency.

**Out of scope.** mTLS, IP allowlisting, rate limiting.

---

## Deferred / Out of Scope for All Steps Above

- **AI hold agent** (deferred by user): when a human picks up, an AI voice
  agent says "one moment, the customer will be right with you" while we ring
  the user back. Wire via Twilio ConversationRelay + Claude API + ElevenLabs
  TTS on the same call leg as the Media Stream.
- **iOS / Android native app**: CallKit blocks 3rd-party call audio; the
  Twilio VoIP-bridge approach is the correct foundation for any future mobile
  surface.
- **Multi-tenant / billing**: in-memory session store and no auth is fine for
  personal use; swap in Redis + JWT for a shared deployment.
- **International carrier compliance**: recording disclosures, two-party
  consent laws, GDPR. Legal review required before production outside the US.
- **Scaling beyond one worker**: asyncpg pool + Redis-backed session store
  needed for multi-process; current in-memory dict is intentionally single-
  worker.

---

## Quick Reference — Key Files

| File | Purpose |
|---|---|
| `src/backend/controller/hold_audio_analyzer.py` | Core classifier, detection logic, Protocols |
| `src/backend/controller/call_hold_controller.py` | Session orchestration, Notifier/CallPlacer Protocols |
| `src/backend/gateway/twilio/` | REST client, TwiML, µ-law decoder, Twilio-backed adapters |
| `src/backend/handlers/call_handlers.py` | FastAPI routes + WS ingest |
| `src/backend/repository/call_repository.py` | Postgres calls/call_events CRUD |
| `src/backend/db/init-db.sql` | Schema (calls, call_events tables at bottom) |
| `src/backend/main.py` | App factory, wires controller + Twilio adapters from env |
| `env.example` | All required env vars with inline comments |
| `pyproject.toml` | `[audio]` optional extra for ML deps |
