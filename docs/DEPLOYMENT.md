# Build & deployment guide

## One-time repository setup

1. Push this repository to GitHub (default branch `main`).
2. **Settings → Actions → General**: allow GitHub Actions. Workflow permissions can stay *Read repository contents*; `release.yml` requests `contents: write` only in its final `publish` job.
3. No secrets or personal access tokens are required — only the built-in `GITHUB_TOKEN`.
4. **Runner availability.** `windows-11-arm` and `macos-15-intel` are GitHub-hosted runners that are free for *public* repositories. For private repositories they may be unavailable or billed; if a job stays queued, check *Settings → Actions → Runners* and your plan. The release is intentionally **not** published when any of the four builds cannot run — never substitute an emulated runner, because the pipeline verifies that the runner's architecture matches the artifact label.
5. Optional: protect `main` and require the *CI* workflow.

## Releasing

```bash
# 1. make sure main is green
git tag v1.0.0
git push origin v1.0.0
```

or *Actions → Release → Run workflow* and enter `1.0.0`.

Pipeline (`.github/workflows/release.yml`):

| Job | What it does |
|---|---|
| `prepare` | Takes the tag (or manual input), validates Semantic Versioning, refuses to overwrite an existing release |
| `build` ×4 | Native runner → asserts runner arch → installs pinned deps → stamps version → runs tests → PyInstaller build → inspects binaries (PE machine type / Mach-O CPU type) → starts the packaged app headless (`--smoke-test`) → uploads the artifact |
| `publish` | Only if all four builds succeeded: confirms all four files exist, writes and re-verifies `SHA256SUMS`, creates the Release with generated notes |

Artifact names:

```
Disk-Analyzer-vX.Y.Z-Windows-x64.zip
Disk-Analyzer-vX.Y.Z-Windows-ARM64.zip
Disk-Analyzer-vX.Y.Z-macOS-Apple-Silicon-arm64.dmg
Disk-Analyzer-vX.Y.Z-macOS-Intel-x86_64.dmg
Disk-Analyzer-vX.Y.Z-SHA256SUMS.txt
```

Pre-release versions (`1.1.0-rc.1`) are published as GitHub pre-releases.

## What verification proves — and what it does not

Proved automatically for every target: the runner architecture, the `DiskAnalyzer.exe` PE machine type (`0x8664` vs `0xAA64`) and all bundled DLL/PYD files (Windows) or the Mach-O CPU types of the executable and libraries (macOS), presence of license/install notes/font/icon/Qt platform plugin, correct embedded version, and that the **frozen app starts and completes a scan + render** headless.

Not covered: interactive GUI behaviour on real displays, code signing, notarization, or Windows/macOS version matrices beyond what the runners provide.

## Code signing (optional, future)

Builds are unsigned. macOS: set the `CODESIGN_IDENTITY` environment variable (Developer ID Application certificate imported into the runner keychain) — `build_macos.py` then signs with it. Notarization (`xcrun notarytool`) is not implemented; do not describe unsigned builds as notarized or Gatekeeper-ready. Windows: add a signing step (e.g. Azure Trusted Signing / signtool) between *build* and *verify*.

## Updating pinned actions

All third-party actions are pinned to full commit SHAs (comment shows the tag). Dependabot (`.github/dependabot.yml`) opens weekly PRs for updates. The Python dependencies are pinned in `requirements*.txt`; PySide6 stays on 6.10.x because 6.11+ raises the minimum macOS version.
