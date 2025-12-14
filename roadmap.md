# Implementation Plan - Hyprwhspr Evolution

## Goal
Upgrade `hyprwhspr` from a simple dictation tool to a high-performance, always-on voice assistant tailored for the user's RTX 4060 hardware.

## Phase 1: High-Fidelity Local Transcription (Immediate)
**Goal:** Replace the current "weak" model/backend with `large-v3` running locally on the RTX 4060.
- **Why:** The user has powerful hardware that is underutilized. `large-v3` offers near-perfect accuracy compared to `base` or `parakeet`.
- **Steps:**
    1. Verify/Install `python-pywhispercpp-cuda` (or ensure current installation supports CUDA).
    2. Download the `large-v3` model (approx 3GB).
    3. Update `config.toml` to use `transcription_backend = "pywhispercpp"` and `model = "large-v3"`.
    4. Verify GPU usage during transcription.

## Phase 2: "Always On" Wake Word (Jarvis Mode)
**Goal:** Enable "Hey Computer" or "Hey Jarvis" activation instead of keypresses.
- **Tech:** Integrate `openwakeword` (runs locally, very low latency).
- **Steps:**
    1. Create a `WakeWordListener` class running in a separate thread/process.
    2. When wake word is detected, trigger the `audio_capture`.
    3. Add a "listening" state UI indicator (e.g., Waybar icon changes color).

## Phase 3: Command & Control System
**Goal:** Allow voice commands to execute actions, not just type text.
- **Concept:** "Type" vs "Execute" modes.
- **Steps:**
    1. Parse input for specific triggers (e.g., starts with "Command").
    2. If command detected, run associated shell script instead of injecting text.
    3. Example: "Command open Firefox", "Command build project".

## Phase 4: Configuration GUI
**Goal:** A native, "archenative" interface to manage `config.toml` that feels integrated with the system.
- **Tech:** Python + `PyGObject` (GTK4 + LibAdwaita).
- **Steps:**
    1. Build a sleek application window following GNOME HIG.
    2. Implement settings pages for Models, Prompts, and Shortcuts.
    3. Save directly to `config.toml`.

## Proposed Immediate Action
Start with **Phase 1** to instantly improve the core experience.
