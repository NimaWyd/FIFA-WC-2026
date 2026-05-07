import { renderHook, act, waitFor } from '@testing-library/react'
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
    mockPredict.mockRejectedValueOnce(new Error('API error'))
    const { result } = renderHook(() => usePredict())

    act(() => { result.current.predict(req) })

    await waitFor(() => {
      expect(result.current.error).toBe('API error')
      expect(result.current.loading).toBe(false)
    })
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
