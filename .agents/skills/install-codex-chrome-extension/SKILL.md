---
name: install-codex-chrome-extension
description: Install, download, unpack, preserve the required official ID, validate, and troubleshoot the Codex Chrome Extension. Use when a user asks for Install Codex Chrome Extension, the Codex Chrome plugin package, a loadable unpacked Codex extension, an official-ID build for hehggadaopoacecdllhhajmbjkdcmajg, CRX3 public-key extraction for this install flow, or Disconnected extension diagnostics.
metadata:
  version: "0.1.0"
---

# Install Codex Chrome Extension

## Default Codex Build

Use the bundled script for repeatable builds:

```bash
node scripts/install_chrome_extension.mjs build --output "<outputs-dir>"
```

Run commands from the `install-codex-chrome-extension` skill directory. Common locations are:

- Windows: `%USERPROFILE%\.codex\skills\install-codex-chrome-extension`
- macOS/Linux: `$HOME/.codex/skills/install-codex-chrome-extension`

By default this downloads the Codex Chrome Extension CRX, extracts the CRX3 ZIP payload, selects the public key that derives the official Codex extension ID, writes it to `manifest.json` as `key`, and creates:

- `codex-chrome-extension/`
- `codex-chrome-extension.zip`
- `codex-chrome-extension.crx`

For Codex, the extension ID is not configurable: use `hehggadaopoacecdllhhajmbjkdcmajg`. This ID must match the native messaging host allowlist, or the extension can show `Disconnected`.

Use the unpacked directory for local loading:

1. Open `chrome://extensions`.
2. Enable Developer mode.
3. Choose "Load unpacked".
4. Select the generated `codex-chrome-extension` directory.

## Build From Inputs

Build from an existing CRX:

```bash
node scripts/install_chrome_extension.mjs build --crx "<path-to-crx>" --output "<outputs-dir>"
```

The CRX3 tooling can support non-Codex experiments, but do not use another ID for the Codex install path. For advanced non-Codex use only:

```bash
node scripts/install_chrome_extension.mjs build --output "<outputs-dir>" --id "<extension-id>" --crx-url "<crx-url>" --project-name "<project-name>"
```

Use `--project-name codex-chrome-extension` for the Codex deliverable unless the user requests a different output name. Use `--strip-update-url` only when producing a non-Codex unpacked build that should not retain Chrome Web Store update metadata.

## Inspect a CRX

Inspect before trusting a CRX or when debugging ID mismatch:

```bash
node scripts/install_chrome_extension.mjs inspect --crx "<path-to-crx>"
```

For the Codex extension, expect:

- `signedHeaderId`: `hehggadaopoacecdllhhajmbjkdcmajg`
- `publicKeyCandidates`: one candidate equal to `hehggadaopoacecdllhhajmbjkdcmajg`

CRX3 packages can contain multiple public-key proofs. Do not blindly use the first key; choose the key whose SHA-256-derived Chrome extension ID matches the requested ID.

## Validate Output

After building, verify the unpacked output:

```powershell
node -e "const fs=require('fs'),crypto=require('crypto'); const m=JSON.parse(fs.readFileSync('<outputs-dir>/codex-chrome-extension/manifest.json','utf8')); const id=Array.from(crypto.createHash('sha256').update(Buffer.from(m.key,'base64')).digest().subarray(0,16),b=>((b>>4).toString(16)+(b&15).toString(16)).replace(/[0-9a-f]/g,c=>String.fromCharCode(97+parseInt(c,16)))).join(''); console.log({name:m.name,version:m.version,id});"
```

For Codex, the ID must be `hehggadaopoacecdllhhajmbjkdcmajg`.

Run the skill's unit tests after changing the script:

```bash
node --test tests/install_chrome_extension.test.mjs
```

## Platform Notes

The script supports Windows and macOS. It writes ZIP files with Node.js directly. It extracts ZIP payloads with PowerShell `Expand-Archive` on Windows and the system `unzip` command on macOS/Linux. If macOS extraction fails, check that `/usr/bin/unzip` is available.

## Disconnected Troubleshooting

If the Codex popup shows `Disconnected`, read `references/troubleshooting.md`.

The common cause after manual unpacking is that Chrome generated a different local extension ID because `manifest.key` was missing. Rebuild with this skill and reload the generated `codex-chrome-extension` directory.

If the ID is correct but communication still fails, check:

- Chrome is running.
- The selected Chrome profile has the extension installed and enabled.
- The native host manifest allows `chrome-extension://hehggadaopoacecdllhhajmbjkdcmajg/`.
- The Codex Chrome plugin was installed from the Codex plugin UI.

Do not claim that a fixed-ID unpacked build is an official signed CRX. It is an unpacked build with a stable ID. The official Web Store extension remains the safest install path when available.
