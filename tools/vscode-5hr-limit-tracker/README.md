# 5 Hour Limit Tracker

Local VS Code status bar timer for a manual 5-hour usage window.

This does not read real Codex, Claude, ChatGPT, or API quota usage. Those services
do not expose quota data to this repository. Use this as a local tracker and reset
it when your real 5-hour window resets.

## Use

1. Open this folder in VS Code:

   ```powershell
   code tools/vscode-5hr-limit-tracker
   ```

2. Press `F5` to run the extension in an Extension Development Host.

3. Use the command palette:

   - `5 Hour Limit: Start Window`
   - `5 Hour Limit: Reset Window`
   - `5 Hour Limit: Pause Timer`
   - `5 Hour Limit: Resume Timer`

The status bar shows remaining time. Hover it to see elapsed time and percent
used.

## Install Locally

To package it as a `.vsix`, install `vsce` and package from this folder:

```powershell
npm install -g @vscode/vsce
cd tools/vscode-5hr-limit-tracker
vsce package
```

Then install the generated `.vsix` from VS Code.
