# Frontend Test Suite — Design Spec
*Issue #40 | Date: 2026-05-07*

## Goal

Add a Vitest-based test suite to the Next.js 14 frontend covering the core prediction flow and key UI components, enabling safe refactoring and regression detection.

## Setup

**New dev dependencies:**
- `vitest`
- `@vitejs/plugin-react`
- `@testing-library/react`
- `@testing-library/user-event`
- `@testing-library/jest-dom`
- `jsdom`

**New config files:**
- `frontend/vitest.config.ts` — Vitest config using `jsdom` environment, aliasing `@/` to `src/`
- `frontend/src/__tests__/setup.ts` — global setup importing `@testing-library/jest-dom`

**New scripts in `package.json`:**
- `"test": "vitest"` — interactive watch mode
- `"test:run": "vitest run"` — single CI run

**Test directory:** `frontend/src/__tests__/`

## Test Files

| File | Subject | What's covered |
|------|---------|----------------|
| `api.test.ts` | `src/lib/api.ts` | `fetchTeams` (cache hit, sort by confederation + rank), `predict` (success response, `ApiError` on non-200), `fetchModelInfo`, timeout error message |
| `usePredict.test.ts` | `src/hooks/usePredict.ts` | initial state, loading=true during fetch, result set on success, error string set on failure, `reset()` clears state |
| `useTeams.test.ts` | `src/hooks/useTeams.ts` | loading state, teams array returned, second call hits cache (fetch called once) |
| `ProbabilityBars.test.tsx` | `src/components/ProbabilityBars.tsx` | percentage labels rendered correctly, malformed-sum warning shown when sum ≠ 1, team name labels present |
| `PredictButton.test.tsx` | `src/components/PredictButton.tsx` | button disabled when `loading=true` or `disabled=true`, fires `onClick` callback when neither is set |

## Mocking Strategy

- **`fetch`** — mocked via `vi.stubGlobal('fetch', vi.fn())` per test file; reset in `afterEach`
- **`framer-motion`** — mocked globally in setup to render a plain `<div>` (eliminates animation side-effects)
- **`next/navigation`** — stubbed in setup (`useRouter`, `usePathname` return safe defaults)

## Out of Scope

- E2E / integration tests against a running backend
- Tests for purely presentational components (`FlagIcon`, `MetadataBadge`, `ScorelineGrid`, etc.)
- CI pipeline integration (separate concern)
