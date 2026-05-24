const vscode = require("vscode");

const START_KEY = "fiveHourLimit.startAt";
const PAUSED_AT_KEY = "fiveHourLimit.pausedAt";
const PAUSED_MS_KEY = "fiveHourLimit.pausedMs";
const DEFAULT_WINDOW_MINUTES = 300;

let statusBar;
let interval;

function getWindowMs() {
  const config = vscode.workspace.getConfiguration("fiveHourLimit");
  const minutes = config.get("windowMinutes", DEFAULT_WINDOW_MINUTES);
  return Math.max(1, Number(minutes) || DEFAULT_WINDOW_MINUTES) * 60 * 1000;
}

function formatDuration(ms) {
  const safeMs = Math.max(0, ms);
  const totalMinutes = Math.floor(safeMs / 60000);
  const hours = Math.floor(totalMinutes / 60);
  const minutes = totalMinutes % 60;
  return `${hours}h ${String(minutes).padStart(2, "0")}m`;
}

function getState(context) {
  return {
    startAt: context.globalState.get(START_KEY),
    pausedAt: context.globalState.get(PAUSED_AT_KEY),
    pausedMs: context.globalState.get(PAUSED_MS_KEY, 0),
  };
}

async function startWindow(context) {
  await context.globalState.update(START_KEY, Date.now());
  await context.globalState.update(PAUSED_AT_KEY, undefined);
  await context.globalState.update(PAUSED_MS_KEY, 0);
  updateStatus(context);
}

async function pauseTimer(context) {
  const state = getState(context);
  if (!state.startAt || state.pausedAt) {
    return;
  }
  await context.globalState.update(PAUSED_AT_KEY, Date.now());
  updateStatus(context);
}

async function resumeTimer(context) {
  const state = getState(context);
  if (!state.startAt || !state.pausedAt) {
    return;
  }
  const additionalPausedMs = Date.now() - state.pausedAt;
  await context.globalState.update(PAUSED_MS_KEY, state.pausedMs + additionalPausedMs);
  await context.globalState.update(PAUSED_AT_KEY, undefined);
  updateStatus(context);
}

function updateStatus(context) {
  const state = getState(context);
  if (!state.startAt) {
    statusBar.text = "$(clock) 5h: not started";
    statusBar.tooltip = "Start a local 5-hour tracking window.";
    statusBar.command = "fiveHourLimit.startWindow";
    statusBar.show();
    return;
  }

  const now = state.pausedAt || Date.now();
  const elapsedMs = Math.max(0, now - state.startAt - state.pausedMs);
  const windowMs = getWindowMs();
  const remainingMs = Math.max(0, windowMs - elapsedMs);
  const percentUsed = Math.min(100, Math.round((elapsedMs / windowMs) * 100));
  const pausedLabel = state.pausedAt ? " paused" : "";

  statusBar.text = `$(clock) 5h: ${formatDuration(remainingMs)} left`;
  statusBar.tooltip = [
    `5 Hour Limit Tracker${pausedLabel}`,
    `Used: ${formatDuration(elapsedMs)} (${percentUsed}%)`,
    `Remaining: ${formatDuration(remainingMs)}`,
    "Click to reset the local tracking window.",
  ].join("\n");
  statusBar.command = "fiveHourLimit.resetWindow";
  statusBar.show();
}

function activate(context) {
  statusBar = vscode.window.createStatusBarItem(vscode.StatusBarAlignment.Right, 100);
  context.subscriptions.push(statusBar);

  context.subscriptions.push(
    vscode.commands.registerCommand("fiveHourLimit.startWindow", () => startWindow(context)),
    vscode.commands.registerCommand("fiveHourLimit.resetWindow", () => startWindow(context)),
    vscode.commands.registerCommand("fiveHourLimit.pause", () => pauseTimer(context)),
    vscode.commands.registerCommand("fiveHourLimit.resume", () => resumeTimer(context))
  );

  interval = setInterval(() => updateStatus(context), 30000);
  context.subscriptions.push({ dispose: () => clearInterval(interval) });
  updateStatus(context);
}

function deactivate() {
  if (interval) {
    clearInterval(interval);
  }
}

module.exports = {
  activate,
  deactivate,
};
