# Changelog

## 2.1.0

- Replaced the default `Hey Samuel` wake phrase with the faster single-word wake `Hey`, including automatic migration from the old factory default.
- Added OpenAI `gpt-4o-mini-transcribe` as the enhanced voice path whenever an API key is connected.
- Kept Google speech recognition as an automatic no-key and network-error fallback.
- Added fuzzy start-only wake matching for common `Samuel` recognition errors such as `Sam` and `Samual`.
- Added a 12-second spoken follow-up window after each reply.
- Added visible Activity diagnostics when speech is ignored because no wake phrase was detected.
- Improved voice activity detection with adaptive background noise, separate start/continue thresholds, 1.5-second pre-roll, and a faster 0.9-second end pause.

## 2.0.0

- Added a draggable, always-on-top Siri-style floating voice orb for Windows and macOS.
- Samuel now starts listening automatically while the full dashboard remains hidden.
- Added live visual states: WAIT, READY, HEARING, THINK, SPEAK, OFF, and ERROR.
- Added 1.2 seconds of audio pre-roll so the beginning of a wake phrase is not cut off.
- Reuses the calibrated noise floor rather than recalibrating and losing speech on every listening cycle.
- Increased natural-pause tolerance and maximum phrase duration while keeping response latency low.
- Requests all recognition alternatives and selects the most complete plausible transcript.
- Added wake handling for both `Hey Samuel` and `Samuel`, with word-boundary protection.

## 1.6.0

- Replaced fixed seven-second microphone recordings with voice-activity and silence detection.
- Added a dedicated non-blocking speech queue so simultaneous replies cannot break text-to-speech.
- Prevented microphone recognition from transcribing Samuel's own voice output.
- Added automatic native Windows/macOS speech fallback when `pyttsx3` fails.
- Added full-volume English voice selection, speech status diagnostics, and a Settings `TEST VOICE` button.

## 1.5.0

- Added dynamic installed-app discovery for Windows and macOS.
- Windows discovery covers Start Menu shortcuts, registry App Paths, and Microsoft Store/Start apps.
- macOS discovery covers system, shared, and user Applications folders.
- Added exact, contained-name, and guarded fuzzy matching for app names and typing mistakes.
- Unknown names are never executed as shell commands; only discovered application targets may launch.

## 1.4.0

- Added native confirmed closing of the currently active window on Windows and macOS.
- Added a verified ChatGPT message workflow that opens the app, locates its input, types literal text, and submits it.
- Added `nvm` and `nope` cancellation phrases.
- Removed trailing `on my screen` text from visual-point targets.
- Prevented close and compound app commands from falling through to Google search.

## 1.3.0

- Added explicit current-screen capture and AI description without asking users to upload screenshots.
- Added direct handling for `analyze/check/describe my screen`, `what am I doing`, and `capture and tell me what you see`.
- Added typo normalization for common screen-analysis phrases.
- New full commands now replace stale pending confirmations.
- Expanded visual-open matching to understand `open ... on screen` without requiring `my` or `the`.

## 1.2.1

- Enlarged and centered the main desktop window, Settings, and AI setup dialog.
- Added display-aware sizing for lower-resolution and scaled Windows/macOS screens.
- Reorganized Settings into Assistant, AI connection, and System sections.
- Increased control spacing, entry height, activity-log size, and minimum window dimensions.

## 1.2.0

- Connected `open ... on my screen` commands to accessibility and AI screen vision.
- Added one-confirmation visual opening by double-clicking the center of the located target.
- Added native Windows and macOS pointer execution without downloading internet instructions.
- Refuses to click when the visual target cannot be located confidently.

## 1.1.3

- Fixed `point at` commands and flexible confirmation phrases such as `yes do it now`.
- Added ChatGPT app/website mappings for Windows and macOS.
- Normalized AI targets such as `ChatGPT desktop app` before execution.
- Prevented silent screen-point failures in debug-console mode and added clear launcher guidance.
- Corrected common `screen` misspellings and added end-to-end regression tests for the reported conversation.

## 1.1.2

- Added guarded typo correction for command verbs and known app/site names.
- Added punctuation, whitespace, mixed-case, and confirmation-phrase tests.
- Clamped AI vision bounding boxes to screenshot boundaries.

## 1.1.1

- Fixed internal prompt labels being spoken as conversational replies.
- Added local greetings and a clear local response to screen-privacy questions.
- Added validation that blocks empty or internal-label AI replies.

## 1.1.0

- Added platform-native themes, Windows DPI awareness, macOS LaunchAgent startup,
  unified start-at-login controls, privacy-settings shortcuts, and crash logging.
- Expanded GitHub packaging targets for Windows, Intel macOS, and Apple Silicon macOS.

## 1.0.0

- Consolidated voice and typed command interfaces.
- Added customizable assistant name, wake phrase, and AI model.
- Added Settings and Diagnostics screens.
- Added secure API-key add, replace, and remove controls.
- Added local command fallback and guided AI onboarding.
- Added explicit-only AI screen vision with visible notification.
- Added Accessibility-first target highlighting and confidence checking.
- Added Windows/macOS launchers, startup support, installer retries, and conditional dependencies.
- Added system-tray operation, action confirmation, tests, and public-repository safety files.

## 0.7.1

- Added the desktop text-command field and SEND button.

## 0.7.0

- Added explicit AI screenshot analysis and visual target highlighting.

## 0.6.2

- Removed conflicting SDK/keyring dependencies and used native credential storage.

## 0.6.0

- Added guided API-key onboarding.

## 0.5.0

- Added allow-listed AI action planning and confirmation.

## 0.4.0

- Added Windows/macOS project structure and automated tests.

## 0.3.0

- Added desktop UI, system tray, listening toggle, startup script, and screen pointing.

## 0.2.0

- Added pending-command memory and reliable Chrome discovery.

## 0.1.0

- Initial speech, text, app-opening, website, and search prototype.
