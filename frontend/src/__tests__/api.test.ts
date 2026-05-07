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
    expect(teams[0].canonical_name).toBe('France')
    expect(teams[1].canonical_name).toBe('Brazil')
    expect(teams[2].canonical_name).toBe('Morocco')
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
