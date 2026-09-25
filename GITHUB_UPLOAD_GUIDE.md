# Uploading Samuel PC Assistant to GitHub

## Before uploading

1. Replace every `YOUR_GITHUB_USERNAME` placeholder in this repository.
2. Review `README.md`, `LICENSE`, and `SECURITY.md`.
3. Run the tests:

   ```bash
   python -m unittest discover -s tests -v
   ```

4. Confirm the folder contains no `.env`, API key, private screenshot, recording, or local settings file.

## Option 1: GitHub website

1. Create a new empty repository named `samuel-pc-assistant`.
2. Do not ask GitHub to add a README, `.gitignore`, or license; they are already included.
3. On the empty repository page, choose **uploading an existing file**.
4. Upload the **contents** of this folder, including the `.github` folder. Do not upload the outer ZIP as the source code.
5. Commit the files to `main`.

## Option 2: Git command line

Run these commands from inside the project folder, replacing the username:

```bash
git init
git add .
git commit -m "Initial release: Samuel PC Assistant v2.1.0"
git branch -M main
git remote add origin https://github.com/YOUR_GITHUB_USERNAME/samuel-pc-assistant.git
git push -u origin main
```

## Recommended repository settings

- Enable **Private vulnerability reporting** under Security settings.
- Protect `main` and require the **Tests** workflow before merging pull requests.
- Enable Dependabot alerts and secret scanning if available for the repository.
- Add topics such as `python`, `voice-assistant`, `desktop-assistant`, `windows`, `macos`, and `openai`.

## Create the v2.1.0 release

After the repository is uploaded:

```bash
git tag v2.1.0
git push origin v2.1.0
```

The tag triggers the build workflow. Its Windows and macOS outputs are unsigned test artifacts. Do not describe them as signed production installers.
