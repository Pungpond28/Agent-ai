# Continuous Voice Command — Design

## Intent
Let a user start microphone listening once and speak multiple commands into the existing Streamlit assistant without clicking the microphone for every phrase.

## Goals
- Add clear Start Listening and Stop Listening controls and a visible listening/recognition status.
- Capture one phrase at a time in a background worker so waiting for speech does not block Streamlit.
- Send recognized phrases through the existing `pending_prompt` command path, preserving offline/Gemini selection, fast-path behavior, and confirmation for dangerous actions.
- Keep the current one-shot microphone action available.

## Non-goals
- Wake-word detection, always-on listening after app launch, speech output, or changing recognition providers.
- Bypassing existing confirmation rules.

## Approaches
- **Background phrase listener with UI polling (selected):** reuse SpeechRecognition and existing command routing; a worker listens for successive phrases and the UI polls for results. This supports hands-free repeated commands while retaining the current stack.
- **Repeat one-shot capture:** simpler, but requires a click for each phrase and does not meet the selected continuous-listening behavior.
- **Streaming audio component:** potentially lower latency, but adds a dependency and replaces more of the existing microphone flow than needed.

## Design decisions
- Listening begins only after the user presses Start and ends when they press Stop.
- Recognition uses the current online Google recognizer or local Whisper according to the existing offline setting.
- The online/offline selector is disabled while listening so recognition and command processing stay in the same mode.
- Each recognized phrase is queued and delivered one at a time through the same prompt handling path as typed input.
- Recognition timeouts and unintelligible speech are non-fatal and return to listening; microphone/setup errors are shown in the UI and stop the worker.
- The UI exposes the latest recognized phrase and listening state. No audio is retained beyond recognition.

## Constraints and open implementation details
- The installed minimum Streamlit version is 1.39. The implementation must use APIs available at that minimum.
- Worker-thread code must not access Streamlit APIs or mutate session state; communication must use a thread-safe queue and stop signal.
- Stop must be responsive even while waiting for a phrase, so capture waits need bounded timeouts.
- Protect against duplicate workers across Streamlit reruns and shut down a prior worker before starting another.
