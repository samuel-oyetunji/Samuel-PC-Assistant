# Contributing to Samuel PC Assistant

Thanks for helping improve Samuel.

## Before you start

1. Search existing issues before opening a new one.
2. Keep changes focused and avoid unrelated formatting rewrites.
3. Never include API keys, screenshots containing private data, voice recordings, or machine-specific settings.

## Local setup

```bash
python -m venv .venv
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
python -m unittest discover -s tests -v
```

Activate `.venv` using the command for your operating system before installing packages.

## Pull requests

- Explain the user-visible problem and the chosen fix.
- Add or update tests for behavior changes.
- Test the affected Windows or macOS path when possible.
- Keep command execution allow-listed and require confirmation for sensitive actions.
- Do not weaken credential storage, screen-capture privacy, or confidence checks.

By contributing, you agree that your contribution is licensed under the MIT License.
