[README.md](https://github.com/user-attachments/files/32656993/README.md)
# Samuel PC Assistant — Version 2.1.0

Samuel is an open-source desktop voice-assistant starter project for Windows and macOS.

[![Tests](https://github.com/samuel-oyetunj/samuel-pc-assistant/actions/workflows/tests.yml/badge.svg)](https://github.com/samuel-oyetunj/samuel-pc-assistant/actions/workflows/tests.yml)

## What this version can do

- Accept keyboard commands immediately.
- Start listening automatically in desktop mode, with an orb control to turn the microphone on or off.
- Speak its responses aloud.
- Recognize the short wake word “Hey.”
- Open common Windows/macOS apps and websites.
- Search Google.
- Ask whether Facebook, WhatsApp, or Instagram should open as an app or website.
- Remember a pending question so replies such as “website”, “yes”, and “cancel” work.
- Find Chrome using the operating system's normal app locations.
- Run as a desktop app with an ON/OFF listening button.
- Type commands and press Enter or SEND; typed commands do not require “Hey.”
- Customize the assistant name, wake phrase, and AI model from Settings.
- Add, replace, or remove the API key from Settings.
- Run built-in diagnostics for OS, Python, AI mode, wake phrase, and audio devices.
- Use Windows DPI awareness and native Vista styling, or macOS Aqua styling.
- Enable or disable start-at-login from Settings on both Windows and macOS.
- Open operating-system privacy permissions directly from Settings.
- Save unexpected startup failures to the platform's standard user log directory.
- Correct common typing mistakes in command verbs and known app/site names.
- Stay available from the system tray after its window is closed.
- Find named interface elements and circle them temporarily (Accessibility permission required).
- Reject unmapped programs safely instead of executing arbitrary commands.
- Understand `point at`, flexible confirmations such as `yes, do it now`, and ChatGPT app/website requests.
- Explain when screen highlighting is unavailable because the debug console was launched instead of the desktop UI.
- Locate a visible icon, file, or folder and double-click it after one explicit confirmation and a high-confidence match.
- Open the main window and dialogs at larger, centered, display-aware sizes with a reorganized Settings layout.
- Capture and describe the current screen after explicit commands such as `analyze my screen`.
- Treat a new command as a replacement for an unanswered confirmation instead of trapping the user in `yes/no`.
- Close the active window after confirmation and recognize `nvm` as cancellation.
- Open ChatGPT, verify its message field, type a requested message, and submit it after confirmation.
- Discover and open installed applications dynamically instead of requiring a hard-coded mapping for every app.
- Stop microphone recording automatically after speech ends instead of imposing a fixed seven-second delay.
- Queue voice replies on a dedicated worker, with native Windows/macOS speech fallback and a Settings voice test.
- Run as an automatically listening background assistant with a draggable Siri-style floating orb.
- Show live orb states for calibration, readiness, hearing, recognition, thinking, speaking, errors, and microphone-off.
- Preserve the start of spoken requests with a 1.2-second audio pre-roll and reuse calibrated background-noise levels.
- Select the most complete plausible speech-recognition result and wake on `Hey` without requiring the assistant name.
- Use fast OpenAI enhanced transcription when an API key is connected, with automatic Google recognition fallback.
- Tolerate common wake-name transcriptions such as `Hey Sam` and `Hey Samual` without accepting the name in the middle of unrelated speech.
- Keep listening for a natural 12-second follow-up window after Samuel replies, so the next sentence does not need another wake phrase.
- Show the exact ignored transcript and reason in Activity instead of failing silently.
- Use adaptive microphone sensitivity, a quieter keep-listening threshold, and a shorter 0.9-second end pause to avoid chopped sentences while responding sooner.

Voice identity verification, always-on offline wake-word detection, messages, calls,
contacts, and AI conversation are planned for later versions.

## Optional AI brain

Without an API key, Samuel uses its built-in command patterns. With an OpenAI API key,
unknown natural-language requests are sent to the Responses API. The model may only
propose an allow-listed action; Samuel validates it and asks for confirmation before
execution.

- Windows: run `configure_ai_windows.bat`, then restart Samuel.
- macOS: run `configure_ai_macos.command`, then restart Samuel.

Each user supplies their own key. The repository never contains a key. API usage may
incur charges on that user's OpenAI Platform account.

When an unknown command needs AI and no key is connected, the desktop app offers:

1. Never mind
2. Add an existing API key
3. Create/fund an account and add a key

Keys entered in the app are stored directly in Windows Credential Manager or macOS Keychain,
not in the repository. AI becomes available immediately without restarting.

The AI request uses Python's built-in HTTPS client, so installation does not depend on
a particular version of the OpenAI Python SDK.

When a key is connected, it is also used for `gpt-4o-mini-transcribe` voice recognition.
Without a key, Samuel automatically keeps using the free Google recognition fallback.

## AI screen vision

For an explicit command such as `Hey, point to the red car`, Samuel first checks
Accessibility data. If that fails and an API key is connected, it visibly announces
screen analysis, captures the primary display in memory, sends it to the OpenAI Responses
API, and highlights the returned bounding box.

Samuel does not write these screenshots to disk. Image inputs use API tokens and may
incur charges. Vision can be inaccurate, so visual opening requires explicit confirmation
and a sufficiently confident match before Samuel double-clicks an item.

## Supported systems

- Windows 10/11 (x64)
- macOS 12+ (Intel or Apple Silicon)
- Python 3.11–3.14

## Windows setup

1. Install **Python 3.11 (64-bit)** from python.org and select **Add python.exe to PATH**.
2. Extract this project to a normal folder such as your Desktop.
3. Double-click `setup_windows.bat` once.
4. Double-click `start_samuel.bat` whenever you want to run Samuel. No black terminal stays open.
5. Optionally run `enable_startup.bat` once to launch Samuel after Windows sign-in.
6. Test by saying `Hey, open calculator`.

Samuel starts listening automatically and hides the full dashboard. Wait until the floating orb says
`READY`, then speak naturally. Single-click the orb to turn listening on or off, drag it anywhere,
and double-click it to open the full dashboard.

If Windows asks for microphone permission, allow it in Windows Privacy settings.

## macOS setup

1. Install Python 3 from python.org if it is not already installed.
2. In Terminal, run `chmod +x setup_macos.command start_samuel.command` once.
3. Open `setup_macos.command`, then open `start_samuel.command`.
4. Allow Microphone and Accessibility permissions when macOS requests them.

The assistant UI, speech, websites, searches, common app launching, and accessibility-based
screen pointing work on both platforms. Screen pointing depends on the accessible names
provided by each app, so canvas/video/game content may still require a future AI-vision layer.

## Public GitHub safety

No API keys, voice samples, contacts, messages, or machine-specific paths are included.
Never commit `.env`, private configuration, or enrolled voice data.

## Development

```bash
python -m venv .venv
```

Activate the environment, then install dependencies:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

See [CONTRIBUTING.md](CONTRIBUTING.md) before opening a pull request. Report security
problems privately using the process in [SECURITY.md](SECURITY.md).

## Releases

Push a tag such as `v2.1.0` to start the Windows, Intel macOS, and Apple Silicon
macOS build workflow. These CI artifacts are unsigned test builds. Apple distribution
still requires your own Apple Developer signing identity, notarization credentials,
and testing on physical Intel and Apple Silicon Macs.

## Test commands

```text
Hey, open calculator
Hey, open Chrome
Hey, go to Facebook
Hey, search Google for Python classes
Hey, point to Recycle Bin
what can you do
```

## Safety design

Samuel can open verified applications discovered through operating-system app locations,
plus allow-listed websites. Spoken text is never executed as a terminal command. Screen
clicking and other sensitive desktop actions require confirmation and confidence checks.

## License

Released under the [MIT License](LICENSE).
