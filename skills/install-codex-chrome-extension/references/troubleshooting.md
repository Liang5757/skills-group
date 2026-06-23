# Codex Chrome Extension Troubleshooting

Use this reference when the Codex extension popup shows `Disconnected` or when a fixed-ID unpacked extension still cannot communicate with Codex.

## Required identifiers

- Extension ID: `hehggadaopoacecdllhhajmbjkdcmajg`
- Native host name: `com.openai.codexextension`
- Web Store URL: `https://chromewebstore.google.com/detail/codex/hehggadaopoacecdllhhajmbjkdcmajg`

## Expected native host state

The Codex Chrome plugin registers a Chrome Native Messaging Host.

On Windows, the plugin check normally expects:

- Manifest path: `%LOCALAPPDATA%\OpenAI\extension\com.openai.codexextension.json`
- Registry key: `HKCU\Software\Google\Chrome\NativeMessagingHosts\com.openai.codexextension`
- Allowed origin: `chrome-extension://hehggadaopoacecdllhhajmbjkdcmajg/`

On macOS, Chrome native messaging manifests commonly live under:

- User scope: `$HOME/Library/Application Support/Google/Chrome/NativeMessagingHosts/com.openai.codexextension.json`
- System scope: `/Library/Google/Chrome/NativeMessagingHosts/com.openai.codexextension.json`
- Allowed origin: `chrome-extension://hehggadaopoacecdllhhajmbjkdcmajg/`

Do not invent or hand-edit the native host registration as the first repair step. Prefer reinstalling the Chrome plugin from the Codex plugin UI when native host registration is missing or invalid.

## Diagnostic order

1. Check that Chrome is installed and running.
2. Check that the selected Chrome profile has the Codex extension installed and enabled.
3. Check that the extension ID is exactly `hehggadaopoacecdllhhajmbjkdcmajg`.
4. Check that the native host manifest exists and allows that origin.
5. If Chrome is running, the extension is enabled, and the manifest is correct but communication still fails, open a fresh Chrome window in the selected profile and retry once.
6. If it still fails, ask the user to reinstall the Chrome plugin from the Codex plugin UI.

## Common cause from unpacked builds

Loading a plain unpacked CRX payload without a `manifest.key` makes Chrome derive a new local extension ID. That new ID will not match the native host allowed origin, so the popup can show `Disconnected`.

Use `scripts/install_chrome_extension.mjs build` to inject the public key that corresponds to the official Codex extension ID before loading the unpacked directory.

## Useful plugin scripts

When the bundled Chrome plugin is available, its root usually contains these scripts:

```powershell
node scripts\chrome-is-running.js --json
node scripts\installed-browsers.js --json
node scripts\check-extension-installed.js --json
node scripts\check-native-host-manifest.js --json
```

Run them from the Chrome plugin root. Common cache locations are:

- Windows: `%USERPROFILE%\.codex\plugins\cache\openai-bundled\chrome\<version>`
- macOS/Linux: `$HOME/.codex/plugins/cache/openai-bundled/chrome/<version>`
