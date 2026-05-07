# Frontend Test Suite Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Vitest-based test suite to the Next.js 14 frontend covering `api.ts`, `usePredict`, `useTeams`, `ProbabilityBars`, and `PredictButton`.

**Architecture:** Vitest + jsdom + @testing-library/react. API calls mocked at module level with `vi.mock`. `framer-motion` mocked per component test file to eliminate animation side-effects. All tests live in `frontend/src/__tests__/`. Since the code already exists, each task writes the test then verifies it passes (no implementation step needed).

**Tech Stack:** Vitest 1.x, @vitejs/plugin-react, @testing-library/react 16, @testing-library/user-event 14, @testing-library/jest-dom 6, jsdom

---

### Task 1: Install dependencies and configure Vitest

**Files:**
- Modify: `frontend/package.json`
- Create: `frontend/vitest.config.ts`
- Create: `frontend/src/__tests__/setup.ts`

- [ ] **Step 1: Install dev dependencies**

```bash
cd frontend
npm install -D vitest @vitejs/plugin-react @testing-library/react @testing-library/user-event @testing-library/jest-dom jsdom
```

Expected: packages added to `package.json` devDependencies, `node_modules` updated, no errors.

- [ ] **Step 2: Add test scripts to `frontend/package.json`**

In the `"scripts"` block, add:
```json
"test": "vitest",
"test:run": "vitest run"
```

- [ ] **Step 3: Create `frontend/vitest.config.ts`**

```ts
import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import path from 'path'

export default defineConfig({
  plugins: [react()],
  test: {
    environment: 'jsdom',
    globals: true,
    setupFiles: ['./src/__tests__/setup.ts'],
  },
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
})
```

- [ ] **Step 4: Create `frontend/src/__tests__/setup.ts`**

```ts
import '@testing-library/jest-dom'
import { vi } from 'vitest'

vi.mock('next/navigation', () => ({
  useRouter: () => ({ push: vi.fn(), replace: vi.fn(), prefetch: vi.fn() }),
  usePathname: () => '/',
  useSearchParams: () => ({ get: vi.fn() }),
}))
```

- [ ] **Step 5: Verify Vitest starts with no errors**

```bash
cd frontend && npm run test:run
```

Expected: exits with "No test files found" or similar — confirms the config is valid with no parse errors.

- [ ] **Step 6: Commit**

```bash
git add frontend/package.json frontend/package-lock.json frontend/vitest.config.ts frontend/src/__tests__/setup.ts
git commit -m "test: configure vitest for frontend (#40)"
```

---

### Task 2: Write api.ts tests

**Files:**
- Create: `frontend/src/__tests__/api.test.ts`

Note: `fetchTeams` uses a module-level `teamsCache` variable. Tests that need a clean cache call `vi.resetModules()` in `beforeEach` and import the module dynamically inside each test. `predict` and `fetchModelInfo` don't touch the cache so they import dynamically once.

- [ ] **Step 1: Create `frontend/src/__tests__/api.test.ts`**

```ts
import { describe, it, expect, vi, beforeEach } from 'vitest'

const mockFetch = vi.fn()
vi.stubGlobal('fetch', mockFetch)

function makeOk(data: unknown): Response {
  return { ok: true, status: 200, json: () => Promise.resolve(data) } as unknown as Response
}

function makeErr(status: number, body: unknown): Response {
  return { ok: false, status, json: () => Promise.resolve(body) } as unknown as Response
}

describe('predict', () => {
  beforeEach(() => mockFetch.mockReset())

  it('returns parsed response on success', async () => {
    const { predict } = await import('@/lib/api')
    const data = {
      home_team: 'Brazil',
      away_team: 'Argentina',
      probabilities: { home_win: 0.5, draw: 0.25, away_win: 0.25 },
    }
    mockFetch.mockResolvedValueOnce(makeOk(data))
    const result = await predict({ home_team: 'Brazil', away_team: 'Argentina', match_date: '2026-06-01' })
    expect(result).toEqual(data)
  })

  it('throws ApiError with detail message on non-200', async () => {
    const { predict } = await import('@/lib/api')
    mockFetch.mockResolvedValueOnce(makeErr(422, { detail: 'Team not found' }))
    await expect(
      predict({ home_team: 'X', away_team: 'Y', match_date: '2026-06-01' })
    ).rejects.toThrow('Team not found')
  })
})

describe('fetchTeams', () => {
  beforeEach(() => {
    vi.resetModules()
    mockFetch.mockReset()
  })

  it('returns teams sorted by confederation order then fifa_rank', async () => {
    const { fetchTeams } = await import('@/lib/api')
    const raw = [
      { canonical_name: 'Morocco', display_name: 'Morocco', confederation: 'CAF', fifa_rank: 12, aliases: [], is_known: true, default_metadata: {} },
      { canonical_name: 'Brazil', display_name: 'Brazil', confederation: 'CONMEBOL', fifa_rank: 1, aliases: [], is_known: true, default_metadata: {} },
      { canonical_name: 'France', display_name: 'France', confederation: 'UEFA', fifa_rank: 2, aliases: [], is_known: true, default_metadata: {} },
    ]
    mockFetch.mockResolvedValueOnce(makeOk(raw))
    const teams = await fetchTeams()
    expect(teams[0].canonical_name).toBe('France')    // UEFA = confOrder 0
    expect(teams[1].canonical_name).toBe('Brazil')    // CONMEBOL = confOrder 1
    expect(teams[2].canonical_name).toBe('Morocco')   // CAF = confOrder 3
  })

  it('caches results — fetch called only once for two calls', async () => {
    const { fetchTeams } = await import('@/lib/api')
    mockFetch.mockResolvedValue(makeOk([]))
    await fetchTeams()
    await fetchTeams()
    expect(mockFetch).toHaveBeenCalledTimes(1)
  })
})

describe('fetchModelInfo', () => {
  beforeEach(() => mockFetch.mockReset())

  it('returns model info on success', async () => {
    const { fetchModelInfo } = await import('@/lib/api')
    const info = { model_version: '1.0', model_type: 'ensemble' }
    mockFetch.mockResolvedValueOnce(makeOk(info))
    const result = await fetchModelInfo()
    expect(result).toEqual(info)
  })
})
```

- [ ] **Step 2: Run tests and verify they pass**

```bash
cd frontend && npm run test:run -- api.test.ts
```

Expected: 5 tests pass across 3 describe blocks.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/api.test.ts
git commit -m "test: add api.ts tests (#40)"
```

---

### Task 3: Write usePredict hook tests

**Files:**
- Create: `frontend/src/__tests__/usePredict.test.ts`

- [ ] **Step 1: Create `frontend/src/__tests__/usePredict.test.ts`**

```ts
import { renderHook, act } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { usePredict } from '@/hooks/usePredict'
import * as api from '@/lib/api'

vi.mock('@/lib/api')

const mockPredict = vi.mocked(api.predict)

const mockResponse = {
  home_team: 'Brazil',
  away_team: 'Argentina',
  match_date: '2026-06-01',
  probabilities: { home_win: 0.45, draw: 0.25, away_win: 0.30 },
  top_scorelines: [{ scoreline: '1-0', probability: 0.12 }],
  expected_goals: { home: 1.5, away: 1.1 },
  explanation: {
    elo_diff: 50, home_elo: 1800, away_elo: 1750,
    form_diff: 0.1, home_form: 0.7, away_form: 0.6,
    rank_diff: 3, home_rank: 1, away_rank: 4,
    elo_win_prob: 0.55, competition_weight: 1.0,
    is_same_confederation: true, data_note: '',
  },
  metadata: {},
}

const req = { home_team: 'Brazil', away_team: 'Argentina', match_date: '2026-06-01' }

describe('usePredict', () => {
  beforeEach(() => mockPredict.mockReset())

  it('starts with null result, false loading, null error', () => {
    const { result } = renderHook(() => usePredict())
    expect(result.current.result).toBeNull()
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sets loading=true while fetch is in-flight', async () => {
    let resolve!: (v: typeof mockResponse) => void
    mockPredict.mockReturnValue(new Promise(r => { resolve = r }))

    const { result } = renderHook(() => usePredict())
    act(() => { result.current.predict(req) })
    expect(result.current.loading).toBe(true)

    await act(async () => { resolve(mockResponse) })
  })

  it('sets result and clears loading on success', async () => {
    mockPredict.mockResolvedValue(mockResponse)
    const { result } = renderHook(() => usePredict())

    await act(async () => { await result.current.predict(req) })

    expect(result.current.result).toEqual(mockResponse)
    expect(result.current.loading).toBe(false)
    expect(result.current.error).toBeNull()
  })

  it('sets error string and clears loading on failure', async () => {
    mockPredict.mockRejectedValue(new Error('API error'))
    const { result } = renderHook(() => usePredict())

    await act(async () => { await result.current.predict(req) })

    expect(result.current.error).toBe('API error')
    expect(result.current.loading).toBe(false)
    expect(result.current.result).toBeNull()
  })

  it('reset clears result and error', async () => {
    mockPredict.mockResolvedValue(mockResponse)
    const { result } = renderHook(() => usePredict())

    await act(async () => { await result.current.predict(req) })
    act(() => { result.current.reset() })

    expect(result.current.result).toBeNull()
    expect(result.current.error).toBeNull()
  })
})
```

- [ ] **Step 2: Run tests and verify they pass**

```bash
cd frontend && npm run test:run -- usePredict.test.ts
```

Expected: 5 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/usePredict.test.ts
git commit -m "test: add usePredict hook tests (#40)"
```

---

### Task 4: Write useTeams hook tests

**Files:**
- Create: `frontend/src/__tests__/useTeams.test.ts`

- [ ] **Step 1: Create `frontend/src/__tests__/useTeams.test.ts`**

```ts
import { renderHook, waitFor } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import { useTeams } from '@/hooks/useTeams'
import * as api from '@/lib/api'

vi.mock('@/lib/api')

const mockFetchTeams = vi.mocked(api.fetchTeams)

const mockTeam = {
  canonical_name: 'Brazil',
  display_name: 'Brazil',
  confederation: 'CONMEBOL' as const,
  fifa_rank: 1,
  aliases: [],
  is_known: true,
  default_metadata: {},
}

describe('useTeams', () => {
  beforeEach(() => mockFetchTeams.mockReset())

  it('starts with loading=true and empty teams array', () => {
    mockFetchTeams.mockReturnValue(new Promise(() => {})) // never resolves
    const { result } = renderHook(() => useTeams())
    expect(result.current.loading).toBe(true)
    expect(result.current.teams).toEqual([])
    expect(result.current.error).toBeNull()
  })

  it('sets teams and loading=false after successful fetch', async () => {
    mockFetchTeams.mockResolvedValue([mockTeam])
    const { result } = renderHook(() => useTeams())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.teams).toEqual([mockTeam])
    expect(result.current.error).toBeNull()
  })

  it('sets error and loading=false on failed fetch', async () => {
    mockFetchTeams.mockRejectedValue(new Error('Network error'))
    const { result } = renderHook(() => useTeams())
    await waitFor(() => expect(result.current.loading).toBe(false))
    expect(result.current.error).toBe('Network error')
    expect(result.current.teams).toEqual([])
  })
})
```

- [ ] **Step 2: Run tests and verify they pass**

```bash
cd frontend && npm run test:run -- useTeams.test.ts
```

Expected: 3 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/useTeams.test.ts
git commit -m "test: add useTeams hook tests (#40)"
```

---

### Task 5: Write ProbabilityBars component tests

**Files:**
- Create: `frontend/src/__tests__/ProbabilityBars.test.tsx`

Note: `framer-motion` is mocked in this file. `motion.div` renders as a plain `<div>` so `initial`/`animate`/`transition` props are silently dropped — tests can query the rendered output normally.

- [ ] **Step 1: Create `frontend/src/__tests__/ProbabilityBars.test.tsx`**

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import React from 'react'
import ProbabilityBars from '@/components/ProbabilityBars'

vi.mock('framer-motion', () => ({
  motion: new Proxy({} as Record<string, unknown>, {
    get: (_: Record<string, unknown>, tag: string) =>
      ({ children, initial, animate, transition, ...rest }: Record<string, unknown>) =>
        React.createElement(tag, rest, children as React.ReactNode),
  }),
}))

describe('ProbabilityBars', () => {
  const baseProps = {
    probabilities: { home_win: 0.5, draw: 0.25, away_win: 0.25 },
    homeTeam: 'Brazil',
    awayTeam: 'Argentina',
  }

  it('renders home team, away team, and draw labels', () => {
    render(<ProbabilityBars {...baseProps} />)
    expect(screen.getByText('Brazil')).toBeInTheDocument()
    expect(screen.getByText('Argentina')).toBeInTheDocument()
    expect(screen.getByText('Draw')).toBeInTheDocument()
  })

  it('renders correct percentage values', () => {
    render(<ProbabilityBars {...baseProps} />)
    expect(screen.getByText('50.0%')).toBeInTheDocument()
    // draw and away are both 25.0%
    const quarters = screen.getAllByText('25.0%')
    expect(quarters).toHaveLength(2)
  })

  it('shows malformed warning when probabilities do not sum to 1', () => {
    render(
      <ProbabilityBars
        probabilities={{ home_win: 0.5, draw: 0.4, away_win: 0.4 }}
        homeTeam="Brazil"
        awayTeam="Argentina"
      />
    )
    expect(screen.getByText(/probabilities sum to/i)).toBeInTheDocument()
  })

  it('does not show malformed warning for valid probabilities', () => {
    render(<ProbabilityBars {...baseProps} />)
    expect(screen.queryByText(/probabilities sum to/i)).not.toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run tests and verify they pass**

```bash
cd frontend && npm run test:run -- ProbabilityBars.test.tsx
```

Expected: 4 tests pass.

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/ProbabilityBars.test.tsx
git commit -m "test: add ProbabilityBars component tests (#40)"
```

---

### Task 6: Write PredictButton component tests and verify full suite

**Files:**
- Create: `frontend/src/__tests__/PredictButton.test.tsx`

- [ ] **Step 1: Create `frontend/src/__tests__/PredictButton.test.tsx`**

```tsx
import { describe, it, expect, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import PredictButton from '@/components/PredictButton'

describe('PredictButton', () => {
  it('is disabled when loading=true', () => {
    render(<PredictButton loading={true} disabled={false} onClick={vi.fn()} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('is disabled when disabled=true', () => {
    render(<PredictButton loading={false} disabled={true} onClick={vi.fn()} />)
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('calls onClick when neither loading nor disabled', async () => {
    const onClick = vi.fn()
    render(<PredictButton loading={false} disabled={false} onClick={onClick} />)
    await userEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledOnce()
  })

  it('shows "Predicting…" text when loading', () => {
    render(<PredictButton loading={true} disabled={false} onClick={vi.fn()} />)
    expect(screen.getByText('Predicting…')).toBeInTheDocument()
  })

  it('shows "Predict Match" text when not loading', () => {
    render(<PredictButton loading={false} disabled={false} onClick={vi.fn()} />)
    expect(screen.getByText('Predict Match')).toBeInTheDocument()
  })
})
```

- [ ] **Step 2: Run the full test suite and verify all 22 tests pass**

```bash
cd frontend && npm run test:run
```

Expected output: 22 tests pass across 5 files (api: 5, usePredict: 5, useTeams: 3, ProbabilityBars: 4, PredictButton: 5).

- [ ] **Step 3: Commit**

```bash
git add frontend/src/__tests__/PredictButton.test.tsx
git commit -m "test: add PredictButton component tests, closes #40"
```
