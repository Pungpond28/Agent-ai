# Continuous Voice Command Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an explicit start/stop mode that listens for successive spoken phrases and routes each phrase through the existing assistant command flow.

**Architecture:** `ai_engine.py` will provide a blocking listener loop intended for a daemon worker; it receives a stop event and thread-safe queue and never calls Streamlit or touches session state. `app.py` will own one worker per Streamlit session, poll the queue with a fragment supported by the project's Streamlit floor, and place each recognized phrase into the existing `pending_prompt` route. Dangerous commands continue through the existing confirmation flow.

**Tech Stack:** Python, Streamlit >=1.39, `speech_recognition`, `threading.Event`, `queue.Queue`.

**Spec:** `docs/superpowers/specs/2026-11-06-continuous-voice-command-design.md`

## Global Constraints

- The installed minimum Streamlit version is 1.39; use only APIs available at that minimum.
- Worker-thread code must not access Streamlit APIs or mutate session state; communication must use a thread-safe queue and stop signal.
- Stop must be responsive even while waiting for a phrase, so capture waits need bounded timeouts.
- Protect against duplicate workers across Streamlit reruns and shut down a prior worker before starting another.
- Keep existing confirmation checks for dangerous operations.
- Do not add third-party dependencies.

## Review Focus

- No speech detected before timeout: listener remains active; verify by inspecting bounded `WaitTimeoutError` handling.
- Speech not understood: discard only that phrase and continue; verify the `UnknownValueError` branch.
- Microphone/device or recognizer failure: report one error and stop the worker; verify error event handling in the UI queue.
- Stop while waiting for speech: worker exits within one bounded listen timeout; verify stop event is checked between captures.
- Streamlit rerun/start duplication: one live worker per session; verify the start guard and stop-before-restart path.

---

### Task 1: Add a continuous phrase listener

**Files:**
- Modify: `my_gemini_os/ai_engine.py`

**Interfaces:**
- Produces: `listen_continuously(stop_event, result_queue, offline=False) -> None`, designed to run in a daemon thread. Queue messages are `(kind, value)` tuples where `kind` is `"recognized"`, `"error"`, or `"stopped"`.

- [x] Add a bounded-timeout loop that checks `stop_event` between captures, calibrates ambient noise once, and reuses existing Google/Whisper recognition settings.
- [x] Queue recognized non-empty phrases; ignore silence timeouts and unintelligible phrases without ending the loop.
- [x] Queue a fatal microphone/recognizer error and stop; always queue `("stopped", None)` on exit.
- [x] Manually inspect the function to confirm no Streamlit access occurs on the worker thread.

### Task 2: Add Streamlit controls and queue polling

**Files:**
- Modify: `my_gemini_os/app.py`

**Interfaces:**
- Consumes: `listen_continuously(stop_event, result_queue, offline=False)` from Task 1.
- Produces: session-owned listener state (`queue`, `stop_event`, `thread`, `status`) and a fragment that polls messages.

- [x] Add Start Listening and Stop Listening controls next to the existing one-shot microphone button, keeping that button intact.
- [x] On start, stop any existing live listener, create a new queue and stop event, snapshot the current offline mode, then launch one daemon worker.
- [x] Disable the offline/online toggle while the worker is active so recognition and agent processing cannot use different modes.
- [x] Poll the result queue in a Streamlit fragment; display listening/recognition/error state and move each recognized phrase into `pending_prompt` before triggering the existing prompt path.
- [x] Ensure multiple queued phrases are not overwritten; retain remaining messages for subsequent app reruns, with one prompt dispatched at a time.
- [x] On stop, set the event and update the UI state; allow the worker to finish its current bounded capture wait.
- [x] Manually trace that typed prompts, one-shot mic, offline mode and dangerous-command confirmation still use their existing routes.

### Task 3: Update usage notes

**Files:**
- Modify: `my_gemini_os/README.md`

- [x] Document that continuous listening is opt-in, uses the selected online/local recognizer, supports repeated phrases, and can be stopped from the UI.
- [x] State that the active offline/online mode is captured when listening starts; changing mode requires stopping and starting again.

### Verification

- Do not add or run automated tests for this change.
- Review the final code paths for queue/thread boundaries, bounded capture waits, queue ordering, and unchanged confirmation path. (Done by source inspection; repo checkout contains the project files as uncommitted additions).
- Python syntax check was attempted with `python` and `py`; neither interpreter is installed in this environment, so automated tests and local runtime verification were unavailable.
- If the local Windows app is available, manually verify start, two successive commands, stop while idle, no-speech timeout recovery, and a dangerous command's confirmation prompt.
